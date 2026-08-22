import time
import psutil

from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QColor, QFont, QPainter, QBrush, QPen
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)

try:
    import pynvml
    HAS_PYNVML = True
except ImportError:
    pynvml = None
    HAS_PYNVML = False


class MiniOverlayWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(230, 120)

        self.drag_position = QPoint()
        self.gpu_handle = None
        self.init_gpu()

        self.last_time = time.time()
        self.last_net = psutil.net_io_counters()

        self.setup_ui()

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_telemetry)
        self.timer.start()

    def init_gpu(self):
        if HAS_PYNVML and pynvml:
            try:
                pynvml.nvmlInit()
                if pynvml.nvmlDeviceGetCount() > 0:
                    self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            except Exception:
                pass

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.container = QFrame()
        self.container.setStyleSheet("""
            QFrame {
                background-color: rgba(10, 10, 10, 220);
                border: 1px solid #ff8f00;
                border-radius: 8px;
            }
        """)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(12, 8, 12, 8)
        container_layout.setSpacing(4)

        # Title bar & close button
        title_box = QHBoxLayout()
        title_lbl = QLabel("📊 SYSTEM HUD")
        title_lbl.setStyleSheet("color: #ff8f00; font-size: 10px; font-weight: bold; letter-spacing: 1px;")

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(16, 16)
        close_btn.setStyleSheet("""
            QPushButton {
                color: #888888; border: none; background: transparent; font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { color: #e53935; }
        """)
        close_btn.clicked.connect(self.hide)

        title_box.addWidget(title_lbl)
        title_box.addStretch()
        title_box.addWidget(close_btn)
        container_layout.addLayout(title_box)

        # Telemetry Labels
        self.cpu_lbl = QLabel("CPU: 0%")
        self.cpu_lbl.setStyleSheet("color: #ffffff; font-size: 11px; font-weight: bold;")

        self.ram_lbl = QLabel("RAM: 0%")
        self.ram_lbl.setStyleSheet("color: #ab47bc; font-size: 11px; font-weight: bold;")

        self.gpu_lbl = QLabel("GPU Temp: N/A")
        self.gpu_lbl.setStyleSheet("color: #26a69a; font-size: 11px; font-weight: bold;")

        self.net_lbl = QLabel("NET: 0.0 KB/s")
        self.net_lbl.setStyleSheet("color: #8bc34a; font-size: 11px; font-weight: bold;")

        grid = QHBoxLayout()
        v1 = QVBoxLayout()
        v1.addWidget(self.cpu_lbl)
        v1.addWidget(self.gpu_lbl)

        v2 = QVBoxLayout()
        v2.addWidget(self.ram_lbl)
        v2.addWidget(self.net_lbl)

        grid.addLayout(v1)
        grid.addLayout(v2)
        container_layout.addLayout(grid)

        layout.addWidget(self.container)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def update_telemetry(self):
        # CPU
        cpu = psutil.cpu_percent(interval=None)
        cpu_color = "#e53935" if cpu > 85 else "#ffffff"
        self.cpu_lbl.setText(f"CPU: {cpu:.0f}%")
        self.cpu_lbl.setStyleSheet(f"color: {cpu_color}; font-size: 11px; font-weight: bold;")

        # RAM
        ram = psutil.virtual_memory().percent
        ram_color = "#e53935" if ram > 90 else "#ab47bc"
        self.ram_lbl.setText(f"RAM: {ram:.0f}%")
        self.ram_lbl.setStyleSheet(f"color: {ram_color}; font-size: 11px; font-weight: bold;")

        # GPU Temp
        gpu_temp_str = "N/A"
        if self.gpu_handle and HAS_PYNVML and pynvml:
            try:
                temp = pynvml.nvmlDeviceGetTemperature(self.gpu_handle, pynvml.NVML_TEMPERATURE_GPU)
                gpu_temp_str = f"{temp}°C"
            except Exception:
                pass
        self.gpu_lbl.setText(f"GPU: {gpu_temp_str}")

        # NET
        now = time.time()
        dt = now - self.last_time
        if dt > 0:
            self.last_time = now
            curr_net = psutil.net_io_counters()
            tot_bytes_sec = (curr_net.bytes_sent + curr_net.bytes_recv - self.last_net.bytes_sent - self.last_net.bytes_recv) / dt
            self.last_net = curr_net
            kb_sec = tot_bytes_sec / 1024.0
            if kb_sec >= 1024:
                self.net_lbl.setText(f"NET: {kb_sec/1024.0:.1f} MB/s")
            else:
                self.net_lbl.setText(f"NET: {kb_sec:.0f} KB/s")
