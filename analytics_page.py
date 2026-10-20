"""Historical Telemetry Analytics & Interactive Visualization Page.

This module provides the dedicated PySide6 Analytics tab for the System Resource Monitor.
It implements the DVP mini-project workflow:
- Dataset import & validation (custom CSV, live log, or sample benchmark dataset)
- Data preprocessing pipeline execution with transparent viva audit reports
- Summary KPI cards reflecting actual dataset metrics
- Interactive PyQtGraph time-series plots with zoom, pan, and dynamic interpretations
- Embedded Matplotlib exploratory charts (distributions, scatter regressions, correlation heatmap)
- Dynamic data-driven statistical interpretations
- Optional offline rule-based and LLM-assisted insights
- One-click export of cleaned CSVs and comprehensive HTML/JSON reports
"""

import os
import glob
from pathlib import Path
from typing import Optional, Dict, Any

import numpy as np
import pandas as pd
import pyqtgraph as pg

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QTabWidget,
    QScrollArea,
    QDialog,
    QTextEdit,
    QLineEdit,
    QProgressBar,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from dashboard import CarbonFiberBackground
from data_preprocessing import TelemetryPreprocessor, PreprocessingValidationError
from telemetry_statistics import (
    compute_descriptive_stats,
    compute_threshold_analysis,
    compute_correlations,
    generate_interpretations,
)
from ai_insights import AIInsightsManager
from report_exporter import export_analytics_report


# =====================================================================
# BACKGROUND PREPROCESSING WORKER THREAD
# =====================================================================

class PreprocessingWorker(QThread):
    finished = Signal(object, object, str)  # preprocessor, cleaned_df, error_msg

    def __init__(self, filepath, deduplicate_rows, deduplicate_ts, rolling_window):
        super().__init__()
        self.filepath = filepath
        self.deduplicate_rows = deduplicate_rows
        self.deduplicate_ts = deduplicate_ts
        self.rolling_window = rolling_window

    def run(self):
        preprocessor = TelemetryPreprocessor()
        try:
            preprocessor.load_csv(self.filepath)
            cleaned_df = preprocessor.preprocess(
                deduplicate_rows=self.deduplicate_rows,
                deduplicate_timestamps=self.deduplicate_ts,
                rolling_window=self.rolling_window,
            )
            self.finished.emit(preprocessor, cleaned_df, "")
        except Exception as e:
            self.finished.emit(None, None, str(e))


# =====================================================================
# MATPLOTLIB CANVASES
# =====================================================================

class CorrelationHeatmapCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(6.5, 4.5), facecolor="#101010")
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)
        self.fig.tight_layout()

    def update_heatmap(self, corr_dict: Dict[str, Dict[str, float]]):
        self.ax.clear()
        if not corr_dict:
            self.ax.text(0.5, 0.5, "Insufficient numeric columns for correlation analysis",
                         ha="center", va="center", color="#888888", fontsize=10)
            self.draw_idle()
            return

        df_corr = pd.DataFrame(corr_dict)
        cols = list(df_corr.columns)
        n = len(cols)

        # Plot matrix as image
        data = df_corr.values
        im = self.ax.imshow(data, cmap="coolwarm", vmin=-1.0, vmax=1.0)

        # Add colorbar
        if not hasattr(self, "cbar") or self.cbar is None:
            self.cbar = self.fig.colorbar(im, ax=self.ax, fraction=0.046, pad=0.04)
            self.cbar.ax.yaxis.set_tick_params(color="#888888")
            for t in self.cbar.ax.get_yticklabels():
                t.set_color("#cccccc")
        else:
            self.cbar.update_normal(im)

        # Labels
        short_labels = [c.replace("_percent", "%").replace("_bytes_per_sec", "/s").replace("_mb_per_sec", "MB/s").replace("_temperature_c", "°C") for c in cols]
        self.ax.set_xticks(range(n))
        self.ax.set_yticks(range(n))
        self.ax.set_xticklabels(short_labels, rotation=35, ha="right", color="#cccccc", fontsize=8)
        self.ax.set_yticklabels(short_labels, color="#cccccc", fontsize=8)

        # Annotate values
        for i in range(n):
            for j in range(n):
                val = data[i, j]
                if not np.isnan(val):
                    text_color = "black" if abs(val) < 0.6 else "white"
                    self.ax.text(j, i, f"{val:.2f}", ha="center", va="center", color=text_color, fontsize=8, fontweight="bold")

        self.ax.set_title("Metric Pearson Correlation Matrix", color="#ff8f00", fontsize=11, fontweight="bold", pad=10)
        self.fig.tight_layout()
        self.draw_idle()


class BivariateScatterCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(6.5, 4.5), facecolor="#101010")
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)
        self.fig.tight_layout()

    def update_scatter(self, df: pd.DataFrame, x_col: str = "cpu_usage_percent", y_col: str = "ram_usage_percent"):
        self.ax.clear()
        if df is None or x_col not in df.columns or y_col not in df.columns:
            self.ax.text(0.5, 0.5, "Select valid metrics to compare", ha="center", va="center", color="#888888")
            self.draw_idle()
            return

        valid = df[[x_col, y_col]].dropna()
        if len(valid) < 3:
            self.ax.text(0.5, 0.5, "Insufficient paired observations", ha="center", va="center", color="#888888")
            self.draw_idle()
            return

        x = valid[x_col].values
        y = valid[y_col].values

        # Scatter
        self.ax.scatter(x, y, color="#26a69a", alpha=0.6, edgecolors="none", s=25, label="Telemetry Samples")

        # Linear regression trendline
        try:
            poly = np.polyfit(x, y, 1)
            line_x = np.linspace(x.min(), x.max(), 100)
            line_y = np.polyval(poly, line_x)
            r = np.corrcoef(x, y)[0, 1]
            self.ax.plot(line_x, line_y, color="#ff8f00", linestyle="--", linewidth=1.8, label=f"Fit (r = {r:+.2f})")
        except Exception:
            pass

        self.ax.set_facecolor("#0a0a0a")
        self.ax.grid(True, linestyle=":", color="#222222")
        self.ax.set_xlabel(x_col.replace("_", " ").title(), color="#cccccc", fontsize=9)
        self.ax.set_ylabel(y_col.replace("_", " ").title(), color="#cccccc", fontsize=9)
        self.ax.tick_params(colors="#888888", labelsize=8)
        self.ax.set_title(f"{x_col.replace('_', ' ').title()} vs {y_col.replace('_', ' ').title()}", color="#ff8f00", fontsize=11, fontweight="bold")
        self.ax.legend(facecolor="#151515", edgecolor="#333333", labelcolor="#dddddd", fontsize=8)
        self.fig.tight_layout()
        self.draw_idle()


class DistributionCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(6.5, 4.5), facecolor="#101010")
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax1 = self.fig.add_subplot(211)
        self.ax2 = self.fig.add_subplot(212)
        self.fig.tight_layout()

    def update_distributions(self, df: pd.DataFrame):
        self.ax1.clear()
        self.ax2.clear()

        if df is None or df.empty:
            self.draw_idle()
            return

        # Top: CPU Distribution
        if "cpu_usage_percent" in df.columns:
            cpu = df["cpu_usage_percent"].dropna()
            self.ax1.hist(cpu, bins=25, color="#ff8f00", alpha=0.75, edgecolor="#111111")
            self.ax1.axvline(cpu.mean(), color="#e53935", linestyle="--", linewidth=1.5, label=f"Mean: {cpu.mean():.1f}%")
            self.ax1.axvline(cpu.median(), color="#55d66f", linestyle=":", linewidth=1.5, label=f"Median: {cpu.median():.1f}%")
            self.ax1.set_facecolor("#0a0a0a")
            self.ax1.grid(True, linestyle=":", color="#222222")
            self.ax1.set_title("CPU Utilization Density Distribution (%)", color="#dddddd", fontsize=10)
            self.ax1.tick_params(colors="#888888", labelsize=8)
            self.ax1.legend(facecolor="#151515", edgecolor="#333333", labelcolor="#dddddd", fontsize=8)

        # Bottom: RAM Distribution
        if "ram_usage_percent" in df.columns:
            ram = df["ram_usage_percent"].dropna()
            self.ax2.hist(ram, bins=25, color="#26a69a", alpha=0.75, edgecolor="#111111")
            self.ax2.axvline(ram.mean(), color="#e53935", linestyle="--", linewidth=1.5, label=f"Mean: {ram.mean():.1f}%")
            self.ax2.axvline(ram.median(), color="#55d66f", linestyle=":", linewidth=1.5, label=f"Median: {ram.median():.1f}%")
            self.ax2.set_facecolor("#0a0a0a")
            self.ax2.grid(True, linestyle=":", color="#222222")
            self.ax2.set_title("RAM Utilization Density Distribution (%)", color="#dddddd", fontsize=10)
            self.ax2.tick_params(colors="#888888", labelsize=8)
            self.ax2.legend(facecolor="#151515", edgecolor="#333333", labelcolor="#dddddd", fontsize=8)

        self.fig.tight_layout()
        self.draw_idle()


# =====================================================================
# MAIN ANALYTICS PAGE
# =====================================================================

class AnalyticsPage(CarbonFiberBackground):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.preprocessor = TelemetryPreprocessor()
        self.cleaned_df: Optional[pd.DataFrame] = None
        self.current_stats: Dict[str, Any] = {}
        self.current_thresholds: Dict[str, Any] = {}
        self.current_correlations: Dict[str, Any] = {}
        self.current_interpretations: Dict[str, Any] = {}
        self.current_ai_insights: Dict[str, Any] = {}

        self.worker: Optional[PreprocessingWorker] = None
        self.current_file_path: Optional[str] = None

        self.setup_ui()
        self._auto_load_recent_or_sample()

    # =================================================================
    # UI SETUP
    # =================================================================

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 25, 30, 25)
        main_layout.setSpacing(15)

        # -------------------------------------------------------------
        # Header
        # -------------------------------------------------------------
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        title = QLabel("HISTORICAL TELEMETRY ANALYTICS & INSIGHTS")
        title.setObjectName("page_title")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ff8f00; letter-spacing: 1.5px;")

        subtitle = QLabel("Data Visualization using Python (DVP) — Post-Collection Pipeline, Statistical Diagnostics & Exploratory Visualizations")
        subtitle.setStyleSheet("font-size: 11px; color: #888888;")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        # Action Buttons in Header
        self.import_btn = QPushButton("📁 Import CSV Dataset")
        self.import_btn.clicked.connect(self.browse_and_load_csv)
        self.apply_button_style(self.import_btn, primary=True)

        self.load_latest_btn = QPushButton("🔄 Load Latest Live Log")
        self.load_latest_btn.clicked.connect(self.load_latest_log)
        self.apply_button_style(self.load_latest_btn)

        self.export_report_btn = QPushButton("📄 Export Full Analytics Report")
        self.export_report_btn.clicked.connect(self.generate_and_export_report)
        self.apply_button_style(self.export_report_btn, accent=True)

        self.export_csv_btn = QPushButton("💾 Export Cleaned CSV")
        self.export_csv_btn.clicked.connect(self.export_cleaned_dataset)
        self.apply_button_style(self.export_csv_btn)

        header_layout.addWidget(self.import_btn)
        header_layout.addWidget(self.load_latest_btn)
        header_layout.addWidget(self.export_csv_btn)
        header_layout.addWidget(self.export_report_btn)
        main_layout.addLayout(header_layout)

        # -------------------------------------------------------------
        # Dataset & Preprocessing Control Toolbar
        # -------------------------------------------------------------
        control_bar = QFrame()
        control_bar.setObjectName("controls_frame")
        control_bar.setStyleSheet("background-color: #0b0b0b; border: 1px solid #242424; border-radius: 4px; padding: 6px;")
        bar_layout = QHBoxLayout(control_bar)
        bar_layout.setContentsMargins(12, 6, 12, 6)
        bar_layout.setSpacing(15)

        self.dataset_label = QLabel("Dataset: [No File Loaded]")
        self.dataset_label.setStyleSheet("color: #26a69a; font-weight: bold; font-size: 11px;")
        bar_layout.addWidget(self.dataset_label)

        bar_layout.addStretch()

        # Preprocessing options
        self.dedup_check = QCheckBox("Deduplicate Records")
        self.dedup_check.setChecked(True)
        self.dedup_check.setStyleSheet("color: #cccccc; font-size: 11px;")
        bar_layout.addWidget(self.dedup_check)

        rw_lbl = QLabel("Rolling Window:")
        rw_lbl.setStyleSheet("color: #888888; font-size: 11px;")
        bar_layout.addWidget(rw_lbl)

        self.rolling_spin = QSpinBox()
        self.rolling_spin.setRange(1, 30)
        self.rolling_spin.setValue(5)
        self.rolling_spin.setSuffix(" samples")
        self.rolling_spin.setStyleSheet("background:#151515; color:#ffffff; padding:3px; border:1px solid #333;")
        bar_layout.addWidget(self.rolling_spin)

        self.run_pipeline_btn = QPushButton("⚡ Run Preprocessing Pipeline")
        self.run_pipeline_btn.clicked.connect(self.run_pipeline)
        self.apply_button_style(self.run_pipeline_btn, primary=True)
        bar_layout.addWidget(self.run_pipeline_btn)

        self.audit_btn = QPushButton("📋 View Audit Summary")
        self.audit_btn.clicked.connect(self.show_audit_dialog)
        self.apply_button_style(self.audit_btn)
        bar_layout.addWidget(self.audit_btn)

        main_layout.addWidget(control_bar)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #ff8f00; }")
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)

        # -------------------------------------------------------------
        # Summary KPI Cards Row
        # -------------------------------------------------------------
        self.kpi_layout = QHBoxLayout()
        self.kpi_layout.setSpacing(12)

        self.kpi_records = self.create_kpi_card("RECORD COUNT", "0 records", "#ffffff")
        self.kpi_cpu = self.create_kpi_card("CPU (AVG / PEAK)", "N/A", "#ff8f00")
        self.kpi_ram = self.create_kpi_card("RAM (AVG / PEAK)", "N/A", "#26a69a")
        self.kpi_temp = self.create_kpi_card("THERMAL (MAX CPU / GPU)", "N/A", "#e53935")
        self.kpi_disk = self.create_kpi_card("STORAGE READ/WRITE PEAK", "N/A", "#ab47bc")
        self.kpi_net = self.create_kpi_card("NETWORK (PEAK DL / UL)", "N/A", "#55d66f")

        self.kpi_layout.addWidget(self.kpi_records)
        self.kpi_layout.addWidget(self.kpi_cpu)
        self.kpi_layout.addWidget(self.kpi_ram)
        self.kpi_layout.addWidget(self.kpi_temp)
        self.kpi_layout.addWidget(self.kpi_disk)
        self.kpi_layout.addWidget(self.kpi_net)
        main_layout.addLayout(self.kpi_layout)

        # -------------------------------------------------------------
        # Tabbed Analytics Views
        # -------------------------------------------------------------
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #222222;
                background-color: #080808;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #111111;
                color: #888888;
                padding: 8px 18px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #1c1c1c;
                color: #ff8f00;
                border-bottom: 2px solid #ff8f00;
            }
        """)

        # Tab 1: Time-Series Visualizations
        self.tab_timeseries = QWidget()
        self.setup_timeseries_tab()
        self.tabs.addTab(self.tab_timeseries, "📈 Time-Series Telemetry")

        # Tab 2: Exploratory & Statistical Distributions
        self.tab_exploratory = QWidget()
        self.setup_exploratory_tab()
        self.tabs.addTab(self.tab_exploratory, "📊 Exploratory & Distributions")

        # Tab 3: Statistical Interpretations & AI Insights
        self.tab_insights = QWidget()
        self.setup_insights_tab()
        self.tabs.addTab(self.tab_insights, "🧠 Statistical Interpretations & AI")

        # Tab 4: Dataset Records Table
        self.tab_records = QWidget()
        self.setup_records_tab()
        self.tabs.addTab(self.tab_records, "📋 Dataset Records Preview")

        main_layout.addWidget(self.tabs, stretch=1)

    def apply_button_style(self, button: QPushButton, primary=False, accent=False):
        if primary:
            bg = "#ff8f00"
            color = "#000000"
            hover = "#ffa000"
        elif accent:
            bg = "#26a69a"
            color = "#000000"
            hover = "#2bbbad"
        else:
            bg = "#141414"
            color = "#cccccc"
            hover = "#222222"

        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {color};
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
        """)

    def create_kpi_card(self, title_text: str, default_val: str, color_hex: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("background-color: #0b0b0b; border: 1px solid #222222; border-radius: 4px; padding: 10px;")
        l = QVBoxLayout(card)
        l.setContentsMargins(10, 8, 10, 8)
        l.setSpacing(4)

        t_lbl = QLabel(title_text)
        t_lbl.setStyleSheet("color: #777777; font-size: 9px; font-weight: bold; letter-spacing: 0.8px;")
        l.addWidget(t_lbl)

        v_lbl = QLabel(default_val)
        v_lbl.setObjectName("val_label")
        v_lbl.setStyleSheet(f"color: {color_hex}; font-size: 15px; font-weight: bold;")
        l.addWidget(v_lbl)
        return card

    # =================================================================
    # TAB 1: TIME-SERIES VISUALIZATIONS
    # =================================================================

    def setup_timeseries_tab(self):
        tab_layout = QVBoxLayout(self.tab_timeseries)
        tab_layout.setContentsMargins(10, 10, 10, 10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(20)

        # 1. CPU Plot
        self.plot_cpu = self.create_pyqtgraph_card("CPU UTILIZATION & MOVING AVERAGE (%)")
        self.curve_cpu_raw = self.plot_cpu.plot(pen=pg.mkPen(color="#ff8f00", width=1.5), name="Instantaneous CPU %")
        self.curve_cpu_roll = self.plot_cpu.plot(pen=pg.mkPen(color="#e53935", width=2.5, style=Qt.DashLine), name="Rolling Trend (5-sample)")
        self.interp_cpu = self.create_interp_label()
        content_layout.addWidget(self.wrap_chart_with_interp(self.plot_cpu, self.interp_cpu))

        # 2. RAM Plot
        self.plot_ram = self.create_pyqtgraph_card("PHYSICAL RAM UTILIZATION (%)")
        self.curve_ram = self.plot_ram.plot(pen=pg.mkPen(color="#26a69a", width=2.0), name="RAM Usage %")
        self.interp_ram = self.create_interp_label()
        content_layout.addWidget(self.wrap_chart_with_interp(self.plot_ram, self.interp_ram))

        # 3. Thermal Plot
        self.plot_temp = self.create_pyqtgraph_card("THERMAL DYNAMICS (°C)")
        self.curve_cpu_temp = self.plot_temp.plot(pen=pg.mkPen(color="#ff5252", width=2.0), name="CPU Temp (°C)")
        self.curve_gpu_temp = self.plot_temp.plot(pen=pg.mkPen(color="#ffb74d", width=2.0), name="GPU Temp (°C)")
        # 80 C threshold reference line
        self.temp_threshold_line = pg.InfiniteLine(pos=80, angle=0, pen=pg.mkPen(color="#ff1744", width=1, style=Qt.DotLine), label="80°C Warning", labelOpts={"color": "#ff1744"})
        self.plot_temp.addItem(self.temp_threshold_line)
        self.interp_temp = self.create_interp_label()
        content_layout.addWidget(self.wrap_chart_with_interp(self.plot_temp, self.interp_temp))

        # 4. Storage Throughput Plot
        self.plot_disk = self.create_pyqtgraph_card("STORAGE I/O THROUGHPUT (MB/s)")
        self.curve_disk_read = self.plot_disk.plot(pen=pg.mkPen(color="#ab47bc", width=1.8), name="Read MB/s")
        self.curve_disk_write = self.plot_disk.plot(pen=pg.mkPen(color="#ffa726", width=1.8), name="Write MB/s")
        self.interp_disk = self.create_interp_label()
        content_layout.addWidget(self.wrap_chart_with_interp(self.plot_disk, self.interp_disk))

        # 5. Network Bandwidth Plot
        self.plot_net = self.create_pyqtgraph_card("NETWORK BANDWIDTH THROUGHPUT (KB/s)")
        self.curve_net_recv = self.plot_net.plot(pen=pg.mkPen(color="#26a69a", width=1.8), name="Inbound (Download) KB/s")
        self.curve_net_sent = self.plot_net.plot(pen=pg.mkPen(color="#42a5f5", width=1.8), name="Outbound (Upload) KB/s")
        self.interp_net = self.create_interp_label()
        content_layout.addWidget(self.wrap_chart_with_interp(self.plot_net, self.interp_net))

        scroll.setWidget(content)
        tab_layout.addWidget(scroll)

    def create_pyqtgraph_card(self, title_text: str) -> pg.PlotWidget:
        pw = pg.PlotWidget()
        pw.setBackground("#0a0a0a")
        pw.setTitle(title_text, color="#ff8f00", size="10pt")
        pw.showGrid(x=True, y=True, alpha=0.25)
        pw.addLegend(offset=(10, 10))
        pw.setMinimumHeight(240)
        return pw

    def create_interp_label(self) -> QLabel:
        lbl = QLabel("Awaiting dataset import...")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("background-color: #0e0e0e; border-left: 3px solid #ff8f00; padding: 8px 12px; color: #bbbbbb; font-size: 11px; border-radius: 0 3px 3px 0;")
        return lbl

    def wrap_chart_with_interp(self, plot_widget: pg.PlotWidget, interp_label: QLabel) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("background-color: #090909; border: 1px solid #1c1c1c; border-radius: 4px; padding: 10px;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        layout.addWidget(plot_widget)
        layout.addWidget(interp_label)
        return frame

    # =================================================================
    # TAB 2: EXPLORATORY & DISTRIBUTIONS
    # =================================================================

    def setup_exploratory_tab(self):
        tab_layout = QVBoxLayout(self.tab_exploratory)
        tab_layout.setContentsMargins(10, 10, 10, 10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(20)

        # Upper row: Scatter and Distribution
        upper_row = QHBoxLayout()
        upper_row.setSpacing(15)

        # Scatter frame
        scatter_frame = QFrame()
        scatter_frame.setStyleSheet("background-color: #090909; border: 1px solid #1c1c1c; border-radius: 4px; padding: 10px;")
        sl = QVBoxLayout(scatter_frame)
        self.canvas_scatter = BivariateScatterCanvas()
        sl.addWidget(self.canvas_scatter)
        upper_row.addWidget(scatter_frame)

        # Distribution frame
        dist_frame = QFrame()
        dist_frame.setStyleSheet("background-color: #090909; border: 1px solid #1c1c1c; border-radius: 4px; padding: 10px;")
        dl = QVBoxLayout(dist_frame)
        self.canvas_dist = DistributionCanvas()
        dl.addWidget(self.canvas_dist)
        upper_row.addWidget(dist_frame)

        content_layout.addLayout(upper_row)

        # Lower row: Correlation Heatmap
        heat_frame = QFrame()
        heat_frame.setStyleSheet("background-color: #090909; border: 1px solid #1c1c1c; border-radius: 4px; padding: 10px;")
        hl = QVBoxLayout(heat_frame)
        self.canvas_heatmap = CorrelationHeatmapCanvas()
        hl.addWidget(self.canvas_heatmap)
        content_layout.addWidget(heat_frame)

        scroll.setWidget(content)
        tab_layout.addWidget(scroll)

    # =================================================================
    # TAB 3: STATISTICAL INTERPRETATIONS & AI INSIGHTS
    # =================================================================

    def setup_insights_tab(self):
        tab_layout = QVBoxLayout(self.tab_insights)
        tab_layout.setContentsMargins(10, 10, 10, 10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(20)

        # 1. Descriptive Statistics Table Card
        stats_card = QFrame()
        stats_card.setStyleSheet("background-color: #090909; border: 1px solid #1c1c1c; border-radius: 4px; padding: 15px;")
        sl = QVBoxLayout(stats_card)
        st_title = QLabel("EMPIRICAL DESCRIPTIVE STATISTICS & PERCENTILE DISTRIBUTIONS")
        st_title.setStyleSheet("color: #ff8f00; font-size: 12px; font-weight: bold;")
        sl.addWidget(st_title)

        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(9)
        self.stats_table.setHorizontalHeaderLabels([
            "Metric", "Obs Count", "Mean", "Median", "Min", "Max", "Std Dev", "95th %ile", "Peak Timestamp"
        ])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stats_table.setStyleSheet("QTableWidget { background:#050505; color:#ccc; border:1px solid #222; } QHeaderView::section { background:#111; color:#ff8f00; font-weight:bold; }")
        self.stats_table.setMinimumHeight(200)
        sl.addWidget(self.stats_table)
        content_layout.addWidget(stats_card)

        # 2. Dynamic Interpretations Card
        interp_card = QFrame()
        interp_card.setStyleSheet("background-color: #090909; border: 1px solid #1c1c1c; border-radius: 4px; padding: 15px;")
        il = QVBoxLayout(interp_card)
        it_title = QLabel("DATA-DRIVEN STATISTICAL FINDINGS & DYNAMICS")
        it_title.setStyleSheet("color: #26a69a; font-size: 12px; font-weight: bold;")
        il.addWidget(it_title)

        self.interp_text_area = QTextEdit()
        self.interp_text_area.setReadOnly(True)
        self.interp_text_area.setStyleSheet("background-color: #0d0d0d; border: 1px solid #222222; color: #dddddd; font-size: 12px; padding: 10px;")
        self.interp_text_area.setMinimumHeight(180)
        il.addWidget(self.interp_text_area)
        content_layout.addWidget(interp_card)

        # 3. Optional AI Insights Card
        ai_card = QFrame()
        ai_card.setStyleSheet("background-color: #090909; border: 1px solid #ff8f00; border-radius: 4px; padding: 15px;")
        al = QVBoxLayout(ai_card)

        ai_header = QHBoxLayout()
        ai_title = QLabel("SYSTEM ENGINEERING INSIGHTS & BOTTLENECK DIAGNOSIS")
        ai_title.setStyleSheet("color: #ff8f00; font-size: 12px; font-weight: bold;")
        ai_header.addWidget(ai_title)

        self.ai_badge_lbl = QLabel("● OFFLINE RULE-BASED ENGINE")
        self.ai_badge_lbl.setStyleSheet("color: #55d66f; font-weight: bold; font-size: 10px;")
        ai_header.addWidget(self.ai_badge_lbl)
        ai_header.addStretch()

        self.configure_ai_btn = QPushButton("⚙️ Configure Optional External LLM")
        self.configure_ai_btn.clicked.connect(self.open_ai_config_dialog)
        self.apply_button_style(self.configure_ai_btn)
        ai_header.addWidget(self.configure_ai_btn)
        al.addLayout(ai_header)

        self.ai_text_area = QTextEdit()
        self.ai_text_area.setReadOnly(True)
        self.ai_text_area.setStyleSheet("background-color: #0d0d0d; border: 1px solid #222222; color: #eeeeee; font-size: 12px; padding: 10px;")
        self.ai_text_area.setMinimumHeight(160)
        al.addWidget(self.ai_text_area)

        content_layout.addWidget(ai_card)

        scroll.setWidget(content)
        tab_layout.addWidget(scroll)

    # =================================================================
    # TAB 4: DATASET RECORDS TABLE
    # =================================================================

    def setup_records_tab(self):
        tab_layout = QVBoxLayout(self.tab_records)
        tab_layout.setContentsMargins(10, 10, 10, 10)

        self.records_table = QTableWidget()
        self.records_table.setStyleSheet("QTableWidget { background:#050505; color:#ccc; border:1px solid #222; } QHeaderView::section { background:#111; color:#26a69a; font-weight:bold; }")
        tab_layout.addWidget(self.records_table)

    # =================================================================
    # ACTIONS & WORKFLOW
    # =================================================================

    def _auto_load_recent_or_sample(self):
        """Try loading the latest real log or generate a self-contained sample log."""
        logs = sorted(glob.glob("data/logs/resource_log_*.csv"), key=os.path.getmtime, reverse=True)
        if logs:
            self.load_dataset(logs[0])
        else:
            sample_path = self.generate_sample_telemetry_if_needed()
            if sample_path:
                self.load_dataset(sample_path)

    def generate_sample_telemetry_if_needed(self) -> str:
        """Create a synthetic academic benchmark log to allow immediate demonstration."""
        sample_path = Path("data") / "logs" / "sample_academic_telemetry.csv"
        if sample_path.exists():
            return str(sample_path.resolve())

        sample_path.parent.mkdir(parents=True, exist_ok=True)
        np.random.seed(101)
        n = 120
        timestamps = [
            (pd.Timestamp("2026-10-16 14:00:00") + pd.Timedelta(seconds=i)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            for i in range(n)
        ]
        # Simulate CPU workload with a middle benchmark burst
        cpu = 15.0 + 10.0 * np.sin(np.linspace(0, 10, n)) + np.random.uniform(0, 8, n)
        cpu[40:70] += 55.0  # Synthetic stress test episode
        cpu = np.clip(cpu, 5.0, 98.0).round(1)

        # Thermal response lagging behind CPU
        temp = 48.0 + 0.35 * cpu + np.random.uniform(-1, 2, n)
        temp = np.clip(temp, 40.0, 86.0).round(1)

        ram_pct = 65.0 + np.cumsum(np.random.uniform(-0.1, 0.2, n))
        ram_pct = np.clip(ram_pct, 60.0, 88.0).round(1)
        total_ram = 16 * (1024**3)
        ram_used = (total_ram * (ram_pct / 100.0)).astype(int)
        ram_avail = total_ram - ram_used

        disk_r = np.random.exponential(1.5, n) * (1024 * 1024)
        disk_r[45:65] += 35 * 1024 * 1024
        disk_w = np.random.exponential(0.8, n) * (1024 * 1024)

        net_s = np.random.exponential(50, n) * 1024
        net_r = np.random.exponential(250, n) * 1024
        net_r[50:60] += 1200 * 1024

        df = pd.DataFrame({
            "timestamp": timestamps,
            "cpu_usage_percent": cpu,
            "cpu_temperature_c": temp,
            "ram_used_bytes": ram_used,
            "ram_available_bytes": ram_avail,
            "ram_usage_percent": ram_pct,
            "gpu_usage_percent": np.clip(cpu * 0.4 + np.random.uniform(0, 10, n), 0, 100).round(1),
            "gpu_temperature_c": np.clip(temp * 0.85, 35, 75).round(1),
            "gpu_memory_used_bytes": [2 * 1024**3] * n,
            "gpu_memory_total_bytes": [8 * 1024**3] * n,
            "gpu_index": [0] * n,
            "gpu_name": ["Synthetic Dedicated GPU"] * n,
            "disk_read_bytes_per_sec": disk_r.round(2),
            "disk_write_bytes_per_sec": disk_w.round(2),
            "network_sent_bytes_per_sec": net_s.round(2),
            "network_received_bytes_per_sec": net_r.round(2),
            "process_count": np.random.randint(220, 245, n),
            "battery_percent": [""] * n,
            "power_plugged": [""] * n,
        })
        df.to_csv(sample_path, index=False)
        return str(sample_path.resolve())

    def browse_and_load_csv(self):
        f, _ = QFileDialog.getOpenFileName(self, "Open Telemetry CSV Dataset", "data/logs", "CSV Files (*.csv);;All Files (*)")
        if f:
            self.load_dataset(f)

    def load_latest_log(self):
        logs = sorted(glob.glob("data/logs/resource_log_*.csv"), key=os.path.getmtime, reverse=True)
        if logs:
            self.load_dataset(logs[0])
        else:
            QMessageBox.information(self, "No Live Logs", "No live telemetry logs found in data/logs/ yet. Start logging from the sidebar or import a file.")

    def load_dataset(self, file_path: str):
        self.current_file_path = file_path
        self.dataset_label.setText(f"Dataset: {os.path.basename(file_path)}")
        self.run_pipeline()

    def run_pipeline(self):
        if not self.current_file_path:
            QMessageBox.warning(self, "No Dataset", "Please select or import a telemetry dataset first.")
            return

        self.progress_bar.show()
        self.run_pipeline_btn.setEnabled(False)

        dedup_rows = self.dedup_check.isChecked()
        rolling_w = self.rolling_spin.value()

        self.worker = PreprocessingWorker(self.current_file_path, dedup_rows, "keep_first", rolling_w)
        self.worker.finished.connect(self.on_pipeline_finished)
        self.worker.start()

    @Slot(object, object, str)
    def on_pipeline_finished(self, preprocessor, cleaned_df, error_msg):
        self.progress_bar.hide()
        self.run_pipeline_btn.setEnabled(True)

        if error_msg or preprocessor is None or cleaned_df is None:
            QMessageBox.critical(self, "Preprocessing Error", f"Failed to preprocess dataset:\n{error_msg}")
            return

        self.preprocessor = preprocessor
        self.cleaned_df = cleaned_df

        # Compute full statistical and interpretation suite
        self.current_stats = compute_descriptive_stats(self.cleaned_df)
        self.current_thresholds = compute_threshold_analysis(self.cleaned_df)
        self.current_correlations = compute_correlations(self.cleaned_df)
        self.current_interpretations = generate_interpretations(self.cleaned_df)

        # Default rule-based insights
        self.current_ai_insights = AIInsightsManager.generate_rule_based_insights(
            self.cleaned_df, self.current_stats, self.current_interpretations, self.current_thresholds
        )

        # Update all UI views
        self.update_kpi_cards()
        self.update_pyqtgraph_plots()
        self.update_exploratory_charts()
        self.update_insights_views()
        self.populate_records_table()

    # =================================================================
    # VIEW UPDATES
    # =================================================================

    def update_kpi_cards(self):
        df = self.cleaned_df
        if df is None or df.empty:
            return

        # 1. Records
        duration = self.preprocessor.summary.get("duration_seconds", 0)
        self.kpi_records.findChild(QLabel, "val_label").setText(f"{len(df):,} rows ({duration:.0f}s)")

        # 2. CPU
        cpu_s = self.current_stats.get("cpu_usage_percent")
        if cpu_s:
            self.kpi_cpu.findChild(QLabel, "val_label").setText(f"{cpu_s['mean']}% / {cpu_s['max']}%")
        else:
            self.kpi_cpu.findChild(QLabel, "val_label").setText("N/A")

        # 3. RAM
        ram_s = self.current_stats.get("ram_usage_percent")
        if ram_s:
            self.kpi_ram.findChild(QLabel, "val_label").setText(f"{ram_s['mean']}% / {ram_s['max']}%")
        else:
            self.kpi_ram.findChild(QLabel, "val_label").setText("N/A")

        # 4. Thermal
        cpu_t = self.current_stats.get("cpu_temperature_c")
        gpu_t = self.current_stats.get("gpu_temperature_c")
        c_str = f"{cpu_t['max']}°C" if cpu_t else "N/A"
        g_str = f"{gpu_t['max']}°C" if gpu_t else "N/A"
        self.kpi_temp.findChild(QLabel, "val_label").setText(f"{c_str} / {g_str}")

        # 5. Disk
        d_read = self.current_stats.get("disk_read_mb_per_sec")
        d_write = self.current_stats.get("disk_write_mb_per_sec")
        if d_read and d_write:
            self.kpi_disk.findChild(QLabel, "val_label").setText(f"{d_read['max']} / {d_write['max']} MB/s")
        else:
            self.kpi_disk.findChild(QLabel, "val_label").setText("N/A")

        # 6. Network
        n_dl = self.current_stats.get("network_recv_kb_per_sec")
        n_ul = self.current_stats.get("network_sent_kb_per_sec")
        if n_dl and n_ul:
            self.kpi_net.findChild(QLabel, "val_label").setText(f"{n_dl['max']} / {n_ul['max']} KB/s")
        else:
            self.kpi_net.findChild(QLabel, "val_label").setText("N/A")

    def update_pyqtgraph_plots(self):
        df = self.cleaned_df
        if df is None or df.empty:
            return

        x = np.arange(len(df))

        # CPU
        if "cpu_usage_percent" in df.columns:
            cpu = df["cpu_usage_percent"].fillna(0).values
            self.curve_cpu_raw.setData(x, cpu)
            if "cpu_usage_percent_rolling_avg" in df.columns:
                self.curve_cpu_roll.setData(x, df["cpu_usage_percent_rolling_avg"].fillna(0).values)
            self.interp_cpu.setText(self.current_interpretations.get("cpu", "CPU analysis complete."))

        # RAM
        if "ram_usage_percent" in df.columns:
            ram = df["ram_usage_percent"].fillna(0).values
            self.curve_ram.setData(x, ram)
            self.interp_ram.setText(self.current_interpretations.get("ram", "RAM analysis complete."))

        # Thermal
        if "cpu_temperature_c" in df.columns:
            c_temp = df["cpu_temperature_c"].fillna(0).values
            self.curve_cpu_temp.setData(x, c_temp)
        if "gpu_temperature_c" in df.columns:
            g_temp = df["gpu_temperature_c"].fillna(0).values
            self.curve_gpu_temp.setData(x, g_temp)
        self.interp_temp.setText(self.current_interpretations.get("temperature", "Thermal analysis complete."))

        # Storage
        if "disk_read_mb_per_sec" in df.columns:
            self.curve_disk_read.setData(x, df["disk_read_mb_per_sec"].fillna(0).values)
        if "disk_write_mb_per_sec" in df.columns:
            self.curve_disk_write.setData(x, df["disk_write_mb_per_sec"].fillna(0).values)
        self.interp_disk.setText(self.current_interpretations.get("storage", "Storage analysis complete."))

        # Network
        if "network_recv_kb_per_sec" in df.columns:
            self.curve_net_recv.setData(x, df["network_recv_kb_per_sec"].fillna(0).values)
        if "network_sent_kb_per_sec" in df.columns:
            self.curve_net_sent.setData(x, df["network_sent_kb_per_sec"].fillna(0).values)
        self.interp_net.setText(self.current_interpretations.get("network", "Network analysis complete."))

    def update_exploratory_charts(self):
        df = self.cleaned_df
        if df is None or df.empty:
            return

        self.canvas_scatter.update_scatter(df, "cpu_usage_percent", "ram_usage_percent")
        self.canvas_dist.update_distributions(df)
        self.canvas_heatmap.update_heatmap(self.current_correlations.get("matrix", {}))

    def update_insights_views(self):
        # Stats table
        self.stats_table.setRowCount(len(self.current_stats))
        for row, (col_name, s) in enumerate(self.current_stats.items()):
            self.stats_table.setItem(row, 0, QTableWidgetItem(col_name))
            self.stats_table.setItem(row, 1, QTableWidgetItem(f"{s['count']:,}"))
            self.stats_table.setItem(row, 2, QTableWidgetItem(f"{s['mean']}"))
            self.stats_table.setItem(row, 3, QTableWidgetItem(f"{s['median']}"))
            self.stats_table.setItem(row, 4, QTableWidgetItem(f"{s['min']}"))
            self.stats_table.setItem(row, 5, QTableWidgetItem(f"{s['max']}"))
            self.stats_table.setItem(row, 6, QTableWidgetItem(f"{s['std']}"))
            self.stats_table.setItem(row, 7, QTableWidgetItem(f"{s['p95']}"))
            self.stats_table.setItem(row, 8, QTableWidgetItem(str(s['peak_timestamp'])))

        # Written interpretations
        interp_lines = []
        for k, text in self.current_interpretations.items():
            if k == "executive_summary":
                continue
            interp_lines.append(f"### {k.replace('_', ' ').upper()} TELEMETRY")
            interp_lines.append(text + "\n")
        self.interp_text_area.setMarkdown("\n".join(interp_lines))

        # AI Insights
        ai = self.current_ai_insights
        self.ai_badge_lbl.setText(f"● {ai.get('badge', 'RULE-BASED').upper()}")
        ai_lines = []
        ai_lines.append(f"*{ai.get('disclaimer', '')}*\n")
        ai_lines.append("#### Key Diagnostic Observations:")
        for obs in ai.get("insights", []):
            ai_lines.append(f"- {obs}")
        ai_lines.append("\n#### Engineering Recommendations:")
        for rec in ai.get("recommendations", []):
            ai_lines.append(f"- {rec}")
        self.ai_text_area.setMarkdown("\n".join(ai_lines))

    def populate_records_table(self):
        df = self.cleaned_df
        if df is None or df.empty:
            return

        display_df = df.head(100)
        cols = list(display_df.columns)
        self.records_table.setColumnCount(len(cols))
        self.records_table.setHorizontalHeaderLabels(cols)
        self.records_table.setRowCount(len(display_df))

        for r_idx in range(len(display_df)):
            for c_idx, c_name in enumerate(cols):
                val = display_df.iloc[r_idx, c_idx]
                val_str = "" if pd.isna(val) else str(val)
                self.records_table.setItem(r_idx, c_idx, QTableWidgetItem(val_str))

    # =================================================================
    # MODALS & EXPORTS
    # =================================================================

    def show_audit_dialog(self):
        if not self.preprocessor or not self.preprocessor.summary:
            QMessageBox.information(self, "No Audit Summary", "Run preprocessing first to inspect audit details.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Preprocessing Pipeline Audit Report")
        dialog.resize(700, 500)
        l = QVBoxLayout(dialog)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet("background:#0d0d0d; color:#dddddd; font-family:monospace; font-size:11px;")
        text_edit.setMarkdown(self.preprocessor.get_summary_text())
        l.addWidget(text_edit)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        l.addWidget(close_btn)
        dialog.exec()

    def open_ai_config_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Configure Optional External AI Analytics")
        dialog.resize(500, 320)
        dialog.setStyleSheet("background-color:#121212; color:#dddddd;")
        l = QVBoxLayout(dialog)
        l.setSpacing(12)

        desc = QLabel(
            "<b>Optional LLM Analytics Integration</b><br>"
            "Zero raw telemetry, personal files, or network addresses are ever transmitted.<br>"
            "Only aggregated statistical summaries (min/max/means) will be sent if you consent."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#aaa; font-size:11px;")
        l.addWidget(desc)

        # Provider combo
        prov_lbl = QLabel("AI Provider:")
        l.addWidget(prov_lbl)
        prov_combo = QComboBox()
        prov_combo.addItems(["Gemini", "OpenAI", "Ollama (Local)"])
        prov_combo.setStyleSheet("background:#222; color:#fff; padding:4px;")
        l.addWidget(prov_combo)

        # API Key
        key_lbl = QLabel("API Key (Stored in memory only):")
        l.addWidget(key_lbl)
        key_input = QLineEdit()
        key_input.setEchoMode(QLineEdit.Password)
        key_input.setPlaceholderText("Enter API Key or leave empty for local Ollama")
        key_input.setStyleSheet("background:#222; color:#fff; padding:5px; border:1px solid #444;")
        l.addWidget(key_input)

        # Consent checkbox
        consent_chk = QCheckBox("I explicitly consent to transmitting aggregated statistical summaries to this service.")
        consent_chk.setStyleSheet("color:#ff8f00; font-size:10px;")
        l.addWidget(consent_chk)

        # Buttons
        btn_box = QHBoxLayout()
        submit_btn = QPushButton("Submit AI Analysis Request")
        self.apply_button_style(submit_btn, primary=True)

        def do_submit():
            if not consent_chk.isChecked():
                QMessageBox.warning(dialog, "Consent Required", "You must provide explicit consent before sending telemetry statistics.")
                return
            provider = prov_combo.currentText().split()[0].lower()
            key = key_input.text().strip()
            if not key and provider != "ollama":
                QMessageBox.warning(dialog, "Key Required", "Please enter an API Key for the chosen provider.")
                return

            dialog.accept()
            self._invoke_external_ai(provider, key)

        submit_btn.clicked.connect(do_submit)
        btn_box.addStretch()
        btn_box.addWidget(submit_btn)
        l.addLayout(btn_box)
        dialog.exec()

    def _invoke_external_ai(self, provider: str, api_key: str):
        self.progress_bar.show()
        try:
            payload = {
                "cpu_mean": self.current_stats.get("cpu_usage_percent", {}).get("mean"),
                "cpu_max": self.current_stats.get("cpu_usage_percent", {}).get("max"),
                "cpu_p95": self.current_stats.get("cpu_usage_percent", {}).get("p95"),
                "ram_mean": self.current_stats.get("ram_usage_percent", {}).get("mean"),
                "ram_max": self.current_stats.get("ram_usage_percent", {}).get("max"),
                "cpu_temp_max": self.current_stats.get("cpu_temperature_c", {}).get("max"),
                "disk_peak_mb": self.current_stats.get("disk_read_mb_per_sec", {}).get("max"),
                "net_peak_kb": self.current_stats.get("network_recv_kb_per_sec", {}).get("max"),
                "duration_sec": self.preprocessor.summary.get("duration_seconds"),
                "record_count": len(self.cleaned_df) if self.cleaned_df is not None else 0,
            }
            res = AIInsightsManager.query_external_ai(payload, provider=provider, api_key=api_key)
            self.current_ai_insights = res
            self.update_insights_views()
            QMessageBox.information(self, "AI Analysis Complete", f"Successfully synthesized insights using {provider.upper()}.")
        except Exception as e:
            QMessageBox.critical(self, "AI Query Failed", f"External AI invocation failed:\n{e}\n\nReverting safely to offline rule-based diagnostics.")
        finally:
            self.progress_bar.hide()

    def export_cleaned_dataset(self):
        if self.cleaned_df is None:
            QMessageBox.warning(self, "No Cleaned Data", "Please load and preprocess a dataset first.")
            return

        f, _ = QFileDialog.getSaveFileName(self, "Save Cleaned Telemetry Dataset", "data/cleaned_telemetry.csv", "CSV Files (*.csv)")
        if f:
            try:
                self.preprocessor.export_cleaned_csv(f)
                QMessageBox.information(self, "Export Successful", f"Cleaned dataset saved to:\n{f}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Error saving cleaned CSV: {e}")

    def generate_and_export_report(self):
        if self.cleaned_df is None:
            QMessageBox.warning(self, "No Data", "Please load and preprocess a dataset first.")
            return

        try:
            # Package Matplotlib figures
            figures = {
                "Multi-Metric Pearson Correlation Heatmap": self.canvas_heatmap.fig,
                "Resource Utilization Histograms & Density": self.canvas_dist.fig,
                "CPU vs RAM Bivariate Cross-Comparison": self.canvas_scatter.fig,
            }
            html_f, json_f = export_analytics_report(
                self.preprocessor,
                stats=self.current_stats,
                thresholds=self.current_thresholds,
                correlations=self.current_correlations,
                interpretations=self.current_interpretations,
                ai_insights=self.current_ai_insights,
                figures=figures,
            )
            QMessageBox.information(
                self,
                "Analytics Report Generated",
                f"Comprehensive DVP Telemetry Report generated successfully!\n\nHTML: {html_f}\nJSON: {json_f}\n\nOpening report in browser..."
            )
            import webbrowser
            webbrowser.open(f"file:///{os.path.abspath(html_f)}")
        except Exception as e:
            QMessageBox.critical(self, "Report Generation Error", f"Failed to generate report: {e}")
