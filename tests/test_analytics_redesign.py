"""Comprehensive test suite for the redesigned Historical Telemetry Analytics dashboard."""

import os
import shutil
import unittest
import numpy as np
import pandas as pd

from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtCore import QTimer

# Ensure QApplication exists for widget testing
app = QApplication.instance() or QApplication([])

from analytics_page import (
    AnalyticsPage,
    HealthScoreGaugeWidget,
    RamDonutCanvas,
    DiskThroughputCanvas,
    CpuDistributionCanvas,
)
from data_preprocessing import TelemetryPreprocessor
from report_exporter import export_analytics_report


class TestAnalyticsRedesign(unittest.TestCase):

    def setUp(self):
        self.page = AnalyticsPage()
        # Ensure initial worker completes
        if self.page.worker and self.page.worker.isRunning():
            self.page.worker.wait(5000)
            app.processEvents()

    def tearDown(self):
        if self.page.worker and self.page.worker.isRunning():
            self.page.worker.wait(5000)
        self.page.deleteLater()
        app.processEvents()

    def test_kpi_cards_count_and_structure(self):
        """Verify exactly four primary KPI cards exist with expected structure."""
        self.assertIsNotNone(self.page.kpi_cpu)
        self.assertIsNotNone(self.page.kpi_ram)
        self.assertIsNotNone(self.page.kpi_temp)
        self.assertIsNotNone(self.page.kpi_records)

        # Check that value and sub-labels exist in each card
        for card in [self.page.kpi_cpu, self.page.kpi_ram, self.page.kpi_temp, self.page.kpi_records]:
            val_lbl = card.findChild(QLabel, "val_label")
            sub_lbl = card.findChild(QLabel, "sub_label")
            self.assertIsNotNone(val_lbl)
            self.assertIsNotNone(sub_lbl)

    def test_load_real_telemetry_dataset_22_rows(self):
        """Verify loading the real 22-row dataset resource_log_20261019_195226.csv."""
        test_csv = "data/logs/resource_log_20261019_195226.csv"
        if not os.path.exists(test_csv):
            self.skipTest(f"{test_csv} not found")

        self.page.load_dataset(test_csv)
        if self.page.worker:
            self.page.worker.wait(5000)
            app.processEvents()

        df = self.page.cleaned_df
        self.assertIsNotNone(df)
        self.assertGreaterEqual(len(df), 20)

        # 1. Verify KPI 1 (CPU): mean and peak computed dynamically
        cpu_val = self.page.kpi_cpu.findChild(QLabel, "val_label").text()
        cpu_sub = self.page.kpi_cpu.findChild(QLabel, "sub_label").text()
        self.assertTrue("%" in cpu_val)
        self.assertTrue("Peak:" in cpu_sub)

        # 2. Verify KPI 2 (RAM): mean and peak computed dynamically
        ram_val = self.page.kpi_ram.findChild(QLabel, "val_label").text()
        ram_sub = self.page.kpi_ram.findChild(QLabel, "sub_label").text()
        self.assertTrue("%" in ram_val)
        self.assertTrue("Peak:" in ram_sub)

        # 3. Verify KPI 3 (Thermal): max temp and threshold
        temp_val = self.page.kpi_temp.findChild(QLabel, "val_label").text()
        temp_sub = self.page.kpi_temp.findChild(QLabel, "sub_label").text()
        self.assertTrue("°C" in temp_val)
        self.assertTrue("80°C" in temp_sub)

        # 4. Verify KPI 4 (Records Analyzed)
        rec_val = self.page.kpi_records.findChild(QLabel, "val_label").text()
        rec_sub = self.page.kpi_records.findChild(QLabel, "sub_label").text()
        self.assertTrue(f"{len(df)} valid records" in rec_val)
        self.assertTrue("raw rows" in rec_sub)

    def test_all_six_visualizations_populate(self):
        """Verify all 6 visualization components populate correctly."""
        test_csv = "data/logs/resource_log_20261019_195226.csv"
        if not os.path.exists(test_csv):
            test_csv = self.page.generate_sample_telemetry_if_needed()
        self.page.load_dataset(test_csv)
        if self.page.worker:
            self.page.worker.wait(5000)
            app.processEvents()

        # Chart 1: Time series plot curves have points
        self.assertEqual(len(self.page.curve_cpu_raw.xData), len(self.page.cleaned_df))
        self.assertEqual(len(self.page.curve_ram_ts.xData), len(self.page.cleaned_df))

        # Chart 2: RAM Donut canvas ax has wedges
        self.assertGreater(len(self.page.canvas_donut.ax.patches), 0)

        # Chart 3: Thermal area curves have points and threshold line
        self.assertEqual(len(self.page.curve_cpu_temp.xData), len(self.page.cleaned_df))
        self.assertIsNotNone(self.page.temp_thresh_line)

        # Chart 4: Storage throughput grouped bars
        self.assertGreater(len(self.page.canvas_disk.ax.patches), 0)

        # Chart 5: CPU distribution histogram patches
        self.assertGreater(len(self.page.canvas_dist.ax.patches), 0)

        # Chart 6: Resource Utilization Heatmap & Health Score
        self.assertGreater(len(self.page.canvas_heatmap.ax.images), 0)
        self.assertIsNotNone(self.page.gauge_widget.score)
        self.assertTrue(0.0 <= self.page.gauge_widget.score <= 100.0)
        self.assertIn(self.page.gauge_widget.tier_name, [
            "OPTIMAL & HEALTHY", "GOOD STATE", "MODERATE LOAD", "CRITICAL / STRESSED"
        ])

    def test_missing_gpu_and_temperatures_handled_gracefully(self):
        """Test dataset without GPU and temperatures without crashing."""
        # Create temporary minimal dataset
        df_min = pd.DataFrame({
            "timestamp": ["2026-10-19 12:00:00", "2026-10-19 12:00:01", "2026-10-19 12:00:02"],
            "cpu_usage_percent": [15.0, 25.0, 35.0],
            "ram_usage_percent": [60.0, 62.0, 61.0],
        })
        tmp_csv = "data/logs/test_minimal_telemetry.csv"
        df_min.to_csv(tmp_csv, index=False)

        try:
            self.page.load_dataset(tmp_csv)
            if self.page.worker:
                self.page.worker.wait(5000)
                app.processEvents()

            # GPU series should be hidden gracefully
            self.assertFalse(self.page.curve_gpu_ts.isVisible())
            # Thermal should show N/A
            self.assertEqual(self.page.kpi_temp.findChild(QLabel, "val_label").text(), "N/A")
            # Gauge should still compute score based on CPU & RAM
            self.assertIsNotNone(self.page.gauge_widget.score)
        finally:
            if os.path.exists(tmp_csv):
                os.remove(tmp_csv)

    def test_report_export_integration(self):
        """Verify report exporter receives figures and outputs valid HTML/JSON."""
        test_csv = "data/logs/resource_log_20261019_195226.csv"
        if not os.path.exists(test_csv):
            test_csv = self.page.generate_sample_telemetry_if_needed()
        self.page.load_dataset(test_csv)
        if self.page.worker:
            self.page.worker.wait(5000)
            app.processEvents()

        figures = {
            "RAM Usage Composition": self.page.canvas_donut.fig,
            "Storage Read/Write": self.page.canvas_disk.fig,
            "CPU Distribution": self.page.canvas_dist.fig,
        }
        test_dir = "data/reports/test_output"
        os.makedirs(test_dir, exist_ok=True)
        try:
            html_f, json_f = export_analytics_report(
                self.page.preprocessor,
                stats=self.page.current_stats,
                thresholds=self.page.current_thresholds,
                correlations=self.page.current_correlations,
                interpretations=self.page.current_interpretations,
                ai_insights=self.page.current_ai_insights,
                figures=figures,
                output_dir=test_dir,
            )
            self.assertTrue(os.path.exists(html_f))
            self.assertTrue(os.path.exists(json_f))
            self.assertGreater(os.path.getsize(html_f), 1000)
            self.assertGreater(os.path.getsize(json_f), 500)
        finally:
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir, ignore_errors=True)

    def test_live_streaming_updates(self):
        """Verify real-time live telemetry stream updates buffer, KPIs, and charts."""
        self.page.toggle_live_feed(enable=True)
        self.assertTrue(self.page.is_live)
        initial_count = len(self.page.live_buffer)

        # Trigger live tick
        self.page._on_live_tick()
        self.assertEqual(len(self.page.live_buffer), initial_count + 1)
        self.assertGreater(len(self.page.cleaned_df), 0)

        # Verify dynamic KPI updates
        self.assertTrue("%" in self.page.kpi_cpu.findChild(QLabel, "val_label").text())
        self.assertTrue("%" in self.page.kpi_ram.findChild(QLabel, "val_label").text())

        # Test toggle off
        self.page.toggle_live_feed(enable=False)
        self.assertFalse(self.page.is_live)

    def test_initial_screen_is_blank_mode_selection_with_two_options(self):
        """Verify initial screen is mode selection (landing) with 1. Live Analysis and 2. Import Dataset."""
        self.assertEqual(self.page.stack.currentIndex(), 0)
        self.assertEqual(self.page.stack.currentWidget(), self.page.landing_widget)
        self.assertFalse(self.page.is_live)

        # Check options 1 and 2
        labels = [lbl.text() for lbl in self.page.landing_widget.findChildren(QLabel)]
        self.assertTrue(any("1. Live Analysis" in t for t in labels))
        self.assertTrue(any("2. Import Dataset" in t for t in labels))

    def test_mode_one_live_analysis_switch(self):
        """Verify Option 1 redirects to dashboard and starts live analysis."""
        self.page.start_live_analysis()
        self.assertEqual(self.page.stack.currentIndex(), 1)
        self.assertEqual(self.page.stack.currentWidget(), self.page.dashboard_widget)
        self.assertTrue(self.page.is_live)
        self.assertTrue(self.page.prep_audit_banner.isHidden())

        # Verify switching back to landing screen
        self.page.show_landing_screen()
        self.assertEqual(self.page.stack.currentIndex(), 0)
        self.assertFalse(self.page.is_live)

    def test_mode_two_import_dataset_shows_audit_with_row_count_nulls_and_no_duplicates(self):
        """Verify Option 2 preprocesses data, redirects to dashboard, and shows row count, null values, and no duplicates."""
        test_csv = "data/logs/test_audit_flow.csv"
        df = pd.DataFrame({
            "timestamp": ["2026-10-21 11:00:00", "2026-10-21 11:00:01", "2026-10-21 11:00:01", "2026-10-21 11:00:02"],
            "cpu_usage_percent": [20.0, 30.0, 30.0, None],
            "ram_usage_percent": [50.0, 55.0, 55.0, 60.0],
            "cpu_temperature_c": [45.0, None, None, 50.0],
        })
        df.to_csv(test_csv, index=False)

        try:
            self.page.load_dataset(test_csv)
            if self.page.worker:
                self.page.worker.wait(5000)
                app.processEvents()

            # Verify redirected to dashboard (index 1)
            self.assertEqual(self.page.stack.currentIndex(), 1)
            self.assertEqual(self.page.stack.currentWidget(), self.page.dashboard_widget)
            self.assertFalse(self.page.prep_audit_banner.isHidden())

            raw_val = self.page.banner_chip_raw.findChild(QLabel, "chip_val").text()
            clean_val = self.page.banner_chip_clean.findChild(QLabel, "chip_val").text()
            dedup_val = self.page.banner_chip_dedup.findChild(QLabel, "chip_val").text()
            null_val = self.page.banner_chip_nulls.findChild(QLabel, "chip_val").text()
            badge_text = self.page.banner_dedup_badge.text()

            # Row count verified
            self.assertEqual(int(raw_val.replace(",", "")), 4)
            self.assertEqual(int(clean_val.replace(",", "")), 3)

            # Null values verified (cpu_usage has 1, cpu_temperature has 1 in cleaned data)
            self.assertGreaterEqual(int(null_val.replace(",", "")), 2)

            # Strict duplicate removal: 0 duplicates remain { no duplicate values }
            self.assertEqual(int(dedup_val.replace(",", "")), 1)
            self.assertIn("0 DUPLICATE VALUES", badge_text)
            self.assertIn("NO DUPLICATES", badge_text)

            # Check that cleaned_df has no duplicate timestamps
            self.assertEqual(self.page.cleaned_df["parsed_timestamp"].duplicated().sum(), 0)

        finally:
            if os.path.exists(test_csv):
                os.remove(test_csv)


if __name__ == "__main__":
    unittest.main()

