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
from system_config import SystemConfigPage
from gpu_page import GPUPerformancePage
from process_manager import ProcessManagerPage
from network_disk_page import NetworkDiskPage
from report_exporter import export_system_report
from mini_overlay import MiniOverlayWidget
from benchmark_page import BenchmarkPage
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QComboBox, QMessageBox, QFileDialog
import psutil


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("System Resource Monitor")
        self.resize(1400, 850)

        # Mini overlay instance
        self.overlay_widget = MiniOverlayWidget()
        self._active_page_index = None

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

        self.net_disk_button = QPushButton(
            "Network & Disk I/O"
        )

        self.process_button = QPushButton(
            "Process Manager"
        )

        self.benchmark_button = QPushButton(
            "Benchmark & Stress Test"
        )

        buttons = [
            self.dashboard_button,
            self.memory_button,
            self.system_button,
            self.gpu_button,
            self.net_disk_button,
            self.process_button,
            self.benchmark_button,
        ]

        for button in buttons:
            button.setObjectName("nav_button")
            sidebar_layout.addWidget(button)

        sidebar_layout.addSpacing(15)

        # Quick Export Button
        self.export_btn = QPushButton("Export Diagnostic Report")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #0d0d0d;
                color: #ff8f00;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff8f00;
                color: #000000;
            }
        """)
        self.export_btn.clicked.connect(self.trigger_export_report)
        sidebar_layout.addWidget(self.export_btn)

        # Mini Overlay Toggle Button
        self.overlay_btn = QPushButton("Toggle Floating Overlay")
        self.overlay_btn.setStyleSheet("""
            QPushButton {
                background-color: #0d0d0d;
                color: #26a69a;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #26a69a;
                color: #000000;
            }
        """)
        self.overlay_btn.clicked.connect(self.toggle_overlay)
        sidebar_layout.addWidget(self.overlay_btn)

        sidebar_layout.addSpacing(10)

        # Refresh Speed Selector
        speed_lbl = QLabel("REFRESH SPEED:")
        speed_lbl.setStyleSheet("color: #777777; font-size: 9px; font-weight: bold; letter-spacing: 1px;")
        sidebar_layout.addWidget(speed_lbl)

        self.speed_combo = QComboBox()
        self.speed_combo.addItem("Task Manager Speed (500ms)", 500)
        self.speed_combo.addItem("Ultra Fast (250ms)", 250)
        self.speed_combo.addItem("Normal Speed (1000ms)", 1000)
        self.speed_combo.addItem("Eco Saver (2000ms)", 2000)
        self.speed_combo.setCurrentIndex(3)
        self.speed_combo.setStyleSheet("""
            QComboBox {
                background-color: #0d0d0d;
                color: #dddddd;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 6px;
                font-size: 11px;
                font-weight: bold;
            }
            QComboBox QAbstractItemView {
                background-color: #111111;
                color: #ffffff;
                selection-background-color: #ff8f00;
            }
        """)
        self.speed_combo.currentIndexChanged.connect(self.on_speed_changed)
        sidebar_layout.addWidget(self.speed_combo)

        sidebar_layout.addStretch()

        # Alert & Monitoring Status
        self.status = QLabel("●  MONITORING ACTIVE")
        self.status.setObjectName("status")
        sidebar_layout.addWidget(self.status)

        # Alert Check Timer
        self.alert_timer = QTimer(self)
        self.alert_timer.setInterval(2000)
        self.alert_timer.timeout.connect(self.check_resource_alerts)
        self.alert_timer.start()

        # =================================================
        # PAGE STACK
        # =================================================

        self.pages = QStackedWidget()

        # =================================================
        # YOUR PAGES
        # =================================================

        self.dashboard_page = DashboardPage()

        self.memory_page = MemoryPage()

        self.system_page = SystemConfigPage()

        self.gpu_page = GPUPerformancePage()

        self.net_disk_page = NetworkDiskPage()

        self.process_page = ProcessManagerPage()

        self.benchmark_page = BenchmarkPage()

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

        self.pages.addWidget(
            self.net_disk_page
        )

        self.pages.addWidget(
            self.process_page
        )

        self.pages.addWidget(
            self.benchmark_page
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

        self.net_disk_button.clicked.connect(
            lambda: self.change_page(4)
        )

        self.process_button.clicked.connect(
            lambda: self.change_page(5)
        )

        self.benchmark_button.clicked.connect(
            lambda: self.change_page(6)
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

        cockpit_activated = (
            index == 0
            and self._active_page_index != 0
        )

        self.pages.setCurrentIndex(
            index
        )

        if cockpit_activated:
            self.dashboard_page.activate_cockpit()

        self._active_page_index = index

        for i in range(self.pages.count()):
            page_widget = self.pages.widget(i)
            if i == index:
                if hasattr(page_widget, "resume_timer"):
                    page_widget.resume_timer()
            else:
                if hasattr(page_widget, "pause_timer"):
                    page_widget.pause_timer()

        buttons = [
            self.dashboard_button,
            self.memory_button,
            self.system_button,
            self.gpu_button,
            self.net_disk_button,
            self.process_button,
            self.benchmark_button,
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

    def on_speed_changed(self, index):
        ms = self.speed_combo.itemData(index)
        if not ms:
            return
        for i in range(self.pages.count()):
            page_widget = self.pages.widget(i)
            if hasattr(page_widget, "set_refresh_interval"):
                page_widget.set_refresh_interval(ms)
        if hasattr(self.overlay_widget, "set_refresh_interval"):
            self.overlay_widget.set_refresh_interval(max(200, ms // 2))

    def toggle_overlay(self):
        if self.overlay_widget.isVisible():
            self.overlay_widget.hide()
        else:
            self.overlay_widget.show()

    def trigger_export_report(self):
        try:
            html_f, json_f = export_system_report()
            QMessageBox.information(
                self,
                "Report Generated",
                f"System Diagnostic Report successfully generated!\n\nHTML: {html_f}\nJSON: {json_f}\n\nOpening report in browser..."
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to generate report: {e}")

    def check_resource_alerts(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent

            if cpu > 85:
                self.status.setText(f"HIGH CPU: {cpu:.0f}%")
                self.status.setStyleSheet("color: #e53935; font-weight: bold; font-size: 10px;")
            elif ram > 90:
                self.status.setText(f"HIGH RAM: {ram:.0f}%")
                self.status.setStyleSheet("color: #e53935; font-weight: bold; font-size: 10px;")
            else:
                self.status.setText("●  MONITORING ACTIVE")
                self.status.setStyleSheet("color: #55d66f; font-weight: bold; font-size: 10px;")
        except Exception:
            pass

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


            /* =================================================
           PERFORMANCE COCKPIT
           ================================================= */

        #cockpit_title {
            color: #eeeeee;
            font-size: 24px;
            font-weight: bold;
            letter-spacing: 2px;
            background: transparent;
            border: none;
            font-family: "Orbitron", "Segoe UI", sans-serif;
        }

        #cockpit_subtitle {
            color: #555555;
            font-size: 9px;
            letter-spacing: 2px;
            background: transparent;
            border: none;
        }

        #cockpit_status {
            color: #55d66f;
            font-size: 10px;
            font-weight: bold;
            background: transparent;
            border: none;
        }

        #cockpit_info {
            background-color: #090909;
            border: 1px solid #242424;
            border-radius: 2px;
        }

        #gpu_name {
            color: #888888;
            font-size: 10px;
            background: transparent;
            border: none;
        }

        #telemetry_value {
            color: #cccccc;
            font-size: 10px;
            font-weight: bold;
            background: transparent;
            border: none;
        }

        #telemetry_title {
            color: #aaaaaa;
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 1px;
            background: transparent;
            border: none;
        }

        #telemetry_label {
            color: #555555;
            font-size: 9px;
            font-weight: bold;
            background: transparent;
            border: none;
        }

    /* =====================================================
       GLOBAL
       ===================================================== */

    QMainWindow {
        background-color: #050505;
    }

    QWidget {
        background-color: #050505;
        color: #d8d8d8;
        font-family: "Orbitron", "Segoe UI", sans-serif;
    }

    #cockpit_title,
    #page_title,
    #section_title,
    #telemetry_title,
    #telemetry_label,
    #logo {
        font-family: "Orbitron", "Segoe UI", sans-serif;
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
        font-family: "Orbitron", "Segoe UI", sans-serif;
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
        font-family: "Orbitron", "Segoe UI", sans-serif;
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

    #application_row[active="true"] {
        background-color: #1b1b1b;
        border: 1px solid #666666;
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
            background-color: #0b0b0b;
            border: 1px solid #303030;
            border-radius: 2px;
            padding: 5px 8px;
            color: #cccccc;
            min-width: 120px;
        }

        QComboBox:hover {
            border: 1px solid #666666;
        }

        QComboBox QAbstractItemView {
            background-color: #0b0b0b;
            color: #dddddd;
            selection-background-color: #321111;
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
