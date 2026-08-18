import sys
import psutil
import pyqtgraph as pg

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class ResourceMonitor(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("System Resource Monitor")
        self.resize(1400, 850)

        # ==========================================
        # DATA HISTORY
        # ==========================================

        self.max_points = 60

        self.time_data = list(range(self.max_points))

        self.cpu_data = [0] * self.max_points
        self.ram_data = [0] * self.max_points

        # ==========================================
        # GUI
        # ==========================================

        self.setup_ui()

        # ==========================================
        # START MONITORING
        # ==========================================

        # First CPU measurement
        psutil.cpu_percent(interval=None)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_system_data)

        # Update every 1 second
        self.timer.start(1000)

        # Initial update
        self.update_system_data()

    # ==================================================
    # MAIN UI
    # ==================================================

    def setup_ui(self):

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ==================================================
        # SIDEBAR
        # ==================================================

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 25, 20, 25)
        sidebar_layout.setSpacing(10)

        logo = QLabel("SYSTEM\nRESOURCE MONITOR")
        logo.setObjectName("logo")
        logo.setAlignment(Qt.AlignCenter)

        sidebar_layout.addWidget(logo)
        sidebar_layout.addSpacing(30)

        self.dashboard_button = QPushButton("Dashboard")
        self.system_button = QPushButton("System Configuration")
        self.memory_button = QPushButton("Memory")
        self.gpu_button = QPushButton("GPU Performance")

        for button in [
            self.dashboard_button,
            self.system_button,
            self.memory_button,
            self.gpu_button,
        ]:
            button.setObjectName("nav_button")

        sidebar_layout.addWidget(self.dashboard_button)
        sidebar_layout.addWidget(self.system_button)
        sidebar_layout.addWidget(self.memory_button)
        sidebar_layout.addWidget(self.gpu_button)

        sidebar_layout.addStretch()

        self.status = QLabel("●  MONITORING ACTIVE")
        self.status.setObjectName("status")

        sidebar_layout.addWidget(self.status)

        # ==================================================
        # PAGES
        # ==================================================

        self.pages = QStackedWidget()
        self.pages.setObjectName("pages")

        self.dashboard_page = self.create_dashboard_page()
        self.system_page = self.create_system_page()
        self.memory_page = self.create_memory_page()
        self.gpu_page = self.create_gpu_page()

        self.pages.addWidget(self.dashboard_page)
        self.pages.addWidget(self.system_page)
        self.pages.addWidget(self.memory_page)
        self.pages.addWidget(self.gpu_page)

        # ==================================================
        # NAVIGATION
        # ==================================================

        self.dashboard_button.clicked.connect(
            lambda: self.change_page(0)
        )

        self.system_button.clicked.connect(
            lambda: self.change_page(1)
        )

        self.memory_button.clicked.connect(
            lambda: self.change_page(2)
        )

        self.gpu_button.clicked.connect(
            lambda: self.change_page(3)
        )

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.pages)

        self.change_page(0)

    # ==================================================
    # PAGE NAVIGATION
    # ==================================================

    def change_page(self, index):

        self.pages.setCurrentIndex(index)

        buttons = [
            self.dashboard_button,
            self.system_button,
            self.memory_button,
            self.gpu_button,
        ]

        for button in buttons:
            button.setProperty("active", False)
            button.style().unpolish(button)
            button.style().polish(button)

        buttons[index].setProperty("active", True)
        buttons[index].style().unpolish(buttons[index])
        buttons[index].style().polish(buttons[index])

    # ==================================================
    # DASHBOARD
    # ==================================================

    def create_dashboard_page(self):

        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(20)

        title = QLabel("Dashboard")
        title.setObjectName("page_title")

        subtitle = QLabel(
            "Real-time system performance overview"
        )
        subtitle.setObjectName("subtitle")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        # ==============================================
        # KPI CARDS
        # ==============================================

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)

        self.cpu_value = QLabel("0%")
        self.gpu_value = QLabel("0%")
        self.ram_value = QLabel("0%")
        self.temp_value = QLabel("--°C")

        cpu_card = self.create_card(
            "CPU",
            self.cpu_value,
            "Usage"
        )

        gpu_card = self.create_card(
            "GPU",
            self.gpu_value,
            "Usage"
        )

        ram_card = self.create_card(
            "RAM",
            self.ram_value,
            "Memory"
        )

        temp_card = self.create_card(
            "TEMPERATURE",
            self.temp_value,
            "GPU"
        )

        cards_layout.addWidget(cpu_card)
        cards_layout.addWidget(gpu_card)
        cards_layout.addWidget(ram_card)
        cards_layout.addWidget(temp_card)

        layout.addLayout(cards_layout)

        # ==============================================
        # REAL-TIME GRAPH
        # ==============================================

        graph_frame = QFrame()
        graph_frame.setObjectName("graph_placeholder")

        graph_layout = QVBoxLayout(graph_frame)
        graph_layout.setContentsMargins(20, 15, 20, 20)

        graph_title = QLabel("REAL-TIME PERFORMANCE")
        graph_title.setObjectName("section_title")

        graph_layout.addWidget(graph_title)

        # PyQtGraph
        self.performance_graph = pg.PlotWidget()

        self.performance_graph.setBackground("#161d26")

        self.performance_graph.showGrid(
            x=True,
            y=True,
            alpha=0.15
        )

        self.performance_graph.setYRange(0, 100)

        self.performance_graph.setLabel(
            "left",
            "Usage (%)"
        )

        self.performance_graph.setLabel(
            "bottom",
            "Time"
        )

        self.performance_graph.addLegend()

        self.cpu_curve = self.performance_graph.plot(
            self.time_data,
            self.cpu_data,
            pen=pg.mkPen(width=2),
            name="CPU"
        )

        self.ram_curve = self.performance_graph.plot(
            self.time_data,
            self.ram_data,
            pen=pg.mkPen(width=2),
            name="RAM"
        )

        graph_layout.addWidget(
            self.performance_graph
        )

        layout.addWidget(
            graph_frame,
            1
        )

        return page

    # ==================================================
    # SYSTEM PAGE
    # ==================================================

    def create_system_page(self):

        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(20)

        title = QLabel("System Configuration")
        title.setObjectName("page_title")

        subtitle = QLabel(
            "Hardware and operating system information"
        )
        subtitle.setObjectName("subtitle")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        system_card = QFrame()
        system_card.setObjectName("info_card")

        card_layout = QVBoxLayout(system_card)

        self.system_labels = {}

        information = [
            "Model",
            "CPU",
            "GPU",
            "RAM",
            "Storage",
            "Operating System",
            "Architecture",
            "Display",
            "Uptime",
            "Battery",
        ]

        for item in information:

            label = QLabel(
                f"{item}: Detecting..."
            )

            label.setObjectName("info_label")

            self.system_labels[item] = label

            card_layout.addWidget(label)

        layout.addWidget(system_card)
        layout.addStretch()

        return page

    # ==================================================
    # MEMORY PAGE
    # ==================================================

    def create_memory_page(self):

        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(20)

        title = QLabel("Memory")
        title.setObjectName("page_title")

        subtitle = QLabel(
            "RAM utilization and memory trends"
        )
        subtitle.setObjectName("subtitle")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.memory_info = QLabel(
            "RAM information loading..."
        )

        self.memory_info.setObjectName(
            "memory_info"
        )

        layout.addWidget(
            self.memory_info
        )

        memory_graph_frame = QFrame()
        memory_graph_frame.setObjectName(
            "graph_placeholder"
        )

        memory_layout = QVBoxLayout(
            memory_graph_frame
        )

        memory_title = QLabel(
            "RAM USAGE"
        )

        memory_title.setObjectName(
            "section_title"
        )

        memory_layout.addWidget(
            memory_title
        )

        self.memory_graph = pg.PlotWidget()

        self.memory_graph.setBackground(
            "#161d26"
        )

        self.memory_graph.showGrid(
            x=True,
            y=True,
            alpha=0.15
        )

        self.memory_graph.setYRange(
            0,
            100
        )

        self.memory_graph.setLabel(
            "left",
            "RAM Usage (%)"
        )

        self.memory_curve = (
            self.memory_graph.plot(
                self.time_data,
                self.ram_data,
                pen=pg.mkPen(width=2)
            )
        )

        memory_layout.addWidget(
            self.memory_graph
        )

        layout.addWidget(
            memory_graph_frame,
            1
        )

        return page

    # ==================================================
    # GPU PAGE
    # ==================================================

    def create_gpu_page(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        layout.setContentsMargins(
            35,
            30,
            35,
            30
        )

        layout.setSpacing(20)

        title = QLabel(
            "GPU Performance"
        )

        title.setObjectName(
            "page_title"
        )

        subtitle = QLabel(
            "Graphics processor telemetry"
        )

        subtitle.setObjectName(
            "subtitle"
        )

        layout.addWidget(title)
        layout.addWidget(subtitle)

        gpu_card = QFrame()
        gpu_card.setObjectName(
            "info_card"
        )

        card_layout = QVBoxLayout(
            gpu_card
        )

        self.gpu_labels = {}

        information = [
            "GPU Utilization",
            "Temperature",
            "VRAM",
            "GPU Clock",
            "Power",
            "Fan Speed",
        ]

        for item in information:

            label = QLabel(
                f"{item}: --"
            )

            label.setObjectName(
                "info_label"
            )

            self.gpu_labels[item] = label

            card_layout.addWidget(
                label
            )

        layout.addWidget(
            gpu_card
        )

        layout.addStretch()

        return page

    # ==================================================
    # KPI CARD
    # ==================================================

    def create_card(
        self,
        title,
        value_label,
        description
    ):

        card = QFrame()

        card.setObjectName(
            "kpi_card"
        )

        layout = QVBoxLayout(
            card
        )

        layout.setContentsMargins(
            20,
            18,
            20,
            18
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

    # ==================================================
    # SYSTEM DATA UPDATE
    # ==================================================

    def update_system_data(self):

        # ==============================================
        # CPU
        # ==============================================

        cpu_usage = psutil.cpu_percent(
            interval=None
        )

        # ==============================================
        # RAM
        # ==============================================

        memory = psutil.virtual_memory()

        ram_usage = memory.percent

        # ==============================================
        # UPDATE KPI CARDS
        # ==============================================

        self.cpu_value.setText(
            f"{cpu_usage:.1f}%"
        )

        self.ram_value.setText(
            f"{ram_usage:.1f}%"
        )

        # ==============================================
        # UPDATE MEMORY PAGE
        # ==============================================

        total_gb = memory.total / (
            1024 ** 3
        )

        used_gb = memory.used / (
            1024 ** 3
        )

        available_gb = memory.available / (
            1024 ** 3
        )

        self.memory_info.setText(
            f"Used: {used_gb:.2f} GB    |    "
            f"Available: {available_gb:.2f} GB    |    "
            f"Total: {total_gb:.2f} GB    |    "
            f"Usage: {ram_usage:.1f}%"
        )

        # ==============================================
        # UPDATE HISTORY
        # ==============================================

        self.cpu_data.append(
            cpu_usage
        )

        self.ram_data.append(
            ram_usage
        )

        self.cpu_data = (
            self.cpu_data[-self.max_points:]
        )

        self.ram_data = (
            self.ram_data[-self.max_points:]
        )

        # ==============================================
        # UPDATE GRAPHS
        # ==============================================

        self.cpu_curve.setData(
            self.cpu_data
        )

        self.ram_curve.setData(
            self.ram_data
        )

        self.memory_curve.setData(
            self.ram_data
        )

        # ==============================================
        # STATUS
        # ==============================================

        self.status.setText(
            "●  MONITORING ACTIVE"
        )

    # ==================================================
    # CLOSE APPLICATION
    # ==================================================

    def closeEvent(self, event):

        self.timer.stop()

        event.accept()


# ======================================================
# APPLICATION START
# ======================================================

if __name__ == "__main__":

    app = QApplication(
        sys.argv
    )

    app.setStyleSheet("""

        QMainWindow {
            background-color: #0d1117;
        }

        QWidget {
            background-color: #0d1117;
            color: #e6edf3;
            font-family: "Segoe UI";
        }

        #sidebar {
            background-color: #111820;
            border-right: 1px solid #27313d;
        }

        #logo {
            color: #ffffff;
            font-size: 17px;
            font-weight: bold;
        }

        #nav_button {
            background-color: transparent;
            color: #9da7b3;
            border: none;
            border-radius: 8px;
            padding: 13px;
            text-align: left;
            font-size: 14px;
        }

        #nav_button:hover {
            background-color: #1b2530;
            color: #ffffff;
        }

        #nav_button[active="true"] {
            background-color: #243241;
            color: #ffffff;
            font-weight: bold;
        }

        #status {
            color: #55d187;
            font-size: 12px;
            padding: 8px;
        }

        #page_title {
            font-size: 28px;
            font-weight: bold;
            color: #ffffff;
        }

        #subtitle {
            color: #8b949e;
            font-size: 14px;
        }

        #kpi_card {
            background-color: #161d26;
            border: 1px solid #27313d;
            border-radius: 12px;
            min-height: 125px;
        }

        #card_title {
            color: #8b949e;
            font-size: 13px;
            font-weight: bold;
        }

        #card_value {
            color: #ffffff;
            font-size: 30px;
            font-weight: bold;
        }

        #card_description {
            color: #6e7781;
            font-size: 12px;
        }

        #graph_placeholder {
            background-color: #161d26;
            border: 1px solid #27313d;
            border-radius: 12px;
        }

        #section_title {
            color: #ffffff;
            font-size: 15px;
            font-weight: bold;
        }

        #info_card {
            background-color: #161d26;
            border: 1px solid #27313d;
            border-radius: 12px;
        }

        #info_label {
            color: #c9d1d9;
            font-size: 15px;
            padding: 8px;
        }

        #memory_info {
            color: #c9d1d9;
            font-size: 15px;
            padding: 10px;
        }

    """)

    window = ResourceMonitor()

    window.show()

    sys.exit(
        app.exec()
    )