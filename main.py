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

    /* =====================================================
       GLOBAL
       ===================================================== */

    QMainWindow {
        background-color: #050505;
    }

    QWidget {
        background-color: #050505;
        color: #d8d8d8;
        font-family: "Segoe UI";
    }


    /* =====================================================
       SIDEBAR
       ===================================================== */

    #sidebar {
        background-color: #080808;
        border-right: 1px solid #242424;
    }

    #logo {
        color: #eeeeee;
        font-size: 16px;
        font-weight: bold;
        background: transparent;
        border: none;
    }

    #nav_button {
        background-color: transparent;
        color: #777777;
        border: none;
        border-radius: 2px;
        padding: 12px;
        text-align: left;
        font-size: 13px;
    }

    #nav_button:hover {
        background-color: #151515;
        color: #dddddd;
    }

    #nav_button[active="true"] {
        background-color: #1a0b0b;
        color: #ffffff;
        border-left: 3px solid #d71920;
        font-weight: bold;
    }

    #status {
        color: #55d66f;
        font-size: 11px;
        padding: 8px;
        background: transparent;
        border: none;
    }


    /* =====================================================
       PAGE
       ===================================================== */

    #page_title {
        color: #f0f0f0;
        font-size: 26px;
        font-weight: bold;
        background: transparent;
        border: none;
    }

    #subtitle {
        color: #686868;
        font-size: 12px;
        background: transparent;
        border: none;
    }

    #dashboard_subtitle {
        color: #686868;
        font-size: 12px;
        background: transparent;
        border: none;
    }


    /* =====================================================
       MEMORY PANELS
       ===================================================== */

    #memory_panel {
        background-color: #090909;
        border: 1px solid #292929;
        border-radius: 3px;
    }

    #memory_panel:hover {
        border: 1px solid #3b3b3b;
    }


    /* =====================================================
       SECTION TITLES
       ===================================================== */

    #section_title {
        color: #dddddd;
        font-size: 12px;
        font-weight: bold;
        background: transparent;
        border: none;
    }


    /* =====================================================
       MEMORY STATISTICS
       ===================================================== */

    #memory_stat {
        color: #aaaaaa;
        font-size: 12px;
        font-weight: bold;
        background: transparent;
        border: none;
        padding: 5px 12px;
    }


    /* =====================================================
       APPLICATION ROW
       ===================================================== */

    #application_row {
        background-color: #0e0e0e;
        border: 1px solid #202020;
        border-radius: 2px;
    }

    #application_row:hover {
        background-color: #151515;
        border: 1px solid #3a3a3a;
    }

    #app_name {
        color: #d5d5d5;
        font-size: 11px;
        background: transparent;
        border: none;
    }

    #app_memory {
        color: #8a8a8a;
        font-size: 11px;
        background: transparent;
        border: none;
    }

    #app_percent {
        color: #eeeeee;
        font-size: 11px;
        font-weight: bold;
        background: transparent;
        border: none;
        min-width: 45px;
    }


    /* =====================================================
       SCROLLBAR
       ===================================================== */

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
    }

    QScrollBar::handle:vertical:hover {
        background: #666666;
    }


    /* =====================================================
       CONTROLS
       ===================================================== */

    #controls_frame {
        background-color: #090909;
        border: 1px solid #292929;
        border-radius: 2px;
    }

    #control_label {
        color: #777777;
        font-size: 10px;
        font-weight: bold;
        background: transparent;
        border: none;
    }

    QComboBox {
        background-color: #0d0d0d;
        border: 1px solid #333333;
        border-radius: 2px;
        padding: 6px 10px;
        color: #cccccc;
        min-width: 120px;
    }

    QComboBox:hover {
        border: 1px solid #777777;
    }

    QComboBox QAbstractItemView {
        background-color: #0c0c0c;
        color: #dddddd;
        selection-background-color: #301010;
        border: 1px solid #333333;
    }


    /* =====================================================
       TELEMETRY
       ===================================================== */

    #telemetry_frame {
        background-color: #070707;
        border: 1px solid #292929;
        border-radius: 3px;
    }

    #graph_title {
        color: #dddddd;
        font-size: 12px;
        font-weight: bold;
        background: transparent;
        border: none;
    }

    #live_label {
        color: #55d66f;
        font-size: 10px;
        font-weight: bold;
        background: transparent;
        border: none;
    }


    /* =====================================================
       GAMING KPI CARDS
       ===================================================== */

    #gaming_card {
        background-color: #090909;
        border: 1px solid #292929;
        border-radius: 3px;
    }

    #gaming_card:hover {
        background-color: #101010;
        border: 1px solid #444444;
    }

""")


    window = MainWindow()


    window.show()



    sys.exit(
        app.exec()
    )