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

        # =================================================
        # LOGO
        # =================================================

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

        # =================================================
        # NAVIGATION BUTTONS
        # =================================================

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

        # =================================================
        # STATUS
        # =================================================

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

        # =================================================
        # YOUR PAGES
        # =================================================

        self.dashboard_page = DashboardPage()

        self.memory_page = MemoryPage()

        # =================================================
        # TEMPORARY TEAMMATE PAGES
        # =================================================

        self.system_page = self.create_placeholder(
            "System Configuration"
        )

        self.gpu_page = self.create_placeholder(
            "GPU Performance"
        )

        # =================================================
        # ADD PAGES
        # =================================================

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
        # NAVIGATION CONNECTIONS
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

        # =================================================
        # ADD SIDEBAR + PAGES
        # =================================================

        main_layout.addWidget(
            sidebar
        )

        main_layout.addWidget(
            self.pages
        )

        # =================================================
        # START ON DASHBOARD
        # =================================================

        self.change_page(
            0
        )

    # =================================================
    # PAGE CHANGE
    # =================================================

    def change_page(
        self,
        index
    ):

        self.pages.setCurrentIndex(
            index
        )

        buttons = [
            self.dashboard_button,
            self.memory_button,
            self.system_button,
            self.gpu_button,
        ]

        # -------------------------------------------------
        # REMOVE ACTIVE STATE
        # -------------------------------------------------

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

        # -------------------------------------------------
        # SET ACTIVE STATE
        # -------------------------------------------------

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

    def create_placeholder(
        self,
        title
    ):

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

        /* =================================================
           MAIN WINDOW
           ================================================= */

        QMainWindow {
            background-color: #080d14;
        }

        QWidget {
            background-color: #080d14;
            color: #e6edf3;
            font-family: "Segoe UI";
        }


        /* =================================================
           SIDEBAR
           ================================================= */

        #sidebar {
            background-color: #0b121c;
            border-right: 1px solid #1c2b3d;
        }


        /* =================================================
           LOGO
           ================================================= */

        #logo {
            color: #ffffff;
            font-size: 17px;
            font-weight: bold;
            background: transparent;
            border: none;
        }


        /* =================================================
           NAVIGATION
           ================================================= */

        #nav_button {
            background-color: transparent;
            color: #7f91a8;
            border: none;
            border-radius: 9px;
            padding: 13px;
            text-align: left;
            font-size: 14px;
        }

        #nav_button:hover {
            background-color: #142235;
            color: #ffffff;
        }

        #nav_button[active="true"] {
            background-color: #172b40;
            color: #ffffff;
            font-weight: bold;
            border-left: 3px solid #00aaff;
        }


        /* =================================================
           STATUS
           ================================================= */

        #status {
            color: #39ff88;
            font-size: 12px;
            padding: 8px;
            background: transparent;
            border: none;
        }


        /* =================================================
           PAGE TITLE
           ================================================= */

        #page_title {
            font-size: 28px;
            font-weight: bold;
            color: #ffffff;
            background: transparent;
            border: none;
        }

        #dashboard_subtitle {
            color: #6e829b;
            font-size: 13px;
            background: transparent;
            border: none;
        }

        #subtitle {
            color: #6e829b;
            font-size: 13px;
            background: transparent;
            border: none;
        }


        /* =================================================
           CONTROLS
           ================================================= */

        #controls_frame {
            background-color: #0d1520;
            border: 1px solid #1d3045;
            border-radius: 8px;
        }

        #control_label {
            color: #7f91a8;
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 1px;
            background: transparent;
            border: none;
        }


        /* =================================================
           COMBO BOX
           ================================================= */

        QComboBox {
            background-color: #101a27;
            border: 1px solid #263c54;
            border-radius: 6px;
            padding: 7px 10px;
            color: #dce7f2;
            min-width: 125px;
        }

        QComboBox:hover {
            border: 1px solid #00aaff;
        }

        QComboBox QAbstractItemView {
            background-color: #101a27;
            color: #ffffff;
            selection-background-color: #173653;
        }


        /* =================================================
           TELEMETRY GRAPH
           ================================================= */

        #telemetry_frame {
            background-color: #0b111a;
            border: 1px solid #16405c;
            border-radius: 14px;
        }

        #graph_title {
            color: #ffffff;
            font-size: 14px;
            font-weight: bold;
            background: transparent;
            border: none;
        }

        #live_label {
            color: #39ff88;
            font-size: 11px;
            font-weight: bold;
            background: transparent;
            border: none;
        }


        /* =================================================
           SECTION TITLES
           ================================================= */

        #section_title {
            color: #ffffff;
            font-size: 14px;
            font-weight: bold;
            background: transparent;
            border: none;
        }


        /* =================================================
           MEMORY
           ================================================= */

        #graph_container {
            background-color: #0b111a;
            border: 1px solid #1c3045;
            border-radius: 12px;
        }

        #memory_value {
            color: #ffffff;
            font-size: 18px;
            padding: 10px;
            background: transparent;
            border: none;
        }

    """)

    # =================================================
    # CREATE WINDOW
    # =================================================

    window = MainWindow()

    # =================================================
    # SHOW WINDOW
    # =================================================

    window.show()

    # =================================================
    # START APPLICATION
    # =================================================

    sys.exit(
        app.exec()
    )