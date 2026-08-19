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
        # GPU / NVML INITIALIZATION
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
                    pynvml.nvmlDeviceGetHandleByIndex(0)
                )

                self.gpu_available = True

        except pynvml.NVMLError as error:

            print(
                f"NVML initialization error: {error}"
            )

            self.gpu_available = False

        # =================================================
        # GRAPH SETTINGS
        # =================================================

        self.max_points = 60

        self.cpu_history = (
            [0] * self.max_points
        )

        self.gpu_history = (
            [0] * self.max_points
        )

        self.ram_history = (
            [0] * self.max_points
        )

        # =================================================
        # UI
        # =================================================

        self.setup_ui()

        # =================================================
        # UPDATE TIMER
        # =================================================

        self.timer = QTimer(
            self
        )

        self.timer.timeout.connect(
            self.update_data
        )

        self.timer.start(
            1000
        )

        # Initial update
        self.update_data()

    # =====================================================
    # SETUP UI
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
            14
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
            "REAL-TIME SYSTEM PERFORMANCE"
        )

        subtitle.setObjectName(
            "dashboard_subtitle"
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

        cards_layout = QHBoxLayout()

        cards_layout.setSpacing(
            12
        )

        # -------------------------------------------------
        # CPU
        # -------------------------------------------------

        self.cpu_value = QLabel(
            "0%"
        )

        cpu_card = self.create_gaming_card(
            title="CPU",
            value_label=self.cpu_value,
            description="PROCESSOR",
            accent="#ff8f00",
            icon="◈"
        )

        # -------------------------------------------------
        # GPU
        # -------------------------------------------------

        self.gpu_value = QLabel(
            "N/A"
        )

        gpu_card = self.create_gaming_card(
            title="GPU",
            value_label=self.gpu_value,
            description="GRAPHICS",
            accent="#8bc34a",
            icon="◆"
        )

        # -------------------------------------------------
        # RAM
        # -------------------------------------------------

        self.ram_value = QLabel(
            "0%"
        )

        ram_card = self.create_gaming_card(
            title="RAM",
            value_label=self.ram_value,
            description="MEMORY",
            accent="#ab47bc",
            icon="▣"
        )

        # -------------------------------------------------
        # TEMPERATURE
        # -------------------------------------------------

        self.temp_value = QLabel(
            "N/A"
        )

        temp_card = self.create_gaming_card(
            title="TEMP",
            value_label=self.temp_value,
            description="GPU TEMP",
            accent="#e53935",
            icon="◉"
        )

        cards_layout.addWidget(
            cpu_card
        )

        cards_layout.addWidget(
            gpu_card
        )

        cards_layout.addWidget(
            ram_card
        )

        cards_layout.addWidget(
            temp_card
        )

        layout.addLayout(
            cards_layout
        )

        # =================================================
        # SECONDARY GPU INFORMATION
        # =================================================

        gpu_info_frame = QFrame()

        gpu_info_frame.setObjectName(
            "gpu_info_frame"
        )

        gpu_info_layout = QHBoxLayout(
            gpu_info_frame
        )

        gpu_info_layout.setContentsMargins(
            12,
            7,
            12,
            7
        )

        gpu_info_title = QLabel(
            "GPU"
        )

        gpu_info_title.setObjectName(
            "small_label"
        )

        self.gpu_name_label = QLabel(
            "NVIDIA GPU"
        )

        self.gpu_name_label.setObjectName(
            "gpu_name"
        )

        self.vram_label = QLabel(
            "VRAM: N/A"
        )

        self.vram_label.setObjectName(
            "small_value"
        )

        self.gpu_power_label = QLabel(
            "POWER: N/A"
        )

        self.gpu_power_label.setObjectName(
            "small_value"
        )

        gpu_info_layout.addWidget(
            gpu_info_title
        )

        gpu_info_layout.addWidget(
            self.gpu_name_label
        )

        gpu_info_layout.addStretch()

        gpu_info_layout.addWidget(
            self.vram_label
        )

        gpu_info_layout.addSpacing(
            20
        )

        gpu_info_layout.addWidget(
            self.gpu_power_label
        )

        layout.addWidget(
            gpu_info_frame
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
            10,
            5,
            10,
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
            18
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
        # TELEMETRY PANEL
        # =================================================

        graph_frame = QFrame()

        graph_frame.setObjectName(
            "telemetry_frame"
        )

        graph_layout = QVBoxLayout(
            graph_frame
        )

        graph_layout.setContentsMargins(
            15,
            10,
            15,
            12
        )

        # -------------------------------------------------
        # GRAPH HEADER
        # -------------------------------------------------

        graph_header = QHBoxLayout()

        graph_title = QLabel(
            "REAL-TIME TELEMETRY"
        )

        graph_title.setObjectName(
            "graph_title"
        )

        live_label = QLabel(
            "● LIVE"
        )

        live_label.setObjectName(
            "live_label"
        )

        graph_header.addWidget(
            graph_title
        )

        graph_header.addStretch()

        graph_header.addWidget(
            live_label
        )

        graph_layout.addLayout(
            graph_header
        )

        # =================================================
        # GRAPH
        # =================================================

        self.graph = pg.PlotWidget()

        self.graph.setBackground(
            "#050505"
        )

        self.graph.showGrid(
            x=True,
            y=True,
            alpha=0.08
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
            "TIME"
        )

        # =================================================
        # AXES
        # =================================================

        self.graph.getAxis(
            "left"
        ).setTextPen(
            "#686868"
        )

        self.graph.getAxis(
            "bottom"
        ).setTextPen(
            "#686868"
        )

        self.graph.getAxis(
            "left"
        ).setPen(
            pg.mkPen(
                "#303030"
            )
        )

        self.graph.getAxis(
            "bottom"
        ).setPen(
            pg.mkPen(
                "#303030"
            )
        )

        # =================================================
        # LEGEND
        # =================================================

        self.graph.addLegend(
            offset=(12, 10)
        )

        # =================================================
        # CPU GRAPH
        # =================================================

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
        # GPU GRAPH
        # =================================================

        self.gpu_curve = pg.PlotDataItem(
            self.gpu_history,
            pen=pg.mkPen(
                "#8bc34a",
                width=2
            ),
            name="GPU"
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
                50
            )
        )

        self.graph.addItem(
            self.gpu_fill
        )

        self.graph.addItem(
            self.gpu_curve
        )

        # =================================================
        # RAM GRAPH
        # =================================================

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
                50
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
        # GRAPH SELECTOR
        # =================================================

        self.metric_selector.currentIndexChanged.connect(
            self.update_graph_visibility
        )

    # =====================================================
    # KPI CARD
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
                background-color: #090909;
                border: 1px solid #292929;
                border-top: 2px solid {accent};
                border-radius: 3px;
            }}
            """
        )

        layout = QVBoxLayout(
            card
        )

        layout.setContentsMargins(
            14,
            10,
            14,
            10
        )

        layout.setSpacing(
            3
        )

        # =================================================
        # TITLE
        # =================================================

        top_row = QHBoxLayout()

        title_label = QLabel(
            title
        )

        title_label.setStyleSheet(
            f"""
            QLabel {{
                color: {accent};
                font-size: 11px;
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
                font-size: 16px;
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
            """
            QLabel {
                color: #eeeeee;
                font-size: 27px;
                font-weight: bold;
                background: transparent;
                border: none;
            }
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
                font-size: 9px;
                font-weight: bold;
                background: transparent;
                border: none;
            }}
            """
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
        # GPU DEFAULTS
        # =================================================

        gpu_usage = 0

        gpu_temperature = None

        vram_used = None

        vram_total = None

        power_usage = None

        # =================================================
        # NVIDIA GPU
        # =================================================

        if self.gpu_available:

            # -------------------------------------------------
            # GPU UTILIZATION
            # -------------------------------------------------

            try:

                utilization = (
                    pynvml.nvmlDeviceGetUtilizationRates(
                        self.gpu_handle
                    )
                )

                gpu_usage = (
                    utilization.gpu
                )

            except pynvml.NVMLError as error:

                print(
                    f"GPU utilization error: {error}"
                )

                gpu_usage = 0

            # -------------------------------------------------
            # GPU TEMPERATURE
            # -------------------------------------------------

            try:

                gpu_temperature = (
                    pynvml.nvmlDeviceGetTemperature(
                        self.gpu_handle,
                        pynvml.NVML_TEMPERATURE_GPU
                    )
                )

            except pynvml.NVMLError as error:

                print(
                    f"GPU temperature error: {error}"
                )

                gpu_temperature = None

            # -------------------------------------------------
            # VRAM
            # -------------------------------------------------

            try:

                memory_info = (
                    pynvml.nvmlDeviceGetMemoryInfo(
                        self.gpu_handle
                    )
                )

                vram_used = (
                    memory_info.used
                )

                vram_total = (
                    memory_info.total
                )

            except pynvml.NVMLError as error:

                print(
                    f"VRAM error: {error}"
                )

                vram_used = None

                vram_total = None

            # -------------------------------------------------
            # POWER
            # -------------------------------------------------

            try:

                power_usage = (
                    pynvml.nvmlDeviceGetPowerUsage(
                        self.gpu_handle
                    )
                    / 1000
                )

            except pynvml.NVMLError:

                power_usage = None

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

        if self.gpu_available:

            self.gpu_value.setText(
                f"{gpu_usage}%"
            )

        else:

            self.gpu_value.setText(
                "N/A"
            )

        # =================================================
        # TEMPERATURE
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
        # GPU NAME
        # =================================================

        if self.gpu_available:

            try:

                gpu_name = (
                    pynvml.nvmlDeviceGetName(
                        self.gpu_handle
                    )
                )

                if isinstance(
                    gpu_name,
                    bytes
                ):

                    gpu_name = (
                        gpu_name.decode(
                            "utf-8",
                            errors="ignore"
                        )
                    )

                self.gpu_name_label.setText(
                    str(gpu_name)
                )

            except pynvml.NVMLError:

                self.gpu_name_label.setText(
                    "NVIDIA GPU"
                )

        else:

            self.gpu_name_label.setText(
                "NVIDIA GPU NOT DETECTED"
            )

        # =================================================
        # VRAM LABEL
        # =================================================

        if (
            vram_used is not None
            and
            vram_total is not None
        ):

            used_gb = (
                vram_used
                / (1024 ** 3)
            )

            total_gb = (
                vram_total
                / (1024 ** 3)
            )

            vram_percent = (
                vram_used
                / vram_total
                * 100
                if vram_total > 0
                else 0
            )

            self.vram_label.setText(
                f"VRAM: "
                f"{used_gb:.1f}/"
                f"{total_gb:.1f} GB "
                f"({vram_percent:.0f}%)"
            )

        else:

            self.vram_label.setText(
                "VRAM: N/A"
            )

        # =================================================
        # POWER LABEL
        # =================================================

        if power_usage is not None:

            self.gpu_power_label.setText(
                f"POWER: {power_usage:.1f} W"
            )

        else:

            self.gpu_power_label.setText(
                "POWER: N/A"
            )

        # =================================================
        # UPDATE HISTORY
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

        # Keep last 60 points
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
        # UPDATE FILLED AREAS
        # =================================================

        self.cpu_bottom.setData(
            [0] * len(
                self.cpu_history
            )
        )

        self.gpu_bottom.setData(
            [0] * len(
                self.gpu_history
            )
        )

        self.ram_bottom.setData(
            [0] * len(
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

        # -------------------------------------------------
        # CPU + GPU + RAM
        # -------------------------------------------------

        if index == 0:

            self.cpu_curve.show()
            self.cpu_fill.show()

            self.gpu_curve.show()
            self.gpu_fill.show()

            self.ram_curve.show()
            self.ram_fill.show()

        # -------------------------------------------------
        # CPU + RAM
        # -------------------------------------------------

        elif index == 1:

            self.cpu_curve.show()
            self.cpu_fill.show()

            self.gpu_curve.hide()
            self.gpu_fill.hide()

            self.ram_curve.show()
            self.ram_fill.show()

        # -------------------------------------------------
        # CPU
        # -------------------------------------------------

        elif index == 2:

            self.cpu_curve.show()
            self.cpu_fill.show()

            self.gpu_curve.hide()
            self.gpu_fill.hide()

            self.ram_curve.hide()
            self.ram_fill.hide()

        # -------------------------------------------------
        # GPU
        # -------------------------------------------------

        elif index == 3:

            self.cpu_curve.hide()
            self.cpu_fill.hide()

            self.gpu_curve.show()
            self.gpu_fill.show()

            self.ram_curve.hide()
            self.ram_fill.hide()

        # -------------------------------------------------
        # RAM
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Shutdown NVML
        # -------------------------------------------------

        if self.gpu_available:

            try:

                pynvml.nvmlShutdown()

            except pynvml.NVMLError:

                pass

        event.accept()