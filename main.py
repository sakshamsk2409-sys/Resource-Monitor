import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
)

from dashboard import DashboardPage
from memory import MemoryPage


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            "System Resource Monitor"
        )

        self.resize(
            1400,
            850
        )

        self.setup_ui()

    # =================================================
    # MAIN UI
    # =================================================

    def setup_ui(self):

        central = QWidget()

        self.setCentralWidget(
            central
        )

        main_layout = QHBoxLayout(
            central
        )

        main_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        main_layout.setSpacing(
            0
        )

        # =================================================
        # SIDEBAR
        # =================================================

        sidebar = QFrame()

        sidebar.setObjectName(
            "sidebar"
        )

        sidebar.setFixedWidth(
            240
        )

        sidebar_layout = QVBoxLayout(
            sidebar
        )

        sidebar_layout.setContentsMargins(
            20,
            25,
            20,
            25
        )

        sidebar_layout.setSpacing(
            10
        )

        # Logo
        logo = QLabel(
            "SYSTEM\nRESOURCE MONITOR"
        )

        logo.setObjectName(
            "logo"
        )

        logo.setAlignment(
            Qt.AlignCenter
        )

        sidebar_layout.addWidget(
            logo
        )

        sidebar_layout.addSpacing(
            30
        )

        # Navigation buttons
        self.dashboard_button = QPushButton(
            "Dashboard"
        )

        self.memory_button = QPushButton(
            "Memory"
        )

        self.system_button = QPushButton(
            "System Configuration"
        )

        self.gpu_button = QPushButton(
            "GPU Performance"
        )

        buttons = [
            self.dashboard_button,
            self.memory_button,
            self.system_button,
            self.gpu_button,
        ]

        for button in buttons:

            button.setObjectName(
                "nav_button"
            )

            sidebar_layout.addWidget(
                button
            )

        sidebar_layout.addStretch()

        # Status
        status = QLabel(
            "●  MONITORING ACTIVE"
        )

        status.setObjectName(
            "status"
        )

        sidebar_layout.addWidget(
            status
        )

        # =================================================
        # PAGE STACK
        # =================================================

        self.pages = QStackedWidget()

        # Your pages
        self.dashboard_page = DashboardPage()

        self.memory_page = MemoryPage()

        # Temporary pages for teammates
        self.system_page = self.create_placeholder(
            "System Configuration"
        )

        self.gpu_page = self.create_placeholder(
            "GPU Performance"
        )

        # Add pages
        self.pages.addWidget(
            self.dashboard_page
        )

        self.pages.addWidget(
            self.memory_page
        )

        self.pages.addWidget(
            self.system_page
        )

        self.pages.addWidget(
            self.gpu_page
        )

        # =================================================
        # NAVIGATION
        # =================================================

        self.dashboard_button.clicked.connect(
            lambda: self.change_page(0)
        )

        self.memory_button.clicked.connect(
            lambda: self.change_page(1)
        )

        self.system_button.clicked.connect(
            lambda: self.change_page(2)
        )

        self.gpu_button.clicked.connect(
            lambda: self.change_page(3)
        )

        # Add sidebar + pages
        main_layout.addWidget(
            sidebar
        )

        main_layout.addWidget(
            self.pages
        )

        # Start on Dashboard
        self.change_page(0)

    # =================================================
    # PAGE CHANGE
    # =================================================

    def change_page(self, index):

        self.pages.setCurrentIndex(
            index
        )

        buttons = [
            self.dashboard_button,
            self.memory_button,
            self.system_button,
            self.gpu_button,
        ]

        # Remove active state
        for button in buttons:

            button.setProperty(
                "active",
                False
            )

            button.style().unpolish(
                button
            )

            button.style().polish(
                button
            )

        # Add active state
        active_button = buttons[index]

        active_button.setProperty(
            "active",
            True
        )

        active_button.style().unpolish(
            active_button
        )

        active_button.style().polish(
            active_button
        )

    # =================================================
    # PLACEHOLDER PAGE
    # =================================================

    def create_placeholder(self, title):

        page = QWidget()

        layout = QVBoxLayout(
            page
        )

        layout.setContentsMargins(
            35,
            30,
            35,
            30
        )

        label = QLabel(
            title
        )

        label.setObjectName(
            "page_title"
        )

        layout.addWidget(
            label
        )

        layout.addStretch()

        return page


# =====================================================
# APPLICATION
# =====================================================

if __name__ == "__main__":

    app = QApplication(
        sys.argv
    )

    # =================================================
    # GLOBAL STYLE
    # =================================================

    app.setStyleSheet("""

        QMainWindow {
            background-color: #0d1117;
        }

        QWidget {
            background-color: #0d1117;
            color: #e6edf3;
            font-family: "Segoe UI";
        }

        /* SIDEBAR */

        #sidebar {
            background-color: #111820;
            border-right: 1px solid #27313d;
        }

        #logo {
            color: #ffffff;
            font-size: 17px;
            font-weight: bold;
        }

        /* NAVIGATION */

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

        /* STATUS */

        #status {
            color: #55d187;
            font-size: 12px;
            padding: 8px;
        }

        /* PAGE */

        #page_title {
            font-size: 28px;
            font-weight: bold;
            color: #ffffff;
        }

        #subtitle {
            color: #8b949e;
            font-size: 14px;
        }

        /* CARDS */

        #metric_card {
            background-color: #161d26;
            border: 1px solid #27313d;
            border-radius: 12px;
            min-height: 120px;
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

        /* GRAPH */

        #graph_container {
            background-color: #161d26;
            border: 1px solid #27313d;
            border-radius: 12px;
        }

        #section_title {
            color: #ffffff;
            font-size: 14px;
            font-weight: bold;
        }

        /* MEMORY */

        #memory_value {
            color: #ffffff;
            font-size: 18px;
            padding: 10px;
        }

        /* DROPDOWN */

        QComboBox {
            background-color: #161d26;
            border: 1px solid #27313d;
            border-radius: 6px;
            padding: 7px 10px;
            color: #ffffff;
            min-width: 120px;
        }

        QComboBox:hover {
            border: 1px solid #4a5562;
        }

        QComboBox QAbstractItemView {
            background-color: #161d26;
            color: #ffffff;
            selection-background-color: #243241;
        }

    """)

    window = MainWindow()

    window.show()

    sys.exit(
        app.exec()
    )