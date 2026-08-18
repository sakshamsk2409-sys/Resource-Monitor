import psutil
import pyqtgraph as pg
import pynvml

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont
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

            gpu_count = pynvml.nvmlDeviceGetCount()

            if gpu_count > 0:

                self.gpu_handle = (
                    pynvml.nvmlDeviceGetHandleByIndex(0)
                )

                self.gpu_available = True

        except pynvml.NVMLError:

            self.gpu_available = False

        # =================================================
        # GRAPH DATA
        # =================================================

        self.max_points = 60

        self.cpu_history = [0] * self.max_points
        self.gpu_history = [0] * self.max_points
        self.ram_history = [0] * self.max_points

        # =================================================
        # BUILD UI
        # =================================================

        self.setup_ui()

        # =================================================
        # TIMER
        # =================================================

        self.timer = QTimer(self)

        self.timer.timeout.connect(
            self.update_data
        )

        self.timer.start(1000)

        self.update_data()

    # =====================================================
    # MAIN UI
    # =====================================================

    def setup_ui(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            30,
            25,
            30,
            25
        )

        layout.setSpacing(16)

        # =================================================
        # HEADER
        # =================================================

        title = QLabel("Dashboard")

        title.setObjectName(
            "page_title"
        )

        subtitle = QLabel(
            "REAL-TIME SYSTEM PERFORMANCE"
        )

        subtitle.setObjectName(
            "dashboard_subtitle"
        )

        layout.addWidget(title)
        layout.addWidget(subtitle)

        # =================================================
        # KPI CARDS
        # =================================================

        cards_layout = QHBoxLayout()

        cards_layout.setSpacing(14)

        # CPU
        self.cpu_value = QLabel("0%")

        cpu_card = self.create_gaming_card(
            title="CPU",
            value_label=self.cpu_value,
            description="PROCESSOR",
            accent="#00aaff",
            icon="◈"
        )

        # GPU
        self.gpu_value = QLabel("N/A")

        gpu_card = self.create_gaming_card(
            title="GPU",
            value_label=self.gpu_value,
            description="GRAPHICS",
            accent="#39ff88",
            icon="◆"
        )

        # RAM
        self.ram_value = QLabel("0%")

        ram_card = self.create_gaming_card(
            title="RAM",
            value_label=self.ram_value,
            description="MEMORY",
            accent="#b35cff",
            icon="▣"
        )

        # Temperature
        self.temp_value = QLabel("N/A")

        temp_card = self.create_gaming_card(
            title="TEMP",
            value_label=self.temp_value,
            description="GPU TEMP",
            accent="#ff6b2c",
            icon="◉"
        )

        cards_layout.addWidget(cpu_card)
        cards_layout.addWidget(gpu_card)
        cards_layout.addWidget(ram_card)
        cards_layout.addWidget(temp_card)

        layout.addLayout(
            cards_layout
        )

        # =================================================
        # CONTROLS
        # =================================================

        controls_frame = QFrame()

        controls_frame.setObjectName(
            "controls_frame"
        )

        controls_layout = QHBoxLayout(
            controls_frame
        )

        controls_layout.setContentsMargins(
            12,
            5,
            12,
            5
        )

        metric_label = QLabel(
            "METRICS"
        )

        metric_label.setObjectName(
            "control_label"
        )

        self.metric_selector = QComboBox()

        self.metric_selector.addItems(
            [
                "CPU + GPU + RAM",
                "CPU + RAM",
                "CPU",
                "GPU",
                "RAM",
            ]
        )

        time_label = QLabel(
            "WINDOW"
        )

        time_label.setObjectName(
            "control_label"
        )

        self.time_selector = QComboBox()

        self.time_selector.addItems(
            [
                "1 Minute",
                "5 Minutes",
                "15 Minutes",
            ]
        )

        controls_layout.addWidget(
            metric_label
        )

        controls_layout.addWidget(
            self.metric_selector
        )

        controls_layout.addSpacing(
            20
        )

        controls_layout.addWidget(
            time_label
        )

        controls_layout.addWidget(
            self.time_selector
        )

        controls_layout.addStretch()

        layout.addWidget(
            controls_frame
        )

        # =================================================
        # GRAPH CONTAINER
        # =================================================

        graph_frame = QFrame()

        graph_frame.setObjectName(
            "telemetry_frame"
        )

        graph_layout = QVBoxLayout(
            graph_frame
        )

        graph_layout.setContentsMargins(
            18,
            12,
            18,
            15
        )

        # Graph heading
        graph_header = QHBoxLayout()

        graph_title = QLabel(
            "REAL-TIME TELEMETRY"
        )

        graph_title.setObjectName(
            "graph_title"
        )

        graph_status = QLabel(
            "● LIVE"
        )

        graph_status.setObjectName(
            "live_label"
        )

        graph_header.addWidget(
            graph_title
        )

        graph_header.addStretch()

        graph_header.addWidget(
            graph_status
        )

        graph_layout.addLayout(
            graph_header
        )

        # =================================================
        # PYQTGRAPH
        # =================================================

        self.graph = pg.PlotWidget()

        self.graph.setBackground(
            "#0b111b"
        )

        self.graph.showGrid(
            x=True,
            y=True,
            alpha=0.12
        )

        self.graph.setYRange(
            0,
            100
        )

        self.graph.setLabel(
            "left",
            "USAGE (%)"
        )

        self.graph.setLabel(
            "bottom",
            "TIME (SECONDS)"
        )

        self.graph.getAxis(
            "left"
        ).setTextPen(
            "#7f8fa6"
        )

        self.graph.getAxis(
            "bottom"
        ).setTextPen(
            "#7f8fa6"
        )

        self.graph.getAxis(
            "left"
        ).setPen(
            pg.mkPen(
                "#263445"
            )
        )

        self.graph.getAxis(
            "bottom"
        ).setPen(
            pg.mkPen(
                "#263445"
            )
        )

        # =================================================
        # GRAPH LEGEND
        # =================================================

        self.graph.addLegend(
            offset=(15, 10)
        )

        # =================================================
        # CPU AREA
        # =================================================

        self.cpu_curve = pg.PlotDataItem(
            self.cpu_history,
            pen=pg.mkPen(
                "#00aaff",
                width=2
            ),
            name="CPU"
        )

        self.cpu_fill = pg.FillBetweenItem(
            self.cpu_curve,
            pg.PlotDataItem(
                [0] * self.max_points
            ),
            brush=pg.mkBrush(
                0,
                170,
                255,
                55
            )
        )

        self.graph.addItem(
            self.cpu_fill
        )

        self.graph.addItem(
            self.cpu_curve
        )

        # =================================================
        # GPU AREA
        # =================================================

        self.gpu_curve = pg.PlotDataItem(
            self.gpu_history,
            pen=pg.mkPen(
                "#39ff88",
                width=2
            ),
            name="GPU"
        )

        self.gpu_fill = pg.FillBetweenItem(
            self.gpu_curve,
            pg.PlotDataItem(
                [0] * self.max_points
            ),
            brush=pg.mkBrush(
                57,
                255,
                136,
                45
            )
        )

        self.graph.addItem(
            self.gpu_fill
        )

        self.graph.addItem(
            self.gpu_curve
        )

        # =================================================
        # RAM AREA
        # =================================================

        self.ram_curve = pg.PlotDataItem(
            self.ram_history,
            pen=pg.mkPen(
                "#b35cff",
                width=2
            ),
            name="RAM"
        )

        self.ram_fill = pg.FillBetweenItem(
            self.ram_curve,
            pg.PlotDataItem(
                [0] * self.max_points
            ),
            brush=pg.mkBrush(
                179,
                92,
                255,
                45
            )
        )

        self.graph.addItem(
            self.ram_fill
        )

        self.graph.addItem(
            self.ram_curve
        )

        graph_layout.addWidget(
            self.graph
        )

        layout.addWidget(
            graph_frame,
            1
        )

        # =================================================
        # METRIC SELECTOR
        # =================================================

        self.metric_selector.currentIndexChanged.connect(
            self.update_graph_visibility
        )

    # =====================================================
    # GAMING KPI CARD
    # =====================================================

    def create_gaming_card(
        self,
        title,
        value_label,
        description,
        accent,
        icon
    ):

        card = QFrame()

        card.setObjectName(
            "gaming_card"
        )

        card.setStyleSheet(
            f"""
            QFrame#gaming_card {{
                background-color: #101722;
                border: 1px solid {accent};
                border-radius: 14px;
            }}
            """
        )

        layout = QVBoxLayout(
            card
        )

        layout.setContentsMargins(
            16,
            12,
            16,
            12
        )

        layout.setSpacing(
            4
        )

        # =================================================
        # TOP ROW
        # =================================================

        top_row = QHBoxLayout()

        title_label = QLabel(
            title
        )

        title_label.setStyleSheet(
            f"""
            QLabel {{
                color: {accent};
                font-size: 13px;
                font-weight: bold;
                background: transparent;
                border: none;
            }}
            """
        )

        icon_label = QLabel(
            icon
        )

        icon_label.setStyleSheet(
            f"""
            QLabel {{
                color: {accent};
                font-size: 20px;
                font-weight: bold;
                background: transparent;
                border: none;
            }}
            """
        )

        top_row.addWidget(
            title_label
        )

        top_row.addStretch()

        top_row.addWidget(
            icon_label
        )

        layout.addLayout(
            top_row
        )

        # =================================================
        # VALUE
        # =================================================

        value_label.setStyleSheet(
            f"""
            QLabel {{
                color: #ffffff;
                font-size: 30px;
                font-weight: bold;
                background: transparent;
                border: none;
            }}
            """
        )

        layout.addWidget(
            value_label
        )

        # =================================================
        # DESCRIPTION
        # =================================================

        description_label = QLabel(
            description
        )

        description_label.setStyleSheet(
            f"""
            QLabel {{
                color: {accent};
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 1px;
                background: transparent;
                border: none;
            }}
            """
        )

        layout.addWidget(
            description_label
        )

        # =================================================
        # MINI BAR
        # =================================================

        mini_bar = QFrame()

        mini_bar.setFixedHeight(
            4
        )

        mini_bar.setStyleSheet(
            f"""
            QFrame {{
                background-color: #1a2635;
                border-radius: 2px;
                border: none;
            }}
            """
        )

        layout.addWidget(
            mini_bar
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

        gpu_usage = 0
        gpu_temperature = None

        if self.gpu_available:

            try:

                utilization = (
                    pynvml.nvmlDeviceGetUtilizationRates(
                        self.gpu_handle
                    )
                )

                gpu_usage = utilization.gpu

                gpu_temperature = (
                    pynvml.nvmlDeviceGetTemperature(
                        self.gpu_handle,
                        pynvml.NVML_TEMPERATURE_GPU
                    )
                )

            except pynvml.NVMLError:

                gpu_usage = 0
                gpu_temperature = None

        # =================================================
        # UPDATE KPI VALUES
        # =================================================

        self.cpu_value.setText(
            f"{cpu:.1f}%"
        )

        self.ram_value.setText(
            f"{ram:.1f}%"
        )

        if self.gpu_available:

            self.gpu_value.setText(
                f"{gpu_usage}%"
            )

        else:

            self.gpu_value.setText(
                "N/A"
            )

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

        self.gpu_history.append(
            gpu_usage
        )

        self.ram_history.append(
            ram
        )

        self.cpu_history = (
            self.cpu_history[
                -self.max_points:
            ]
        )

        self.gpu_history = (
            self.gpu_history[
                -self.max_points:
            ]
        )

        self.ram_history = (
            self.ram_history[
                -self.max_points:
            ]
        )

        # =================================================
        # UPDATE CURVES
        # =================================================

        self.cpu_curve.setData(
            self.cpu_history
        )

        self.gpu_curve.setData(
            self.gpu_history
        )

        self.ram_curve.setData(
            self.ram_history
        )

        # =================================================
        # UPDATE FILLS
        # =================================================

        self.cpu_fill.setCurves(
            self.cpu_curve,
            pg.PlotDataItem(
                self.cpu_history
            )
        )

        self.gpu_fill.setCurves(
            self.gpu_curve,
            pg.PlotDataItem(
                self.gpu_history
            )
        )

        self.ram_fill.setCurves(
            self.ram_curve,
            pg.PlotDataItem(
                self.ram_history
            )

        )

    # =====================================================
    # GRAPH VISIBILITY
    # =====================================================

    def update_graph_visibility(
        self,
        index
    ):

        # CPU + GPU + RAM
        if index == 0:

            self.cpu_curve.show()
            self.cpu_fill.show()

            self.gpu_curve.show()
            self.gpu_fill.show()

            self.ram_curve.show()
            self.ram_fill.show()

        # CPU + RAM
        elif index == 1:

            self.cpu_curve.show()
            self.cpu_fill.show()

            self.gpu_curve.hide()
            self.gpu_fill.hide()

            self.ram_curve.show()
            self.ram_fill.show()

        # CPU
        elif index == 2:

            self.cpu_curve.show()
            self.cpu_fill.show()

            self.gpu_curve.hide()
            self.gpu_fill.hide()

            self.ram_curve.hide()
            self.ram_fill.hide()

        # GPU
        elif index == 3:

            self.cpu_curve.hide()
            self.cpu_fill.hide()

            self.gpu_curve.show()
            self.gpu_fill.show()

            self.ram_curve.hide()
            self.ram_fill.hide()

        # RAM
        elif index == 4:

            self.cpu_curve.hide()
            self.cpu_fill.hide()

            self.gpu_curve.hide()
            self.gpu_fill.hide()

            self.ram_curve.show()
            self.ram_fill.show()

    # =====================================================
    # CLEANUP
    # =====================================================

    def closeEvent(
        self,
        event
    ):

        self.timer.stop()

        event.accept()