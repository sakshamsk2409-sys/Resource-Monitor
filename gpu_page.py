import pyqtgraph as pg

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
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

try:
    import pynvml
    HAS_PYNVML = True
except ImportError:
    pynvml = None
    HAS_PYNVML = False


class GPUPerformancePage(CarbonFiberBackground):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.gpu_available = False
        self.gpu_handle = None
        self.gpu_name = "N/A"
        self.driver_ver = "N/A"
        self.nvml_ver = "N/A"

        self.gpu_history = []
        self.temp_history = []

        self.init_gpu()
        self.setup_ui()

        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.update_telemetry)
        self.timer.start()

    def set_refresh_interval(self, ms):
        self.timer.setInterval(ms)

    def pause_timer(self):
        if self.timer.isActive():
            self.timer.stop()

    def resume_timer(self):
        if not self.timer.isActive():
            self.timer.start()

    def init_gpu(self):
        if HAS_PYNVML and pynvml:
            try:
                pynvml.nvmlInit()
                gpu_count = pynvml.nvmlDeviceGetCount()
                if gpu_count > 0:
                    self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    self.gpu_available = True

                    try:
                        name = pynvml.nvmlDeviceGetName(self.gpu_handle)
                        if isinstance(name, bytes):
                            name = name.decode("utf-8", errors="ignore")
                        self.gpu_name = str(name)
                    except Exception:
                        self.gpu_name = "NVIDIA GPU"

                    try:
                        d_ver = pynvml.nvmlSystemGetDriverVersion()
                        if isinstance(d_ver, bytes):
                            d_ver = d_ver.decode("utf-8", errors="ignore")
                        self.driver_ver = str(d_ver)
                    except Exception:
                        pass

                    try:
                        n_ver = pynvml.nvmlSystemGetNVMLVersion()
                        if isinstance(n_ver, bytes):
                            n_ver = n_ver.decode("utf-8", errors="ignore")
                        self.nvml_ver = str(n_ver)
                    except Exception:
                        pass
                else:
                    self.gpu_name = "No NVIDIA GPU Detected"
            except Exception as e:
                print("GPU NVML init error:", e)
                self.gpu_available = False
                self.gpu_name = "NVML Error / No NVIDIA GPU"
        else:
            self.gpu_name = "NVML Library Not Installed"

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(35, 30, 35, 30)
        main_layout.setSpacing(20)

        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        title = QLabel("GPU PERFORMANCE & HARDWARE TELEMETRY")
        title.setObjectName("page_title")

        subtitle = QLabel(f"Hardware Monitor: {self.gpu_name}")
        subtitle.setObjectName("subtitle")

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 10, 10, 10)
        content_layout.setSpacing(20)

        # Overview Card
        content_layout.addWidget(self.create_overview_card())

        if self.gpu_available:
            # Metrics Cards Row
            content_layout.addLayout(self.create_metrics_row())

            # Real-Time Telemetry Graph
            content_layout.addWidget(self.create_graph_card())
        else:
            # Fallback Card
            content_layout.addWidget(self.create_fallback_card())

        content_layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def create_card(self, title_text):
        card = QFrame()
        card.setObjectName("memory_panel")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(12)

        card_title = QLabel(title_text)
        card_title.setObjectName("section_title")
        card_layout.addWidget(card_title)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #222222; max-height: 1px;")
        card_layout.addWidget(sep)

        return card, card_layout

    def create_overview_card(self):
        card, layout = self.create_card("GRAPHICS PROCESSOR SPECIFICATIONS")
        grid = QGridLayout()
        grid.setSpacing(15)

        items = [
            ("GPU Device Name", self.gpu_name),
            ("NVML Driver Version", self.driver_ver),
            ("NVML API Version", self.nvml_ver),
            ("Hardware Status", "● ACTIVE / TELEMETRY ONLINE" if self.gpu_available else "○ INACTIVE / STANDBY"),
        ]

        for i, (label, val) in enumerate(items):
            l_widget = QLabel(label)
            l_widget.setStyleSheet("color: #888888; font-size: 11px; font-weight: bold;")

            v_widget = QLabel(val)
            color = "#55d66f" if "ACTIVE" in val else ("#ffaa00" if i == 0 else "#e0e0e0")
            v_widget.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")

            row, col = divmod(i, 2)
            grid.addWidget(l_widget, row * 2, col * 2)
            grid.addWidget(v_widget, row * 2 + 1, col * 2)

        layout.addLayout(grid)
        return card

    def create_metrics_row(self):
        row = QHBoxLayout()
        row.setSpacing(15)

        # 1. Core Utilization Card
        c1, l1 = self.create_card("CORE LOAD")
        self.gpu_load_val = QLabel("0%")
        self.gpu_load_val.setStyleSheet("color: #ffaa00; font-size: 24px; font-weight: bold;")
        l1.addWidget(self.gpu_load_val)
        row.addWidget(c1)

        # 2. VRAM Card
        c2, l2 = self.create_card("VRAM USAGE")
        self.vram_val = QLabel("0.0 GB / 0.0 GB (0%)")
        self.vram_val.setStyleSheet("color: #ab47bc; font-size: 18px; font-weight: bold;")
        l2.addWidget(self.vram_val)
        row.addWidget(c2)

        # 3. Temperature Card
        c3, l3 = self.create_card("GPU TEMP")
        self.temp_val = QLabel("N/A")
        self.temp_val.setStyleSheet("color: #e53935; font-size: 24px; font-weight: bold;")
        l3.addWidget(self.temp_val)
        row.addWidget(c3)

        # 4. Power & Clock Card
        c4, l4 = self.create_card("POWER & CLOCK")
        self.power_val = QLabel("Power: N/A")
        self.power_val.setStyleSheet("color: #26a69a; font-size: 12px; font-weight: bold;")
        self.clock_val = QLabel("Clock: N/A")
        self.clock_val.setStyleSheet("color: #8bc34a; font-size: 12px; font-weight: bold;")
        l4.addWidget(self.power_val)
        l4.addWidget(self.clock_val)
        row.addWidget(c4)

        return row

    def create_graph_card(self):
        card, layout = self.create_card("GPU CORE UTILIZATION & TEMPERATURE HISTORY (60s)")

        self.graph = pg.PlotWidget()
        self.graph.setBackground("#050505")
        self.graph.showGrid(x=True, y=True, alpha=0.15)
        self.graph.setYRange(0, 100)
        self.graph.setFixedHeight(220)

        # Utilization curve (Amber)
        self.gpu_curve = self.graph.plot(pen=pg.mkPen(color="#ffaa00", width=2), name="GPU Load %")

        # Temp curve (Red)
        self.temp_curve = self.graph.plot(pen=pg.mkPen(color="#e53935", width=2), name="Temp °C")

        layout.addWidget(self.graph)
        return card

    def create_fallback_card(self):
        card, layout = self.create_card("NVIDIA TELEMETRY NOTICE")

        lbl = QLabel(
            "NVIDIA GPU telemetry via NVML is currently not active.\n\n"
            "• If you have an NVIDIA GPU, verify that the NVIDIA graphics driver is installed and pynvml / nvidia-ml-py is installed.\n"
            "• On systems with Integrated Graphics (Intel HD/Iris or AMD Radeon), standard CPU/RAM telemetry is active in the Dashboard."
        )
        lbl.setStyleSheet("color: #aaaaaa; font-size: 12px; line-height: 1.5;")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        return card

    def update_telemetry(self):
        if not self.gpu_available or not self.gpu_handle:
            return

        # Core utilization
        gpu_util = 0
        try:
            res = pynvml.nvmlDeviceGetUtilizationRates(self.gpu_handle)
            gpu_util = res.gpu
            self.gpu_load_val.setText(f"{gpu_util}%")
        except Exception:
            pass

        # VRAM
        try:
            mem = pynvml.nvmlDeviceGetMemoryInfo(self.gpu_handle)
            used_gb = mem.used / (1024**3)
            total_gb = mem.total / (1024**3)
            pct = (mem.used / mem.total) * 100 if mem.total else 0
            self.vram_val.setText(f"{used_gb:.2f} GB / {total_gb:.2f} GB ({pct:.0f}%)")
        except Exception:
            pass

        # Temperature
        gpu_temp = 0
        try:
            gpu_temp = pynvml.nvmlDeviceGetTemperature(self.gpu_handle, pynvml.NVML_TEMPERATURE_GPU)
            self.temp_val.setText(f"{gpu_temp} °C")
        except Exception:
            self.temp_val.setText("N/A")

        # Power
        try:
            pwr = pynvml.nvmlDeviceGetPowerUsage(self.gpu_handle) / 1000.0
            self.power_val.setText(f"Power: {pwr:.1f} W")
        except Exception:
            self.power_val.setText("Power: N/A")

        # Clock
        try:
            clk = pynvml.nvmlDeviceGetClockInfo(self.gpu_handle, pynvml.NVML_CLOCK_GRAPHICS)
            self.clock_val.setText(f"Clock: {clk} MHz")
        except Exception:
            self.clock_val.setText("Clock: N/A")

        # History Plot
        self.gpu_history.append(gpu_util)
        self.temp_history.append(gpu_temp)

        if len(self.gpu_history) > 60:
            self.gpu_history.pop(0)
            self.temp_history.pop(0)

        if hasattr(self, "gpu_curve"):
            self.gpu_curve.setData(self.gpu_history)
            self.temp_curve.setData(self.temp_history)
