import math
import psutil
import pyqtgraph as pg

from PySide6.QtCore import (
    QTimer,
    Qt,
    QRectF,
    QFileInfo,
    Signal,
    QPoint,
    QThread,
    QObject,
    Slot,
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
    QApplication,
    QFileIconProvider,
    QStyle,
    QScrollArea,
    QToolTip,
    QComboBox,
)

from dashboard import CarbonFiberBackground


APP_COLORS = [
<<<<<<< Updated upstream
    "#ef4444",   # Red
    "#2563eb",   # Blue
    "#22c55e",   # Green
    "#a855f7",   # Purple
    "#facc15",   # Yellow
    "#06b6d4",   # Cyan
    "#f97316",   # Orange
    "#ec4899",   # Pink
    "#14b8a6",   # Teal
    "#8b5cf6",   # Violet
=======
    "#e53935",
    "#ff8f00",
    "#8bc34a",
    "#ab47bc",
    "#fdd835",
    "#ef5350",
    "#26a69a",
    "#ec407a",
    "#7cb342",
    "#ffa726",
>>>>>>> Stashed changes
]

DONUT_WIDTH = 30


# =========================================================
# PROCESS MEMORY WORKER
# =========================================================

class MemoryWorker(QObject):

    finished = Signal(list)
    request_scan = Signal()

    def __init__(self):
        super().__init__()
        self.request_scan.connect(self.collect)

    @Slot()
    def collect(self):

        processes = {}

        try:
            process_list = psutil.process_iter(
                ["name", "memory_info", "exe"]
            )

            for process in process_list:

                try:
                    info = process.info

                    name = info.get("name")
                    memory_info = info.get("memory_info")

                    if not name or not memory_info:
                        continue

                    rss = memory_info.rss

                    if rss <= 0:
                        continue

                    name = name.strip()

                    if name.lower().endswith(".exe"):
                        name = name[:-4]

                    if name not in processes:
                        processes[name] = {
                            "value": 0,
                            "icon_path": "",
                        }

                    processes[name]["value"] += rss

                    if not processes[name]["icon_path"]:
                        processes[name]["icon_path"] = (
                            info.get("exe") or ""
                        )

                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.ZombieProcess,
                    PermissionError,
                    OSError,
                ):
                    continue

                except Exception:
                    continue

        except Exception:
            processes = {}

        result = []

        for name, data in processes.items():

            result.append(
                {
                    "name": name,
                    "value": data["value"],
                    "icon_path": data["icon_path"],
                }
            )

        result.sort(
            key=lambda item: item["value"],
            reverse=True
        )

        self.finished.emit(result)


# =========================================================
# MEMORY DONUT
# =========================================================

class MemoryDonut(QWidget):

    slice_hovered = Signal(object)
    slice_selected = Signal(object)

    def __init__(self, parent=None):

        super().__init__(parent)

        self.data = []
        self.display_values = {}
        self.hovered_name = None
        self.selected_name = None
        self.system_percent = None

        self.animation_timer = QTimer(self)
        self.animation_timer.setInterval(16)
        self.animation_timer.timeout.connect(
            self._animate_values
        )

        self.setMinimumHeight(300)
        self.setMinimumWidth(400)

        self.setAttribute(
            Qt.WA_TranslucentBackground
        )

        self.setMouseTracking(True)

    def set_data(self, data, system_percent=None):

        self.data = data
        self.system_percent = system_percent

        active_names = {
            item["name"]
            for item in data
        }

        self.display_values = {
            name: value
            for name, value in self.display_values.items()
            if name in active_names
        }

        for item in data:
            self.display_values.setdefault(
                item["name"],
                0
            )

        if self.hovered_name not in active_names:
            self.hovered_name = None

        if self.selected_name not in active_names:
            self.selected_name = None

        self.update()

        if not self.animation_timer.isActive():
           self.animation_timer.start()

    def set_selected(self, name):

        self.selected_name = name
        self.update()

    def set_hovered(self, item):

        self.hovered_name = (
            item["name"]
            if item
            else None
        )

        self.update()

    def _animate_values(self):

        moving = False

        for item in self.data:

            name = item["name"]

            current = self.display_values.get(
                name,
                0
            )

            target = item["value"]

            if abs(target - current) > 1024:

                self.display_values[name] = (
                    current
                    + (target - current) * 0.22
                )

                moving = True

            else:

                self.display_values[name] = target

        self.update()

        if not moving:
            self.animation_timer.stop()

    def _slice_at(self, position):

        width = self.width()
        height = self.height()

        center = QPoint(
            width // 2,
            height // 2
        )

        dx = position.x() - center.x()
        dy = position.y() - center.y()

        radius = math.sqrt(
            dx * dx + dy * dy
        )

        diameter = min(
            width,
            height
        ) * 0.60

        if (
            radius < diameter * 0.29
            or radius > diameter * 0.53
        ):
            return None

        total = sum(
            self.display_values.get(
                item["name"],
                item["value"]
            )
            for item in self.data
        )

        if total <= 0:
            return None

        angle = (
            180 / math.pi
        ) * math.atan2(
            -dy,
            dx
        )

        clockwise_angle = (
            90 - angle
        ) % 360

        cursor = 0

        for item in self.data:

            span = (
                self.display_values.get(
                    item["name"],
                    item["value"]
                )
                / total
                * 360
            )

            if (
                cursor
                <= clockwise_angle
                < cursor + span
            ):
                return item

            cursor += span

        return None

    def mouseMoveEvent(self, event):

        item = self._slice_at(
            event.position().toPoint()
        )

        name = (
            item["name"]
            if item
            else None
        )

        if name != self.hovered_name:

            self.hovered_name = name

            self.slice_hovered.emit(
                item
            )

            self.update()

        if item:

            total = sum(
                entry["value"]
                for entry in self.data
            )

            percentage = (
                item["value"] / total * 100
                if total
                else 0
            )

            QToolTip.showText(
                self.mapToGlobal(
                    event.position().toPoint()
                ),
                (
                    f"<b>{item['name']}</b><br>"
                    f"{item['value'] / (1024 ** 3):.2f} GB RAM<br>"
                    f"{percentage:.1f}% of process memory"
                ),
                self,
            )

        else:

            QToolTip.hideText()

    def leaveEvent(self, event):

        self.hovered_name = None

        self.slice_hovered.emit(
            None
        )

        QToolTip.hideText()

        self.update()

        super().leaveEvent(event)

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:

            item = self._slice_at(
                event.position().toPoint()
            )

            if item:

                self.selected_name = (
                    item["name"]
                )

                self.slice_selected.emit(
                    item
                )

                self.update()

        super().mousePressEvent(event)

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.Antialiasing
        )

        width = self.width()
        height = self.height()

        center_x = width / 2
        center_y = height / 2

<<<<<<< Updated upstream
        # =================================================
        # DONUT SIZE
        # =================================================

        diameter = min(
            width,
            height
        ) * 0.82
=======
        diameter = (
            min(width, height)
            * 0.72
        )
>>>>>>> Stashed changes

        rect = QRectF(
            center_x - diameter / 2,
            center_y - diameter / 2,
            diameter,
            diameter
        )

        background_pen = QPen(
            QColor("#252525")
        )

<<<<<<< Updated upstream
        background_pen.setWidth(DONUT_WIDTH)

        background_pen.setCapStyle(
            Qt.FlatCap
        )
=======
        background_pen.setWidth(24)
        background_pen.setCapStyle(Qt.FlatCap)
>>>>>>> Stashed changes

        painter.setPen(
            background_pen
        )

        painter.drawArc(
            rect,
            90 * 16,
            -360 * 16
        )

        total = sum(
            item["value"]
            for item in self.data
        )

        if total <= 0:

            painter.end()
            return

        start_angle = 90 * 16

        for item in self.data:

            value = self.display_values.get(
                item["name"],
                item["value"]
            )

            if value <= 0:
                continue

            percentage = value / total

            span_angle = (
                -360
                * percentage
                * 16
            )

            color = QColor(
                item["color"]
            )

            is_hovered = (
                item["name"]
                == self.hovered_name
            )

            is_selected = (
                item["name"]
                == self.selected_name
            )

            offset = (
                7
                if is_hovered
                else 3
                if is_selected
                else 0
            )

            angle = (
                start_angle / 16
            ) - 90

            offset_x = (
                math.cos(
                    math.radians(angle)
                )
                * offset
            )

            offset_y = (
                -math.sin(
                    math.radians(angle)
                )
                * offset
            )

            slice_rect = rect.translated(
                offset_x,
                offset_y
            )

            if is_hovered:
<<<<<<< Updated upstream
                glow_pen = QPen(QColor(color.red(), color.green(), color.blue(), 55))
                glow_pen.setWidth(40)
                painter.setPen(glow_pen)
                painter.drawArc(slice_rect, int(start_angle), int(span_angle))
=======

                glow_pen = QPen(
                    QColor(
                        color.red(),
                        color.green(),
                        color.blue(),
                        55
                    )
                )

                glow_pen.setWidth(34)
>>>>>>> Stashed changes

                painter.setPen(
                    glow_pen
                )

<<<<<<< Updated upstream
            pen.setWidth(DONUT_WIDTH)
=======
                painter.drawArc(
                    slice_rect,
                    int(start_angle),
                    int(span_angle)
                )
>>>>>>> Stashed changes

            pen = QPen(color)

            pen.setWidth(24)
            pen.setCapStyle(Qt.FlatCap)

            painter.setPen(pen)

            painter.drawArc(
                slice_rect,
                int(start_angle),
                int(span_angle)
            )

            start_angle += span_angle

<<<<<<< Updated upstream
        # =================================================
        # INNER BLACK CIRCLE
        # =================================================

        inner_diameter = diameter - (DONUT_WIDTH * 2)
=======
        inner_diameter = (
            diameter - 48
        )
>>>>>>> Stashed changes

        inner_rect = QRectF(
            center_x - inner_diameter / 2,
            center_y - inner_diameter / 2,
            inner_diameter,
            inner_diameter
        )

        painter.setPen(Qt.NoPen)

        painter.setBrush(
            QBrush(
                QColor("#090909")
            )
        )

        painter.drawEllipse(
            inner_rect
        )

        hovered_item = next(
            (
                item
                for item in self.data
                if item["name"]
                == self.hovered_name
            ),
            None
        )

        center_name = (
            hovered_item["name"]
            if hovered_item
            else "PROCESS MEMORY"
        )

        center_value = (
            hovered_item["value"]
            if hovered_item
            else total
        )

        used_gb = (
            center_value
            / (1024 ** 3)
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
            f"{used_gb:.2f} GB"
        )

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
            center_name.upper()
        )

        if hovered_item:

            percentage = (
                hovered_item["value"]
                / total
                * 100
                if total
                else 0
            )

            painter.setPen(
                QColor("#888888")
            )

            painter.drawText(
                QRectF(
                    center_x - 100,
                    center_y + 38,
                    200,
                    20
                ),
                Qt.AlignCenter,
                f"{percentage:.1f}% OF TOTAL"
            )

        elif self.system_percent is not None:

            painter.setPen(
                QColor("#555555")
            )

            painter.drawText(
                QRectF(
                    center_x - 100,
                    center_y + 38,
                    200,
                    20
                ),
                Qt.AlignCenter,
                f"SYSTEM RAM {self.system_percent:.1f}%"
            )

        painter.end()


# =========================================================
# APPLICATION ROW
# =========================================================

class ApplicationMemoryRow(QFrame):

    hovered = Signal(object)
    selected = Signal(object)

    def __init__(self, item, parent=None):

        super().__init__(parent)

        self.item = item

        self.setMouseTracking(True)

    def enterEvent(self, event):

        self.hovered.emit(
            self.item
        )

        super().enterEvent(event)

    def leaveEvent(self, event):

        self.hovered.emit(None)

        super().leaveEvent(event)

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:

            self.selected.emit(
                self.item
            )

        super().mousePressEvent(event)


# =========================================================
# MEMORY PAGE
# =========================================================

class MemoryPage(CarbonFiberBackground):

    def __init__(self):

        super().__init__()

        # Cache application icons for the lifetime of the Memory page.
        self.icon_cache = {}
        self.icon_provider = QFileIconProvider()

        self.max_points = 60

        self.ram_history = (
            [0] * self.max_points
        )

        self.application_data = []
        self.process_data = []

        self.view_mode = "grouped"

        self.max_apps = 8

        self.setup_ui()

        # -------------------------------------------------
        # FAST RAM TIMER
        # -------------------------------------------------

        self.timer = QTimer(self)

        self.timer.timeout.connect(
            self.update_memory
        )

        self.timer.start(500)

        # -------------------------------------------------
        # BACKGROUND PROCESS WORKER
        # -------------------------------------------------

        self.worker_thread = QThread(
            self
        )

        self.worker = MemoryWorker()

        self.worker.moveToThread(
            self.worker_thread
        )

        self.worker.finished.connect(
            self.process_memory_data
        )

        self.worker_thread.start()

        # -------------------------------------------------
        # PROCESS SCAN TIMER
        # -------------------------------------------------

        self.scan_timer = QTimer(self)

        self.scan_timer.setInterval(
            2000
        )

        self.scan_timer.timeout.connect(
            self.request_process_scan
        )

        self.scan_timer.start()

        # Initial RAM update
        self.update_memory()

        # Initial process scan
        QTimer.singleShot(
            100,
            self.request_process_scan
        )

    def set_refresh_interval(self, ms):

        self.timer.setInterval(ms)

    def pause_timer(self):

        if self.timer.isActive():
            self.timer.stop()

        if self.scan_timer.isActive():
            self.scan_timer.stop()

    def resume_timer(self):

        if not self.timer.isActive():
            self.update_memory()
            self.timer.start()

        if not self.scan_timer.isActive():
            self.scan_timer.start()

            QTimer.singleShot(
                100,
                self.request_process_scan
            )

    # =====================================================
    # REQUEST PROCESS SCAN
    # =====================================================

    def request_process_scan(self):

        if not self.worker_thread.isRunning():
            return

        self.worker.request_scan.emit()

    # =====================================================
    # SETUP UI
    # =====================================================

    def setup_ui(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            30,
            25,
            30,
            25
        )

        layout.setSpacing(14)

        title = QLabel("Memory")

        title.setObjectName(
            "page_title"
        )

        subtitle = QLabel(
            "RAM utilization and application memory usage"
        )

        subtitle.setObjectName(
            "subtitle"
        )

        layout.addWidget(title)
        layout.addWidget(subtitle)

        # =================================================
        # TOP SECTION
        # =================================================

        top_section = QHBoxLayout()

        top_section.setSpacing(14)

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

        self.donut = MemoryDonut()

        self.donut.slice_hovered.connect(
            self._highlight_application
        )

        self.donut.slice_selected.connect(
            self._select_application
        )

        donut_layout.addWidget(
            self.donut
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

        scroll = QScrollArea()

        scroll.setWidgetResizable(True)

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

        self.app_list_layout.setSpacing(6)

        scroll.setWidget(
            self.app_list_widget
        )

        mode_row = QHBoxLayout()

        mode_label = QLabel("VIEW")

        mode_label.setObjectName(
            "app_percent"
        )

        mode_row.addWidget(
            mode_label
        )

        self.view_mode_box = QComboBox()

        self.view_mode_box.addItem(
            "Grouped",
            "grouped"
        )

        self.view_mode_box.addItem(
            "Top Processes",
            "top"
        )

        self.view_mode_box.addItem(
            "All Processes",
            "all"
        )

        self.view_mode_box.setToolTip(
            "Choose how process memory is grouped"
        )

        self.view_mode_box.currentIndexChanged.connect(
            self._change_view_mode
        )

        mode_row.addWidget(
            self.view_mode_box,
            1
        )

        app_layout.addLayout(
            mode_row
        )

        app_layout.addWidget(scroll)

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
        # RAM GRAPH
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
            "#0d0d0d"
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

        self.graph.getAxis(
            "left"
        ).setTextPen("#686868")

        self.graph.getAxis(
            "bottom"
        ).setTextPen("#686868")

        self.graph.getAxis(
            "left"
        ).setPen(
            pg.mkPen("#303030")
        )

        self.graph.getAxis(
            "bottom"
        ).setPen(
            pg.mkPen("#303030")
        )

        self.ram_curve = self.graph.plot(
            self.ram_history,
            pen=pg.mkPen(
                "#ab47bc",
                width=2
            )
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
                60
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
    # VIEW MODE
    # =====================================================

    def _change_view_mode(self):

        self.view_mode = (
            self.view_mode_box.currentData()
        )

        if self.process_data:

            self.process_memory_data(
                self.process_data
            )

    # =====================================================
    # HIGHLIGHT
    # =====================================================

    def _highlight_application(self, item):

        name = (
            item["name"]
            if item
            else None
        )

        for index in range(
            self.app_list_layout.count()
        ):

            row = (
                self.app_list_layout
                .itemAt(index)
                .widget()
            )

            if isinstance(
                row,
                ApplicationMemoryRow
            ):

                row.setProperty(
                    "active",
                    row.item["name"] == name
                )

                row.style().unpolish(row)
                row.style().polish(row)

    # =====================================================
    # SELECT
    # =====================================================

    def _select_application(self, item):

        name = (
            item["name"]
            if item
            else None
        )

        self.donut.set_selected(name)

        self._highlight_application(
            item
        )

    # =====================================================
    # FAST RAM UPDATE
    # =====================================================

    def update_memory(self):

        memory = psutil.virtual_memory()

        total = memory.total
        used = memory.used
        available = memory.available
        percent = memory.percent

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

        # Update system percentage
        # without scanning processes.
        self.donut.system_percent = percent
        self.donut.update()

    # =====================================================
    # PROCESS DATA RECEIVED FROM WORKER
    # =====================================================

    @Slot(list)
    def process_memory_data(
        self,
        sorted_processes
    ):

        self.process_data = sorted_processes

        top_processes = (
            sorted_processes[
                :self.max_apps
            ]
        )

        if self.view_mode == "all":

            visible_processes = (
                sorted_processes
            )

        else:

            visible_processes = (
                top_processes
            )

<<<<<<< Updated upstream
        # =================================================
        # EVERYTHING ELSE
        # =================================================
=======
        max_memory = (
            top_processes[0]["value"]
            if top_processes
            else 0
        )
>>>>>>> Stashed changes

        other_memory = sum(
            item["value"]
            for item
            in sorted_processes[
                self.max_apps:
            ]
        )

        chart_data = []

        for index, item in enumerate(
            visible_processes
        ):

            name = item["name"]
            memory = item["value"]

            color = APP_COLORS[
                index
                % len(APP_COLORS)
            ]

<<<<<<< Updated upstream
=======
            if max_memory > 0:

                base_color = QColor(
                    color
                )

                red_color = QColor(
                    "#e53935"
                )

                intensity = (
                    memory
                    / max_memory
                )

                color = QColor(
                    int(
                        base_color.red()
                        * (1 - intensity)
                        + red_color.red()
                        * intensity
                    ),
                    int(
                        base_color.green()
                        * (1 - intensity)
                        + red_color.green()
                        * intensity
                    ),
                    int(
                        base_color.blue()
                        * (1 - intensity)
                        + red_color.blue()
                        * intensity
                    ),
                ).name()

>>>>>>> Stashed changes
            chart_data.append(
                {
                    "name": name,
                    "value": memory,
                    "icon_path": item.get(
                        "icon_path",
                        ""
                    ),
                    "color": color,
                }
            )

        if (
            other_memory > 0
            and self.view_mode == "grouped"
        ):

            chart_data.append(
                {
                    "name": "Other Apps",
                    "value": other_memory,
                    "color": "#3a3a3a",
                }
            )

        self.application_data = (
            chart_data
        )

        self.donut.set_data(
            chart_data,
            psutil.virtual_memory().percent
        )

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

        total = sum(
            item["value"]
            for item in data
        )

        if total <= 0:
            return

        for item in data:

            name = item["name"]
            value = item["value"]
            color = item["color"]

            percentage = (
                value / total
            ) * 100

            gb = (
                value
                / (1024 ** 3)
            )

            row = ApplicationMemoryRow(
                item
            )

            row.setObjectName(
                "application_row"
            )

            row.hovered.connect(
                self.donut.set_hovered
            )

            row.selected.connect(
                self._select_application
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

            row_layout.setSpacing(8)

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

            icon_path = item.get(
                "icon_path",
                ""
            )

            # Cache Windows application icons by executable path.
            # QFileIconProvider can be relatively expensive, so
            # do not ask Windows for the same icon every refresh.
            if icon_path:

                if icon_path in self.icon_cache:

                    app_icon = self.icon_cache[
                        icon_path
                    ]

                else:

                    try:

                        app_icon = (
                            self.icon_provider.icon(
                                QFileInfo(
                                    icon_path
                                )
                            )
                        )

                        self.icon_cache[
                            icon_path
                        ] = app_icon

                    except Exception:

                        app_icon = (
                            QApplication.style()
                            .standardIcon(
                                QStyle.SP_ComputerIcon
                            )
                        )

                        self.icon_cache[
                            icon_path
                        ] = app_icon

            else:

                app_icon = (
                    QApplication.style()
                    .standardIcon(
                        QStyle.SP_ComputerIcon
                    )
                )

            icon_label = QLabel()

            icon_label.setPixmap(
                app_icon.pixmap(
                    20,
                    20
                )
            )

            row_layout.addWidget(
                icon_label
            )

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
    # CLOSE
    # =====================================================

    def closeEvent(
        self,
        event
    ):

        self.timer.stop()
        self.scan_timer.stop()

        if self.worker_thread.isRunning():

            self.worker_thread.quit()

            if not self.worker_thread.wait(
                2000
            ):

                self.worker_thread.terminate()
                self.worker_thread.wait()

        event.accept()