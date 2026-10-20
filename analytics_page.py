"""Historical Telemetry Analytics & Interactive Visualization Page.

Polished, professional, enterprise-grade single-page analytics dashboard
comparable in visual quality to Tableau and Power BI:
- Real-time live hardware telemetry stream (psutil / NVML) with 60fps graph updates
- Dark charcoal enterprise theme (#0a0d14 / #131823) with restrained accents
- Single continuous scrollable page containing all 4 KPI cards and 6 varied visualizations
- Prominent primary actions: Import CSV Dataset & Export Analytics Report
- Interactive hover tooltips, zoom, and pan
- Dynamic calculation of all metrics directly from live data or loaded dataset schema
- Graceful handling of missing metrics, empty datasets, and invalid readings
- Transparent viva-ready data quality and preprocessing audit summaries
"""

import os
import glob
import math
from pathlib import Path
from typing import Optional, Dict, Any, List

import numpy as np
import pandas as pd
import pyqtgraph as pg

from PySide6.QtCore import Qt, QThread, Signal, Slot, QRectF, QPointF, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPainterPath
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
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
    QScrollArea,
    QDialog,
    QTextEdit,
    QLineEdit,
    QProgressBar,
    QMenu,
    QSizePolicy,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from dashboard import CarbonFiberBackground
from telemetry_logger import TelemetrySampler
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
# CUSTOM POWER-BI GRADE RADIAL GAUGE WIDGET (CHART 6)
# =====================================================================

class HealthScoreGaugeWidget(QWidget):
    """Custom high-precision hardware-accelerated radial gauge indicator.
    
    Renders a deterministic 0-100 system health score with:
    - 240-degree background track and glowing tier-colored arc
    - Large center score callout and tier status badge
    - Subtitle metric penalty breakdown chips (CPU, RAM, Thermals)
    - Full explanation of deterministic scoring methodology on hover
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.score: Optional[float] = None
        self.tier_name: str = "Awaiting Data"
        self.tier_color = QColor("#64748b")
        self.cpu_penalty: float = 0.0
        self.ram_penalty: float = 0.0
        self.thermal_penalty: float = 0.0
        self.setMinimumHeight(240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.setToolTip(
            "<b>Deterministic System Health Score (0 - 100)</b><br>"
            "Formula: 100 - (CPU Penalty + RAM Penalty + Thermal Penalty)<br><br>"
            "• <b>CPU Penalty (max 35)</b>: Penalizes mean load > 30% and peak spikes > 70% / 85%<br>"
            "• <b>RAM Penalty (max 35)</b>: Penalizes mean memory > 70% and sustained usage > 85%<br>"
            "• <b>Thermal Penalty (max 30)</b>: Penalizes peak core temperatures > 65°C and > 80°C<br><br>"
            "<b>Tiers:</b><br>"
            "• 85 - 100: OPTIMAL & HEALTHY (Green)<br>"
            "• 70 - 84: GOOD OPERATING STATE (Teal)<br>"
            "• 55 - 69: MODERATE LOAD (Amber)<br>"
            "• 0 - 54: CRITICAL STRESS / THROTTLING (Red)"
        )

    def set_score_breakdown(
        self,
        score: Optional[float],
        cpu_pen: float = 0.0,
        ram_pen: float = 0.0,
        thermal_pen: float = 0.0,
    ):
        self.score = score
        self.cpu_penalty = cpu_pen
        self.ram_penalty = ram_pen
        self.thermal_penalty = thermal_pen

        if score is None:
            self.tier_name = "UNAVAILABLE"
            self.tier_color = QColor("#64748b")
        elif score >= 85:
            self.tier_name = "OPTIMAL & HEALTHY"
            self.tier_color = QColor("#10b981")  # Emerald
        elif score >= 70:
            self.tier_name = "GOOD STATE"
            self.tier_color = QColor("#14b8a6")  # Teal
        elif score >= 55:
            self.tier_name = "MODERATE LOAD"
            self.tier_color = QColor("#f59e0b")  # Amber
        else:
            self.tier_name = "CRITICAL / STRESSED"
            self.tier_color = QColor("#ef4444")  # Crimson

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        center_x = w / 2.0
        center_y = h * 0.46
        radius = min(w * 0.38, h * 0.38, 95.0)

        arc_rect = QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2)

        start_angle = 210 * 16
        span_angle = -240 * 16

        pen_width = max(10.0, radius * 0.16)

        # 1. Background track
        track_pen = QPen(QColor("#1e2638"), pen_width)
        track_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(arc_rect, start_angle, span_angle)

        # 2. Active colored arc
        if self.score is not None:
            clamped_pct = max(0.0, min(1.0, self.score / 100.0))
            active_span = int(span_angle * clamped_pct)

            active_pen = QPen(self.tier_color, pen_width)
            active_pen.setCapStyle(Qt.RoundCap)
            painter.setPen(active_pen)
            painter.drawArc(arc_rect, start_angle, active_span)

            # Center Score
            painter.setPen(QColor("#ffffff"))
            font_score = QFont("Segoe UI", int(radius * 0.36), QFont.Bold)
            painter.setFont(font_score)
            painter.drawText(
                QRectF(center_x - radius, center_y - radius * 0.55, radius * 2, radius * 0.75),
                Qt.AlignCenter,
                f"{int(round(self.score))}",
            )

            # Subtitle
            painter.setPen(QColor("#94a3b8"))
            font_sub = QFont("Segoe UI", 9)
            painter.setFont(font_sub)
            painter.drawText(
                QRectF(center_x - radius, center_y + radius * 0.15, radius * 2, 20),
                Qt.AlignCenter,
                "SCORE OUT OF 100",
            )
        else:
            painter.setPen(QColor("#64748b"))
            font_na = QFont("Segoe UI", int(radius * 0.32), QFont.Bold)
            painter.setFont(font_na)
            painter.drawText(
                QRectF(center_x - radius, center_y - radius * 0.4, radius * 2, radius * 0.8),
                Qt.AlignCenter,
                "N/A",
            )

        # 3. Tier Status Badge
        badge_y = center_y + radius * 0.48
        badge_rect = QRectF(center_x - 85, badge_y, 170, 22)
        painter.setPen(Qt.NoPen)
        badge_bg = QColor(self.tier_color)
        badge_bg.setAlpha(35)
        painter.setBrush(QBrush(badge_bg))
        painter.drawRoundedRect(badge_rect, 11, 11)

        painter.setPen(self.tier_color)
        font_tier = QFont("Segoe UI", 8, QFont.Bold)
        font_tier.setLetterSpacing(QFont.AbsoluteSpacing, 0.8)
        painter.setFont(font_tier)
        painter.drawText(badge_rect, Qt.AlignCenter, f"● {self.tier_name}")

        # 4. Deduction Breakdown Chips below
        chip_y = badge_y + 28
        chip_rect = QRectF(10, chip_y, w - 20, 24)
        painter.setPen(QColor("#94a3b8"))
        font_chips = QFont("Segoe UI", 8)
        painter.setFont(font_chips)

        if self.score is not None:
            breakdown_text = (
                f"CPU Penalty: -{self.cpu_penalty:.1f}   |   "
                f"RAM Penalty: -{self.ram_penalty:.1f}   |   "
                f"Thermal: -{self.thermal_penalty:.1f}"
            )
        else:
            breakdown_text = "Insufficient telemetry columns to compute health index"

        painter.drawText(chip_rect, Qt.AlignCenter, breakdown_text)
        painter.end()


# =====================================================================
# MATPLOTLIB CANVASES (CHARTS 2, 4, 5)
# =====================================================================

class RamDonutCanvas(FigureCanvasQTAgg):
    """Chart 2: RAM Usage Composition Donut Chart."""

    def __init__(self, parent=None):
        self.fig = Figure(figsize=(4.8, 3.2), facecolor="#131823")
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(left=0.05, right=0.95, top=0.90, bottom=0.10)
        self.draw_empty()

    def draw_empty(self, message="Awaiting memory telemetry..."):
        self.ax.clear()
        self.ax.set_facecolor("#131823")
        self.ax.text(
            0.5, 0.5, message,
            ha="center", va="center", color="#64748b", fontsize=9,
        )
        self.ax.axis("off")
        self.draw_idle()

    def update_donut(self, df: pd.DataFrame):
        self.ax.clear()
        self.ax.set_facecolor("#131823")

        if df is None or df.empty:
            self.draw_empty("No dataset records available")
            return

        has_gb = "ram_used_gb" in df.columns and "ram_available_gb" in df.columns
        has_bytes = "ram_used_bytes" in df.columns and "ram_available_bytes" in df.columns
        has_pct = "ram_usage_percent" in df.columns

        if not (has_gb or has_bytes or has_pct):
            self.draw_empty("RAM metrics not present in dataset")
            return

        if has_gb:
            used_val = float(df["ram_used_gb"].dropna().iloc[-1] if not df["ram_used_gb"].dropna().empty else 0)
            avail_val = float(df["ram_available_gb"].dropna().iloc[-1] if not df["ram_available_gb"].dropna().empty else 0)
            unit = "GB"
            used_pct = round((used_val / max(0.001, used_val + avail_val)) * 100, 1)
        elif has_bytes:
            used_val = float(df["ram_used_bytes"].dropna().iloc[-1] / (1024**3))
            avail_val = float(df["ram_available_bytes"].dropna().iloc[-1] / (1024**3))
            unit = "GB"
            used_pct = round((used_val / max(0.001, used_val + avail_val)) * 100, 1)
        else:
            used_pct = float(df["ram_usage_percent"].dropna().iloc[-1] if not df["ram_usage_percent"].dropna().empty else 0)
            used_val = used_pct
            avail_val = max(0.0, 100.0 - used_pct)
            unit = "%"

        sizes = [used_val, avail_val]
        colors = ["#a855f7", "#1e293b"]

        wedges, _ = self.ax.pie(
            sizes,
            colors=colors,
            startangle=90,
            counterclock=False,
            wedgeprops=dict(width=0.38, edgecolor="#131823", linewidth=2.5),
        )

        self.ax.text(
            0, 0.08, f"{used_pct:.1f}%",
            ha="center", va="center", color="#ffffff",
            fontsize=18, fontweight="bold",
        )
        sub_label = f"Used ({used_val:.1f} {unit})" if unit == "GB" else "Utilization"
        self.ax.text(
            0, -0.16, sub_label,
            ha="center", va="center", color="#94a3b8",
            fontsize=8, fontweight="bold",
        )

        if unit == "GB":
            labels = [
                f"Used: {used_val:.1f} GB ({used_pct:.1f}%)",
                f"Avail: {avail_val:.1f} GB ({100-used_pct:.1f}%)",
            ]
        else:
            labels = [
                f"Utilized: {used_val:.1f}%",
                f"Unutilized: {avail_val:.1f}%",
            ]

        self.ax.legend(
            wedges, labels,
            loc="lower center",
            bbox_to_anchor=(0.5, -0.06),
            frameon=False,
            fontsize=8,
            labelcolor="#cbd5e1",
            ncol=2,
            handlelength=0.8,
            handletextpad=0.5,
        )

        self.ax.axis("equal")
        self.draw_idle()


class DiskThroughputCanvas(FigureCanvasQTAgg):
    """Chart 4: Storage Read/Write Throughput Grouped Bar Chart."""

    def __init__(self, parent=None):
        self.fig = Figure(figsize=(4.8, 3.2), facecolor="#131823")
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(left=0.12, right=0.96, top=0.88, bottom=0.20)
        self.draw_empty()

    def draw_empty(self, message="Awaiting storage telemetry..."):
        self.ax.clear()
        self.ax.set_facecolor("#131823")
        self.ax.text(
            0.5, 0.5, message,
            ha="center", va="center", color="#64748b", fontsize=9,
        )
        self.ax.axis("off")
        self.draw_idle()

    def update_bars(self, df: pd.DataFrame):
        self.ax.clear()
        self.ax.set_facecolor("#131823")

        if df is None or df.empty:
            self.draw_empty("No dataset records available")
            return

        r_col = "disk_read_mb_per_sec" if "disk_read_mb_per_sec" in df.columns else None
        w_col = "disk_write_mb_per_sec" if "disk_write_mb_per_sec" in df.columns else None

        if not r_col or not w_col:
            if "disk_read_bytes_per_sec" in df.columns and "disk_write_bytes_per_sec" in df.columns:
                df = df.copy()
                df["disk_read_mb_per_sec"] = (df["disk_read_bytes_per_sec"] / (1024 * 1024)).round(2)
                df["disk_write_mb_per_sec"] = (df["disk_write_bytes_per_sec"] / (1024 * 1024)).round(2)
                r_col = "disk_read_mb_per_sec"
                w_col = "disk_write_mb_per_sec"
            else:
                self.draw_empty("Disk throughput columns missing in dataset")
                return

        n_total = len(df)
        if n_total <= 35:
            sample_df = df
            indices = np.arange(len(sample_df))
            bar_width = 0.38
        else:
            step = max(1, n_total // 30)
            sample_df = df.iloc[::step].reset_index(drop=True)
            indices = np.arange(len(sample_df))
            bar_width = 0.38

        read_vals = sample_df[r_col].values
        write_vals = sample_df[w_col].values

        read_plot = np.where(np.isnan(read_vals), 0, read_vals)
        write_plot = np.where(np.isnan(write_vals), 0, write_vals)

        self.ax.bar(
            indices - bar_width / 2.0, read_plot,
            width=bar_width, color="#38bdf8", alpha=0.9, label="Disk Read",
        )
        self.ax.bar(
            indices + bar_width / 2.0, write_plot,
            width=bar_width, color="#f59e0b", alpha=0.9, label="Disk Write",
        )

        self.ax.set_ylabel("Throughput (MB/s)", color="#94a3b8", fontsize=8)
        self.ax.set_xlabel("Sample Timeline Order", color="#94a3b8", fontsize=8)
        self.ax.tick_params(colors="#64748b", labelsize=7)
        self.ax.grid(True, linestyle=":", color="#1e2638", alpha=0.7, axis="y")

        for spine in ["top", "right"]:
            self.ax.spines[spine].set_visible(False)
        self.ax.spines["left"].set_color("#1e2638")
        self.ax.spines["bottom"].set_color("#1e2638")

        peak_r = df[r_col].dropna().max() if not df[r_col].dropna().empty else 0.0
        peak_w = df[w_col].dropna().max() if not df[w_col].dropna().empty else 0.0

        self.ax.legend(
            loc="upper right",
            frameon=True,
            facecolor="#181f2f",
            edgecolor="#26334a",
            labelcolor="#cbd5e1",
            fontsize=7,
        )

        self.ax.text(
            0.02, 0.94,
            f"Peak Read: {peak_r:.1f} MB/s   |   Peak Write: {peak_w:.1f} MB/s",
            transform=self.ax.transAxes,
            color="#cbd5e1", fontsize=7, fontweight="bold",
            va="top", ha="left",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#181f2f", edgecolor="#26334a", alpha=0.85),
        )

        self.draw_idle()


class CpuDistributionCanvas(FigureCanvasQTAgg):
    """Chart 5: CPU Utilization Distribution Histogram."""

    def __init__(self, parent=None):
        self.fig = Figure(figsize=(4.8, 3.2), facecolor="#131823")
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(left=0.12, right=0.96, top=0.88, bottom=0.20)
        self.draw_empty()

    def draw_empty(self, message="Awaiting CPU telemetry..."):
        self.ax.clear()
        self.ax.set_facecolor("#131823")
        self.ax.text(
            0.5, 0.5, message,
            ha="center", va="center", color="#64748b", fontsize=9,
        )
        self.ax.axis("off")
        self.draw_idle()

    def update_histogram(self, df: pd.DataFrame):
        self.ax.clear()
        self.ax.set_facecolor("#131823")

        if df is None or df.empty or "cpu_usage_percent" not in df.columns:
            self.draw_empty("CPU usage metric not available")
            return

        cpu_series = df["cpu_usage_percent"].dropna()
        if len(cpu_series) == 0:
            self.draw_empty("No valid CPU readings found")
            return

        n_samples = len(cpu_series)
        mean_val = float(cpu_series.mean())
        median_val = float(cpu_series.median())
        std_val = float(cpu_series.std()) if n_samples > 1 else 0.0

        bin_count = max(5, min(20, int(np.sqrt(n_samples)) * 2))

        self.ax.hist(
            cpu_series,
            bins=bin_count,
            color="#0284c7",
            edgecolor="#0f172a",
            alpha=0.85,
            linewidth=1.2,
        )

        self.ax.axvline(
            mean_val, color="#f59e0b", linestyle="--", linewidth=1.8,
            label=f"Mean: {mean_val:.1f}%",
        )
        self.ax.axvline(
            median_val, color="#2dd4bf", linestyle=":", linewidth=1.8,
            label=f"Median: {median_val:.1f}%",
        )

        self.ax.set_xlabel("CPU Utilization (%)", color="#94a3b8", fontsize=8)
        self.ax.set_ylabel("Frequency (Samples)", color="#94a3b8", fontsize=8)
        self.ax.tick_params(colors="#64748b", labelsize=7)
        self.ax.grid(True, linestyle=":", color="#1e2638", alpha=0.7, axis="y")

        for spine in ["top", "right"]:
            self.ax.spines[spine].set_visible(False)
        self.ax.spines["left"].set_color("#1e2638")
        self.ax.spines["bottom"].set_color("#1e2638")

        sample_badge = f"N = {n_samples:,} samples"
        if n_samples < 30:
            sample_badge += " (Limited Sample)"

        self.ax.text(
            0.02, 0.94,
            f"{sample_badge}   |   σ = {std_val:.1f}%",
            transform=self.ax.transAxes,
            color="#cbd5e1", fontsize=7, fontweight="bold",
            va="top", ha="left",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#181f2f", edgecolor="#26334a", alpha=0.85),
        )

        self.ax.legend(
            loc="upper right",
            frameon=True,
            facecolor="#181f2f",
            edgecolor="#26334a",
            labelcolor="#cbd5e1",
            fontsize=7,
        )

        self.draw_idle()


# =====================================================================
# COLLAPSIBLE ACCORDION PANEL HELPER
# =====================================================================

class CollapsiblePanel(QFrame):
    """Clean enterprise disclosure card that toggles visibility on click."""

    def __init__(self, title_text: str, content_widget: QWidget, parent=None, expanded=False):
        super().__init__(parent)
        self.content_widget = content_widget
        self.expanded = expanded

        self.setStyleSheet("""
            CollapsiblePanel {
                background-color: #131823;
                border: 1px solid #1e2638;
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        self.toggle_btn = QPushButton()
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                background: transparent;
                border: none;
                color: #e2e8f0;
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 0.8px;
                padding: 4px 0px;
            }
            QPushButton:hover {
                color: #38bdf8;
            }
        """)
        self.title_text = title_text
        self.toggle_btn.clicked.connect(self.toggle)
        layout.addWidget(self.toggle_btn)

        layout.addWidget(self.content_widget)
        self._update_state()

    def toggle(self):
        self.expanded = not self.expanded
        self._update_state()

    def _update_state(self):
        arrow = "▼" if self.expanded else "▶"
        self.toggle_btn.setText(f"{arrow}  {self.title_text}")
        self.content_widget.setVisible(self.expanded)


# =====================================================================
# MAIN SINGLE-PAGE ANALYTICS DASHBOARD
# =====================================================================

class AnalyticsPage(CarbonFiberBackground):
    """Modern single-page Historical Telemetry Analytics & Live Insights dashboard."""

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

        # Real-time Live Stream telemetry engine
        self.sampler = TelemetrySampler()
        self.live_buffer: List[Dict[str, Any]] = []
        self.max_live_samples: int = 60
        self.is_live: bool = True
        self.live_timer = QTimer(self)
        self.live_timer.setInterval(1000)
        self.live_timer.timeout.connect(self._on_live_tick)

        self.setup_ui()
        self._auto_load_recent_or_sample()

    def set_refresh_interval(self, ms: int):
        """Allow main speed selector to set live update interval."""
        if hasattr(self, "live_timer"):
            self.live_timer.setInterval(max(250, ms))

    # =================================================================
    # UI SETUP
    # =================================================================

    def setup_ui(self):
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(24, 18, 24, 18)
        page_layout.setSpacing(12)

        # -------------------------------------------------------------
        # 1. COMPACT ENTERPRISE HEADER
        # -------------------------------------------------------------
        header_card = QFrame()
        header_card.setStyleSheet("background-color: #10141f; border: 1px solid #1e2638; border-radius: 6px;")
        hl = QHBoxLayout(header_card)
        hl.setContentsMargins(16, 12, 16, 12)
        hl.setSpacing(16)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title_lbl = QLabel("HISTORICAL TELEMETRY ANALYTICS")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #f1f5f9; letter-spacing: 1.2px;")

        subtitle_lbl = QLabel("System Performance, Statistical Diagnostics & Live Insights")
        subtitle_lbl.setStyleSheet("font-size: 11px; color: #94a3b8;")

        title_box.addWidget(title_lbl)
        title_box.addWidget(subtitle_lbl)
        hl.addLayout(title_box)

        hl.addStretch()

        # Primary Actions in Header
        self.import_btn = QPushButton("📁 Import CSV Dataset")
        self.import_btn.setCursor(Qt.PointingHandCursor)
        self.import_btn.clicked.connect(self.browse_and_load_csv)
        self.apply_button_style(self.import_btn, primary=True)
        hl.addWidget(self.import_btn)

        self.export_report_btn = QPushButton("📄 Export Analytics Report")
        self.export_report_btn.setCursor(Qt.PointingHandCursor)
        self.export_report_btn.clicked.connect(self.generate_and_export_report)
        self.apply_button_style(self.export_report_btn, accent=True)
        hl.addWidget(self.export_report_btn)

        self.more_btn = QPushButton("⚙ More Actions ▾")
        self.more_btn.setCursor(Qt.PointingHandCursor)
        self.apply_button_style(self.more_btn)
        self.setup_more_actions_menu()
        hl.addWidget(self.more_btn)

        page_layout.addWidget(header_card)

        # -------------------------------------------------------------
        # 2. FILTER & PREPROCESSING TOOLBAR (WITH LIVE MODE TOGGLE)
        # -------------------------------------------------------------
        filter_bar = QFrame()
        filter_bar.setStyleSheet("background-color: #10141f; border: 1px solid #1e2638; border-radius: 6px;")
        fl = QHBoxLayout(filter_bar)
        fl.setContentsMargins(14, 8, 14, 8)
        fl.setSpacing(14)

        # Live Feed Toggle Button
        self.live_toggle_btn = QPushButton("🔴 LIVE FEED: ACTIVE")
        self.live_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.live_toggle_btn.clicked.connect(self.toggle_live_feed)
        self.apply_button_style(self.live_toggle_btn, accent=True, small=True)
        fl.addWidget(self.live_toggle_btn)

        self.dataset_label = QLabel("Mode: 🔴 Real-Time Live Feed")
        self.dataset_label.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")
        fl.addWidget(self.dataset_label)

        fl.addStretch()

        # Timeline filter
        tf_lbl = QLabel("Time Filter:")
        tf_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        fl.addWidget(tf_lbl)

        self.time_filter_combo = QComboBox()
        self.time_filter_combo.addItems([
            "All Timeline Records (100%)",
            "First 50% Timeline",
            "Second 50% Timeline",
            "Peak Activity Window",
        ])
        self.time_filter_combo.setStyleSheet("""
            QComboBox {
                background: #181f2f;
                color: #e2e8f0;
                border: 1px solid #26334a;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: bold;
            }
            QComboBox QAbstractItemView {
                background: #131823;
                color: #ffffff;
                selection-background-color: #0284c7;
            }
        """)
        self.time_filter_combo.currentIndexChanged.connect(self.on_filter_changed)
        fl.addWidget(self.time_filter_combo)

        # Deduplicate checkbox
        self.dedup_check = QCheckBox("Deduplicate Records")
        self.dedup_check.setChecked(True)
        self.dedup_check.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        self.dedup_check.stateChanged.connect(self.on_filter_changed)
        fl.addWidget(self.dedup_check)

        # Rolling Window selector
        rw_lbl = QLabel("Rolling Window:")
        rw_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        fl.addWidget(rw_lbl)

        self.rolling_spin = QSpinBox()
        self.rolling_spin.setRange(1, 30)
        self.rolling_spin.setValue(5)
        self.rolling_spin.setSuffix(" samples")
        self.rolling_spin.setStyleSheet("""
            QSpinBox {
                background: #181f2f;
                color: #ffffff;
                border: 1px solid #26334a;
                border-radius: 4px;
                padding: 3px 6px;
                font-size: 10px;
                font-weight: bold;
            }
        """)
        self.rolling_spin.valueChanged.connect(self.on_filter_changed)
        fl.addWidget(self.rolling_spin)

        # Preprocessing trigger
        self.rerun_btn = QPushButton("⚡ Re-run Pipeline")
        self.rerun_btn.setCursor(Qt.PointingHandCursor)
        self.rerun_btn.clicked.connect(self.run_pipeline)
        self.apply_button_style(self.rerun_btn, small=True)
        fl.addWidget(self.rerun_btn)

        page_layout.addWidget(filter_bar)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(2)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #38bdf8; }")
        self.progress_bar.hide()
        page_layout.addWidget(self.progress_bar)

        # -------------------------------------------------------------
        # 3. CONTINUOUS SCROLLABLE DASHBOARD BODY
        # -------------------------------------------------------------
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #0d1117;
                width: 8px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #1e2638;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #38bdf8;
            }
        """)

        dashboard_container = QWidget()
        dash_layout = QVBoxLayout(dashboard_container)
        dash_layout.setContentsMargins(0, 4, 0, 16)
        dash_layout.setSpacing(14)

        # -------------------------------------------------------------
        # SECTION A: EXACTLY FOUR PRIMARY KPI CARDS
        # -------------------------------------------------------------
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)

        self.kpi_cpu = self.create_kpi_card(
            title="AVERAGE CPU UTILIZATION",
            accent_color="#38bdf8",
            initial_val="N/A",
            initial_sub="Peak: N/A • Rolling Trend",
        )
        kpi_row.addWidget(self.kpi_cpu)

        self.kpi_ram = self.create_kpi_card(
            title="AVERAGE RAM UTILIZATION",
            accent_color="#a855f7",
            initial_val="N/A",
            initial_sub="Peak: N/A • Threshold 85%",
        )
        kpi_row.addWidget(self.kpi_ram)

        self.kpi_temp = self.create_kpi_card(
            title="MAXIMUM CPU TEMPERATURE",
            accent_color="#f43f5e",
            initial_val="N/A",
            initial_sub="GPU Peak: N/A • Warning 80°C",
        )
        kpi_row.addWidget(self.kpi_temp)

        self.kpi_records = self.create_kpi_card(
            title="RECORDS ANALYZED",
            accent_color="#2dd4bf",
            initial_val="0 records",
            initial_sub="0.0s span • 0 raw rows",
        )
        kpi_row.addWidget(self.kpi_records)

        dash_layout.addLayout(kpi_row)

        # -------------------------------------------------------------
        # SECTION B: 2-COLUMN × 3-ROW MAIN ANALYTICS GRID (6 CHARTS)
        # -------------------------------------------------------------
        grid = QGridLayout()
        grid.setSpacing(14)

        # Chart 1: Time Series Multi-Line Plot
        self.chart1_card = self.create_chart_card(
            title="CPU, RAM & GPU UTILIZATION OVER TIME",
            subtitle="Multi-series line chart with rolling average trendline (%)",
        )
        self.plot_timeseries = pg.PlotWidget()
        self.setup_pyqtgraph_widget(self.plot_timeseries)
        self.curve_cpu_raw = self.plot_timeseries.plot(
            pen=pg.mkPen(color=QColor(56, 189, 248, 110), width=1.5),
            name="Instantaneous CPU %",
        )
        self.curve_cpu_roll = self.plot_timeseries.plot(
            pen=pg.mkPen(color="#0284c7", width=2.5),
            name="CPU Rolling Trend (5-sample)",
        )
        self.curve_ram_ts = self.plot_timeseries.plot(
            pen=pg.mkPen(color="#a855f7", width=2.0),
            name="RAM Utilization %",
        )
        self.curve_gpu_ts = self.plot_timeseries.plot(
            pen=pg.mkPen(color="#2dd4bf", width=1.8),
            name="GPU Utilization %",
        )
        self.chart1_card.layout().addWidget(self.plot_timeseries)
        self.chart1_hover_lbl = QLabel("Hover or drag over chart to inspect timestamps and telemetry values")
        self.chart1_hover_lbl.setStyleSheet("color: #94a3b8; font-size: 9px; padding-top: 4px;")
        self.chart1_card.layout().addWidget(self.chart1_hover_lbl)
        self.setup_pyqtgraph_hover(self.plot_timeseries, self.on_chart1_hover)
        grid.addWidget(self.chart1_card, 0, 0)

        # Chart 2: RAM Donut
        self.chart2_card = self.create_chart_card(
            title="RAM USAGE COMPOSITION",
            subtitle="Physical memory allocation: Used vs Available (GB)",
        )
        self.canvas_donut = RamDonutCanvas()
        self.chart2_card.layout().addWidget(self.canvas_donut)
        grid.addWidget(self.chart2_card, 0, 1)

        # Chart 3: Thermal Dynamics
        self.chart3_card = self.create_chart_card(
            title="THERMAL DYNAMICS & HOTSPOTS",
            subtitle="Core CPU and GPU temperatures with configurable 80°C alert limit",
        )
        self.plot_thermal = pg.PlotWidget()
        self.setup_pyqtgraph_widget(self.plot_thermal, y_label="Temp (°C)")
        self.curve_cpu_temp = self.plot_thermal.plot(
            pen=pg.mkPen(color="#f43f5e", width=2.0),
            name="CPU Temperature (°C)",
            fillLevel=0,
            brush=QColor(244, 63, 94, 25),
        )
        self.curve_gpu_temp = self.plot_thermal.plot(
            pen=pg.mkPen(color="#f59e0b", width=2.0),
            name="GPU Temperature (°C)",
            fillLevel=0,
            brush=QColor(245, 158, 11, 20),
        )
        self.temp_thresh_line = pg.InfiniteLine(
            pos=80, angle=0,
            pen=pg.mkPen(color="#ef4444", width=1.5, style=Qt.DashLine),
            label="80°C Warning Limit",
            labelOpts={"color": "#ef4444", "position": 0.88},
        )
        self.plot_thermal.addItem(self.temp_thresh_line)
        self.chart3_card.layout().addWidget(self.plot_thermal)
        self.chart3_hover_lbl = QLabel("Thermal threshold: 80°C warning alert")
        self.chart3_hover_lbl.setStyleSheet("color: #94a3b8; font-size: 9px; padding-top: 4px;")
        self.chart3_card.layout().addWidget(self.chart3_hover_lbl)
        self.setup_pyqtgraph_hover(self.plot_thermal, self.on_chart3_hover)
        grid.addWidget(self.chart3_card, 1, 0)

        # Chart 4: Storage Grouped Bar
        self.chart4_card = self.create_chart_card(
            title="STORAGE READ & WRITE THROUGHPUT",
            subtitle="Dual-series disk I/O throughput rates in Megabytes per second (MB/s)",
        )
        self.canvas_disk = DiskThroughputCanvas()
        self.chart4_card.layout().addWidget(self.canvas_disk)
        grid.addWidget(self.chart4_card, 1, 1)

        # Chart 5: CPU Histogram
        self.chart5_card = self.create_chart_card(
            title="CPU UTILIZATION DISTRIBUTION",
            subtitle="Empirical sample density, mean, median, and dispersion profile",
        )
        self.canvas_dist = CpuDistributionCanvas()
        self.chart5_card.layout().addWidget(self.canvas_dist)
        grid.addWidget(self.chart5_card, 2, 0)

        # Chart 6: System Health Radial Gauge
        self.chart6_card = self.create_chart_card(
            title="SYSTEM HEALTH INDEX",
            subtitle="Deterministic composite score (0-100) based on compute, RAM & thermals",
        )
        self.gauge_widget = HealthScoreGaugeWidget()
        self.chart6_card.layout().addWidget(self.gauge_widget)
        grid.addWidget(self.chart6_card, 2, 1)

        dash_layout.addLayout(grid)

        # -------------------------------------------------------------
        # SECTION C: COMPACT DATA QUALITY & COLLECTION SUMMARY
        # -------------------------------------------------------------
        self.summary_card = QFrame()
        self.summary_card.setStyleSheet("background-color: #10141f; border: 1px solid #1e2638; border-radius: 6px;")
        sml = QVBoxLayout(self.summary_card)
        sml.setContentsMargins(16, 12, 16, 12)
        sml.setSpacing(10)

        sm_header = QHBoxLayout()
        sm_title = QLabel("DATA QUALITY & COLLECTION SUMMARY")
        sm_title.setStyleSheet("color: #e2e8f0; font-size: 11px; font-weight: bold; letter-spacing: 0.8px;")
        sm_header.addWidget(sm_title)
        sm_header.addStretch()

        self.quality_badge = QLabel("● LIVE STREAMING ACTIVE")
        self.quality_badge.setStyleSheet("color: #10b981; font-size: 10px; font-weight: bold;")
        sm_header.addWidget(self.quality_badge)
        sml.addLayout(sm_header)

        self.chips_layout = QHBoxLayout()
        self.chips_layout.setSpacing(10)

        self.chip_raw = self.create_summary_chip("Raw Records", "0")
        self.chip_clean = self.create_summary_chip("Cleaned Records", "0")
        self.chip_dedup = self.create_summary_chip("Deduplicated", "0")
        self.chip_missing = self.create_summary_chip("Missing Cells", "0")
        self.chip_interval = self.create_summary_chip("Sampling Interval", "N/A")
        self.chip_span = self.create_summary_chip("Time Span", "0.0s")

        self.chips_layout.addWidget(self.chip_raw)
        self.chips_layout.addWidget(self.chip_clean)
        self.chips_layout.addWidget(self.chip_dedup)
        self.chips_layout.addWidget(self.chip_missing)
        self.chips_layout.addWidget(self.chip_interval)
        self.chips_layout.addWidget(self.chip_span)
        sml.addLayout(self.chips_layout)

        dash_layout.addWidget(self.summary_card)

        # -------------------------------------------------------------
        # SECTION D: COLLAPSIBLE DETAIL PANELS
        # -------------------------------------------------------------
        self.audit_text_edit = QTextEdit()
        self.audit_text_edit.setReadOnly(True)
        self.audit_text_edit.setStyleSheet(
            "background:#0a0d14; color:#cbd5e1; border:1px solid #1e2638; font-family:monospace; font-size:10px; padding:8px;"
        )
        self.audit_text_edit.setMinimumHeight(150)
        self.panel_audit = CollapsiblePanel("Preprocessing Pipeline Audit & Transformation Details", self.audit_text_edit)
        dash_layout.addWidget(self.panel_audit)

        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(9)
        self.stats_table.setHorizontalHeaderLabels([
            "Metric", "Obs Count", "Mean", "Median", "Min", "Max", "Std Dev", "95th %ile", "Peak Timestamp"
        ])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stats_table.setStyleSheet("""
            QTableWidget {
                background: #0a0d14;
                color: #cbd5e1;
                border: 1px solid #1e2638;
                gridline-color: #1e2638;
                font-size: 10px;
            }
            QHeaderView::section {
                background: #10141f;
                color: #38bdf8;
                font-weight: bold;
                border: 1px solid #1e2638;
                padding: 4px;
            }
        """)
        self.stats_table.setMinimumHeight(180)
        self.panel_stats = CollapsiblePanel("Empirical Descriptive Statistics & Percentile Distributions", self.stats_table)
        dash_layout.addWidget(self.panel_stats)

        diag_container = QWidget()
        dl = QVBoxLayout(diag_container)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.setSpacing(8)

        diag_header = QHBoxLayout()
        self.ai_badge_lbl = QLabel("● RULE-BASED DIAGNOSTIC ENGINE")
        self.ai_badge_lbl.setStyleSheet("color: #10b981; font-weight: bold; font-size: 10px;")
        diag_header.addWidget(self.ai_badge_lbl)
        diag_header.addStretch()

        self.configure_ai_btn = QPushButton("⚙ Configure Optional External LLM")
        self.configure_ai_btn.clicked.connect(self.open_ai_config_dialog)
        self.apply_button_style(self.configure_ai_btn, small=True)
        diag_header.addWidget(self.configure_ai_btn)
        dl.addLayout(diag_header)

        self.insights_text = QTextEdit()
        self.insights_text.setReadOnly(True)
        self.insights_text.setStyleSheet(
            "background:#0a0d14; color:#e2e8f0; border:1px solid #1e2638; font-size:11px; padding:10px;"
        )
        self.insights_text.setMinimumHeight(140)
        dl.addWidget(self.insights_text)

        self.panel_insights = CollapsiblePanel("System Engineering Diagnostics & Bottleneck Analysis", diag_container)
        dash_layout.addWidget(self.panel_insights)

        self.records_table = QTableWidget()
        self.records_table.setStyleSheet("""
            QTableWidget {
                background: #0a0d14;
                color: #cbd5e1;
                border: 1px solid #1e2638;
                gridline-color: #1e2638;
                font-size: 10px;
            }
            QHeaderView::section {
                background: #10141f;
                color: #2dd4bf;
                font-weight: bold;
                border: 1px solid #1e2638;
                padding: 4px;
            }
        """)
        self.records_table.setMinimumHeight(180)
        self.panel_records = CollapsiblePanel("Dataset Records Preview (First 100 Rows)", self.records_table)
        dash_layout.addWidget(self.panel_records)

        scroll.setWidget(dashboard_container)
        page_layout.addWidget(scroll, stretch=1)

    # =================================================================
    # COMPONENT CREATION HELPERS
    # =================================================================

    def apply_button_style(self, button: QPushButton, primary=False, accent=False, small=False):
        pad = "4px 8px" if small else "6px 14px"
        font_sz = "10px" if small else "11px"

        if primary:
            bg = "#0284c7"
            color = "#ffffff"
            hover = "#0369a1"
            border = "#38bdf8"
        elif accent:
            bg = "#059669"
            color = "#ffffff"
            hover = "#047857"
            border = "#10b981"
        else:
            bg = "#181f2f"
            color = "#cbd5e1"
            hover = "#222c42"
            border = "#26334a"

        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {color};
                border: 1px solid {border};
                border-radius: 4px;
                padding: {pad};
                font-size: {font_sz};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
        """)

    def setup_more_actions_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #131823;
                color: #e2e8f0;
                border: 1px solid #1e2638;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 18px;
            }
            QMenu::item:selected {
                background-color: #0284c7;
                color: #ffffff;
            }
        """)

        act_latest = menu.addAction("🔄 Load Latest Live Log")
        act_latest.triggered.connect(self.load_latest_log)

        act_clean_csv = menu.addAction("💾 Export Cleaned CSV")
        act_clean_csv.triggered.connect(self.export_cleaned_dataset)

        self.more_btn.setMenu(menu)

    def create_kpi_card(
        self, title: str, accent_color: str, initial_val: str, initial_sub: str
    ) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #131823;
                border: 1px solid #1e2638;
                border-top: 3px solid {accent_color};
                border-radius: 6px;
            }}
        """)
        l = QVBoxLayout(card)
        l.setContentsMargins(14, 10, 14, 10)
        l.setSpacing(3)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #94a3b8; font-size: 9px; font-weight: bold; letter-spacing: 0.8px;")
        l.addWidget(title_lbl)

        val_lbl = QLabel(initial_val)
        val_lbl.setObjectName("val_label")
        val_lbl.setStyleSheet(f"color: {accent_color}; font-size: 20px; font-weight: 800;")
        l.addWidget(val_lbl)

        sub_lbl = QLabel(initial_sub)
        sub_lbl.setObjectName("sub_label")
        sub_lbl.setStyleSheet("color: #64748b; font-size: 10px;")
        l.addWidget(sub_lbl)

        return card

    def create_chart_card(self, title: str, subtitle: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #131823;
                border: 1px solid #1e2638;
                border-radius: 6px;
            }
        """)
        l = QVBoxLayout(card)
        l.setContentsMargins(14, 12, 14, 12)
        l.setSpacing(6)

        header = QVBoxLayout()
        header.setSpacing(1)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("color: #f1f5f9; font-size: 11px; font-weight: bold; letter-spacing: 0.8px;")
        header.addWidget(t_lbl)

        sub_lbl = QLabel(subtitle)
        sub_lbl.setStyleSheet("color: #94a3b8; font-size: 9px;")
        header.addWidget(sub_lbl)

        l.addLayout(header)
        return card

    def create_summary_chip(self, label: str, default_val: str) -> QFrame:
        chip = QFrame()
        chip.setStyleSheet("background-color: #181f2f; border: 1px solid #26334a; border-radius: 4px;")
        cl = QVBoxLayout(chip)
        cl.setContentsMargins(10, 6, 10, 6)
        cl.setSpacing(2)

        lbl = QLabel(label.upper())
        lbl.setStyleSheet("color: #94a3b8; font-size: 8px; font-weight: bold; letter-spacing: 0.5px;")
        cl.addWidget(lbl)

        val = QLabel(default_val)
        val.setObjectName("chip_val")
        val.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: bold;")
        cl.addWidget(val)

        return chip

    def setup_pyqtgraph_widget(self, pw: pg.PlotWidget, y_label="%"):
        pw.setBackground("#131823")
        pw.showGrid(x=True, y=True, alpha=0.15)
        pw.setMinimumHeight(230)
        pw.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        pw.getAxis("bottom").setPen(pg.mkPen("#1e2638", width=1))
        pw.getAxis("bottom").setTextPen(pg.mkPen("#64748b"))
        pw.getAxis("left").setPen(pg.mkPen("#1e2638", width=1))
        pw.getAxis("left").setTextPen(pg.mkPen("#64748b"))
        pw.getAxis("left").setLabel(y_label, color="#94a3b8", size="9pt")

        legend = pw.addLegend(offset=(10, 10))
        legend.setLabelTextColor("#cbd5e1")
        legend.setBrush(QColor(19, 24, 35, 210))
        legend.setPen(pg.mkPen("#26334a", width=1))

    def setup_pyqtgraph_hover(self, pw: pg.PlotWidget, callback):
        def on_mouse_moved(evt):
            pos = evt
            if pw.sceneBoundingRect().contains(pos):
                mouse_point = pw.plotItem.vb.mapSceneToView(pos)
                callback(mouse_point.x())

        pw.scene().sigMouseMoved.connect(on_mouse_moved)

    def on_chart1_hover(self, x_pos):
        df = self.cleaned_df
        if df is None or df.empty:
            return
        idx = int(round(x_pos))
        if 0 <= idx < len(df):
            ts = df["timestamp"].iloc[idx] if "timestamp" in df.columns else f"Sample {idx}"
            cpu = df["cpu_usage_percent"].iloc[idx] if "cpu_usage_percent" in df.columns else np.nan
            ram = df["ram_usage_percent"].iloc[idx] if "ram_usage_percent" in df.columns else np.nan
            gpu = df["gpu_usage_percent"].iloc[idx] if "gpu_usage_percent" in df.columns else np.nan

            txt = f"Time: {ts}   |   CPU: {cpu:.1f}%   |   RAM: {ram:.1f}%"
            if not pd.isna(gpu):
                txt += f"   |   GPU: {gpu:.1f}%"
            self.chart1_hover_lbl.setText(txt)

    def on_chart3_hover(self, x_pos):
        df = self.cleaned_df
        if df is None or df.empty:
            return
        idx = int(round(x_pos))
        if 0 <= idx < len(df):
            ts = df["timestamp"].iloc[idx] if "timestamp" in df.columns else f"Sample {idx}"
            cpu_t = df["cpu_temperature_c"].iloc[idx] if "cpu_temperature_c" in df.columns else np.nan
            gpu_t = df["gpu_temperature_c"].iloc[idx] if "gpu_temperature_c" in df.columns else np.nan

            txt = f"Time: {ts}   |   CPU Temp: {cpu_t:.1f}°C"
            if not pd.isna(gpu_t):
                txt += f"   |   GPU Temp: {gpu_t:.1f}°C"
            txt += "   |   Threshold: 80°C"
            self.chart3_hover_lbl.setText(txt)

    # =================================================================
    # ACTIONS & WORKFLOW
    # =================================================================

    def toggle_live_feed(self, enable: Optional[bool] = None):
        """Toggle real-time streaming mode on/off."""
        if enable is None:
            self.is_live = not self.is_live
        else:
            self.is_live = enable

        if self.is_live:
            self.live_toggle_btn.setText("🔴 LIVE STREAM: ACTIVE")
            self.apply_button_style(self.live_toggle_btn, accent=True, small=True)
            self.dataset_label.setText("Mode: 🔴 Real-Time Live Feed")
            self.dataset_label.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")
            if not self.live_timer.isActive():
                self.live_timer.start(1000)
            self._on_live_tick()
        else:
            self.live_toggle_btn.setText("▶ RESUME LIVE STREAM")
            self.apply_button_style(self.live_toggle_btn, primary=True, small=True)
            if self.current_file_path:
                self.dataset_label.setText(f"Dataset: {os.path.basename(self.current_file_path)}")
                self.dataset_label.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 11px;")
            else:
                self.dataset_label.setText("Live Stream: PAUSED")
                self.dataset_label.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 11px;")
            if self.live_timer.isActive():
                self.live_timer.stop()

    def _on_live_tick(self):
        """Poll instantaneous telemetry and update all 6 charts in real time."""
        if not self.is_live:
            return

        record = self.sampler.sample()
        if not record:
            return

        # Derived fields
        ram_u = record.get("ram_used_bytes") or 0
        ram_a = record.get("ram_available_bytes") or 0
        record["ram_used_gb"] = round(ram_u / (1024**3), 2)
        record["ram_available_gb"] = round(ram_a / (1024**3), 2)

        dr = record.get("disk_read_bytes_per_sec") or 0.0
        dw = record.get("disk_write_bytes_per_sec") or 0.0
        record["disk_read_mb_per_sec"] = round(dr / (1024 * 1024), 2)
        record["disk_write_mb_per_sec"] = round(dw / (1024 * 1024), 2)
        record["disk_total_mb_per_sec"] = round(record["disk_read_mb_per_sec"] + record["disk_write_mb_per_sec"], 2)

        ns = record.get("network_sent_bytes_per_sec") or 0.0
        nr = record.get("network_received_bytes_per_sec") or 0.0
        record["network_sent_kb_per_sec"] = round(ns / 1024, 2)
        record["network_recv_kb_per_sec"] = round(nr / 1024, 2)

        self.live_buffer.append(record)
        self.live_buffer = self.live_buffer[-self.max_live_samples:]

        self.cleaned_df = pd.DataFrame(self.live_buffer)

        # Calculate rolling averages dynamically
        rw = self.rolling_spin.value()
        if rw > 1 and "cpu_usage_percent" in self.cleaned_df.columns:
            self.cleaned_df["cpu_usage_percent_rolling_avg"] = (
                self.cleaned_df["cpu_usage_percent"].rolling(rw, min_periods=1).mean().round(2)
            )

        # Calculate statistics
        self.current_stats = compute_descriptive_stats(self.cleaned_df)
        self.current_thresholds = compute_threshold_analysis(self.cleaned_df)

        # Update all 4 KPI cards and 6 charts live!
        self.update_kpi_cards()
        self.update_all_charts()
        self.update_quality_summary()

    def _auto_load_recent_or_sample(self):
        """Seed initial history and launch live telemetry streaming."""
        logs = sorted(glob.glob("data/logs/resource_log_*.csv"), key=os.path.getmtime, reverse=True)
        if logs:
            try:
                df = pd.read_csv(logs[0])
                if len(df) > 0:
                    records = df.tail(30).to_dict("records")
                    for r in records:
                        if "ram_used_bytes" in r:
                            r["ram_used_gb"] = round((r.get("ram_used_bytes") or 0) / (1024**3), 2)
                            r["ram_available_gb"] = round((r.get("ram_available_bytes") or 0) / (1024**3), 2)
                        if "disk_read_bytes_per_sec" in r:
                            r["disk_read_mb_per_sec"] = round((r.get("disk_read_bytes_per_sec") or 0) / (1024 * 1024), 2)
                            r["disk_write_mb_per_sec"] = round((r.get("disk_write_bytes_per_sec") or 0) / (1024 * 1024), 2)
                    self.live_buffer = records
            except Exception:
                pass

        # Start live stream immediately so the dashboard is live working!
        self.toggle_live_feed(enable=True)

    def generate_sample_telemetry_if_needed(self) -> str:
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
        cpu = 15.0 + 10.0 * np.sin(np.linspace(0, 10, n)) + np.random.uniform(0, 8, n)
        cpu[40:70] += 55.0
        cpu = np.clip(cpu, 5.0, 98.0).round(1)

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
        f, _ = QFileDialog.getOpenFileName(
            self, "Open Telemetry CSV Dataset", "data/logs", "CSV Files (*.csv);;All Files (*)"
        )
        if f:
            self.load_dataset(f)

    def load_latest_log(self):
        logs = sorted(glob.glob("data/logs/resource_log_*.csv"), key=os.path.getmtime, reverse=True)
        if logs:
            self.load_dataset(logs[0])
        else:
            QMessageBox.information(
                self, "No Live Logs Found",
                "No live telemetry logs found in data/logs/. Start logging from the sidebar or import a file."
            )

    def load_dataset(self, file_path: str):
        # Pause live streaming when viewing a specific historical CSV
        self.toggle_live_feed(enable=False)
        self.current_file_path = file_path
        self.dataset_label.setText(f"Dataset: {os.path.basename(file_path)}")
        self.dataset_label.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 11px;")
        self.run_pipeline()

    def on_filter_changed(self):
        """Re-render views when user updates filter selection."""
        if not self.is_live and self.current_file_path:
            self.run_pipeline()

    def run_pipeline(self):
        if not self.current_file_path:
            QMessageBox.warning(self, "No Dataset", "Please select or import a telemetry dataset first.")
            return

        self.progress_bar.show()
        self.rerun_btn.setEnabled(False)

        dedup_rows = self.dedup_check.isChecked()
        rolling_w = self.rolling_spin.value()

        self.worker = PreprocessingWorker(self.current_file_path, dedup_rows, "keep_first", rolling_w)
        self.worker.finished.connect(self.on_pipeline_finished)
        self.worker.start()

    @Slot(object, object, str)
    def on_pipeline_finished(self, preprocessor, cleaned_df, error_msg):
        self.progress_bar.hide()
        self.rerun_btn.setEnabled(True)

        if error_msg or preprocessor is None or cleaned_df is None:
            QMessageBox.critical(self, "Preprocessing Error", f"Failed to preprocess dataset:\n{error_msg}")
            return

        self.preprocessor = preprocessor

        filter_mode = self.time_filter_combo.currentText()
        if len(cleaned_df) > 4:
            if "First 50%" in filter_mode:
                self.cleaned_df = cleaned_df.iloc[: len(cleaned_df) // 2].copy()
            elif "Second 50%" in filter_mode:
                self.cleaned_df = cleaned_df.iloc[len(cleaned_df) // 2 :].copy()
            elif "Peak Activity" in filter_mode:
                if "cpu_usage_percent" in cleaned_df.columns:
                    peak_idx = cleaned_df["cpu_usage_percent"].idxmax()
                    loc = cleaned_df.index.get_loc(peak_idx)
                    start = max(0, loc - 10)
                    end = min(len(cleaned_df), loc + 11)
                    self.cleaned_df = cleaned_df.iloc[start:end].copy()
                else:
                    self.cleaned_df = cleaned_df.copy()
            else:
                self.cleaned_df = cleaned_df.copy()
        else:
            self.cleaned_df = cleaned_df.copy()

        self.current_stats = compute_descriptive_stats(self.cleaned_df)
        self.current_thresholds = compute_threshold_analysis(self.cleaned_df)
        self.current_correlations = compute_correlations(self.cleaned_df)
        self.current_interpretations = generate_interpretations(self.cleaned_df)

        self.current_ai_insights = AIInsightsManager.generate_rule_based_insights(
            self.cleaned_df, self.current_stats, self.current_interpretations, self.current_thresholds
        )

        self.update_kpi_cards()
        self.update_all_charts()
        self.update_quality_summary()
        self.update_detail_panels()

    # =================================================================
    # DYNAMIC VIEW UPDATES
    # =================================================================

    def update_kpi_cards(self):
        df = self.cleaned_df
        if df is None or df.empty:
            return

        if self.is_live:
            raw_count = len(df)
            valid_count = len(df)
            duration_sec = float(len(df))
        else:
            raw_count = len(self.preprocessor.raw_df) if (self.preprocessor and self.preprocessor.raw_df is not None) else len(df)
            valid_count = len(df)
            duration_sec = self.preprocessor.summary.get("duration_seconds", 0.0) if self.preprocessor else 0.0

        # KPI 1: Average CPU Utilization
        cpu_s = self.current_stats.get("cpu_usage_percent")
        if cpu_s:
            mean_c = cpu_s["mean"]
            peak_c = cpu_s["max"]
            self.kpi_cpu.findChild(QLabel, "val_label").setText(f"{mean_c:.1f}%")
            self.kpi_cpu.findChild(QLabel, "sub_label").setText(f"Peak: {peak_c:.1f}% • Mean Baseline")
        else:
            self.kpi_cpu.findChild(QLabel, "val_label").setText("N/A")
            self.kpi_cpu.findChild(QLabel, "sub_label").setText("No CPU telemetry")

        # KPI 2: Average RAM Utilization
        ram_s = self.current_stats.get("ram_usage_percent")
        if ram_s:
            mean_r = ram_s["mean"]
            peak_r = ram_s["max"]
            is_high = mean_r >= 85.0 or peak_r >= 90.0
            sub_text = f"Peak: {peak_r:.1f}% • Limit: 85%"
            if is_high:
                sub_text += " [⚠️ High Memory Pressure]"
            self.kpi_ram.findChild(QLabel, "val_label").setText(f"{mean_r:.1f}%")
            self.kpi_ram.findChild(QLabel, "sub_label").setText(sub_text)
        else:
            self.kpi_ram.findChild(QLabel, "val_label").setText("N/A")
            self.kpi_ram.findChild(QLabel, "sub_label").setText("No RAM telemetry")

        # KPI 3: Maximum CPU Temperature
        cpu_t = self.current_stats.get("cpu_temperature_c")
        gpu_t = self.current_stats.get("gpu_temperature_c")
        if cpu_t:
            max_c = cpu_t["max"]
            gpu_str = f"GPU Max: {gpu_t['max']:.1f}°C" if gpu_t else "GPU: N/A"
            is_warn = max_c >= 80.0
            sub_text = f"{gpu_str} • Threshold: 80°C"
            if is_warn:
                sub_text += " [⚠️ Alert]"
            self.kpi_temp.findChild(QLabel, "val_label").setText(f"{max_c:.1f}°C")
            self.kpi_temp.findChild(QLabel, "sub_label").setText(sub_text)
        else:
            self.kpi_temp.findChild(QLabel, "val_label").setText("N/A")
            self.kpi_temp.findChild(QLabel, "sub_label").setText("Thermal sensor unavailable")

        # KPI 4: Records Analyzed
        if self.is_live:
            self.kpi_records.findChild(QLabel, "val_label").setText(f"{valid_count:,} live samples")
            self.kpi_records.findChild(QLabel, "sub_label").setText(f"{duration_sec:.0f}s live window • Streaming")
        else:
            self.kpi_records.findChild(QLabel, "val_label").setText(f"{valid_count:,} valid records")
            self.kpi_records.findChild(QLabel, "sub_label").setText(f"{duration_sec:.1f}s collection • {raw_count:,} raw rows")

    def update_all_charts(self):
        df = self.cleaned_df
        if df is None or df.empty:
            return

        x = np.arange(len(df))

        # CHART 1: CPU, RAM & GPU Over Time
        if "cpu_usage_percent" in df.columns:
            cpu_vals = df["cpu_usage_percent"].fillna(0).values
            self.curve_cpu_raw.setData(x, cpu_vals)

            roll_col = "cpu_usage_percent_rolling_avg"
            if roll_col in df.columns:
                self.curve_cpu_roll.setData(x, df[roll_col].fillna(0).values)
            else:
                self.curve_cpu_roll.setData(x, cpu_vals)

        if "ram_usage_percent" in df.columns:
            self.curve_ram_ts.setData(x, df["ram_usage_percent"].fillna(0).values)

        if "gpu_usage_percent" in df.columns and not df["gpu_usage_percent"].dropna().empty:
            self.curve_gpu_ts.setData(x, df["gpu_usage_percent"].fillna(0).values)
            self.curve_gpu_ts.setVisible(True)
        else:
            self.curve_gpu_ts.setData([], [])
            self.curve_gpu_ts.setVisible(False)

        # CHART 2: RAM Donut
        self.canvas_donut.update_donut(df)

        # CHART 3: Thermal Dynamics
        if "cpu_temperature_c" in df.columns and not df["cpu_temperature_c"].dropna().empty:
            self.curve_cpu_temp.setData(x, df["cpu_temperature_c"].fillna(0).values)
        else:
            self.curve_cpu_temp.setData([], [])

        if "gpu_temperature_c" in df.columns and not df["gpu_temperature_c"].dropna().empty:
            self.curve_gpu_temp.setData(x, df["gpu_temperature_c"].fillna(0).values)
            self.curve_gpu_temp.setVisible(True)
        else:
            self.curve_gpu_temp.setData([], [])
            self.curve_gpu_temp.setVisible(False)

        # CHART 4: Storage Read/Write Throughput Grouped Bar
        self.canvas_disk.update_bars(df)

        # CHART 5: CPU Utilization Distribution Histogram
        self.canvas_dist.update_histogram(df)

        # CHART 6: System Health Score Gauge
        self.calculate_and_update_health_score(df)

    def calculate_and_update_health_score(self, df: pd.DataFrame):
        """Deterministic system health index calculation."""
        has_cpu = "cpu_usage_percent" in df.columns and not df["cpu_usage_percent"].dropna().empty
        has_ram = "ram_usage_percent" in df.columns and not df["ram_usage_percent"].dropna().empty

        if not (has_cpu or has_ram):
            self.gauge_widget.set_score_breakdown(None)
            return

        cpu_pen = 0.0
        if has_cpu:
            c_mean = float(df["cpu_usage_percent"].dropna().mean())
            c_peak = float(df["cpu_usage_percent"].dropna().max())
            if c_mean > 30.0:
                cpu_pen += min(20.0, (c_mean - 30.0) * 0.45)
            if c_peak > 85.0:
                cpu_pen += 15.0
            elif c_peak > 70.0:
                cpu_pen += 8.0
            cpu_pen = min(35.0, cpu_pen)

        ram_pen = 0.0
        if has_ram:
            r_mean = float(df["ram_usage_percent"].dropna().mean())
            r_peak = float(df["ram_usage_percent"].dropna().max())
            if r_mean > 70.0:
                ram_pen += min(20.0, (r_mean - 70.0) * 0.8)
            if r_peak > 90.0:
                ram_pen += 15.0
            elif r_peak > 85.0:
                ram_pen += 8.0
            ram_pen = min(35.0, ram_pen)

        thermal_pen = 0.0
        has_temp = "cpu_temperature_c" in df.columns and not df["cpu_temperature_c"].dropna().empty
        if has_temp:
            t_max = float(df["cpu_temperature_c"].dropna().max())
            if t_max > 65.0:
                thermal_pen += min(15.0, (t_max - 65.0) * 1.0)
            if t_max > 80.0:
                thermal_pen += min(15.0, (t_max - 80.0) * 1.5)
            thermal_pen = min(30.0, thermal_pen)

        raw_score = 100.0 - (cpu_pen + ram_pen + thermal_pen)
        final_score = max(5.0, min(100.0, raw_score))

        self.gauge_widget.set_score_breakdown(
            score=final_score,
            cpu_pen=cpu_pen,
            ram_pen=ram_pen,
            thermal_pen=thermal_pen,
        )

    def update_quality_summary(self):
        df = self.cleaned_df
        if df is None or df.empty:
            return

        if self.is_live:
            self.chip_raw.findChild(QLabel, "chip_val").setText(f"{len(df):,}")
            self.chip_clean.findChild(QLabel, "chip_val").setText(f"{len(df):,}")
            self.chip_dedup.findChild(QLabel, "chip_val").setText("0")
            self.chip_missing.findChild(QLabel, "chip_val").setText("0")
            self.chip_interval.findChild(QLabel, "chip_val").setText("1.00s")
            self.chip_span.findChild(QLabel, "chip_val").setText(f"{len(df):.0f}s live")
            self.quality_badge.setText("● LIVE FEED STREAMING")
            self.quality_badge.setStyleSheet("color: #10b981; font-size: 10px; font-weight: bold;")
        else:
            summary = self.preprocessor.summary if self.preprocessor else {}
            raw_rows = summary.get("original_rows", len(df))
            clean_rows = summary.get("cleaned_rows", len(df))
            rems = summary.get("records_removed", [])
            dedup_count = sum(r.get("count", 0) for r in rems if "duplicate" in r.get("reason", "").lower())
            mvc = summary.get("missing_values_by_column", {})
            total_missing = sum(d.get("count", 0) for d in mvc.values())
            istats = summary.get("sampling_interval_analysis", {})
            mean_dt = istats.get("mean_interval_sec")
            dt_str = f"{mean_dt:.2f}s avg" if mean_dt else "N/A"
            dur = summary.get("duration_seconds", 0.0)

            self.chip_raw.findChild(QLabel, "chip_val").setText(f"{raw_rows:,}")
            self.chip_clean.findChild(QLabel, "chip_val").setText(f"{clean_rows:,}")
            self.chip_dedup.findChild(QLabel, "chip_val").setText(f"{dedup_count:,}")
            self.chip_missing.findChild(QLabel, "chip_val").setText(f"{total_missing:,}")
            self.chip_interval.findChild(QLabel, "chip_val").setText(dt_str)
            self.chip_span.findChild(QLabel, "chip_val").setText(f"{dur:.1f}s")
            self.quality_badge.setText("● AUDIT VALIDATED")
            self.quality_badge.setStyleSheet("color: #10b981; font-size: 10px; font-weight: bold;")

    def update_detail_panels(self):
        df = self.cleaned_df
        if df is None:
            return

        if self.preprocessor:
            self.audit_text_edit.setMarkdown(self.preprocessor.get_summary_text())

        self.stats_table.setRowCount(len(self.current_stats))
        for row, (col_name, s) in enumerate(self.current_stats.items()):
            self.stats_table.setItem(row, 0, QTableWidgetItem(col_name))
            self.stats_table.setItem(row, 1, QTableWidgetItem(f"{s.get('count', 0):,}"))
            self.stats_table.setItem(row, 2, QTableWidgetItem(f"{s.get('mean', 'N/A')}"))
            self.stats_table.setItem(row, 3, QTableWidgetItem(f"{s.get('median', 'N/A')}"))
            self.stats_table.setItem(row, 4, QTableWidgetItem(f"{s.get('min', 'N/A')}"))
            self.stats_table.setItem(row, 5, QTableWidgetItem(f"{s.get('max', 'N/A')}"))
            self.stats_table.setItem(row, 6, QTableWidgetItem(f"{s.get('std', 'N/A')}"))
            self.stats_table.setItem(row, 7, QTableWidgetItem(f"{s.get('p95', 'N/A')}"))
            self.stats_table.setItem(row, 8, QTableWidgetItem(str(s.get('peak_timestamp', 'N/A'))))

        ai = self.current_ai_insights
        self.ai_badge_lbl.setText(f"● {ai.get('badge', 'RULE-BASED').upper()}")
        lines = []
        lines.append(f"*{ai.get('disclaimer', '')}*\n")
        lines.append("#### Key Diagnostic Observations:")
        for obs in ai.get("insights", []):
            lines.append(f"- {obs}")
        lines.append("\n#### Engineering Recommendations:")
        for rec in ai.get("recommendations", []):
            lines.append(f"- {rec}")
        self.insights_text.setMarkdown("\n".join(lines))

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

    def export_cleaned_dataset(self):
        if self.cleaned_df is None:
            QMessageBox.warning(self, "No Cleaned Data", "Please load and preprocess a dataset first.")
            return

        f, _ = QFileDialog.getSaveFileName(
            self, "Save Cleaned Telemetry Dataset", "data/cleaned_telemetry.csv", "CSV Files (*.csv)"
        )
        if f:
            try:
                self.cleaned_df.to_csv(f, index=False)
                QMessageBox.information(self, "Export Successful", f"Cleaned dataset saved to:\n{f}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Error saving cleaned CSV: {e}")

    def generate_and_export_report(self):
        if self.cleaned_df is None:
            QMessageBox.warning(self, "No Data", "Please load and preprocess a dataset first.")
            return

        try:
            figures = {
                "RAM Allocation & Composition": self.canvas_donut.fig,
                "Storage Read/Write Throughput Rates": self.canvas_disk.fig,
                "Resource Utilization Histograms & Density": self.canvas_dist.fig,
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
                f"Comprehensive Telemetry Analytics Report generated successfully!\n\n"
                f"HTML: {html_f}\nJSON: {json_f}\n\nOpening report in browser..."
            )
            import webbrowser
            webbrowser.open(f"file:///{os.path.abspath(html_f)}")
        except Exception as e:
            QMessageBox.critical(self, "Report Generation Error", f"Failed to generate report: {e}")

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

        prov_lbl = QLabel("AI Provider:")
        l.addWidget(prov_lbl)
        prov_combo = QComboBox()
        prov_combo.addItems(["Gemini", "OpenAI", "Ollama (Local)"])
        prov_combo.setStyleSheet("background:#222; color:#fff; padding:4px;")
        l.addWidget(prov_combo)

        key_lbl = QLabel("API Key (Stored in memory only):")
        l.addWidget(key_lbl)
        key_input = QLineEdit()
        key_input.setEchoMode(QLineEdit.Password)
        key_input.setPlaceholderText("Enter API Key or leave empty for local Ollama")
        key_input.setStyleSheet("background:#222; color:#fff; padding:5px; border:1px solid #444;")
        l.addWidget(key_input)

        consent_chk = QCheckBox("I explicitly consent to transmitting aggregated statistical summaries to this service.")
        consent_chk.setStyleSheet("color:#38bdf8; font-size:10px;")
        l.addWidget(consent_chk)

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
                "duration_sec": self.preprocessor.summary.get("duration_seconds", len(self.cleaned_df) if self.cleaned_df is not None else 0),
                "record_count": len(self.cleaned_df) if self.cleaned_df is not None else 0,
            }
            res = AIInsightsManager.query_external_ai(payload, provider=provider, api_key=api_key)
            self.current_ai_insights = res
            self.update_detail_panels()
            QMessageBox.information(self, "AI Analysis Complete", f"Successfully synthesized insights using {provider.upper()}.")
        except Exception as e:
            QMessageBox.critical(self, "AI Query Failed", f"External AI invocation failed:\n{e}\n\nReverting safely to offline rule-based diagnostics.")
        finally:
            self.progress_bar.hide()

    def closeEvent(self, event):
        if hasattr(self, "live_timer") and self.live_timer.isActive():
            self.live_timer.stop()
        if hasattr(self, "worker") and self.worker and self.worker.isRunning():
            self.worker.wait(2000)
        super().closeEvent(event)
