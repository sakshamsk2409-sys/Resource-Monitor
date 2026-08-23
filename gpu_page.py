from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QGridLayout,
)

from dashboard import CarbonFiberBackground

# ---------------------------------------------------------
# Matplotlib
# ---------------------------------------------------------
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

# ---------------------------------------------------------
# NVIDIA NVML
# ---------------------------------------------------------
try:
    import pynvml
    HAS_PYNVML = True
except ImportError:
    pynvml = None
    HAS_PYNVML = False


class GPUPerformancePage(CarbonFiberBackground):

    def __init__(self, parent=None):
        super().__init__(parent)

        # -------------------------------------------------
        # GPU state
        # -------------------------------------------------
        self.gpu_available = False
        self.gpu_handle = None

        self.gpu_name = "N/A"
        self.driver_ver = "N/A"
        self.nvml_ver = "N/A"

        # -------------------------------------------------
        # History
        # -------------------------------------------------
        self.gpu_history = []
        self.temp_history = []

        # -------------------------------------------------
        # Initialize GPU
        # -------------------------------------------------
        self.init_gpu()

        # -------------------------------------------------
        # Build UI
        # -------------------------------------------------
        self.setup_ui()

        # -------------------------------------------------
        # Telemetry timer
        # -------------------------------------------------
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.update_telemetry)
        self.timer.start()

    # =====================================================
    # TIMER CONTROL
    # =====================================================

    def set_refresh_interval(self, ms):
        self.timer.setInterval(ms)

    def pause_timer(self):
        if self.timer.isActive():
            self.timer.stop()

    def resume_timer(self):
        if not self.timer.isActive():
            self.timer.start()

    # =====================================================
    # GPU INITIALIZATION
    # =====================================================

    def init_gpu(self):

        if not HAS_PYNVML or not pynvml:
            self.gpu_name = "NVML Library Not Installed"
            return

        try:
            pynvml.nvmlInit()

            gpu_count = pynvml.nvmlDeviceGetCount()

            if gpu_count <= 0:
                self.gpu_name = "No NVIDIA GPU Detected"
                return

            # Use first NVIDIA GPU
            self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            self.gpu_available = True

            # GPU name
            try:
                name = pynvml.nvmlDeviceGetName(self.gpu_handle)

                if isinstance(name, bytes):
                    name = name.decode(
                        "utf-8",
                        errors="ignore"
                    )

                self.gpu_name = str(name)

            except Exception:
                self.gpu_name = "GPU"

            # Driver version
            try:
                version = pynvml.nvmlSystemGetDriverVersion()

                if isinstance(version, bytes):
                    version = version.decode(
                        "utf-8",
                        errors="ignore"
                    )

                self.driver_ver = str(version)

            except Exception:
                pass

            # NVML version
            try:
                version = pynvml.nvmlSystemGetNVMLVersion()

                if isinstance(version, bytes):
                    version = version.decode(
                        "utf-8",
                        errors="ignore"
                    )

                self.nvml_ver = str(version)

            except Exception:
                pass

        except Exception as e:

            print("GPU NVML init error:", e)

            self.gpu_available = False
            self.gpu_name = "NVML Error / No NVIDIA GPU"

    # =====================================================
    # UI
    # =====================================================

    def setup_ui(self):

        main_layout = QVBoxLayout(self)

        main_layout.setContentsMargins(
            35,
            30,
            35,
            30
        )

        main_layout.setSpacing(20)

        # -------------------------------------------------
        # Header
        # -------------------------------------------------

        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        title = QLabel(
            "GPU PERFORMANCE & HARDWARE TELEMETRY"
        )

        title.setObjectName("page_title")

        subtitle = QLabel(
            f"Hardware Monitor: {self.gpu_name}"
        )

        subtitle.setObjectName("subtitle")

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)

        main_layout.addLayout(header_layout)

        # -------------------------------------------------
        # Scroll area
        # -------------------------------------------------

        scroll = QScrollArea()

        scroll.setWidgetResizable(True)

        scroll.setStyleSheet(
            "QScrollArea { "
            "background: transparent; "
            "border: none; "
            "}"
        )

        content = QWidget()

        content_layout = QVBoxLayout(content)

        content_layout.setContentsMargins(
            0,
            10,
            10,
            10
        )

        content_layout.setSpacing(20)

        # -------------------------------------------------
        # Overview
        # -------------------------------------------------

        content_layout.addWidget(
            self.create_overview_card()
        )

        if self.gpu_available:

            content_layout.addLayout(
                self.create_metrics_row()
            )

            content_layout.addWidget(
                self.create_graph_card()
            )

        else:

            content_layout.addWidget(
                self.create_fallback_card()
            )

        content_layout.addStretch()

        scroll.setWidget(content)

        main_layout.addWidget(scroll)

    # =====================================================
    # GENERIC CARD
    # =====================================================

    def create_card(self, title_text):

        card = QFrame()

        card.setObjectName(
            "memory_panel"
        )

        card_layout = QVBoxLayout(card)

        card_layout.setContentsMargins(
            20,
            18,
            20,
            18
        )

        card_layout.setSpacing(12)

        card_title = QLabel(
            title_text
        )

        card_title.setObjectName(
            "section_title"
        )

        card_layout.addWidget(card_title)

        separator = QFrame()

        separator.setFrameShape(
            QFrame.HLine
        )

        separator.setStyleSheet(
            "background-color: #222222; "
            "max-height: 1px;"
        )

        card_layout.addWidget(separator)

        return card, card_layout

    # =====================================================
    # GPU OVERVIEW
    # =====================================================

    def create_overview_card(self):

        card, layout = self.create_card(
            "GRAPHICS PROCESSOR SPECIFICATIONS"
        )

        grid = QGridLayout()

        grid.setSpacing(15)

        items = [
            (
                "GPU Device Name",
                self.gpu_name
            ),
            (
                "NVML Driver Version",
                self.driver_ver
            ),
            (
                "NVML API Version",
                self.nvml_ver
            ),
            (
                "Hardware Status",
                (
                    "● ACTIVE / TELEMETRY ONLINE"
                    if self.gpu_available
                    else
                    "○ INACTIVE / STANDBY"
                )
            ),
        ]

        for i, (label, value) in enumerate(items):

            label_widget = QLabel(label)

            label_widget.setStyleSheet(
                "color: #888888; "
                "font-size: 11px; "
                "font-weight: bold;"
            )

            value_widget = QLabel(value)

            if "ACTIVE" in value:
                color = "#55d66f"

            elif i == 0:
                color = "#ffaa00"

            else:
                color = "#e0e0e0"

            value_widget.setStyleSheet(
                f"color: {color}; "
                "font-size: 11px; "
                "font-weight: bold;"
            )

            row, col = divmod(i, 2)

            grid.addWidget(
                label_widget,
                row * 2,
                col * 2
            )

            grid.addWidget(
                value_widget,
                row * 2 + 1,
                col * 2
            )

        layout.addLayout(grid)

        return card

    # =====================================================
    # METRICS
    # =====================================================

    def create_metrics_row(self):

        row = QHBoxLayout()

        row.setSpacing(15)

        # -------------------------------------------------
        # GPU Load
        # -------------------------------------------------

        card, layout = self.create_card(
            "CORE LOAD"
        )

        self.gpu_load_val = QLabel(
            "0%"
        )

        self.gpu_load_val.setStyleSheet(
            "color: #ffaa00; "
            "font-size: 24px; "
            "font-weight: bold;"
        )

        layout.addWidget(
            self.gpu_load_val
        )

        row.addWidget(card)

        # -------------------------------------------------
        # VRAM
        # -------------------------------------------------

        card, layout = self.create_card(
            "VRAM USAGE"
        )

        self.vram_val = QLabel(
            "0.0 GB / 0.0 GB (0%)"
        )

        self.vram_val.setStyleSheet(
            "color: #ab47bc; "
            "font-size: 18px; "
            "font-weight: bold;"
        )

        layout.addWidget(
            self.vram_val
        )

        row.addWidget(card)

        # -------------------------------------------------
        # Temperature
        # -------------------------------------------------

        card, layout = self.create_card(
            "GPU TEMP"
        )

        self.temp_val = QLabel(
            "N/A"
        )

        self.temp_val.setStyleSheet(
            "color: #e53935; "
            "font-size: 24px; "
            "font-weight: bold;"
        )

        layout.addWidget(
            self.temp_val
        )

        row.addWidget(card)

        # -------------------------------------------------
        # Power + Clock
        # -------------------------------------------------

        card, layout = self.create_card(
            "POWER & CLOCK"
        )

        self.power_val = QLabel(
            "Power: N/A"
        )

        self.power_val.setStyleSheet(
            "color: #26a69a; "
            "font-size: 12px; "
            "font-weight: bold;"
        )

        self.clock_val = QLabel(
            "Clock: N/A"
        )

        self.clock_val.setStyleSheet(
            "color: #8bc34a; "
            "font-size: 12px; "
            "font-weight: bold;"
        )

        layout.addWidget(
            self.power_val
        )

        layout.addWidget(
            self.clock_val
        )

        row.addWidget(card)

        return row

    # =====================================================
    # MATPLOTLIB GRAPH
    # =====================================================

    def create_graph_card(self):

        card, layout = self.create_card(
            "GPU CORE UTILIZATION & TEMPERATURE HISTORY"
        )

        # -------------------------------------------------
        # Matplotlib Figure
        # -------------------------------------------------

        self.figure = Figure(
            figsize=(8, 3),
            dpi=100,
            facecolor="#050505"
        )

        self.canvas = FigureCanvasQTAgg(
            self.figure
        )

        self.ax = self.figure.add_subplot(111)

        # Background
        self.ax.set_facecolor(
            "#050505"
        )

        # -------------------------------------------------
        # Axes styling
        # -------------------------------------------------

        self.ax.tick_params(
            colors="#777777",
            labelsize=8
        )

        for spine in self.ax.spines.values():
            spine.set_color("#333333")

        self.ax.grid(
            True,
            alpha=0.15,
            color="#888888"
        )

        self.ax.set_ylim(
            0,
            100
        )

        self.ax.set_ylabel(
            "Usage / Temperature",
            color="#777777",
            fontsize=8
        )

        # -------------------------------------------------
        # Lines
        # -------------------------------------------------

        self.gpu_line, = self.ax.plot(
            [],
            [],
            color="#ffaa00",
            linewidth=2,
            label="GPU Load %"
        )

        self.temp_line, = self.ax.plot(
            [],
            [],
            color="#e53935",
            linewidth=2,
            label="Temperature °C"
        )

        # -------------------------------------------------
        # Legend
        # -------------------------------------------------

        legend = self.ax.legend(
            loc="upper left",
            fontsize=8,
            frameon=False
        )

        for text in legend.get_texts():
            text.set_color("#aaaaaa")

        # -------------------------------------------------
        # Layout
        # -------------------------------------------------

        self.figure.tight_layout(
            pad=1.5
        )

        self.canvas.setMinimumHeight(
            220
        )

        layout.addWidget(
            self.canvas
        )

        return card

    # =====================================================
    # FALLBACK
    # =====================================================

    def create_fallback_card(self):

        card, layout = self.create_card(
            "NVIDIA TELEMETRY NOTICE"
        )

        label = QLabel(
            "NVIDIA GPU telemetry via NVML is currently "
            "not active.\n\n"
            "• If you have an NVIDIA GPU, verify that "
            "the NVIDIA graphics driver is installed and "
            "pynvml / nvidia-ml-py is installed.\n"
            "• On systems with Integrated Graphics "
            "(Intel HD/Iris or AMD Radeon), standard "
            "CPU/RAM telemetry is active in the Dashboard."
        )

        label.setStyleSheet(
            "color: #aaaaaa; "
            "font-size: 12px;"
        )

        label.setWordWrap(True)

        layout.addWidget(
            label
        )

        return card

    # =====================================================
    # TELEMETRY
    # =====================================================

    def update_telemetry(self):

        if (
            not self.gpu_available
            or not self.gpu_handle
        ):
            return

        # -------------------------------------------------
        # GPU utilization
        # -------------------------------------------------

        gpu_util = 0

        try:

            result = (
                pynvml.nvmlDeviceGetUtilizationRates(
                    self.gpu_handle
                )
            )

            gpu_util = result.gpu

            self.gpu_load_val.setText(
                f"{gpu_util}%"
            )

        except Exception:
            pass

        # -------------------------------------------------
        # VRAM
        # -------------------------------------------------

        try:

            mem = (
                pynvml.nvmlDeviceGetMemoryInfo(
                    self.gpu_handle
                )
            )

            used_gb = (
                mem.used /
                (1024 ** 3)
            )

            total_gb = (
                mem.total /
                (1024 ** 3)
            )

            percentage = (
                (mem.used / mem.total) * 100
                if mem.total
                else 0
            )

            self.vram_val.setText(
                f"{used_gb:.2f} GB / "
                f"{total_gb:.2f} GB "
                f"({percentage:.0f}%)"
            )

        except Exception:
            pass

        # -------------------------------------------------
        # Temperature
        # -------------------------------------------------

        gpu_temp = 0

        try:

            gpu_temp = (
                pynvml.nvmlDeviceGetTemperature(
                    self.gpu_handle,
                    pynvml.NVML_TEMPERATURE_GPU
                )
            )

            self.temp_val.setText(
                f"{gpu_temp} °C"
            )

        except Exception:

            self.temp_val.setText(
                "N/A"
            )

        # -------------------------------------------------
        # Power
        # -------------------------------------------------

        try:

            power = (
                pynvml.nvmlDeviceGetPowerUsage(
                    self.gpu_handle
                ) / 1000.0
            )

            self.power_val.setText(
                f"Power: {power:.1f} W"
            )

        except Exception:

            self.power_val.setText(
                "Power: N/A"
            )

        # -------------------------------------------------
        # Clock
        # -------------------------------------------------

        try:

            clock = (
                pynvml.nvmlDeviceGetClockInfo(
                    self.gpu_handle,
                    pynvml.NVML_CLOCK_GRAPHICS
                )
            )

            self.clock_val.setText(
                f"Clock: {clock} MHz"
            )

        except Exception:

            self.clock_val.setText(
                "Clock: N/A"
            )

        # -------------------------------------------------
        # History
        # -------------------------------------------------

        self.gpu_history.append(
            gpu_util
        )

        self.temp_history.append(
            gpu_temp
        )

        # 60 samples
        if len(self.gpu_history) > 60:

            self.gpu_history.pop(0)
            self.temp_history.pop(0)

        # -------------------------------------------------
        # Matplotlib update
        # -------------------------------------------------

        if hasattr(self, "gpu_line"):

            x_values = range(
                len(self.gpu_history)
            )

            self.gpu_line.set_data(
                x_values,
                self.gpu_history
            )

            self.temp_line.set_data(
                x_values,
                self.temp_history
            )

            self.ax.set_xlim(
                0,
                max(60, len(self.gpu_history))
            )

            # Redraw
            self.canvas.draw_idle()