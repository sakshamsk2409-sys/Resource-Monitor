"""Statistical Computations and Dynamic Interpretation Engine.

This module computes descriptive statistics, percentiles, threshold breaches,
correlation matrices, sustained load episodes, and academic interpretations
derived strictly from empirical telemetry data.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd


DEFAULT_THRESHOLDS = {
    "cpu_usage_percent": 80.0,
    "ram_usage_percent": 85.0,
    "cpu_temperature_c": 80.0,
    "gpu_usage_percent": 85.0,
    "gpu_temperature_c": 80.0,
    "disk_total_mb_per_sec": 50.0,
    "network_total_kb_per_sec": 5000.0,
}


def compute_descriptive_stats(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Calculate mean, median, min, max, std, and key percentiles for all numeric metrics."""
    stats = {}
    if df is None or df.empty:
        return stats

    numeric_cols = df.select_dtypes(include=[np.number]).columns

    for col in numeric_cols:
        series = df[col].dropna()
        if series.empty:
            continue

        q = series.quantile([0.25, 0.50, 0.75, 0.95, 0.99]).to_dict()
        val_min = float(series.min())
        val_max = float(series.max())
        val_mean = float(series.mean())
        val_median = float(series.median())
        val_std = float(series.std()) if len(series) > 1 else 0.0

        # Peak timestamp if parsed_timestamp exists
        peak_timestamp = "N/A"
        if "parsed_timestamp" in df.columns:
            try:
                max_idx = series.idxmax()
                peak_timestamp = str(df.loc[max_idx, "parsed_timestamp"])
            except Exception:
                pass

        stats[col] = {
            "count": int(series.count()),
            "missing": int(df[col].isna().sum()),
            "mean": round(val_mean, 2),
            "median": round(val_median, 2),
            "min": round(val_min, 2),
            "max": round(val_max, 2),
            "std": round(val_std, 2),
            "p25": round(float(q.get(0.25, 0.0)), 2),
            "p75": round(float(q.get(0.75, 0.0)), 2),
            "p95": round(float(q.get(0.95, 0.0)), 2),
            "p99": round(float(q.get(0.99, 0.0)), 2),
            "peak_timestamp": peak_timestamp,
        }

    return stats


def compute_threshold_analysis(
    df: pd.DataFrame, thresholds: Optional[Dict[str, float]] = None
) -> Dict[str, Dict[str, Any]]:
    """Compute time spent, sample counts, and longest streaks above configurable thresholds."""
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS

    results = {}
    if df is None or df.empty:
        return results

    total_rows = len(df)
    has_dt = "parsed_timestamp" in df.columns and total_rows > 1
    total_duration_sec = 0.0
    if has_dt:
        total_duration_sec = (df["parsed_timestamp"].iloc[-1] - df["parsed_timestamp"].iloc[0]).total_seconds()
        avg_sample_dt = max(0.1, total_duration_sec / max(1, total_rows - 1))
    else:
        avg_sample_dt = 1.0

    for metric, thresh_val in thresholds.items():
        if metric not in df.columns:
            continue

        series = df[metric].dropna()
        if series.empty:
            continue

        breach_mask = df[metric] > thresh_val
        breach_count = int(breach_mask.sum())
        breach_pct = round((breach_count / total_rows) * 100, 2)
        est_duration_sec = round(breach_count * avg_sample_dt, 1)

        # Calculate longest contiguous streak above threshold
        streak = 0
        max_streak = 0
        for val in breach_mask:
            if val:
                streak += 1
                if streak > max_streak:
                    max_streak = streak
            else:
                streak = 0

        results[metric] = {
            "threshold": thresh_val,
            "samples_above": breach_count,
            "percent_time_above": breach_pct,
            "est_duration_seconds": est_duration_sec,
            "longest_streak_samples": max_streak,
            "longest_streak_seconds": round(max_streak * avg_sample_dt, 1),
        }

    return results


def compute_correlations(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute Pearson correlation matrix and identify notable pairwise relationships."""
    results = {"matrix": {}, "notable_pairs": []}
    if df is None or df.empty:
        return results

    # Focus on primary telemetry metrics to avoid redundant multicollinear features
    candidate_cols = [
        "cpu_usage_percent",
        "cpu_temperature_c",
        "ram_usage_percent",
        "gpu_usage_percent",
        "gpu_temperature_c",
        "disk_read_mb_per_sec",
        "disk_write_mb_per_sec",
        "disk_total_mb_per_sec",
        "network_sent_kb_per_sec",
        "network_recv_kb_per_sec",
        "network_total_kb_per_sec",
        "process_count",
    ]
    present_cols = [c for c in candidate_cols if c in df.columns and df[c].dropna().nunique() > 1]

    if len(present_cols) < 2:
        return results

    corr_df = df[present_cols].corr(method="pearson").round(3)
    results["matrix"] = corr_df.to_dict()

    notable = []
    seen = set()
    for col_a in present_cols:
        for col_b in present_cols:
            if col_a == col_b:
                continue
            pair_key = tuple(sorted([col_a, col_b]))
            if pair_key in seen:
                continue
            seen.add(pair_key)

            r_val = corr_df.loc[col_a, col_b]
            if np.isnan(r_val):
                continue

            abs_r = abs(r_val)
            if abs_r >= 0.40:
                strength = "Strong" if abs_r >= 0.70 else "Moderate"
                direction = "Positive" if r_val > 0 else "Inverse"
                notable.append({
                    "col1": col_a,
                    "col2": col_b,
                    "correlation": float(r_val),
                    "strength": strength,
                    "direction": direction,
                })

    notable.sort(key=lambda x: abs(x["correlation"]), reverse=True)
    results["notable_pairs"] = notable
    return results


def detect_sustained_periods_and_anomalies(df: pd.DataFrame) -> Dict[str, Any]:
    """Detect sustained workload periods and 3-sigma statistical spikes."""
    findings = {
        "sustained_cpu_periods": [],
        "sustained_ram_periods": [],
        "thermal_spikes": [],
        "io_bursts": [],
    }

    if df is None or len(df) < 5:
        return findings

    has_ts = "parsed_timestamp" in df.columns

    # 1. Sustained CPU (>75% for >= 3 consecutive samples)
    if "cpu_usage_percent" in df.columns:
        cpu = df["cpu_usage_percent"].fillna(0)
        start_idx = None
        for i, val in enumerate(cpu):
            if val >= 75.0:
                if start_idx is None:
                    start_idx = i
            else:
                if start_idx is not None and (i - start_idx) >= 3:
                    findings["sustained_cpu_periods"].append({
                        "start_idx": start_idx,
                        "end_idx": i - 1,
                        "samples": i - start_idx,
                        "start_time": str(df.loc[start_idx, "parsed_timestamp"]) if has_ts else f"Sample {start_idx}",
                        "end_time": str(df.loc[i - 1, "parsed_timestamp"]) if has_ts else f"Sample {i-1}",
                        "peak_usage": round(float(cpu.iloc[start_idx:i].max()), 1),
                    })
                start_idx = None
        if start_idx is not None and (len(cpu) - start_idx) >= 3:
            findings["sustained_cpu_periods"].append({
                "start_idx": start_idx,
                "end_idx": len(cpu) - 1,
                "samples": len(cpu) - start_idx,
                "start_time": str(df.loc[start_idx, "parsed_timestamp"]) if has_ts else f"Sample {start_idx}",
                "end_time": str(df.loc[len(cpu) - 1, "parsed_timestamp"]) if has_ts else f"Sample {len(cpu)-1}",
                "peak_usage": round(float(cpu.iloc[start_idx:].max()), 1),
            })

    # 2. Thermal spikes (Temp > mean + 2.5 * std or > 85°C)
    if "cpu_temperature_c" in df.columns:
        temp = df["cpu_temperature_c"].dropna()
        if not temp.empty:
            t_mean = temp.mean()
            t_std = temp.std() if len(temp) > 1 else 0.0
            spike_threshold = max(80.0, t_mean + 2.5 * t_std) if t_std > 2.0 else 82.0
            spikes = df[df["cpu_temperature_c"] >= spike_threshold]
            for idx, row in spikes.head(5).iterrows():
                findings["thermal_spikes"].append({
                    "timestamp": str(row["parsed_timestamp"]) if has_ts else f"Index {idx}",
                    "temperature": round(float(row["cpu_temperature_c"]), 1),
                    "cpu_usage": round(float(row.get("cpu_usage_percent", 0.0)), 1),
                })

    # 3. I/O bursts (Disk throughput > 3-sigma above mean)
    disk_col = "disk_total_mb_per_sec" if "disk_total_mb_per_sec" in df.columns else None
    if disk_col and not df[disk_col].dropna().empty:
        d_series = df[disk_col].dropna()
        d_mean = d_series.mean()
        d_std = d_series.std() if len(d_series) > 1 else 0.0
        if d_std > 1.0:
            burst_mask = df[disk_col] > (d_mean + 3 * d_std)
            bursts = df[burst_mask]
            for idx, row in bursts.head(5).iterrows():
                findings["io_bursts"].append({
                    "timestamp": str(row["parsed_timestamp"]) if has_ts else f"Index {idx}",
                    "disk_mb_s": round(float(row[disk_col]), 2),
                })

    return findings


def generate_interpretations(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate analytical explanations and chart-specific narratives from computed stats."""
    if df is None or df.empty:
        return {"executive_summary": ["No data available for analytical interpretation."]}

    stats = compute_descriptive_stats(df)
    thresholds = compute_threshold_analysis(df)
    correlations = compute_correlations(df)
    anomalies = detect_sustained_periods_and_anomalies(df)

    interpretations = {}
    exec_summary = []

    # -----------------------------------------------------------------
    # 1. CPU WORKLOAD INTERPRETATION
    # -----------------------------------------------------------------
    cpu_stat = stats.get("cpu_usage_percent")
    if cpu_stat:
        mean_u = cpu_stat["mean"]
        max_u = cpu_stat["max"]
        p95_u = cpu_stat["p95"]
        peak_t = cpu_stat["peak_timestamp"]
        thresh_info = thresholds.get("cpu_usage_percent", {})
        high_pct = thresh_info.get("percent_time_above", 0.0)

        # Trend estimation using simple linear regression slope
        series = df["cpu_usage_percent"].dropna()
        if len(series) > 3:
            x = np.arange(len(series))
            slope, _ = np.polyfit(x, series.values, 1)
            trend_desc = "rising over time" if slope > 0.05 else ("gradually declining" if slope < -0.05 else "fluctuating steadily without persistent drift")
        else:
            trend_desc = "observed across a brief sample window"

        cpu_text = (
            f"Mean CPU utilization was **{mean_u}%** (median {cpu_stat['median']}%, std dev {cpu_stat['std']}%), "
            f"with a maximum peak of **{max_u}%** observed at `{peak_t}`. The 95th percentile stood at **{p95_u}%**. "
            f"The overall utilization trend is {trend_desc}. "
        )
        if high_pct > 0:
            cpu_text += (
                f"The system spent **{high_pct}%** of recording time ({thresh_info.get('est_duration_seconds', 0)}s) "
                f"exceeding the high-load threshold of {thresh_info.get('threshold')}%. "
                f"The longest continuous heavy workload interval lasted {thresh_info.get('longest_streak_seconds', 0)}s."
            )
        else:
            cpu_text += "CPU utilization remained safely within typical non-saturating bounds throughout the test run."

        interpretations["cpu"] = cpu_text
        exec_summary.append(f"CPU Load: Average {mean_u}%, Peak {max_u}% at {peak_t}.")

    # -----------------------------------------------------------------
    # 2. RAM ALLOCATION INTERPRETATION
    # -----------------------------------------------------------------
    ram_stat = stats.get("ram_usage_percent")
    if ram_stat:
        ram_mean = ram_stat["mean"]
        ram_max = ram_stat["max"]
        ram_min = ram_stat["min"]
        delta_ram = round(ram_max - ram_min, 1)

        ram_used_gb_stat = stats.get("ram_used_gb")
        gb_clause = f" (peaking at **{ram_used_gb_stat['max']} GB**)" if ram_used_gb_stat else ""

        if delta_ram < 3.0:
            ram_behavior = "remained remarkably static, indicating stable resident memory allocation without dynamic churn."
        elif delta_ram > 15.0:
            ram_behavior = f"exhibited substantial dynamic variation ({delta_ram}% swing), reflecting active working-set expansion{gb_clause}."
        else:
            ram_behavior = f"displayed moderate memory allocation shifts ({delta_ram}% variation) during active execution."

        ram_text = (
            f"Physical memory usage averaged **{ram_mean}%** (min {ram_min}%, max {ram_max}%){gb_clause}. "
            f"RAM consumption {ram_behavior} "
        )
        if ram_max > 85.0:
            ram_text += "Approaching high memory capacity thresholds suggests potential page-file pressure during high workloads."
        else:
            ram_text += "Sufficient headroom was maintained throughout, minimizing risks of paging or OS memory starvation."

        interpretations["ram"] = ram_text
        exec_summary.append(f"RAM Usage: Average {ram_mean}%, Range [{ram_min}% - {ram_max}%].")

    # -----------------------------------------------------------------
    # 3. THERMAL DYNAMICS INTERPRETATION
    # -----------------------------------------------------------------
    temp_stat = stats.get("cpu_temperature_c")
    if temp_stat:
        t_mean = temp_stat["mean"]
        t_max = temp_stat["max"]
        t_peak_time = temp_stat["peak_timestamp"]

        temp_text = (
            f"CPU package temperature averaged **{t_mean} °C**, reaching a maximum temperature of **{t_max} °C** "
            f"at `{t_peak_time}` (95th percentile: **{temp_stat['p95']} °C**). "
        )
        if t_max >= 85.0:
            temp_text += (
                f"Peak temperatures reached the upper thermal operating boundary (>=85 °C). "
                f"Thermal throttling mitigation was likely engaged by the processor power management firmware."
            )
        elif t_max >= 75.0:
            temp_text += "Thermal profile remained elevated but controlled beneath critical manufacturer trip points."
        else:
            temp_text += "Operating temperatures remained well within optimal cooling limits with robust thermal headroom."

        interpretations["temperature"] = temp_text
        exec_summary.append(f"Thermal Profile: CPU Mean {t_mean} °C, Max {t_max} °C.")
    else:
        interpretations["temperature"] = "CPU thermal telemetry was unavailable on the host sensor interface."

    # -----------------------------------------------------------------
    # 4. GPU PERFORMANCE INTERPRETATION
    # -----------------------------------------------------------------
    gpu_stat = stats.get("gpu_usage_percent")
    if gpu_stat and gpu_stat["count"] > 0:
        gpu_mean = gpu_stat["mean"]
        gpu_max = gpu_stat["max"]
        gpu_temp_stat = stats.get("gpu_temperature_c")
        gtemp_clause = f" with a maximum die temperature of **{gpu_temp_stat['max']} °C**" if gpu_temp_stat else ""
        vram_stat = stats.get("gpu_memory_used_gb")
        vram_clause = f", consuming up to **{vram_stat['max']} GB** of VRAM" if vram_stat else ""

        interpretations["gpu"] = (
            f"Primary GPU utilization averaged **{gpu_mean}%** with burst peak activity of **{gpu_max}%**{gtemp_clause}{vram_clause}. "
            f"The graphics pipeline operated predominantly in a {'compute-intensive' if gpu_mean > 50 else 'light/idle desktop'} state."
        )
        exec_summary.append(f"GPU Utilization: Mean {gpu_mean}%, Peak {gpu_max}%.")
    else:
        interpretations["gpu"] = "Dedicated GPU telemetry was not recorded or no compatible accelerator was actively polled."

    # -----------------------------------------------------------------
    # 5. STORAGE & NETWORK I/O INTERPRETATION
    # -----------------------------------------------------------------
    d_read_stat = stats.get("disk_read_mb_per_sec")
    d_write_stat = stats.get("disk_write_mb_per_sec")
    if d_read_stat and d_write_stat:
        d_read_peak = d_read_stat["max"]
        d_write_peak = d_write_stat["max"]
        io_dominant = "read-heavy" if d_read_stat["mean"] > d_write_stat["mean"] else "write-heavy"

        d_text = (
            f"Disk throughput exhibited a **{io_dominant}** pattern. "
            f"Peak read throughput reached **{d_read_peak} MB/s** (average {d_read_stat['mean']} MB/s), "
            f"while peak write throughput hit **{d_write_peak} MB/s** (average {d_write_stat['mean']} MB/s). "
        )
        if max(d_read_peak, d_write_peak) > 50.0:
            d_text += "High-burst storage transactions were observed, typical of active application initialization or file operations."
        else:
            d_text += "Storage subsystem activity was modest and non-saturating."
        interpretations["storage"] = d_text
        exec_summary.append(f"Storage I/O: Peak Read {d_read_peak} MB/s, Peak Write {d_write_peak} MB/s.")

    net_sent_stat = stats.get("network_sent_kb_per_sec")
    net_recv_stat = stats.get("network_recv_kb_per_sec")
    if net_sent_stat and net_recv_stat:
        net_text = (
            f"Network bandwidth traffic peaked at **{net_recv_stat['max']} KB/s** inbound (download) "
            f"and **{net_sent_stat['max']} KB/s** outbound (upload), with average throughputs of "
            f"{net_recv_stat['mean']} KB/s and {net_sent_stat['mean']} KB/s respectively."
        )
        interpretations["network"] = net_text

    # -----------------------------------------------------------------
    # 6. CORRELATION & CO-VARIATION INTERPRETATION
    # -----------------------------------------------------------------
    notable = correlations.get("notable_pairs", [])
    if notable:
        corr_items = []
        for p in notable[:4]:
            c1_clean = p["col1"].replace("_", " ")
            c2_clean = p["col2"].replace("_", " ")
            corr_items.append(
                f"**{p['strength']} {p['direction']} Correlation** (r = {p['correlation']:+.2f}) between `{c1_clean}` and `{c2_clean}`"
            )
        cross_text = (
            "Empirical multi-variable correlation analysis revealed:\n- "
            + "\n- ".join(corr_items)
            + "\n\n*Methodological Note: Statistical correlation documents co-variation in empirical readings but does not imply unidirectional causality.*"
        )
    else:
        cross_text = (
            "Cross-resource correlation coefficients across tracked metrics remained modest (|r| < 0.40), "
            "indicating relatively independent subsystem utilization during the monitored timeframe."
        )
    interpretations["cross_resource"] = cross_text

    interpretations["executive_summary"] = exec_summary
    return interpretations
