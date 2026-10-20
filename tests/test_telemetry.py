"""Comprehensive Test Suite for System Resource Monitor Telemetry & Analytics.

Tests cover:
- CSV schema definitions, column ordering, and metadata
- Instantaneous disk and network throughput rate calculations
- Counter resets, initial observations, and missing-sensor representation
- TelemetryLogger lifecycle (start, pause, resume, stop)
- Data preprocessing pipeline, range validation, duplicate handling, and time gaps
- Descriptive statistics, threshold breaches, and Pearson correlation matrices
- Data-driven interpretation narratives
- Offline rule-based diagnostics
- HTML and JSON analytics report generation
"""

import os
import io
import time
import shutil
import unittest
import numpy as np
import pandas as pd

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from telemetry_logger import TelemetrySampler, TelemetryLogger, SCHEMA_COLUMNS, COLUMN_METADATA
from data_preprocessing import TelemetryPreprocessor, PreprocessingValidationError
from telemetry_statistics import (
    compute_descriptive_stats,
    compute_threshold_analysis,
    compute_correlations,
    detect_sustained_periods_and_anomalies,
    generate_interpretations,
)
from ai_insights import AIInsightsManager
from chatbot_page import build_local_response
from report_exporter import export_analytics_report


class TestTelemetrySchemaAndSampling(unittest.TestCase):
    """Test telemetry sampling, schema adherence, and rate calculations."""

    def test_schema_columns_count_and_types(self):
        self.assertIn("timestamp", SCHEMA_COLUMNS)
        self.assertIn("cpu_usage_percent", SCHEMA_COLUMNS)
        self.assertIn("ram_used_bytes", SCHEMA_COLUMNS)
        self.assertIn("disk_read_bytes_per_sec", SCHEMA_COLUMNS)
        self.assertIn("network_sent_bytes_per_sec", SCHEMA_COLUMNS)
        self.assertEqual(len(SCHEMA_COLUMNS), len(COLUMN_METADATA))

    def test_sampler_missing_values_representation(self):
        sampler = TelemetrySampler()
        record = sampler.sample()
        # Verify that all schema keys are present in sample record
        for col in SCHEMA_COLUMNS:
            self.assertIn(col, record)

        # First sample cannot compute rates since no elapsed delta time exists
        self.assertIsNone(record["disk_read_bytes_per_sec"])
        self.assertIsNone(record["network_sent_bytes_per_sec"])

    def test_sampler_rate_calculation_on_second_sample(self):
        sampler = TelemetrySampler()
        sampler.sample()
        time.sleep(0.1)
        record2 = sampler.sample()

        # Rates should now either be non-negative float numbers or None if counters unavailable
        if record2["disk_read_bytes_per_sec"] is not None:
            self.assertGreaterEqual(record2["disk_read_bytes_per_sec"], 0.0)
        if record2["network_sent_bytes_per_sec"] is not None:
            self.assertGreaterEqual(record2["network_sent_bytes_per_sec"], 0.0)

    def test_counter_reset_does_not_emit_negative_throughput(self):
        sampler = TelemetrySampler()
        sampler._last_time = time.time() - 1.0

        # Create dummy counters
        class MockCounter:
            def __init__(self, r, w):
                self.read_bytes = r
                self.write_bytes = w
                self.bytes_sent = r
                self.bytes_recv = w

        sampler._last_disk = MockCounter(1000000, 1000000)
        sampler._last_net = MockCounter(1000000, 1000000)

        # Next sample has smaller cumulative counter (simulating counter reset or reboot)
        record = sampler.sample()
        # Should not be negative!
        if record["disk_read_bytes_per_sec"] is not None:
            self.assertGreaterEqual(record["disk_read_bytes_per_sec"], 0.0)
        if record["network_sent_bytes_per_sec"] is not None:
            self.assertGreaterEqual(record["network_sent_bytes_per_sec"], 0.0)


class TestTelemetryLoggerLifecycle(unittest.TestCase):
    """Test TelemetryLogger start, pause, resume, stop and file persistence."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.test_dir = os.path.join("data", "test_scratch")
        os.makedirs(self.test_dir, exist_ok=True)
        self.test_csv = os.path.join(self.test_dir, "test_log.csv")
        if os.path.exists(self.test_csv):
            os.remove(self.test_csv)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_logger_lifecycle_and_headers(self):
        logger = TelemetryLogger()
        out_path = logger.start_logging(self.test_csv, interval_sec=0.05)
        self.assertTrue(os.path.exists(out_path))

        # Spin Qt event loop briefly to log records
        t0 = time.time()
        while time.time() - t0 < 0.2:
            self.app.processEvents()
            time.sleep(0.01)

        self.assertGreaterEqual(logger.record_count, 1)

        # Pause
        logger.pause_logging()
        self.assertTrue(logger.is_paused)
        count_paused = logger.record_count

        t0 = time.time()
        while time.time() - t0 < 0.1:
            self.app.processEvents()
            time.sleep(0.01)

        self.assertEqual(logger.record_count, count_paused)

        # Resume
        logger.resume_logging()
        self.assertTrue(logger.is_recording)

        t0 = time.time()
        while time.time() - t0 < 0.15:
            self.app.processEvents()
            time.sleep(0.01)

        self.assertGreater(logger.record_count, count_paused)

        # Stop
        logger.stop_logging()
        self.assertTrue(logger.is_stopped)

        # Verify file contents
        with open(self.test_csv, "r", encoding="utf-8") as f:
            lines = f.readlines()

        self.assertGreaterEqual(len(lines), 2)
        # Verify header is strictly SCHEMA_COLUMNS
        header_cols = [c.strip() for c in lines[0].split(",")]
        self.assertEqual(header_cols, SCHEMA_COLUMNS)


class TestDataPreprocessingPipeline(unittest.TestCase):
    """Test Data Preprocessor loading, validation, range masking, and derived metrics."""

    def test_empty_csv_raises_error(self):
        preprocessor = TelemetryPreprocessor()
        with self.assertRaises(PreprocessingValidationError):
            preprocessor.load_csv(io.StringIO(""))

    def test_missing_timestamp_raises_error(self):
        preprocessor = TelemetryPreprocessor()
        bad_csv = "cpu_usage_percent,ram_usage_percent\n50.0,60.0"
        with self.assertRaises(PreprocessingValidationError):
            preprocessor.load_csv(io.StringIO(bad_csv))

    def test_preprocessing_range_validation_and_deduplication(self):
        raw_csv = """timestamp,cpu_usage_percent,cpu_temperature_c,ram_used_bytes,ram_available_bytes,ram_usage_percent,disk_read_bytes_per_sec,network_sent_bytes_per_sec
2026-10-16 10:00:00.000,25.0,55.0,8589934592,8589934592,50.0,1048576,512000
2026-10-16 10:00:01.000,105.0,58.0,8589934592,8589934592,53.0,-500,520000
2026-10-16 10:00:01.000,105.0,58.0,8589934592,8589934592,53.0,-500,520000
2026-10-16 10:00:02.000,-10.0,,9663676416,7516192768,56.0,2097152,530000
2026-10-16 10:00:15.000,85.0,75.0,10737418240,6442450944,62.5,5242880,1048576
"""
        prep = TelemetryPreprocessor()
        prep.load_csv(io.StringIO(raw_csv))
        cleaned = prep.preprocess(deduplicate_rows=True, rolling_window=3)

        # Rows check: 5 input -> 1 exact duplicate removed -> 4 rows
        self.assertEqual(prep.summary["original_rows"], 5)
        self.assertEqual(prep.summary["final_rows"], 4)

        # Invalid percentage check: 105.0 and -10.0 masked to NaN
        self.assertEqual(prep.summary["invalid_readings_detected"]["invalid_percentages"], 2)

        # Negative throughput check: -500 masked to NaN
        self.assertEqual(prep.summary["invalid_readings_detected"]["negative_throughputs"], 1)

        # Feature engineering derived columns
        self.assertIn("ram_used_gb", cleaned.columns)
        self.assertEqual(cleaned["ram_used_gb"].iloc[0], 8.0)
        self.assertIn("disk_read_mb_per_sec", cleaned.columns)
        self.assertIn("cpu_usage_percent_rolling_avg", cleaned.columns)

        # Time gaps check: gap from 10:00:02 to 10:00:15 (13s > 2.5x median 1s)
        self.assertGreaterEqual(prep.summary["sampling_interval_analysis"]["gaps_count"], 1)

        # Audit summary text
        summary_txt = prep.get_summary_text()
        self.assertIn("Preprocessing Pipeline Audit Summary", summary_txt)
        self.assertIn("Input Record Count", summary_txt)


class TestTelemetryStatisticsAndInterpretations(unittest.TestCase):
    """Test descriptive statistics, threshold analysis, correlations, and narrative generator."""

    def setUp(self):
        np.random.seed(42)
        n = 50
        self.df = pd.DataFrame({
            "timestamp": pd.date_range("2026-10-16 12:00:00", periods=n, freq="1s"),
            "cpu_usage_percent": np.random.uniform(20, 95, n),
            "cpu_temperature_c": np.random.uniform(50, 88, n),
            "ram_usage_percent": np.random.uniform(60, 85, n),
            "ram_used_gb": np.random.uniform(8, 14, n),
            "disk_read_mb_per_sec": np.random.uniform(0, 100, n),
            "disk_write_mb_per_sec": np.random.uniform(0, 40, n),
            "network_sent_kb_per_sec": np.random.uniform(10, 500, n),
            "network_recv_kb_per_sec": np.random.uniform(50, 3000, n),
        })
        self.df["parsed_timestamp"] = self.df["timestamp"]

    def test_descriptive_stats_computation(self):
        stats = compute_descriptive_stats(self.df)
        self.assertIn("cpu_usage_percent", stats)
        cpu_s = stats["cpu_usage_percent"]
        self.assertGreater(cpu_s["mean"], 0)
        self.assertGreater(cpu_s["max"], cpu_s["min"])
        self.assertIn("p95", cpu_s)
        self.assertIn("p99", cpu_s)

    def test_threshold_analysis(self):
        thresholds = compute_threshold_analysis(self.df, {"cpu_usage_percent": 80.0})
        self.assertIn("cpu_usage_percent", thresholds)
        t_data = thresholds["cpu_usage_percent"]
        self.assertIn("samples_above", t_data)
        self.assertIn("percent_time_above", t_data)
        self.assertIn("longest_streak_samples", t_data)

    def test_correlation_matrix(self):
        corrs = compute_correlations(self.df)
        self.assertIn("matrix", corrs)
        self.assertIn("notable_pairs", corrs)

    def test_anomalies_and_interpretations(self):
        anomalies = detect_sustained_periods_and_anomalies(self.df)
        self.assertIn("sustained_cpu_periods", anomalies)

        interps = generate_interpretations(self.df)
        self.assertIn("cpu", interps)
        self.assertIn("ram", interps)
        self.assertIn("temperature", interps)
        self.assertIn("storage", interps)
        self.assertIn("cross_resource", interps)
        self.assertIn("executive_summary", interps)

        # Verify interpretations contain computed figures, not hardcoded placeholders
        self.assertIn("%", interps["cpu"])
        self.assertIn("°C", interps["temperature"])


class TestAIInsightsAndReportExport(unittest.TestCase):
    """Test offline rule-based diagnosis and report generation."""

    def test_rule_based_insights_offline(self):
        stats = {
            "cpu_usage_percent": {"mean": 75.0, "max": 95.0, "p95": 88.0},
            "ram_usage_percent": {"mean": 82.0, "min": 65.0, "max": 89.0},
            "cpu_temperature_c": {"mean": 72.0, "max": 87.0},
        }
        res = AIInsightsManager.generate_rule_based_insights(None, stats, {}, {})
        self.assertEqual(res["mode"], "RULE_BASED")
        self.assertFalse(res["is_ai_generated"])
        self.assertGreater(len(res["insights"]), 0)
        self.assertGreater(len(res["recommendations"]), 0)

    def test_analytics_report_export(self):
        test_dir = os.path.join("data", "test_report_scratch")
        os.makedirs(test_dir, exist_ok=True)

        prep = TelemetryPreprocessor()
        prep.summary = {
            "source_path": "test.csv",
            "original_rows": 100,
            "final_rows": 100,
            "retained_percentage": 100.0,
            "start_time": "2026-10-16 12:00:00",
            "end_time": "2026-10-16 12:01:40",
            "duration_seconds": 100.0,
            "transformations_performed": ["Deduplication", "Derived calculations"],
            "missing_values_by_column": {},
        }
        stats = {"cpu_usage_percent": {"count": 100, "mean": 45.0, "median": 42.0, "min": 10.0, "max": 90.0, "std": 15.0, "p95": 80.0, "peak_timestamp": "2026-10-16 12:00:50"}}

        html_f, json_f = export_analytics_report(
            prep,
            stats=stats,
            output_dir=test_dir,
        )

        self.assertTrue(os.path.exists(html_f))
        self.assertTrue(os.path.exists(json_f))

        with open(html_f, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("SYSTEM TELEMETRY HISTORICAL ANALYTICS REPORT", content)
            self.assertIn("cpu_usage_percent", content)

        shutil.rmtree(test_dir, ignore_errors=True)


class TestMonitorAssistant(unittest.TestCase):
    """Verify the offline assistant stays deterministic and network-independent."""

    def setUp(self):
        self.metrics = {
            "cpu": 92.0,
            "memory": 88.0,
            "memory_available_gb": 1.5,
            "disk": 72.0,
            "network_sent_mb": 12.0,
            "network_received_mb": 48.0,
        }

    def test_cpu_response_contains_live_metric_and_guidance(self):
        response = build_local_response("How is my CPU?", self.metrics)
        self.assertIn("92.0%", response)
        self.assertIn("Close intensive applications", response)

    def test_help_and_unknown_questions_are_actionable(self):
        self.assertIn("CPU", build_local_response("help", self.metrics))
        self.assertIn("system status", build_local_response("something else", self.metrics))


if __name__ == "__main__":
    unittest.main()
