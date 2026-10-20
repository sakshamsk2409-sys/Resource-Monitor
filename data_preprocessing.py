"""Data Preprocessing Pipeline for System Resource Monitor Telemetry.

This module provides a reproducible, explainable, and rigorous data preparation pipeline
using Pandas and NumPy for the Data Visualization using Python (DVP) project.

Key capabilities:
- CSV loading and schema validation
- Timestamp parsing and chronological sorting
- Duplicate record and timestamp detection
- Missing-value audit by column
- Invalid numeric and range violation detection
- Sampling interval regularisation and time-gap analysis
- Feature engineering of derived metrics (GB, MB/s, KB/s, total bandwidth)
- Configurable rolling windows and Exponential Moving Averages (EMA)
- Preservation of raw data alongside cleaned data
- Generation of transparent, viva-ready preprocessing audit summaries
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import numpy as np
import pandas as pd

from telemetry_logger import SCHEMA_COLUMNS, COLUMN_METADATA


class PreprocessingValidationError(Exception):
    """Raised when an imported CSV file fails essential schema or content checks."""
    pass


class TelemetryPreprocessor:
    """Manages the end-to-end data preparation workflow for system telemetry."""

    def __init__(self):
        self.raw_df: Optional[pd.DataFrame] = None
        self.cleaned_df: Optional[pd.DataFrame] = None
        self.summary: Dict[str, Any] = {}
        self.source_path: Optional[str] = None

    def load_csv(self, filepath_or_buffer) -> pd.DataFrame:
        """Load telemetry data from a CSV file path or file-like object.
        
        Performs early validation of file readability, emptiness, and minimum columns.
        """
        if isinstance(filepath_or_buffer, (str, Path)):
            path = Path(filepath_or_buffer)
            self.source_path = str(path.resolve())
            if not path.is_file():
                raise PreprocessingValidationError(f"File not found: {path}")
            if path.stat().st_size == 0:
                raise PreprocessingValidationError(f"File is completely empty: {path}")
        else:
            self.source_path = "<buffer>"

        try:
            df = pd.read_csv(filepath_or_buffer)
        except Exception as e:
            raise PreprocessingValidationError(f"Failed to parse CSV file: {e}")

        if df.empty:
            raise PreprocessingValidationError("Dataset contains 0 rows of data.")

        # Strip whitespace from string headers
        df.columns = [str(c).strip() for c in df.columns]

        if "timestamp" not in df.columns:
            # Check if there is an alternative timestamp column
            possible_ts = [c for c in df.columns if "time" in c.lower() or "date" in c.lower()]
            if possible_ts:
                df = df.rename(columns={possible_ts[0]: "timestamp"})
            else:
                raise PreprocessingValidationError(
                    f"Dataset missing required 'timestamp' column. Found columns: {list(df.columns)}"
                )

        self.raw_df = df.copy()
        self.cleaned_df = None
        self.summary = {}
        return self.raw_df

    def validate_schema(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Inspect schema compliance against the documented telemetry standard."""
        actual_cols = list(df.columns)
        matched_standard = [c for c in actual_cols if c in SCHEMA_COLUMNS]
        missing_standard = [c for c in SCHEMA_COLUMNS if c not in actual_cols]
        custom_cols = [c for c in actual_cols if c not in SCHEMA_COLUMNS]

        return {
            "total_columns": len(actual_cols),
            "matched_standard_columns": matched_standard,
            "missing_standard_columns": missing_standard,
            "custom_columns": custom_cols,
            "has_cpu": any("cpu" in c for c in actual_cols),
            "has_ram": any("ram" in c or "mem" in c for c in actual_cols),
            "has_gpu": any("gpu" in c for c in actual_cols),
            "has_disk": any("disk" in c for c in actual_cols),
            "has_network": any("net" in c for c in actual_cols),
        }

    def preprocess(
        self,
        deduplicate_rows: bool = True,
        deduplicate_timestamps: str = "keep_first",  # 'keep_first', 'keep_last', 'none'
        rolling_window: int = 5,
        ema_span: Optional[int] = 5,
    ) -> pd.DataFrame:
        """Run the comprehensive cleaning, validation, and feature-engineering pipeline."""
        if self.raw_df is None:
            raise PreprocessingValidationError("No dataset loaded. Call load_csv() first.")

        df = self.raw_df.copy()
        orig_row_count = len(df)
        transformations: List[str] = []
        records_removed: List[Dict[str, Any]] = []
        invalid_readings: Dict[str, int] = {
            "unparseable_timestamps": 0,
            "invalid_percentages": 0,
            "negative_throughputs": 0,
            "negative_bytes": 0,
        }

        # -------------------------------------------------------------
        # 1. TIMESTAMP PARSING & SORTING
        # -------------------------------------------------------------
        df["parsed_timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        bad_ts_count = int(df["parsed_timestamp"].isna().sum())
        if bad_ts_count > 0:
            invalid_readings["unparseable_timestamps"] = bad_ts_count
            records_removed.append({
                "reason": "Unparseable timestamp",
                "count": bad_ts_count,
            })
            df = df.dropna(subset=["parsed_timestamp"])
            transformations.append(f"Dropped {bad_ts_count} rows with invalid timestamps")

        if df.empty:
            raise PreprocessingValidationError("All timestamp values in dataset were malformed.")

        # Sort chronologically
        df = df.sort_values(by="parsed_timestamp").reset_index(drop=True)
        transformations.append("Sorted records chronologically by timestamp")

        # -------------------------------------------------------------
        # 2. DUPLICATE DETECTION
        # -------------------------------------------------------------
        duplicate_rows_count = int(df.duplicated(subset=[c for c in df.columns if c != "parsed_timestamp"]).sum())
        if deduplicate_rows and duplicate_rows_count > 0:
            df = df.drop_duplicates(subset=[c for c in df.columns if c != "parsed_timestamp"]).reset_index(drop=True)
            records_removed.append({
                "reason": "Exact duplicate row",
                "count": duplicate_rows_count,
            })
            transformations.append(f"Deduplicated {duplicate_rows_count} exact duplicate rows")

        duplicate_ts_count = int(df.duplicated(subset=["parsed_timestamp"]).sum())
        if deduplicate_timestamps == "keep_first" and duplicate_ts_count > 0:
            df = df.drop_duplicates(subset=["parsed_timestamp"], keep="first").reset_index(drop=True)
            records_removed.append({
                "reason": "Duplicate timestamp (keep first)",
                "count": duplicate_ts_count,
            })
            transformations.append(f"Removed {duplicate_ts_count} duplicate timestamp collision rows")
        elif deduplicate_timestamps == "keep_last" and duplicate_ts_count > 0:
            df = df.drop_duplicates(subset=["parsed_timestamp"], keep="last").reset_index(drop=True)
            records_removed.append({
                "reason": "Duplicate timestamp (keep last)",
                "count": duplicate_ts_count,
            })
            transformations.append(f"Removed {duplicate_ts_count} duplicate timestamp collision rows")

        # -------------------------------------------------------------
        # 3. NUMERIC TYPE CONVERSION & RANGE VALIDATION
        # -------------------------------------------------------------
        percentage_cols = [c for c in df.columns if "percent" in c or "usage" in c and "bytes" not in c]
        for col in percentage_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            # Percentages must be 0.0 - 100.0
            invalid_mask = (df[col] < 0.0) | (df[col] > 100.0)
            inv_count = int(invalid_mask.sum())
            if inv_count > 0:
                invalid_readings["invalid_percentages"] += inv_count
                df.loc[invalid_mask, col] = np.nan
                transformations.append(f"Masked {inv_count} out-of-bounds percentage values in '{col}' to NaN")

        # Temperature columns: range check (-20 to 130 °C)
        temp_cols = [c for c in df.columns if "temp" in c]
        for col in temp_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            invalid_temp_mask = (df[col] < -20.0) | (df[col] > 135.0)
            inv_temp_count = int(invalid_temp_mask.sum())
            if inv_temp_count > 0:
                df.loc[invalid_temp_mask, col] = np.nan
                transformations.append(f"Masked {inv_temp_count} abnormal temperature values in '{col}' to NaN")

        # Throughput rate columns: must be >= 0
        rate_cols = [c for c in df.columns if "bytes_per_sec" in c or "rate" in c]
        for col in rate_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            neg_mask = df[col] < 0.0
            neg_count = int(neg_mask.sum())
            if neg_count > 0:
                invalid_readings["negative_throughputs"] += neg_count
                df.loc[neg_mask, col] = np.nan
                transformations.append(f"Masked {neg_count} negative rate values in '{col}' to NaN")

        # Byte counters: must be >= 0
        byte_cols = [c for c in df.columns if "_bytes" in c and "sec" not in c]
        for col in byte_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            neg_bytes = df[col] < 0
            neg_b_count = int(neg_bytes.sum())
            if neg_b_count > 0:
                invalid_readings["negative_bytes"] += neg_b_count
                df.loc[neg_bytes, col] = np.nan
                transformations.append(f"Masked {neg_b_count} negative byte readings in '{col}' to NaN")

        # -------------------------------------------------------------
        # 4. SAMPLING INTERVAL & TIME GAP ANALYSIS
        # -------------------------------------------------------------
        time_deltas = df["parsed_timestamp"].diff().dt.total_seconds().dropna()
        interval_stats = {}
        gaps: List[Dict[str, Any]] = []

        if len(time_deltas) > 0:
            median_dt = float(time_deltas.median())
            mean_dt = float(time_deltas.mean())
            std_dt = float(time_deltas.std()) if len(time_deltas) > 1 else 0.0
            # A gap is defined as an interval > 2.5x the median interval (minimum 3.0s)
            gap_threshold = max(3.0, median_dt * 2.5)

            gap_indices = time_deltas[time_deltas > gap_threshold].index
            for idx in gap_indices:
                prev_ts = str(df.loc[idx - 1, "parsed_timestamp"])
                curr_ts = str(df.loc[idx, "parsed_timestamp"])
                duration = round(float(time_deltas[idx]), 2)
                gaps.append({
                    "start": prev_ts,
                    "end": curr_ts,
                    "gap_sec": duration,
                })

            interval_stats = {
                "mean_interval_sec": round(mean_dt, 3),
                "median_interval_sec": round(median_dt, 3),
                "std_interval_sec": round(std_dt, 3),
                "min_interval_sec": round(float(time_deltas.min()), 3),
                "max_interval_sec": round(float(time_deltas.max()), 3),
                "gaps_count": len(gaps),
                "gaps": gaps[:10],  # Limit top 10 gaps in summary
            }

        # -------------------------------------------------------------
        # 5. FEATURE ENGINEERING (DERIVED METRICS)
        # -------------------------------------------------------------
        if "ram_used_bytes" in df.columns:
            df["ram_used_gb"] = (df["ram_used_bytes"] / (1024**3)).round(2)
        if "ram_available_bytes" in df.columns:
            df["ram_available_gb"] = (df["ram_available_bytes"] / (1024**3)).round(2)
        if "gpu_memory_used_bytes" in df.columns:
            df["gpu_memory_used_gb"] = (df["gpu_memory_used_bytes"] / (1024**3)).round(2)
        if "gpu_memory_total_bytes" in df.columns:
            df["gpu_memory_total_gb"] = (df["gpu_memory_total_bytes"] / (1024**3)).round(2)

        # Storage MB/s
        if "disk_read_bytes_per_sec" in df.columns:
            df["disk_read_mb_per_sec"] = (df["disk_read_bytes_per_sec"] / (1024 * 1024)).round(2)
        if "disk_write_bytes_per_sec" in df.columns:
            df["disk_write_mb_per_sec"] = (df["disk_write_bytes_per_sec"] / (1024 * 1024)).round(2)
        if "disk_read_mb_per_sec" in df.columns and "disk_write_mb_per_sec" in df.columns:
            df["disk_total_mb_per_sec"] = (
                df["disk_read_mb_per_sec"].fillna(0) + df["disk_write_mb_per_sec"].fillna(0)
            ).round(2)

        # Network KB/s and MB/s
        if "network_sent_bytes_per_sec" in df.columns:
            df["network_sent_kb_per_sec"] = (df["network_sent_bytes_per_sec"] / 1024).round(2)
        if "network_received_bytes_per_sec" in df.columns:
            df["network_recv_kb_per_sec"] = (df["network_received_bytes_per_sec"] / 1024).round(2)
        if "network_sent_kb_per_sec" in df.columns and "network_recv_kb_per_sec" in df.columns:
            df["network_total_kb_per_sec"] = (
                df["network_sent_kb_per_sec"].fillna(0) + df["network_recv_kb_per_sec"].fillna(0)
            ).round(2)

        transformations.append("Computed derived human-readable metrics (GB, MB/s, KB/s, total throughputs)")

        # -------------------------------------------------------------
        # 6. ROLLING AVERAGES & EXPONENTIAL MOVING AVERAGES (EMA)
        # -------------------------------------------------------------
        smooth_targets = [
            c for c in ["cpu_usage_percent", "ram_usage_percent", "cpu_temperature_c", "gpu_usage_percent"]
            if c in df.columns
        ]

        if rolling_window and rolling_window > 1:
            for col in smooth_targets:
                df[f"{col}_rolling_avg"] = df[col].rolling(window=rolling_window, min_periods=1).mean().round(2)
            transformations.append(f"Calculated {rolling_window}-sample rolling moving averages for key workloads")

        if ema_span and ema_span > 1:
            for col in smooth_targets:
                df[f"{col}_ema"] = df[col].ewm(span=ema_span, adjust=False).mean().round(2)
            transformations.append(f"Calculated exponential moving average (EMA, span={ema_span}) for key workloads")

        # -------------------------------------------------------------
        # 7. MISSING VALUE AUDIT
        # -------------------------------------------------------------
        missing_by_col = {}
        for col in df.columns:
            if col == "parsed_timestamp":
                continue
            null_count = int(df[col].isna().sum())
            if null_count > 0:
                missing_by_col[col] = {
                    "count": null_count,
                    "percent": round((null_count / len(df)) * 100, 2),
                }

        self.cleaned_df = df
        self.summary = {
            "source_path": self.source_path,
            "original_rows": orig_row_count,
            "final_rows": len(df),
            "retained_percentage": round((len(df) / orig_row_count) * 100, 2) if orig_row_count > 0 else 0.0,
            "duplicate_records_detected": duplicate_rows_count,
            "duplicate_timestamps_detected": duplicate_ts_count,
            "records_removed": records_removed,
            "invalid_readings_detected": invalid_readings,
            "sampling_interval_analysis": interval_stats,
            "missing_values_by_column": missing_by_col,
            "transformations_performed": transformations,
            "start_time": str(df["parsed_timestamp"].iloc[0]) if not df.empty else "N/A",
            "end_time": str(df["parsed_timestamp"].iloc[-1]) if not df.empty else "N/A",
            "duration_seconds": round(
                (df["parsed_timestamp"].iloc[-1] - df["parsed_timestamp"].iloc[0]).total_seconds(), 2
            ) if len(df) > 1 else 0.0,
        }

        return self.cleaned_df

    def get_summary_text(self) -> str:
        """Return a structured, readable markdown summary report suitable for viva review."""
        if not self.summary:
            return "No preprocessing summary available. Run preprocess() first."

        s = self.summary
        lines = []
        lines.append("## Preprocessing Pipeline Audit Summary")
        lines.append(f"- **Source Dataset**: `{s.get('source_path', 'Direct Buffer')}`")
        lines.append(f"- **Input Record Count**: {s['original_rows']:,}")
        lines.append(f"- **Final Cleaned Records**: {s['final_rows']:,} ({s['retained_percentage']}%)")
        lines.append(f"- **Observation Window**: {s.get('start_time')} to {s.get('end_time')} ({s.get('duration_seconds', 0):.1f} s)")

        lines.append("\n### Sampling Cadence & Time Gaps")
        sia = s.get("sampling_interval_analysis", {})
        if sia:
            lines.append(f"- **Nominal Interval**: Median = {sia.get('median_interval_sec')}s | Mean = {sia.get('mean_interval_sec')}s (Std = {sia.get('std_interval_sec')}s)")
            lines.append(f"- **Min / Max Interval**: {sia.get('min_interval_sec')}s / {sia.get('max_interval_sec')}s")
            lines.append(f"- **Irregular Gaps (>2.5x median)**: {sia.get('gaps_count')} detected")
            for gap in sia.get("gaps", []):
                lines.append(f"  - Gap of **{gap['gap_sec']}s** between `{gap['start']}` and `{gap['end']}`")
        else:
            lines.append("- Insufficient observations to calculate interval distribution.")

        lines.append("\n### Data Quality & Integrity Checks")
        lines.append(f"- **Exact Duplicate Rows**: {s.get('duplicate_records_detected', 0)}")
        lines.append(f"- **Timestamp Collisions**: {s.get('duplicate_timestamps_detected', 0)}")
        inv = s.get("invalid_readings_detected", {})
        for k, v in inv.items():
            lines.append(f"- **{k.replace('_', ' ').capitalize()}**: {v}")

        lines.append("\n### Missing Value Distribution")
        mvc = s.get("missing_values_by_column", {})
        if mvc:
            for col, info in mvc.items():
                lines.append(f"- `{col}`: {info['count']} missing ({info['percent']}%)")
        else:
            lines.append("- Complete data coverage across all retained columns.")

        lines.append("\n### Transformations Executed")
        for t in s.get("transformations_performed", []):
            lines.append(f"- {t}")

        return "\n".join(lines)

    def export_cleaned_csv(self, output_path: str) -> str:
        """Export the cleaned dataset to a CSV file."""
        if self.cleaned_df is None:
            raise ValueError("No cleaned dataset to export. Run preprocess() first.")
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        # Drop temporary datetime object for clean ISO string
        export_df = self.cleaned_df.copy()
        if "parsed_timestamp" in export_df.columns:
            export_df["timestamp"] = export_df["parsed_timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S.%f").str[:-3]
            export_df = export_df.drop(columns=["parsed_timestamp"])
        export_df.to_csv(out_p, index=False, encoding="utf-8")
        return str(out_p.resolve())

    def export_summary_json(self, output_path: str) -> str:
        """Export the preprocessing summary dictionary to a JSON file."""
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(self.summary, f, indent=2)
        return str(out_p.resolve())
