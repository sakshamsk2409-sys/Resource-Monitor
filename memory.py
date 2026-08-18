import math

import psutil
import pyqtgraph as pg

from PySide6.QtCore import QTimer
from PySide6.QtGui import QBrush, QPen
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
)


class MemoryPage(QWidget):

    def __init__(self):

        super().__init__()

        self.max_points = 60

        self.ram_history = [
            0
        ] * self.max_points

        self.setup_ui()

        self.timer = QTimer(
            self
        )

        self.timer.timeout.connect(
            self.update_memory
        )

        self.timer.start(
            1000
        )

        self.update_memory()

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

        title = QLabel(
            "Memory"
        )

        title.setObjectName(
            "page_title"
        )

        subtitle = QLabel(
            "RAM utilization and memory trends"
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

        top_section = QHBoxLayout()

        top_section.setSpacing(
            18
        )

        donut_frame = QFrame()

        donut_frame.setObjectName(
            "graph_container"
        )

        donut_layout = QVBoxLayout(
            donut_frame
        )

        donut_title = QLabel(
            "MEMORY USAGE"
        )

        donut_title.setObjectName(
            "section_title"
        )

        donut_layout.addWidget(
            donut_title
        )

        self.donut = pg.PlotWidget()

        self.donut.setBackground(
            "#161d26"
        )

        self.donut.hideAxis(
            "left"
        )

        self.donut.hideAxis(
            "bottom"
        )

        self.donut.setAspectLocked(
            True
        )

        self.donut.setMouseEnabled(
            False,
            False
        )

        self.donut.setXRange(
            -120,
            120
        )

        self.donut.setYRange(
            -120,
            120
        )

        donut_layout.addWidget(
            self.donut
        )

        info_frame = QFrame()

        info_frame.setObjectName(
            "graph_container"
        )

        info_layout = QVBoxLayout(
            info_frame
        )

        info_title = QLabel(
            "MEMORY INFORMATION"
        )

        info_title.setObjectName(
            "section_title"
        )

        info_layout.addWidget(
            info_title
        )

        self.total_label = QLabel(
            "Total: -- GB"
        )

        self.used_label = QLabel(
            "Used: -- GB"
        )

        self.available_label = QLabel(
            "Available: -- GB"
        )

        self.percent_label = QLabel(
            "Usage: --%"
        )

        labels = [
            self.total_label,
            self.used_label,
            self.available_label,
            self.percent_label,
        ]

        for label in labels:

            label.setObjectName(
                "memory_value"
            )

            info_layout.addWidget(
                label
            )

        info_layout.addStretch()

        top_section.addWidget(
            donut_frame,
            1
        )

        top_section.addWidget(
            info_frame,
            1
        )

        layout.addLayout(
            top_section,
            1
        )

        graph_frame = QFrame()

        graph_frame.setObjectName(
            "graph_container"
        )

        graph_layout = QVBoxLayout(
            graph_frame
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
            "RAM Usage (%)"
        )

        self.graph.setLabel(
            "bottom",
            "Time"
        )

        self.ram_curve = (
            self.graph.plot(
                self.ram_history,
                pen=pg.mkPen(
                    width=2
                )
            )
        )

        graph_layout.addWidget(
            self.graph
        )

        layout.addWidget(
            graph_frame,
            1
        )

    def update_memory(self):

        memory = psutil.virtual_memory()

        total = (
            memory.total
            / (1024 ** 3)
        )

        used = (
            memory.used
            / (1024 ** 3)
        )

        available = (
            memory.available
            / (1024 ** 3)
        )

        percent = memory.percent

        self.total_label.setText(
            f"Total: {total:.2f} GB"
        )

        self.used_label.setText(
            f"Used: {used:.2f} GB"
        )

        self.available_label.setText(
            f"Available: {available:.2f} GB"
        )

        self.percent_label.setText(
            f"Usage: {percent:.1f}%"
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

        self.draw_donut(
            percent
        )

    def draw_donut(
        self,
        used_percent
    ):

        self.donut.clear()

        used_percent = max(
            0,
            min(
                100,
                used_percent
            )
        )

        background = (
            pg.QtWidgets.QGraphicsEllipseItem(
                -80,
                -80,
                160,
                160
            )
        )

        background.setPen(
            QPen(
                pg.mkColor(
                    "#27313d"
                ),
                18
            )
        )

        self.donut.addItem(
            background
        )

        used_arc = (
            pg.QtWidgets.QGraphicsEllipseItem(
                -80,
                -80,
                160,
                160
            )
        )

        used_arc.setPen(
            QPen(
                pg.mkColor(
                    "#4f8cff"
                ),
                18
            )
        )

        start_angle = 90 * 16

        span_angle = (
            -used_percent
            * 360
            * 16
            / 100
        )

        used_arc.setStartAngle(
            int(start_angle)
        )

        used_arc.setSpanAngle(
            int(span_angle)
        )

        self.donut.addItem(
            used_arc
        )

        text = pg.TextItem(
            f"{used_percent:.1f}%",
            color="white",
            anchor=(
                0.5,
                0.5
            )
        )

        text.setFont(
            pg.QtGui.QFont(
                "Segoe UI",
                20
            )
        )

        text.setPos(
            0,
            0
        )

        self.donut.addItem(
            text
        )

    def closeEvent(
        self,
        event
    ):

        self.timer.stop()

        event.accept()