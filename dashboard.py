import math
import json
import re
import subprocess
import sys
import time
import platform
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen
import psutil
import pyqtgraph as pg

try:
    import pynvml
    HAS_PYNVML = True
except ImportError:
    pynvml = None
    HAS_PYNVML = False


from PySide6.QtCore import (
    Qt,
    QTimer,
    QRectF,
    QPointF,
    Property,
    QPropertyAnimation,
    QSequentialAnimationGroup,
    QParallelAnimationGroup,
    QPauseAnimation,
    QEasingCurve,
)
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QFont,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QComboBox,
    QPushButton,
    QDialog,
    QFormLayout,
    QSpinBox,
    QDialogButtonBox,
)

class CarbonFiberBackground(QWidget):
    def __init__(self, parent=None):

        super().__init__(parent)

        self.setAttribute(
            Qt.WA_StyledBackground,
            False
        )

    def paintEvent(self, event):

        painter = QPainter(
            self
        )

        painter.fillRect(
            self.rect(),
            QColor("#101010")
        )

        tile = 18
        width = self.width()
        height = self.height()

        painter.setPen(
            Qt.NoPen
        )

        for row, y in enumerate(range(-tile, height + tile, tile)):

            row_offset = (row % 2) * (tile // 2)

            for x in range(-tile, width + tile, tile):

                left = x + row_offset

                painter.setBrush(
                    QColor("#171717")
                )

                painter.drawPolygon(
                    QPolygonF(
                        [
                            QPointF(left, y + 7),
                            QPointF(left + 7, y),
                            QPointF(left + tile, y),
                            QPointF(left + tile - 7, y + 7),
                        ]
                    )
                )

                painter.setBrush(
                    QColor("#0b0b0b")
                )

                painter.drawPolygon(
                    QPolygonF(
                        [
                            QPointF(left, y + 9),
                            QPointF(left + tile - 7, y + 9),
                            QPointF(left + tile, y + tile),
                            QPointF(left + 7, y + tile),
                        ]
                    )
                )

        painter.end()

class PerformanceGauge(QWidget):

    def __init__(
        self,
        title,
        unit,
        accent,
        minimum=0,
        maximum=100,
        redline=90,
        parent=None
    ):

        super().__init__(parent)

        self.title = title
        self.unit = unit
        self.accent = accent

        self.minimum = minimum
        self.maximum = maximum
        self.redline = redline

        self.value = minimum
        self.target_value = minimum
        self.display_value = minimum
        self.value_available = True
        self.startup_active = False
        self.startup_progress = 0.0

        self.setMinimumSize(250, 250)
        self.setSizePolicy(self.sizePolicy())
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Smooth animation timer (30ms ~ 33 FPS smooth step)
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(30)
        self.anim_timer.timeout.connect(self.animate_smooth_step)
        self.anim_timer.start()

    def setValue(self, value):
        if value is None:
            self.value_available = False
            self.target_value = self.minimum
        else:
            self.value_available = True
            self.target_value = max(self.minimum, min(self.maximum, float(value)))

    def get_startup_progress(self):
        return self.startup_progress

    def set_startup_progress(self, progress):
        self.startup_progress = progress

        if progress <= 1.0:
            self.display_value = self.minimum + (
                self.maximum - self.minimum
            ) * progress
        else:
            upper_value = self.minimum + (
                self.maximum - self.minimum
            ) * 0.92
            self.display_value = upper_value + (
                self.target_value - upper_value
            ) * (progress - 1.0)

        self.value = self.display_value
        self.update()

    startupProgress = Property(
        float,
        get_startup_progress,
        set_startup_progress
    )

    def startup_sweep(self, duration=2000):
        self.startup_active = True
        self.startup_progress = 0.0
        self.display_value = self.minimum
        self.value = self.minimum
        self.update()

        sweep_up = QPropertyAnimation(
            self,
            b"startupProgress"
        )
        sweep_up.setDuration(int(duration * 0.36))
        sweep_up.setStartValue(0.0)
        sweep_up.setEndValue(1.0)
        sweep_up.setEasingCurve(QEasingCurve.InOutCubic)

        return_sweep = QPropertyAnimation(
            self,
            b"startupProgress"
        )
        return_sweep.setDuration(int(duration * 0.55))
        return_sweep.setStartValue(1.0)
        return_sweep.setEndValue(2.0)
        return_sweep.setEasingCurve(QEasingCurve.InOutCubic)

        animation = QSequentialAnimationGroup(self)
        animation.addAnimation(sweep_up)
        animation.addAnimation(QPauseAnimation(int(duration * 0.09)))
        animation.addAnimation(return_sweep)
        animation.finished.connect(self.finish_startup_sweep)
        return animation

    def finish_startup_sweep(self):
        self.startup_active = False
        self.startup_progress = 0.0
        self.display_value = self.target_value
        self.value = self.display_value
        self.update()

    def animate_smooth_step(self):
        if self.startup_active:
            return

        diff = self.target_value - self.display_value
        if abs(diff) > 0.02:
            self.display_value += diff * 0.18
            self.value = self.display_value
            self.update()
        elif self.display_value != self.target_value:
            self.display_value = self.target_value
            self.value = self.display_value
            self.update()

    def get_value_color(self):

        percentage = (
            (self.value - self.minimum)
            /
            (self.maximum - self.minimum)
        )

        redline_percentage = (
            (self.redline - self.minimum)
            /
            (self.maximum - self.minimum)
        )

        if percentage >= redline_percentage:

            return QColor(
                "#e53935"
            )

        if percentage >= 0.75:

            return QColor(
                "#ff8f00"
            )

        return QColor(
            self.accent
        )

    def paintEvent(self, event):

        painter = QPainter(
            self
        )

        painter.setRenderHint(
            QPainter.Antialiasing
        )

        width = self.width()
        height = self.height()

        center = QPointF(
            width / 2,
            height / 2
        )

        size = min(
            width,
            height
        )

        radius = (
            size * 0.37
        )

        painter.setPen(
            Qt.NoPen
        )

        painter.setBrush(
            QColor(
                "#090909"
            )
        )

        painter.drawEllipse(
            QRectF(
                center.x() - radius - 25,
                center.y() - radius - 25,
                (radius + 25) * 2,
                (radius + 25) * 2
            )
        )
        leather_pen = QPen(
            QColor("#7a2525")
        )

        leather_pen.setWidth(
            7
        )

        painter.setPen(
            leather_pen
        )

        painter.setBrush(
            Qt.NoBrush
        )

        painter.drawEllipse(
            QRectF(
                center.x() - radius - 24,
                center.y() - radius - 24,
                (radius + 24) * 2,
                (radius + 24) * 2
            )
        )

        outer_pen = QPen(
            QColor(
                "#292929"
            )
        )

        outer_pen.setWidth(
            2
        )

        painter.setPen(
            outer_pen
        )

        painter.setBrush(
            Qt.NoBrush
        )

        painter.drawEllipse(
            QRectF(
                center.x() - radius - 12,
                center.y() - radius - 12,
                (radius + 12) * 2,
                (radius + 12) * 2
            )
        )

        start_angle = 225
        end_angle = -45

        total_angle = (
            start_angle - end_angle
        )

        track_pen = QPen(
            QColor(
                "#242424"
            )
        )

        track_pen.setWidth(
            16
        )

        track_pen.setCapStyle(
            Qt.RoundCap
        )

        painter.setPen(
            track_pen
        )

        arc_rect = QRectF(
            center.x() - radius,
            center.y() - radius,
            radius * 2,
            radius * 2
        )

        painter.drawArc(
            arc_rect,
            int(start_angle * 16),
            int(-total_angle * 16)
        )

        redline_ratio = (
            self.redline - self.minimum
        ) / (
            self.maximum - self.minimum
        )

        redline_angle = (
            total_angle
            * redline_ratio
        )

        red_pen = QPen(
            QColor(
                "#4b1717"
            )
        )

        red_pen.setWidth(
            16
        )

        red_pen.setCapStyle(
            Qt.RoundCap
        )

        painter.setPen(
            red_pen
        )

        painter.drawArc(
            arc_rect,
            int(
                (
                    start_angle
                    -
                    redline_angle
                )
                * 16
            ),
            int(
                -(
                    total_angle
                    -
                    redline_angle
                )
                * 16
            )
        )

        # ACTIVE ARC
        value_ratio = (
            self.value - self.minimum
        ) / (
            self.maximum - self.minimum
        )

        active_angle = (
            total_angle
            * value_ratio
        )

        active_color = (
            self.get_value_color()
        )

        active_pen = QPen(
            active_color
        )

        active_pen.setWidth(
            16
        )

        active_pen.setCapStyle(
            Qt.RoundCap
        )

        painter.setPen(
            active_pen
        )

        painter.drawArc(
            arc_rect,
            int(start_angle * 16),
            int(-active_angle * 16)
        )
        # TICKS
        painter.setPen(
            QPen(
                QColor(
                    "#555555"
                ),
                1
            )
        )

        tick_count = 10

        for i in range(
            tick_count + 1
        ):

            ratio = (
                i / tick_count
            )

            angle = math.radians(
                start_angle
                -
                total_angle * ratio
            )

            outer_radius = (
                radius + 3
            )

            inner_radius = (
                radius - 10
            )

            x1 = (
                center.x()
                +
                math.cos(angle)
                * inner_radius
            )

            y1 = (
                center.y()
                -
                math.sin(angle)
                * inner_radius
            )

            x2 = (
                center.x()
                +
                math.cos(angle)
                * outer_radius
            )

            y2 = (
                center.y()
                -
                math.sin(angle)
                * outer_radius
            )

            painter.drawLine(
                QPointF(x1, y1),
                QPointF(x2, y2)
            )
        # NEEDLE
        needle_ratio = value_ratio

        needle_angle = math.radians(
            start_angle
            -
            total_angle
            * needle_ratio
        )

        needle_length = (
            radius - 18
        )

        needle_x = (
            center.x()
            +
            math.cos(needle_angle)
            * needle_length
        )

        needle_y = (
            center.y()
            -
            math.sin(needle_angle)
            * needle_length
        )

        needle_color = (
            self.get_value_color()
        )

        needle_pen = QPen(
            needle_color
        )

        needle_pen.setWidth(
            3
        )

        needle_pen.setCapStyle(
            Qt.RoundCap
        )

        painter.setPen(
            needle_pen
        )

        painter.drawLine(
            center,
            QPointF(
                needle_x,
                needle_y
            )
        )

        # NEEDLE HUB

        painter.setPen(
            Qt.NoPen
        )

        painter.setBrush(
            QColor(
                "#dddddd"
            )
        )

        painter.drawEllipse(
            QRectF(
                center.x() - 5,
                center.y() - 5,
                10,
                10
            )
        )

        painter.setBrush(
            needle_color
        )

        painter.drawEllipse(
            QRectF(
                center.x() - 3,
                center.y() - 3,
                6,
                6
            )
        )

        # =================================================
        # TITLE
        # =================================================

        painter.setPen(
            QColor(
                "#888888"
            )
        )

        painter.setFont(
            QFont(
                "Segoe UI",
                10,
                QFont.Bold
            )
        )

        title_rect = QRectF(
            center.x() - 100,
            center.y() - radius + 18,
            200,
            25
        )

        painter.drawText(
            title_rect,
            Qt.AlignCenter,
            self.title.upper()
        )

        value_text = "N/A" if not self.value_available else f"{self.value:.0f}"

        painter.setPen(
            QColor(
                "#eeeeee"
            )
        )

        painter.setFont(
            QFont(
                "Segoe UI",
                26,
                QFont.Bold
            )
        )

        value_rect = QRectF(
            center.x() - 80,
            center.y() + 20,
            160,
            38
        )

        painter.drawText(
            value_rect,
            Qt.AlignCenter,
            value_text
        )

        painter.setPen(
            active_color
        )

        painter.setFont(
            QFont(
                "Segoe UI",
                9,
                QFont.Bold
            )
        )

        unit_rect = QRectF(
            center.x() - 60,
            center.y() + 57,
            120,
            20
        )

        painter.drawText(
            unit_rect,
            Qt.AlignCenter,
            self.unit
        )

        if value_ratio >= redline_ratio:

            status = "REDLINE"

            status_color = QColor(
                "#e53935"
            )

        elif value_ratio >= 0.75:

            status = "HIGH"

            status_color = QColor(
                "#ff8f00"
            )

        else:

            status = "NORMAL"

            status_color = QColor(
                "#666666"
            )

        painter.setPen(
            status_color
        )

        painter.setFont(
            QFont(
                "Segoe UI",
                8,
                QFont.Bold
            )
        )

        status_rect = QRectF(
            center.x() - 70,
            center.y() + 78,
            140,
            18
        )

        painter.drawText(
            status_rect,
            Qt.AlignCenter,
            status
        )

        painter.end()



class DashboardPage(CarbonFiberBackground):

    def __init__(self):

        super().__init__()

        self.lhm_process = None
        self.start_libre_hardware_monitor()


        self.gpu_available = False
        self.gpu_handle = None
        self.gpu_name = "N/A"

        if HAS_PYNVML and pynvml:
            try:
                pynvml.nvmlInit()
                gpu_count = pynvml.nvmlDeviceGetCount()

                if gpu_count > 0:
                    self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    self.gpu_available = True
                    try:
                        gpu_name = pynvml.nvmlDeviceGetName(self.gpu_handle)
                        if isinstance(gpu_name, bytes):
                            gpu_name = gpu_name.decode("utf-8", errors="ignore")
                        self.gpu_name = str(gpu_name)
                    except Exception:
                        self.gpu_name = "NVIDIA GPU"
                else:
                    self.gpu_name = "NO NVIDIA GPU"

            except Exception as error:
                print("NVML initialization failed:", error)
                self.gpu_available = False
        else:
            self.gpu_name = "NVML NOT INSTALLED"

            self.gpu_name = (
                "NVIDIA GPU NOT DETECTED"
            )

        self.max_points = 60

        self.gauge_refresh_settings = {
            "cpu_load": 500,
            "cpu_temp": 800,
            "gpu_0": 700,
            "gpu_temp": 900,
            "ram_load": 600,
            "gpu_1": 750,
        }

        self.gauge_timers = {}

        self.cpu_history = (
            [0] * self.max_points
        )

        self.gpu_history = (
            [0] * self.max_points
        )

        self.gpu_1_history = (
            [0] * self.max_points
        )

        self.ram_history = (
            [0] * self.max_points
        )

        self.setup_ui()

        for key, interval in self.gauge_refresh_settings.items():
            timer = QTimer(self)
            timer.setInterval(interval)
            timer.timeout.connect(lambda gauge=key: self.refresh_gauge_value(gauge))
            timer.start()
            self.gauge_timers[key] = timer

        self.timer = QTimer(
            self
        )

        self.timer.timeout.connect(
            self.update_data
        )

        self.timer.start(500)
        self.update_data()

    def start_libre_hardware_monitor(self):

        """Start the bundled LibreHardwareMonitor web server when needed."""

        if not sys.platform.startswith("win"):
            return

        try:
            with urlopen(
                "http://127.0.0.1:8085/data.json",
                timeout=0.15
            ):
                return
        except (OSError, URLError, ValueError):
            pass

        monitor_path = (
            Path(__file__).resolve().parent
            / ".tools"
            / "LibreHardwareMonitor"
            / "LibreHardwareMonitor.exe"
        )

        if not monitor_path.is_file():
            return

        try:
            self.lhm_process = subprocess.Popen(
                [str(monitor_path)],
                cwd=str(monitor_path.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError:
            self.lhm_process = None

    def closeEvent(self, event):

        self.timer.stop()

        if self.lhm_process is not None and self.lhm_process.poll() is None:
            self.lhm_process.terminate()

        super().closeEvent(event)

    def set_refresh_interval(self, ms):
        self.timer.setInterval(ms)

    def activate_cockpit(self):
        gauges = [
            self.cpu_gauge,
            self.cpu_temp_gauge,
            self.ram_gauge,
            self.temp_gauge,
            self.gpu_0_gauge,
            self.gpu_1_gauge,
        ]

        if hasattr(self, "startup_animation"):
            self.startup_animation.stop()
            self.startup_animation.deleteLater()

        self.startup_animation = QParallelAnimationGroup(self)

        for gauge in gauges:
            self.startup_animation.addAnimation(
                gauge.startup_sweep()
            )

        self.startup_animation.finished.connect(
            self.finish_cockpit_startup
        )
        self.startup_animation.start()

    def finish_cockpit_startup(self):
        for gauge in (
            self.cpu_gauge,
            self.cpu_temp_gauge,
            self.ram_gauge,
            self.temp_gauge,
            self.gpu_0_gauge,
            self.gpu_1_gauge,
        ):
            gauge.finish_startup_sweep()

    def get_gpu_display_name(self):

        """Return the detected GPU name in a compact cockpit format."""

        gpu_name = self.gpu_name.strip()
        if not self.gpu_available or self.gpu_handle is None:
            return gpu_name

        is_laptop = bool(re.search(r"\blaptop\b", gpu_name, re.IGNORECASE))
        display_name = re.sub(r"\bgeforce\s+", "", gpu_name, flags=re.IGNORECASE)
        display_name = re.sub(r"\s+laptop\s+gpu\b", "", display_name, flags=re.IGNORECASE)
        display_name = re.sub(r"\b\d+(?:\.\d+)?\s*(?:GB|GiB)\b", "", display_name, flags=re.IGNORECASE)
       
        display_name = " ".join(display_name.split()).upper()

        try:
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(self.gpu_handle)
            memory_gb = round(memory_info.total / (1024 ** 3))
            memory_text = f"{memory_gb} GB"
        except Exception:
            memory_text = "VRAM"

        laptop_suffix = " LAPTOP" if is_laptop else ""
        return f"{display_name} {memory_text}{laptop_suffix}"

    def setup_ui(self):

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            25,
            20,
            25,
            20
        )

        layout.setSpacing(
            10
        )


        header = QHBoxLayout()

        title = QLabel(
            self.get_gpu_display_name()
        )

        title.setObjectName(
            "cockpit_title"
        )

        status = QLabel(
            "● SYSTEM ONLINE"
        )

        status.setObjectName(
            "cockpit_status"
        )

        header.addWidget(title)

        header.addStretch()

        header.addWidget(
            status
        )

        layout.addLayout(
            header
        )

        gauge_row_1 = QHBoxLayout()

        gauge_row_1.setSpacing(
            8
        )

        # CPU
        self.cpu_gauge = PerformanceGauge(
            title="CPU LOAD",
            unit="%",
            accent="#ff8f00",
            redline=90
        )

        # CPU TEMPERATURE
        self.cpu_temp_gauge = PerformanceGauge(
            title="CPU TEMP",
            unit="°C",
            accent="#8bc34a",
            minimum=30,
            maximum=100,
            redline=85
        )

        self.gpu_0_gauge = PerformanceGauge(
            title="GPU 0",
            unit="%",
            accent="#29b6f6",
            redline=90
        )

        gauge_row_1.addWidget(
            self.cpu_gauge
        )

        gauge_row_1.addWidget(
            self.cpu_temp_gauge
        )

        gauge_row_1.addWidget(
            self.gpu_0_gauge
        )

        layout.addLayout(
            gauge_row_1,
            1
        )


        gauge_row_2 = QHBoxLayout()

        gauge_row_2.setSpacing(
            8
        )

        # RAM
        self.ram_gauge = PerformanceGauge(
            title="MEMORY LOAD",
            unit="%",
            accent="#ab47bc",
            redline=90
        )

        # TEMP
        self.temp_gauge = PerformanceGauge(
            title="GPU TEMP",
            unit="°C",
            accent="#e53935",
            minimum=30,
            maximum=100,
            redline=85
        )

        gauge_row_2.addWidget(
            self.ram_gauge
        )

        gauge_row_2.addWidget(
            self.temp_gauge
        )

        self.gpu_1_gauge = PerformanceGauge(
            title="GPU 1",
            unit="%",
            accent="#26c6da",
            redline=90
        )

        gauge_row_2.addWidget(
            self.gpu_1_gauge
        )

        layout.addLayout(
            gauge_row_2,
            1
        )

        telemetry_header = QHBoxLayout()

        telemetry_title = QLabel(
            "LIVE TELEMETRY"
        )

        telemetry_title.setObjectName(
            "telemetry_title"
        )

        telemetry_header.addWidget(
            telemetry_title
        )

        telemetry_header.addStretch()

        self.gauge_settings_button = QPushButton("GAUGE SETTINGS")
        self.gauge_settings_button.setObjectName("telemetry_button")
        self.gauge_settings_button.clicked.connect(self.open_gauge_refresh_dialog)

        telemetry_header.addWidget(
            self.gauge_settings_button
        )

        layout.addLayout(
            telemetry_header
        )

        self.graph = pg.PlotWidget()

        self.graph.setMinimumHeight(
            180
        )

        self.graph.setBackground(
            "#0d0d0d"
        )

        self.graph.showGrid(
            x=True,
            y=True,
            alpha=0.07
        )

        self.graph.setYRange(
            0,
            100
        )

        self.graph.setLabel(
            "left",
            "LOAD %"
        )

        self.graph.setLabel(
            "bottom",
            "TIME"
        )

        self.graph.getAxis(
            "left"
        ).setTextPen(
            "#666666"
        )

        self.graph.getAxis(
            "bottom"
        ).setTextPen(
            "#666666"
        )

        self.graph.getAxis(
            "left"
        ).setPen(
            pg.mkPen(
                "#292929"
            )
        )

        self.graph.getAxis(
            "bottom"
        ).setPen(
            pg.mkPen(
                "#292929"
            )
        )


        self.graph.addLegend(
            offset=(10, 10)
        )


        self.cpu_curve = pg.PlotDataItem(
            self.cpu_history,
            pen=pg.mkPen(
                "#ff8f00",
                width=2
            ),
            name="CPU"
        )

        self.cpu_bottom = pg.PlotDataItem(
            [0] * self.max_points
        )

        self.cpu_fill = pg.FillBetweenItem(
            self.cpu_curve,
            self.cpu_bottom,
            brush=pg.mkBrush(
                255,
                143,
                0,
                50
            )
        )

        self.graph.addItem(
            self.cpu_fill
        )

        self.graph.addItem(
            self.cpu_curve
        )
        self.gpu_curve = pg.PlotDataItem(
            self.gpu_history,
            pen=pg.mkPen(
                "#8bc34a",
                width=2
            ),
            name="GPU 0"
        )

        self.gpu_bottom = pg.PlotDataItem(
            [0] * self.max_points
        )

        self.gpu_fill = pg.FillBetweenItem(
            self.gpu_curve,
            self.gpu_bottom,
            brush=pg.mkBrush(
                139,
                195,
                74,
                45
            )
        )

        self.graph.addItem(
            self.gpu_fill
        )

        self.graph.addItem(
            self.gpu_curve
        )

        self.gpu_1_curve = pg.PlotDataItem(
            self.gpu_1_history,
            pen=pg.mkPen(
                "#26c6da",
                width=2
            ),
            name="GPU 1"
        )

        self.gpu_1_bottom = pg.PlotDataItem(
            [0] * self.max_points
        )

        self.gpu_1_fill = pg.FillBetweenItem(
            self.gpu_1_curve,
            self.gpu_1_bottom,
            brush=pg.mkBrush(
                38,
                198,
                218,
                35
            )
        )

        self.graph.addItem(
            self.gpu_1_fill
        )

        self.graph.addItem(
            self.gpu_1_curve
        )


        self.ram_curve = pg.PlotDataItem(
            self.ram_history,
            pen=pg.mkPen(
                "#ab47bc",
                width=2
            ),
            name="RAM"
        )

        self.ram_bottom = pg.PlotDataItem(
            [0] * self.max_points
        )

        self.ram_fill = pg.FillBetweenItem(
            self.ram_curve,
            self.ram_bottom,
            brush=pg.mkBrush(
                171,
                71,
                188,
                45
            )
        )

        self.graph.addItem(
            self.ram_fill
        )

        self.graph.addItem(
            self.ram_curve
        )

        layout.addWidget(
            self.graph,
            1
        )

    def refresh_gauge_value(self, gauge_name):
        if gauge_name == "cpu_load":
            self.cpu_gauge.setValue(psutil.cpu_percent(interval=None))
        elif gauge_name == "cpu_temp":
            self.cpu_temp_gauge.setValue(self.get_cpu_temperature())
        elif gauge_name == "gpu_0":
            gpu_usage = self.get_lhm_gpu_usage()
            self.gpu_0_gauge.setValue(gpu_usage[0] if len(gpu_usage) > 0 else None)
        elif gauge_name == "gpu_temp":
            gpu_temperature = None
            if self.gpu_available:
                try:
                    gpu_temperature = pynvml.nvmlDeviceGetTemperature(
                        self.gpu_handle,
                        pynvml.NVML_TEMPERATURE_GPU,
                    )
                except Exception:
                    gpu_temperature = None
            self.temp_gauge.setValue(gpu_temperature)
        elif gauge_name == "ram_load":
            self.ram_gauge.setValue(psutil.virtual_memory().percent)
        elif gauge_name == "gpu_1":
            gpu_usage = self.get_lhm_gpu_usage()
            self.gpu_1_gauge.setValue(gpu_usage[1] if len(gpu_usage) > 1 else None)

    def set_gauge_refresh_interval(self, gauge_name, interval_ms):
        if gauge_name not in self.gauge_refresh_settings:
            return

        self.gauge_refresh_settings[gauge_name] = max(100, int(interval_ms))
        if gauge_name in self.gauge_timers:
            self.gauge_timers[gauge_name].setInterval(self.gauge_refresh_settings[gauge_name])

    def open_gauge_refresh_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Gauge Refresh Settings")
        dialog.setModal(True)
        dialog.resize(420, 280)

        form_layout = QFormLayout(dialog)
        form_layout.setLabelAlignment(Qt.AlignLeft)

        controls = {}
        gauge_labels = {
            "cpu_load": "CPU Load",
            "cpu_temp": "CPU Temp",
            "gpu_0": "GPU 0 Usage",
            "gpu_temp": "GPU Temp",
            "ram_load": "Memory Load",
            "gpu_1": "GPU 1 Usage",
        }

        for key, label in gauge_labels.items():
            spin_box = QSpinBox(dialog)
            spin_box.setRange(100, 5000)
            spin_box.setSingleStep(50)
            spin_box.setSuffix(" ms")
            spin_box.setValue(self.gauge_refresh_settings[key])
            spin_box.valueChanged.connect(
                lambda value, gauge_name=key: self.set_gauge_refresh_interval(gauge_name, value)
            )
            controls[key] = spin_box
            form_layout.addRow(label, spin_box)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok, dialog)
        button_box.accepted.connect(dialog.accept)
        form_layout.addRow(button_box)

        dialog.exec()

    def get_cpu_temperature(self):

        """Return the live CPU package temperature from available sensors."""

        hardware_temperature = self.get_lhm_cpu_temperature()
        if hardware_temperature is not None:
            return hardware_temperature

        return self.get_psutil_cpu_temperature()

    def get_lhm_cpu_temperature(self):

        """Read the local LibreHardwareMonitor web feed when it is running."""

        try:
            with urlopen(
                "http://127.0.0.1:8085/data.json",
                timeout=0.3
            ) as response:
                sensor_tree = json.load(response)
        except (OSError, URLError, ValueError):
            return None

        def find_cpu_node(node):
            if not isinstance(node, dict):
                return None

            hardware_id = node.get("HardwareId", "").lower()
            node_text = node.get("Text", "").lower()
            if "cpu" in hardware_id or "cpu" in node_text:
                return node

            for child in node.get("Children", []):
                cpu_node = find_cpu_node(child)
                if cpu_node is not None:
                    return cpu_node

            return None

        def find_temperature_sensors(node):
            sensors = []

            if not isinstance(node, dict):
                return sensors

            if node.get("Type") == "Temperature":
                name = node.get("Text", "").lower()
                if "distance to tjmax" not in name:
                    try:
                        raw_value = node.get("RawValue", node.get("Value", ""))
                        value = float(str(raw_value).split()[0])
                        sensors.append((name, value))
                    except (AttributeError, IndexError, ValueError):
                        pass

            for child in node.get("Children", []):
                sensors.extend(find_temperature_sensors(child))

            return sensors

        cpu_node = find_cpu_node(sensor_tree)
        if cpu_node is None:
            return None

        temperatures = find_temperature_sensors(cpu_node)
        if not temperatures:
            return None

        for name, value in temperatures:
            if name == "cpu package":
                return value

        for name, value in temperatures:
            if name == "core max":
                return value

        return max(value for _, value in temperatures)

    def get_lhm_gpu_usage(self):

        """Return live GPU core loads from LibreHardwareMonitor."""

        try:
            with urlopen(
                "http://127.0.0.1:8085/data.json",
                timeout=0.3
            ) as response:
                sensor_tree = json.load(response)
        except (OSError, URLError, ValueError):
            return []

        gpu_nodes = []

        def find_gpu_nodes(node):
            if not isinstance(node, dict):
                return

            hardware_type = str(node.get("HardwareType", "")).lower()
            node_text = str(node.get("Text", "")).lower()
            if "gpu" in hardware_type or any(
                name in node_text
                for name in (
                    "nvidia",
                    "radeon",
                    "graphics",
                    "iris",
                    "uhd graphics",
                    "arc graphics",
                )
            ):
                gpu_nodes.append(node)

            for child in node.get("Children", []):
                find_gpu_nodes(child)

        def find_loads(node):
            loads = []
            if not isinstance(node, dict):
                return loads

            sensor_type = str(node.get("Type", "")).lower()
            sensor_name = str(node.get("Text", "")).lower()
            if sensor_type == "load" and any(
                name in sensor_name
                for name in ("gpu core", "3d", "gpu")
            ):
                raw_value = node.get("RawValue", node.get("Value", ""))
                try:
                    loads.append((sensor_name, float(str(raw_value).split()[0])))
                except (AttributeError, IndexError, ValueError):
                    pass

            for child in node.get("Children", []):
                loads.extend(find_loads(child))
            return loads

        find_gpu_nodes(sensor_tree)
        usage = []
        for node in gpu_nodes:
            loads = find_loads(node)
            if loads:
                preferred_loads = [
                    value
                    for name, value in loads
                    if name in ("gpu core", "d3d 3d")
                ]
                usage.append(
                    max(preferred_loads if preferred_loads else [
                        value for _, value in loads
                    ])
                )

        return usage[:2]

    def get_psutil_cpu_temperature(self):

        """Return the best available CPU temperature reported by psutil."""

        if not hasattr(psutil, "sensors_temperatures"):
            return self.get_windows_cpu_temperature()

        try:
            sensor_groups = psutil.sensors_temperatures(
                fahrenheit=False
            )
        except (AttributeError, OSError):
            return None

        preferred_readings = []
        other_readings = []

        for group_name, readings in sensor_groups.items():
            group_is_cpu = any(
                keyword in group_name.lower()
                for keyword in ("coretemp", "cpu", "k10temp", "zenpower")
            )

            for reading in readings:
                current = getattr(reading, "current", None)
                if current is None:
                    continue

                label = getattr(reading, "label", "").lower()
                if any(
                    keyword in label
                    for keyword in ("package", "cpu", "tdie", "tctl")
                ):
                    preferred_readings.append(current)
                elif group_is_cpu or "core" in label:
                    other_readings.append(current)

        if preferred_readings:
            return max(preferred_readings)

        if other_readings:
            return max(other_readings)

        return self.get_windows_cpu_temperature()

    def get_windows_cpu_temperature(self):

        """Read Windows ACPI thermal zones when no native sensor API exists."""

        if not sys.platform.startswith("win"):
            return None

        now = time.monotonic()
        cached_at = getattr(self, "_cpu_temperature_cached_at", 0)
        if now - cached_at < 2.0:
            return getattr(self, "_cpu_temperature_cached", None)

        def run_powershell(command):
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    command,
                ],
                capture_output=True,
                text=True,
                timeout=0.8,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            output = result.stdout.strip()
            if not output:
                return []
            values = json.loads(output)
            return values if isinstance(values, list) else [values]

        try:
            temperatures = [
                float(reading)
                for reading in run_powershell(
                    "$readings = @(); "
                    "foreach ($namespace in @('root/LibreHardwareMonitor', "
                    "'root/OpenHardwareMonitor')) { "
                    "try { $readings += Get-CimInstance -Namespace $namespace "
                    "-ClassName Sensor -ErrorAction Stop | "
                    "Where-Object { $_.SensorType -eq 'Temperature' -and "
                    "$_.Value -ne $null -and $_.Name -notlike '*Distance*' "
                    "-and ($_.Name -match 'CPU|Package|Core|Tdie|Tctl' "
                    "-or $_.Identifier -match 'cpu') } "
                    "} catch {} }; "
                    "$readings | Select-Object -ExpandProperty Value "
                    "| ConvertTo-Json -Compress"
                )
            ]
        except (OSError, subprocess.TimeoutExpired, TypeError, ValueError, json.JSONDecodeError):
            temperatures = []

        if not temperatures:
            try:
                readings = run_powershell(
                    "(Get-CimInstance -Namespace root/wmi "
                    "-ClassName MSAcpi_ThermalZoneTemperature "
                    "| Select-Object -ExpandProperty CurrentTemperature "
                    "| ConvertTo-Json -Compress)"
                )
                temperatures = [
                    (float(reading) / 10) - 273.15
                    for reading in readings
                    if reading is not None
                ]
            except (OSError, subprocess.TimeoutExpired, TypeError, ValueError, json.JSONDecodeError):
                temperatures = []

        self._cpu_temperature_cached_at = now
        self._cpu_temperature_cached = max(temperatures) if temperatures else None
        return self._cpu_temperature_cached

    def update_data(self):

        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        cpu_temperature = self.get_cpu_temperature()
        gpu_adapter_usage = self.get_lhm_gpu_usage()
        gpu_temperature = None

        if self.gpu_available:
            try:
                gpu_temperature = pynvml.nvmlDeviceGetTemperature(
                    self.gpu_handle,
                    pynvml.NVML_TEMPERATURE_GPU
                )
            except Exception:
                gpu_temperature = None

        gpu_0_usage = (
            gpu_adapter_usage[0]
            if len(gpu_adapter_usage) > 0
            else None
        )
        gpu_1_usage = (
            gpu_adapter_usage[1]
            if len(gpu_adapter_usage) > 1
            else None
        )

        self.cpu_gauge.setValue(cpu)
        self.cpu_temp_gauge.setValue(cpu_temperature)
        self.ram_gauge.setValue(ram)
        self.temp_gauge.setValue(gpu_temperature)
        self.gpu_0_gauge.setValue(gpu_0_usage)
        self.gpu_1_gauge.setValue(gpu_1_usage)

        self.cpu_history.append(cpu)
        self.gpu_history.append(gpu_0_usage or 0)
        self.gpu_1_history.append(gpu_1_usage or 0)
        self.ram_history.append(ram)

        self.cpu_history = self.cpu_history[-self.max_points:]
        self.gpu_history = self.gpu_history[-self.max_points:]
        self.gpu_1_history = self.gpu_1_history[-self.max_points:]
        self.ram_history = self.ram_history[-self.max_points:]

        self.cpu_curve.setData(self.cpu_history)
        self.gpu_curve.setData(self.gpu_history)
        self.gpu_1_curve.setData(self.gpu_1_history)
        self.ram_curve.setData(self.ram_history)
        self.cpu_bottom.setData([0] * len(self.cpu_history))
        self.gpu_bottom.setData([0] * len(self.gpu_history))
        self.gpu_1_bottom.setData([0] * len(self.gpu_1_history))
        self.ram_bottom.setData([0] * len(self.ram_history))
    def closeEvent(
        self,
        event
    ):

        self.timer.stop()

        event.accept()