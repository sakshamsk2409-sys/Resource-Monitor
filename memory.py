import psutil
import pyqtgraph as pg

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import Wedge
from matplotlib.colors import to_rgba

from PySide6.QtCore import QTimer, Qt, QRectF, QFileInfo
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
    QApplication,
    QFileIconProvider,
    QStyle,
    QScrollArea,
)

APP_COLORS = [
    "#e53935",   # Red
    "#ff8f00",   # Orange
    "#8bc34a",   # Green
    "#ab47bc",   # Purple
    "#fdd835",   # Yellow
    "#ef5350",   # Light red
    "#26a69a",   # Teal
    "#ec407a",   # Pink
    "#7cb342",   # Lime
    "#ffa726",   # Amber
]


# =========================================================
# MEMORY DONUT
# =========================================================

class MemoryDonut(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.data = []

        self.setMinimumHeight(300)
        self.setMinimumWidth(400)

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
    # PAINT DONUT
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

        # =================================================
        # DONUT SIZE
        # =================================================

        diameter = min(
            width,
            height
        ) * 0.60

        rect = QRectF(
            center_x - diameter / 2,
            center_y - diameter / 2,
            diameter,
            diameter
        )

        # =================================================
        # BACKGROUND RING
        # =================================================

        background_pen = QPen(
            QColor("#252525")
        )

        background_pen.setWidth(
            24
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

        # =================================================
        # TOTAL PROCESS MEMORY
        # =================================================

        total = sum(
            item["value"]
            for item in self.data
        )

        if total <= 0:

            painter.end()

            return

        # =================================================
        # DRAW APPLICATION ARCS
        # =================================================

        start_angle = 90 * 16

        for item in self.data:

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
                24
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

        # =================================================
        # INNER BLACK CIRCLE
        # =================================================

        inner_diameter = (
            diameter - 48
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
                QColor("#090909")
            )
        )

        painter.drawEllipse(
            inner_rect
        )

        # =================================================
        # CENTER VALUE
        # =================================================

        used_gb = (
            total / (1024 ** 3)
        )

        painter.setPen(
            QColor("#eeeeee")
        )

        painter.setFont(
            QFont(
                "Segoe UI",
                20,
                QFont.Bold
            )
        )

        value_rect = QRectF(
            center_x - 100,
            center_y - 22,
            200,
            40
        )

        painter.drawText(
            value_rect,
            Qt.AlignCenter,
            f"{used_gb:.1f} GB"
        )

        # =================================================
        # CENTER LABEL
        # =================================================

        painter.setPen(
            QColor("#777777")
        )

        painter.setFont(
            QFont(
                "Segoe UI",
                9
            )
        )

        label_rect = QRectF(
            center_x - 100,
            center_y + 17,
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
# 3D PIE CHART
# =========================================================

class PieChart3D(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.data = []

        self.setMinimumHeight(300)
        self.setMinimumWidth(400)

        self.figure = Figure(
            figsize=(4, 3),
            dpi=100
        )

        self.figure.patch.set_facecolor(
            "#090909"
        )

        self.canvas = FigureCanvasQTAgg(
            self.figure
        )

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        layout.addWidget(
            self.canvas
        )

        self.ax = (
            self.figure.add_subplot(
                111
            )
        )

        self.ax.set_facecolor(
            "#090909"
        )

    # =====================================================
    # SET DATA
    # =====================================================

    def set_data(self, data):

        self.data = data

        self.draw_chart()

    # =====================================================
    # DRAW 3D PIE
    # =====================================================

    def draw_chart(self):

        self.ax.clear()

        self.ax.set_facecolor(
            "#090909"
        )

        total = sum(
            item["value"]
            for item in self.data
        )

        if total <= 0:
            self.canvas.draw()
            return

        values = [
            item["value"]
            for item in self.data
        ]

        colors = [
            item["color"]
            for item in self.data
        ]

        labels = [
            item["name"]
            for item in self.data
        ]

        # =================================================
        # 3D SHADOW LAYER
        # =================================================

        shadow_offset = 0.04
        shadow_depth = 0.18

        shadow_colors = []
        for color in colors:
            r, g, b = to_rgba(
                color
            )[:3]
            shadow_colors.append(
                (
                    r * 0.3,
                    g * 0.3,
                    b * 0.3,
                    0.6
                )
            )

        # Draw shadow wedges (offset down-right)
        self.ax.pie(
            values,
            labels=None,
            colors=shadow_colors,
            startangle=90,
            counterclock=False,
            radius=0.85,
            center=(
                shadow_offset,
                -shadow_offset
            ),
            wedgeprops=dict(
                width=0.3,
                edgecolor="none",
            ),
        )

        # Draw 3D side edges (connecting shadow to top)
        wedges, _ = self.ax.pie(
            values,
            labels=None,
            colors=shadow_colors,
            startangle=90,
            counterclock=False,
            radius=0.85,
            center=(
                shadow_offset,
                -shadow_offset
            ),
            wedgeprops=dict(
                width=0.3,
                edgecolor="none",
            ),
        )

        # =================================================
        # TOP COLORED LAYER
        # =================================================

        self.ax.pie(
            values,
            labels=None,
            colors=colors,
            startangle=90,
            counterclock=False,
            radius=0.85,
            center=(0, 0),
            wedgeprops=dict(
                width=0.3,
                edgecolor="#090909",
                linewidth=0.5,
            ),
        )

        # =================================================
        # LABELS
        # =================================================

        self.ax.pie(
            values,
            labels=labels,
            colors=[
                "transparent"
                for _ in values
            ],
            startangle=90,
            counterclock=False,
            radius=1.15,
            labeldistance=1.15,
            textprops=dict(
                color="#cccccc",
                fontsize=7,
            ),
            wedgeprops=dict(
                edgecolor="none",
            ),
        )

        self.ax.set_xlim(
            -1.4,
            1.4
        )

        self.ax.set_ylim(
            -1.4,
            1.4
        )

        self.ax.set_aspect(
            "equal"
        )

        for spine in (
            self.ax.spines.values()
        ):
            spine.set_visible(
                False
            )

        self.canvas.draw()


# =========================================================
# MEMORY PAGE
# =========================================================

class MemoryPage(QWidget):

    def __init__(self):

        super().__init__()

        # =================================================
        # RAM HISTORY
        # =================================================

        self.max_points = 60

        self.ram_history = (
            [0] * self.max_points
        )

        # =================================================
        # APPLICATION SETTINGS
        # =================================================

        self.application_data = []

        # Number of individual processes/apps
        # displayed separately.
        self.max_apps = 8

        # =================================================
        # BUILD UI
        # =================================================

        self.setup_ui()

        # =================================================
        # UPDATE TIMER
        # =================================================

        self.timer = QTimer(
            self
        )

        self.timer.timeout.connect(
            self.update_memory
        )

        self.timer.start(500)
        self.update_memory()

    def set_refresh_interval(self, ms):
        self.timer.setInterval(ms)

    def pause_timer(self):
        if self.timer.isActive():
            self.timer.stop()

    def resume_timer(self):
        if not self.timer.isActive():
            self.update_memory()
            self.timer.start()

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
            14
        )

        # =================================================
        # DONUT PANEL
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

        self.pie_chart = PieChart3D()

        donut_layout.addWidget(
            self.pie_chart
        )

        # =================================================
        # APPLICATION PANEL
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

        # =================================================
        # SCROLL AREA
        # =================================================

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
                background: #080808;
                width: 6px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background: #3a3a3a;
                min-height: 25px;
                border-radius: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background: #666666;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
            """
        )

        self.app_list_widget = QWidget()

        self.app_list_widget.setStyleSheet(
            """
            QWidget {
                background: transparent;
            }
            """
        )

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
        # ADD TOP PANELS
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
        # MEMORY STATISTICS
        # =================================================

        info_frame = QFrame()

        info_frame.setObjectName(
            "memory_panel"
        )

        info_layout = QHBoxLayout(
            info_frame
        )

        info_layout.setContentsMargins(
            15,
            8,
            15,
            8
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

        statistics = [
            self.total_label,
            self.used_label,
            self.available_label,
            self.percent_label,
        ]

        for label in statistics:

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
        # RAM GRAPH PANEL
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
            "RAM USAGE (%)"
        )

        self.graph.setLabel(
            "bottom",
            "TIME"
        )

        # -------------------------------------------------
        # AXIS STYLE
        # -------------------------------------------------

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
        # RAM CURVE
        # =================================================

        self.ram_curve = (
            self.graph.plot(
                self.ram_history,
                pen=pg.mkPen(
                    "#ab47bc",
                    width=2
                )
            )
        )

        # =================================================
        # RAM FILL
        # =================================================

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
                    171,
                    71,
                    188,
                    60
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

        # =================================================
        # SYSTEM RAM
        # =================================================

        memory = psutil.virtual_memory()

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
        # UPDATE HISTORY
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
        # UPDATE APPLICATION MEMORY
        # =================================================

        self.update_application_memory(
            total
        )

    # =====================================================
    # GET APPLICATION MEMORY
    # =====================================================

    def update_application_memory(
        self,
        total_memory
    ):

        processes = {}
        process_icons = {}

        # =================================================
        # GET ALL RUNNING PROCESSES
        # =================================================

        for process in psutil.process_iter():
            try:
                name = process.name()
                memory_info = process.memory_info()

                if not name or not memory_info:
                    continue

                rss = memory_info.rss
                if rss <= 0:
                    continue

                name = name.strip()
                if name.lower().endswith(".exe"):
                    name = name[:-4]
                processes[name] = processes.get(name, 0) + rss

                if name not in process_icons:
                    try:
                        process_icons[name] = process.exe()
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, PermissionError, OSError):
                        process_icons[name] = ""

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, PermissionError, OSError, Exception):
                continue

        # =================================================
        # SORT BY MEMORY
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

        max_memory = (
            top_processes[0][1]
            if top_processes
            else 0
        )

        # =================================================
        # EVERYTHING ELSE
        # =================================================

        other_memory = sum(
            memory
            for name, memory
            in sorted_processes[
                self.max_apps:
            ]
        )

        # =================================================
        # BUILD CHART DATA
        # =================================================

        chart_data = []

        for index, (
            name,
            memory
        ) in enumerate(
            top_processes
        ):

            color = APP_COLORS[
                index
                % len(APP_COLORS)
            ]

            if max_memory > 0:
                base_color = QColor(color)
                red_color = QColor("#e53935")
                intensity = memory / max_memory
                color = QColor(
                    int(base_color.red() * (1 - intensity) + red_color.red() * intensity),
                    int(base_color.green() * (1 - intensity) + red_color.green() * intensity),
                    int(base_color.blue() * (1 - intensity) + red_color.blue() * intensity),
                ).name()

            chart_data.append(
                {
                    "name": name,
                    "value": memory,
                    "icon_path": process_icons.get(name, ""),
                    "color": color,
                }
            )

        # =================================================
        # OTHER APPS
        # =================================================

        if other_memory > 0:

            chart_data.append(
                {
                    "name": "Other Apps",
                    "value": other_memory,
                    "color": "#3a3a3a",
                }
            )

        # =================================================
        # SAVE
        # =================================================

        self.application_data = (
            chart_data
        )

        # =================================================
        # UPDATE PIE CHART
        # =================================================

        self.pie_chart.set_data(
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

        # =================================================
        # CLEAR OLD ROWS
        # =================================================

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

        # =================================================
        # TOTAL PROCESS MEMORY
        # =================================================

        total = sum(
            item["value"]
            for item in data
        )

        if total <= 0:
            return

        # =================================================
        # CREATE APPLICATION ROWS
        # =================================================

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

            # =================================================
            # ROW
            # =================================================

            row = QFrame()

            row.setObjectName(
                "application_row"
            )

            row_layout = QHBoxLayout(
                row
            )

            row_layout.setContentsMargins(
                7,
                5,
                7,
                5
            )

            row_layout.setSpacing(
                8
            )

            # =================================================
            # COLOR MARKER
            # =================================================

            color_box = QFrame()

            color_box.setFixedSize(
                6,
                26
            )

            color_box.setStyleSheet(
                f"""
                QFrame {{
                    background-color: {color};
                    border: none;
                    border-radius: 1px;
                }}
                """
            )

            row_layout.addWidget(
                color_box
            )

            # APPLICATION ICON
            icon_path = item.get("icon_path", "")
            if icon_path:
                app_icon = QFileIconProvider().icon(
                    QFileInfo(icon_path)
                )
            else:
                app_icon = QApplication.style().standardIcon(
                    QStyle.SP_ComputerIcon
                )

            icon_label = QLabel()
            icon_label.setPixmap(
                app_icon.pixmap(20, 20)
            )
            row_layout.addWidget(
                icon_label
            )

            # =================================================
            # APPLICATION NAME
            # =================================================

            name_label = QLabel(
                name
            )

            name_label.setObjectName(
                "app_name"
            )

            name_label.setToolTip(
                name
            )

            row_layout.addWidget(
                name_label,
                1
            )

            # =================================================
            # MEMORY
            # =================================================

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

            # =================================================
            # PERCENTAGE
            # =================================================

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

        # =================================================
        # EMPTY SPACE
        # =================================================

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