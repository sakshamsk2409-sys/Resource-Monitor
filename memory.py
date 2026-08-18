import psutil

import pyqtgraph as pg

from PySide6.QtCore import (
    QTimer,
    Qt,
    QRectF,
)

from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QFont,
)

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
)


# =========================================================
# APPLICATION COLORS
# =========================================================

APP_COLORS = [
    "#00aaff",
    "#b35cff",
    "#39ff88",
    "#ff6b2c",
    "#ffd23f",
    "#ff4f81",
    "#00d9ff",
    "#8b5cf6",
    "#14b8a6",
    "#f97316",
]


# =========================================================
# DONUT CHART WIDGET
# =========================================================

class MemoryDonut(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.data = []

        self.setMinimumHeight(330)

        self.setMinimumWidth(420)

        self.setAttribute(
            Qt.WA_TranslucentBackground
        )

    # =====================================================
    # SET DATA
    # =====================================================

    def set_data(self, data):

        self.data = data

        self.update()

    # =====================================================
    # PAINT
    # =====================================================

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.Antialiasing
        )

        width = self.width()
        height = self.height()

        center_x = width / 2
        center_y = height / 2

        # -------------------------------------------------
        # CHART SIZE
        # -------------------------------------------------

        diameter = min(
            width,
            height
        ) * 0.58

        rect = QRectF(
            center_x - diameter / 2,
            center_y - diameter / 2,
            diameter,
            diameter
        )

        # -------------------------------------------------
        # BACKGROUND RING
        # -------------------------------------------------

        background_pen = QPen(
            QColor("#1b2a3a")
        )

        background_pen.setWidth(
            28
        )

        background_pen.setCapStyle(
            Qt.RoundCap
        )

        painter.setPen(
            background_pen
        )

        painter.drawArc(
            rect,
            90 * 16,
            -360 * 16
        )

        # -------------------------------------------------
        # DRAW DATA
        # -------------------------------------------------

        total = sum(
            item["value"]
            for item in self.data
        )

        if total <= 0:

            painter.end()

            return

        start_angle = 90 * 16

        for index, item in enumerate(
            self.data
        ):

            value = item["value"]

            if value <= 0:
                continue

            percentage = (
                value / total
            )

            span_angle = (
                -360
                * percentage
                * 16
            )

            color = QColor(
                item["color"]
            )

            pen = QPen(
                color
            )

            pen.setWidth(
                28
            )

            pen.setCapStyle(
                Qt.RoundCap
            )

            painter.setPen(
                pen
            )

            painter.drawArc(
                rect,
                int(start_angle),
                int(span_angle)
            )

            start_angle += span_angle

        # -------------------------------------------------
        # CENTER CIRCLE
        # -------------------------------------------------

        inner_diameter = (
            diameter - 56
        )

        inner_rect = QRectF(
            center_x - inner_diameter / 2,
            center_y - inner_diameter / 2,
            inner_diameter,
            inner_diameter
        )

        painter.setPen(
            Qt.NoPen
        )

        painter.setBrush(
            QBrush(
                QColor("#0b111a")
            )
        )

        painter.drawEllipse(
            inner_rect
        )

        # -------------------------------------------------
        # CENTER TEXT
        # -------------------------------------------------

        used_total = sum(
            item["value"]
            for item in self.data
        )

        used_gb = (
            used_total
            / (1024 ** 3)
        )

        painter.setPen(
            QColor("#ffffff")
        )

        painter.setFont(
            QFont(
                "Segoe UI",
                20,
                QFont.Bold
            )
        )

        total_text = (
            f"{used_gb:.1f} GB"
        )

        total_rect = QRectF(
            center_x - 100,
            center_y - 20,
            200,
            40
        )

        painter.drawText(
            total_rect,
            Qt.AlignCenter,
            total_text
        )

        painter.setPen(
            QColor("#71839a")
        )

        painter.setFont(
            QFont(
                "Segoe UI",
                9
            )
        )

        label_rect = QRectF(
            center_x - 100,
            center_y + 15,
            200,
            25
        )

        painter.drawText(
            label_rect,
            Qt.AlignCenter,
            "PROCESS MEMORY"
        )

        painter.end()


# =========================================================
# MEMORY PAGE
# =========================================================

class MemoryPage(QWidget):

    def __init__(self):

        super().__init__()

        # =================================================
        # GRAPH HISTORY
        # =================================================

        self.max_points = 60

        self.ram_history = (
            [0] * self.max_points
        )

        # =================================================
        # APPLICATION MEMORY
        # =================================================

        self.application_data = []

        # Number of individual applications
        # displayed in the donut.
        self.max_apps = 8

        # =================================================
        # BUILD UI
        # =================================================

        self.setup_ui()

        # =================================================
        # TIMER
        # =================================================

        self.timer = QTimer(
            self
        )

        self.timer.timeout.connect(
            self.update_memory
        )

        # Update every second
        self.timer.start(
            1000
        )

        # Initial update
        self.update_memory()

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
            16
        )

        # =================================================
        # HEADER
        # =================================================

        title = QLabel(
            "Memory"
        )

        title.setObjectName(
            "page_title"
        )

        subtitle = QLabel(
            "RAM utilization and application memory usage"
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
        # TOP SECTION
        # =================================================

        top_section = QHBoxLayout()

        top_section.setSpacing(
            18
        )

        # =================================================
        # DONUT CONTAINER
        # =================================================

        donut_frame = QFrame()

        donut_frame.setObjectName(
            "memory_panel"
        )

        donut_layout = QVBoxLayout(
            donut_frame
        )

        donut_layout.setContentsMargins(
            18,
            12,
            18,
            15
        )

        donut_title = QLabel(
            "MEMORY BY APPLICATION"
        )

        donut_title.setObjectName(
            "section_title"
        )

        donut_layout.addWidget(
            donut_title
        )

        self.donut = MemoryDonut()

        donut_layout.addWidget(
            self.donut
        )

        # =================================================
        # APPLICATION LIST
        # =================================================

        app_frame = QFrame()

        app_frame.setObjectName(
            "memory_panel"
        )

        app_layout = QVBoxLayout(
            app_frame
        )

        app_layout.setContentsMargins(
            18,
            12,
            18,
            15
        )

        app_title = QLabel(
            "APPLICATION MEMORY"
        )

        app_title.setObjectName(
            "section_title"
        )

        app_layout.addWidget(
            app_title
        )

        # -------------------------------------------------
        # Scroll area
        # -------------------------------------------------

        scroll = QScrollArea()

        scroll.setWidgetResizable(
            True
        )

        scroll.setFrameShape(
            QFrame.NoFrame
        )

        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        scroll.setStyleSheet(
            """
            QScrollArea {
                background: transparent;
                border: none;
            }

            QScrollBar:vertical {
                background: #0b111a;
                width: 6px;
                border-radius: 3px;
            }

            QScrollBar::handle:vertical {
                background: #263c54;
                border-radius: 3px;
            }
            """
        )

        self.app_list_widget = QWidget()

        self.app_list_layout = QVBoxLayout(
            self.app_list_widget
        )

        self.app_list_layout.setContentsMargins(
            0,
            0,
            5,
            0
        )

        self.app_list_layout.setSpacing(
            6
        )

        scroll.setWidget(
            self.app_list_widget
        )

        app_layout.addWidget(
            scroll
        )

        # =================================================
        # ADD TOP SECTION
        # =================================================

        top_section.addWidget(
            donut_frame,
            3
        )

        top_section.addWidget(
            app_frame,
            2
        )

        layout.addLayout(
            top_section,
            2
        )

        # =================================================
        # MEMORY INFORMATION
        # =================================================

        info_frame = QFrame()

        info_frame.setObjectName(
            "memory_panel"
        )

        info_layout = QHBoxLayout(
            info_frame
        )

        info_layout.setContentsMargins(
            18,
            12,
            18,
            12
        )

        self.total_label = QLabel(
            "TOTAL: -- GB"
        )

        self.used_label = QLabel(
            "USED: -- GB"
        )

        self.available_label = QLabel(
            "AVAILABLE: -- GB"
        )

        self.percent_label = QLabel(
            "USAGE: --%"
        )

        information = [
            self.total_label,
            self.used_label,
            self.available_label,
            self.percent_label,
        ]

        for label in information:

            label.setObjectName(
                "memory_stat"
            )

            info_layout.addWidget(
                label
            )

        layout.addWidget(
            info_frame
        )

        # =================================================
        # REAL-TIME GRAPH
        # =================================================

        graph_frame = QFrame()

        graph_frame.setObjectName(
            "memory_panel"
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

        graph_title = QLabel(
            "RAM USAGE OVER TIME"
        )

        graph_title.setObjectName(
            "section_title"
        )

        graph_layout.addWidget(
            graph_title
        )

        self.graph = pg.PlotWidget()

        self.graph.setBackground(
            "#0b111a"
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
            "RAM USAGE (%)"
        )

        self.graph.setLabel(
            "bottom",
            "TIME"
        )

        self.graph.getAxis(
            "left"
        ).setTextPen(
            "#71839a"
        )

        self.graph.getAxis(
            "bottom"
        ).setTextPen(
            "#71839a"
        )

        # -------------------------------------------------
        # RAM LINE
        # -------------------------------------------------

        self.ram_curve = (
            self.graph.plot(
                self.ram_history,
                pen=pg.mkPen(
                    "#b35cff",
                    width=2
                )
            )
        )

        # -------------------------------------------------
        # RAM FILL
        # -------------------------------------------------

        self.ram_bottom = (
            pg.PlotDataItem(
                [0] * self.max_points
            )
        )

        self.ram_fill = (
            pg.FillBetweenItem(
                self.ram_curve,
                self.ram_bottom,
                brush=pg.mkBrush(
                    179,
                    92,
                    255,
                    45
                )
            )
        )

        self.graph.addItem(
            self.ram_fill
        )

        graph_layout.addWidget(
            self.graph
        )

        layout.addWidget(
            graph_frame,
            1
        )

    # =====================================================
    # UPDATE MEMORY
    # =====================================================

    def update_memory(self):

        memory = psutil.virtual_memory()

        # =================================================
        # SYSTEM MEMORY
        # =================================================

        total = memory.total

        used = memory.used

        available = memory.available

        percent = memory.percent

        # =================================================
        # UPDATE STATISTICS
        # =================================================

        self.total_label.setText(
            f"TOTAL: {total / (1024 ** 3):.2f} GB"
        )

        self.used_label.setText(
            f"USED: {used / (1024 ** 3):.2f} GB"
        )

        self.available_label.setText(
            f"AVAILABLE: {available / (1024 ** 3):.2f} GB"
        )

        self.percent_label.setText(
            f"USAGE: {percent:.1f}%"
        )

        # =================================================
        # HISTORY
        # =================================================

        self.ram_history.append(
            percent
        )

        self.ram_history = (
            self.ram_history[
                -self.max_points:
            ]
        )

        self.ram_curve.setData(
            self.ram_history
        )

        self.ram_bottom.setData(
            [0] * self.max_points
        )

        # =================================================
        # APPLICATION MEMORY
        # =================================================

        self.update_application_memory(
            total
        )

    # =====================================================
    # APPLICATION MEMORY
    # =====================================================

    def update_application_memory(
        self,
        total_memory
    ):

        processes = {}

        # =================================================
        # READ ALL RUNNING PROCESSES
        # =================================================

        for process in psutil.process_iter(
            [
                "name",
                "memory_info"
            ]
        ):

            try:

                name = process.info[
                    "name"
                ]

                memory_info = process.info[
                    "memory_info"
                ]

                if not name:
                    continue

                if not memory_info:
                    continue

                rss = memory_info.rss

                if rss <= 0:
                    continue

                # -------------------------------------------------
                # Group processes with the same name
                # -------------------------------------------------

                name = name.strip()

                processes[name] = (
                    processes.get(
                        name,
                        0
                    )
                    + rss
                )

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
                OSError,
            ):

                continue

        # =================================================
        # SORT
        # =================================================

        sorted_processes = sorted(
            processes.items(),
            key=lambda item: item[1],
            reverse=True
        )

        # =================================================
        # TOP APPLICATIONS
        # =================================================

        top_processes = (
            sorted_processes[
                :self.max_apps
            ]
        )

        # Everything else
        other_memory = sum(
            memory
            for name, memory
            in sorted_processes[
                self.max_apps:
            ]
        )

        # =================================================
        # BUILD DONUT DATA
        # =================================================

        chart_data = []

        for index, (
            name,
            memory
        ) in enumerate(
            top_processes
        ):

            chart_data.append(
                {
                    "name": name,
                    "value": memory,
                    "color": APP_COLORS[
                        index
                        % len(APP_COLORS)
                    ],
                }
            )

        # -------------------------------------------------
        # OTHER PROCESSES
        # -------------------------------------------------

        if other_memory > 0:

            chart_data.append(
                {
                    "name": "Other Apps",
                    "value": other_memory,
                    "color": "#344457",
                }
            )

        # =================================================
        # SAVE DATA
        # =================================================

        self.application_data = (
            chart_data
        )

        # =================================================
        # UPDATE DONUT
        # =================================================

        self.donut.set_data(
            chart_data
        )

        # =================================================
        # UPDATE APPLICATION LIST
        # =================================================

        self.update_application_list(
            chart_data
        )

    # =====================================================
    # APPLICATION LIST
    # =====================================================

    def update_application_list(
        self,
        data
    ):

        # -------------------------------------------------
        # CLEAR OLD ITEMS
        # -------------------------------------------------

        while (
            self.app_list_layout.count()
            > 0
        ):

            item = (
                self.app_list_layout.takeAt(
                    0
                )
            )

            widget = item.widget()

            if widget is not None:

                widget.deleteLater()

        # -------------------------------------------------
        # TOTAL
        # -------------------------------------------------

        total = sum(
            item["value"]
            for item in data
        )

        if total <= 0:
            return

        # -------------------------------------------------
        # CREATE ROW FOR EACH APP
        # -------------------------------------------------

        for item in data:

            name = item[
                "name"
            ]

            value = item[
                "value"
            ]

            color = item[
                "color"
            ]

            percentage = (
                value / total
            ) * 100

            gb = (
                value
                / (1024 ** 3)
            )

            row = QFrame()

            row.setObjectName(
                "application_row"
            )

            row_layout = QHBoxLayout(
                row
            )

            row_layout.setContentsMargins(
                8,
                6,
                8,
                6
            )

            row_layout.setSpacing(
                8
            )

            # -------------------------------------------------
            # COLOR INDICATOR
            # -------------------------------------------------

            color_box = QFrame()

            color_box.setFixedSize(
                8,
                28
            )

            color_box.setStyleSheet(
                f"""
                QFrame {{
                    background-color: {color};
                    border-radius: 4px;
                    border: none;
                }}
                """
            )

            row_layout.addWidget(
                color_box
            )

            # -------------------------------------------------
            # NAME
            # -------------------------------------------------

            name_label = QLabel(
                name
            )

            name_label.setObjectName(
                "app_name"
            )

            row_layout.addWidget(
                name_label,
                1
            )

            # -------------------------------------------------
            # MEMORY
            # -------------------------------------------------

            memory_label = QLabel(
                f"{gb:.2f} GB"
            )

            memory_label.setObjectName(
                "app_memory"
            )

            memory_label.setAlignment(
                Qt.AlignRight
            )

            row_layout.addWidget(
                memory_label
            )

            # -------------------------------------------------
            # PERCENTAGE
            # -------------------------------------------------

            percent_label = QLabel(
                f"{percentage:.1f}%"
            )

            percent_label.setObjectName(
                "app_percent"
            )

            percent_label.setAlignment(
                Qt.AlignRight
            )

            row_layout.addWidget(
                percent_label
            )

            self.app_list_layout.addWidget(
                row
            )

        self.app_list_layout.addStretch()

    # =====================================================
    # CLEANUP
    # =====================================================

    def closeEvent(
        self,
        event
    ):

        self.timer.stop()

        event.accept()