import psutil
import pyqtgraph as pg
import pynvml

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QComboBox,
)


class DashboardPage(QWidget):

    def __init__(self):

        super().__init__()

        # =================================================
        # GPU INITIALIZATION
        # =================================================

        self.gpu_available = False
        self.gpu_handle = None

        try:

            pynvml.nvmlInit()

            gpu_count = (
                pynvml.nvmlDeviceGetCount()
            )

            if gpu_count > 0:

                self.gpu_handle = (
                    pynvml.nvmlDeviceGetHandleByIndex(
                        0
                    )
                )

                self.gpu_available = True

        except pynvml.NVMLError:

            self.gpu_available = False

        # =================================================
        # GRAPH HISTORY
        # =================================================

        self.max_points = 60

        self.cpu_history = [
            0
        ] * self.max_points

        self.ram_history = [
            0
        ] * self.max_points

        # =================================================
        # CREATE GUI
        # =================================================

        self.setup_ui()

        # =================================================
        # MONITORING TIMER
        # =================================================

        self.timer = QTimer(
            self
        )

        self.timer.timeout.connect(
            self.update_data
        )

        # Update every 1 second
        self.timer.start(
            1000
        )

        # Initial update
        self.update_data()

    # =====================================================
    # UI
    # =====================================================

    def setup_ui(self):

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            30,
            25,
            30,
            25
        )

        layout.setSpacing(
            18
        )

        # =================================================
        # HEADER
        # =================================================

        title = QLabel(
            "Dashboard"
        )

        title.setObjectName(
            "page_title"
        )

        subtitle = QLabel(
            "Real-time system performance overview"
        )

        subtitle.setObjectName(
            "subtitle"
        )

        layout.addWidget(
            title
        )

        layout.addWidget(
            subtitle
        )

        # =================================================
        # KPI CARDS
        # =================================================

        cards = QHBoxLayout()

        cards.setSpacing(
            15
        )

        # Values
        self.cpu_value = QLabel(
            "0%"
        )

        self.gpu_value = QLabel(
            "N/A"
        )

        self.ram_value = QLabel(
            "0%"
        )

        self.temp_value = QLabel(
            "N/A"
        )

        # CPU
        cards.addWidget(
            self.create_card(
                "CPU",
                self.cpu_value,
                "Utilization"
            )
        )

        # GPU
        cards.addWidget(
            self.create_card(
                "GPU",
                self.gpu_value,
                "Utilization"
            )
        )

        # RAM
        cards.addWidget(
            self.create_card(
                "RAM",
                self.ram_value,
                "Memory"
            )
        )

        # Temperature
        cards.addWidget(
            self.create_card(
                "TEMPERATURE",
                self.temp_value,
                "GPU"
            )
        )

        layout.addLayout(
            cards
        )

        # =================================================
        # CONTROLS
        # =================================================

        controls = QHBoxLayout()

        metric_label = QLabel(
            "Metrics:"
        )

        self.metric_selector = QComboBox()

        self.metric_selector.addItems(
            [
                "CPU + RAM",
                "CPU",
                "RAM",
            ]
        )

        time_label = QLabel(
            "Time:"
        )

        self.time_selector = QComboBox()

        self.time_selector.addItems(
            [
                "1 Minute",
                "5 Minutes",
                "15 Minutes",
            ]
        )

        controls.addWidget(
            metric_label
        )

        controls.addWidget(
            self.metric_selector
        )

        controls.addSpacing(
            20
        )

        controls.addWidget(
            time_label
        )

        controls.addWidget(
            self.time_selector
        )

        controls.addStretch()

        layout.addLayout(
            controls
        )

        # =================================================
        # REAL-TIME GRAPH
        # =================================================

        graph_frame = QFrame()

        graph_frame.setObjectName(
            "graph_container"
        )

        graph_layout = QVBoxLayout(
            graph_frame
        )

        graph_layout.setContentsMargins(
            20,
            15,
            20,
            20
        )

        graph_title = QLabel(
            "REAL-TIME TELEMETRY"
        )

        graph_title.setObjectName(
            "section_title"
        )

        graph_layout.addWidget(
            graph_title
        )

        # PyQtGraph
        self.graph = pg.PlotWidget()

        self.graph.setBackground(
            "#161d26"
        )

        self.graph.showGrid(
            x=True,
            y=True,
            alpha=0.15
        )

        self.graph.setYRange(
            0,
            100
        )

        self.graph.setLabel(
            "left",
            "Usage (%)"
        )

        self.graph.setLabel(
            "bottom",
            "Time"
        )

        self.graph.addLegend()

        # CPU curve
        self.cpu_curve = (
            self.graph.plot(
                self.cpu_history,
                pen=pg.mkPen(
                    width=2
                ),
                name="CPU"
            )
        )

        # RAM curve
        self.ram_curve = (
            self.graph.plot(
                self.ram_history,
                pen=pg.mkPen(
                    width=2
                ),
                name="RAM"
            )
        )

        graph_layout.addWidget(
            self.graph
        )

        layout.addWidget(
            graph_frame,
            1
        )

        # =================================================
        # METRIC SELECTOR EVENT
        # =================================================

        self.metric_selector.currentIndexChanged.connect(
            self.update_graph_visibility
        )

    # =====================================================
    # KPI CARD
    # =====================================================

    def create_card(
        self,
        title,
        value_label,
        description
    ):

        card = QFrame()

        card.setObjectName(
            "metric_card"
        )

        layout = QVBoxLayout(
            card
        )

        layout.setContentsMargins(
            18,
            15,
            18,
            15
        )

        title_label = QLabel(
            title
        )

        title_label.setObjectName(
            "card_title"
        )

        value_label.setObjectName(
            "card_value"
        )

        description_label = QLabel(
            description
        )

        description_label.setObjectName(
            "card_description"
        )

        layout.addWidget(
            title_label
        )

        layout.addWidget(
            value_label
        )

        layout.addWidget(
            description_label
        )

        return card

    # =====================================================
    # UPDATE DATA
    # =====================================================

    def update_data(self):

        # =================================================
        # CPU
        # =================================================

        cpu = psutil.cpu_percent(
            interval=None
        )

        # =================================================
        # RAM
        # =================================================

        memory = psutil.virtual_memory()

        ram = memory.percent

        # =================================================
        # GPU
        # =================================================

        gpu_usage = None
        gpu_temperature = None

        if self.gpu_available:

            try:

                utilization = (
                    pynvml.nvmlDeviceGetUtilizationRates(
                        self.gpu_handle
                    )
                )

                gpu_usage = (
                    utilization.gpu
                )

                gpu_temperature = (
                    pynvml.nvmlDeviceGetTemperature(
                        self.gpu_handle,
                        pynvml.NVML_TEMPERATURE_GPU
                    )
                )

            except pynvml.NVMLError:

                gpu_usage = None
                gpu_temperature = None

        # =================================================
        # CPU CARD
        # =================================================

        self.cpu_value.setText(
            f"{cpu:.1f}%"
        )

        # =================================================
        # RAM CARD
        # =================================================

        self.ram_value.setText(
            f"{ram:.1f}%"
        )

        # =================================================
        # GPU CARD
        # =================================================

        if gpu_usage is not None:

            self.gpu_value.setText(
                f"{gpu_usage}%"
            )

        else:

            self.gpu_value.setText(
                "N/A"
            )

        # =================================================
        # TEMPERATURE CARD
        # =================================================

        if gpu_temperature is not None:

            self.temp_value.setText(
                f"{gpu_temperature}°C"
            )

        else:

            self.temp_value.setText(
                "N/A"
            )

        # =================================================
        # HISTORY
        # =================================================

        self.cpu_history.append(
            cpu
        )

        self.ram_history.append(
            ram
        )

        self.cpu_history = (
            self.cpu_history[
                -self.max_points:
            ]
        )

        self.ram_history = (
            self.ram_history[
                -self.max_points:
            ]
        )

        # =================================================
        # UPDATE GRAPH
        # =================================================

        self.cpu_curve.setData(
            self.cpu_history
        )

        self.ram_curve.setData(
            self.ram_history
        )

    # =====================================================
    # GRAPH VISIBILITY
    # =====================================================

    def update_graph_visibility(
        self,
        index
    ):

        if index == 0:

            self.cpu_curve.show()

            self.ram_curve.show()

        elif index == 1:

            self.cpu_curve.show()

            self.ram_curve.hide()

        elif index == 2:

            self.cpu_curve.hide()

            self.ram_curve.show()

    # =====================================================
    # CLEANUP
    # =====================================================

    def closeEvent(
        self,
        event
    ):

        self.timer.stop()

        event.accept()