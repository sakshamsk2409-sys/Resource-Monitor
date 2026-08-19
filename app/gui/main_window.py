"""
MVP main window.

Shows live tiles (CPU / RAM / GPU / Disk / Network) plus a rolling
multi-series graph, matching the "Resource Monitor" tab from the
project spec. This is intentionally a single-tab MVP - the full
System Configuration / Memory / GPU Performance tabs come later.

IMPORTANT: this file only talks to TelemetryService. It never imports
psutil or pynvml directly.
"""

import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from app.core.constants import APP_NAME, HISTORY_LENGTH, POLL_INTERVAL_MS
from app.services.telemetry_service import TelemetryService


class Tile(QWidget):
    """A single stat tile, e.g. 'CPU  42%'."""

    def __init__(self, label: str):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        self.title_label = QLabel(label)
        self.title_label.setStyleSheet("color: #9aa0a6; font-size: 12px;")

        self.value_label = QLabel("--")
        self.value_label.setStyleSheet("color: #e8eaed; font-size: 24px; font-weight: 600;")

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        self.setStyleSheet("background-color: #202124; border-radius: 8px;")

    def set_value(self, text: str):
        self.value_label.setText(text)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(900, 600)
        self.setStyleSheet("background-color: #121212;")

        self.telemetry_service = TelemetryService()

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)

        # --- Tiles ---
        tiles_layout = QGridLayout()
        self.cpu_tile = Tile("CPU")
        self.ram_tile = Tile("RAM")
        self.gpu_tile = Tile("GPU")
        self.vram_tile = Tile("VRAM")
        self.disk_tile = Tile("DISK (R/W MB/s)")
        self.net_tile = Tile("NETWORK (\u2191/\u2193 MB/s)")
        self.temp_tile = Tile("CPU TEMP")

        tiles = [
            self.cpu_tile, self.ram_tile, self.gpu_tile,
            self.vram_tile, self.disk_tile, self.net_tile, self.temp_tile,
        ]
        for i, tile in enumerate(tiles):
            tiles_layout.addWidget(tile, i // 4, i % 4)

        root_layout.addLayout(tiles_layout)

        # --- Graph ---
        pg.setConfigOption("background", "#121212")
        pg.setConfigOption("foreground", "#9aa0a6")
        self.plot_widget = pg.PlotWidget(title="Live Usage (%)")
        self.plot_widget.setYRange(0, 100)
        self.plot_widget.addLegend()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)

        self.x_data = list(range(HISTORY_LENGTH))
        self.cpu_data = [0.0] * HISTORY_LENGTH
        self.ram_data = [0.0] * HISTORY_LENGTH
        self.gpu_data = [0.0] * HISTORY_LENGTH

        self.cpu_curve = self.plot_widget.plot(
            self.x_data, self.cpu_data, pen=pg.mkPen("#4fc3f7", width=2), name="CPU"
        )
        self.ram_curve = self.plot_widget.plot(
            self.x_data, self.ram_data, pen=pg.mkPen("#81c784", width=2), name="RAM"
        )
        self.gpu_curve = self.plot_widget.plot(
            self.x_data, self.gpu_data, pen=pg.mkPen("#ffb74d", width=2), name="GPU"
        )

        root_layout.addWidget(self.plot_widget, stretch=1)

        if not self.telemetry_service.gpu_available:
            self.gpu_tile.set_value("N/A")
            self.vram_tile.set_value("N/A")

        # --- Poll loop ---
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(POLL_INTERVAL_MS)
        self.refresh()

    def refresh(self):
        sample = self.telemetry_service.get_current_metrics()

        self.cpu_tile.set_value(f"{sample.cpu_usage:.0f}%")
        self.ram_tile.set_value(f"{sample.ram_usage:.0f}%")
        self.disk_tile.set_value(f"{sample.disk_read_mb_s:.1f} / {sample.disk_write_mb_s:.1f}")
        self.net_tile.set_value(
            f"{sample.network_upload_mb_s:.1f} / {sample.network_download_mb_s:.1f}"
        )
        self.temp_tile.set_value(
            f"{sample.cpu_temperature:.0f}\u00b0C" if sample.cpu_temperature is not None else "N/A"
        )

        if sample.gpu_usage is not None:
            self.gpu_tile.set_value(f"{sample.gpu_usage:.0f}%")
        if sample.vram_usage is not None:
            self.vram_tile.set_value(f"{sample.vram_usage:.0f}%")

        self._push(self.cpu_data, sample.cpu_usage)
        self._push(self.ram_data, sample.ram_usage)
        self._push(self.gpu_data, sample.gpu_usage or 0.0)

        self.cpu_curve.setData(self.x_data, self.cpu_data)
        self.ram_curve.setData(self.x_data, self.ram_data)
        self.gpu_curve.setData(self.x_data, self.gpu_data)

    @staticmethod
    def _push(data_list: list, value: float):
        data_list.pop(0)
        data_list.append(value)

    def closeEvent(self, event):
        self.timer.stop()
        self.telemetry_service.shutdown()
        super().closeEvent(event)
