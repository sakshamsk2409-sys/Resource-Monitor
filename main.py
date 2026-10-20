import sys
import subprocess
import importlib.util
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)


def _auto_install_dependencies():
    deps = [
        "PySide6>=6.7,<7",
        "psutil>=6.0,<8",
        "pyqtgraph>=0.13,<1",
        "matplotlib>=3.9,<4",
        "numpy>=1.26,<3",
        "pandas>=2.2,<4",
        "nvidia-ml-py>=12.0,<14",
    ]

    module_map = {
        "nvidia-ml-py": "pynvml",
    }

    missing = []
    for dep in deps:
        pkg_name = dep.split(">=")[0].split("==")[0].split("<")[0]
        mod_name = module_map.get(pkg_name, pkg_name)
        if importlib.util.find_spec(mod_name) is None:
            missing.append(dep)

    if not missing:
        return

    print("Missing dependencies detected. Installing...")

    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
        subprocess.check_call(["uv", "pip", "install", "--python", sys.executable] + missing)
    except (FileNotFoundError, subprocess.CalledProcessError):
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
        except subprocess.CalledProcessError:
            print("Auto-install failed. Please run manually:")
            print(f"  uv pip install --python {sys.executable} {' '.join(missing)}")
            print("or:")
            print(f"  python -m pip install {' '.join(missing)}")
            sys.exit(1)

    print("Dependencies installed successfully.")


_auto_install_dependencies()


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
from network_disk_page import NetworkDiskPage
from report_exporter import export_system_report
from mini_overlay import MiniOverlayWidget
from benchmark_page import BenchmarkPage
from analytics_page import AnalyticsPage
from telemetry_logger import TelemetryLogger
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

        self.benchmark_button = QPushButton(
            "Benchmark & Stress Test"
        )

        self.analytics_button = QPushButton(
            "Analytics & Telemetry"
        )

        buttons = [
            self.dashboard_button,
            self.memory_button,
            self.system_button,
            self.gpu_button,
            self.net_disk_button,
            self.benchmark_button,
            self.analytics_button,
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

        sidebar_layout.addSpacing(12)

        # =================================================
        # TELEMETRY CSV RECORDER CONTROLS PANEL
        # =================================================
        self.setup_logging_panel(sidebar_layout)

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

        self.benchmark_page = BenchmarkPage()

        self.analytics_page = AnalyticsPage()

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
            self.benchmark_page
        )

        self.pages.addWidget(
            self.analytics_page
        )

        # =================================================
        # TELEMETRY LOGGER INITIALIZATION
        # =================================================
        self.logger = TelemetryLogger(
            temperature_provider=self.dashboard_page.get_cpu_temperature,
            cpu_provider=self.dashboard_page.get_cpu_load,
            parent=self
        )
        self.logger.status_changed.connect(self.on_logger_status_changed)
        self.logger.stats_updated.connect(self.on_logger_stats_updated)
        self.logger.error_occurred.connect(self.on_logger_error)

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

        self.benchmark_button.clicked.connect(
            lambda: self.change_page(5)
        )

        self.analytics_button.clicked.connect(
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
            self.benchmark_button,
            self.analytics_button,
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
            if hasattr(self, 'dashboard_page') and hasattr(self.dashboard_page, 'get_cpu_load'):
                cpu = self.dashboard_page.get_cpu_load()
            else:
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

    # =================================================
    # TELEMETRY LOGGING CONTROLS & HANDLERS
    # =================================================

    def setup_logging_panel(self, sidebar_layout):
        import os
        panel = QFrame()
        panel.setObjectName("recorder_card")
        panel.setStyleSheet("""
            #recorder_card {
                background-color: #0b0b0b;
                border: 1px solid #282828;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Title & Status badge row
        top_row = QHBoxLayout()
        header_lbl = QLabel("TELEMETRY RECORDER")
        header_lbl.setStyleSheet("color: #777777; font-size: 9px; font-weight: bold; letter-spacing: 0.8px;")
        top_row.addWidget(header_lbl)

        self.log_status_badge = QLabel("● IDLE")
        self.log_status_badge.setStyleSheet("color: #888888; font-size: 9px; font-weight: bold;")
        top_row.addWidget(self.log_status_badge)
        layout.addLayout(top_row)

        # Interval combo
        int_row = QHBoxLayout()
        int_lbl = QLabel("INTERVAL:")
        int_lbl.setStyleSheet("color: #666666; font-size: 9px; font-weight: bold;")
        int_row.addWidget(int_lbl)

        self.log_interval_combo = QComboBox()
        self.log_interval_combo.addItem("1.0s (Default)", 1.0)
        self.log_interval_combo.addItem("0.5s (2 Hz)", 0.5)
        self.log_interval_combo.addItem("0.25s (4 Hz)", 0.25)
        self.log_interval_combo.addItem("2.0s (Eco)", 2.0)
        self.log_interval_combo.addItem("5.0s (Slow)", 5.0)
        self.log_interval_combo.setCurrentIndex(0)
        self.log_interval_combo.setStyleSheet("""
            QComboBox {
                background-color: #121212;
                color: #cccccc;
                border: 1px solid #333333;
                border-radius: 3px;
                padding: 3px 6px;
                font-size: 10px;
            }
        """)
        self.log_interval_combo.currentIndexChanged.connect(self.on_logging_interval_changed)
        int_row.addWidget(self.log_interval_combo)
        layout.addLayout(int_row)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.log_start_btn = QPushButton("Start Logging")
        self.log_start_btn.setStyleSheet("""
            QPushButton {
                background-color: #153315;
                color: #55d66f;
                border: 1px solid #2d662d;
                border-radius: 3px;
                padding: 6px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1e4a1e;
            }
        """)
        self.log_start_btn.clicked.connect(self.toggle_logging)
        btn_row.addWidget(self.log_start_btn)

        self.log_pause_btn = QPushButton("Pause")
        self.log_pause_btn.setEnabled(False)
        self.log_pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #222211;
                color: #ffaa00;
                border: 1px solid #444422;
                border-radius: 3px;
                padding: 6px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #33331a;
            }
            QPushButton:disabled {
                background-color: #111111;
                color: #444444;
                border: 1px solid #222222;
            }
        """)
        self.log_pause_btn.clicked.connect(self.toggle_pause_resume)
        btn_row.addWidget(self.log_pause_btn)
        layout.addLayout(btn_row)

        # Stats
        stats_row = QHBoxLayout()
        self.log_recs_lbl = QLabel("Records: 0")
        self.log_recs_lbl.setStyleSheet("color: #aaaaaa; font-size: 9px;")
        self.log_time_lbl = QLabel("Time: 00:00:00")
        self.log_time_lbl.setStyleSheet("color: #aaaaaa; font-size: 9px;")
        stats_row.addWidget(self.log_recs_lbl)
        stats_row.addStretch()
        stats_row.addWidget(self.log_time_lbl)
        layout.addLayout(stats_row)

        # File path
        self.log_file_lbl = QLabel("File: [No Log Active]")
        self.log_file_lbl.setStyleSheet("color: #555555; font-size: 8px;")
        self.log_file_lbl.setToolTip("Target CSV destination (data/logs/)")
        layout.addWidget(self.log_file_lbl)

        sidebar_layout.addWidget(panel)

    def toggle_logging(self):
        import os
        if not hasattr(self, "logger") or self.logger is None:
            return

        if self.logger.is_recording or self.logger.is_paused:
            path = self.logger.file_path
            count = self.logger.record_count
            self.logger.stop_logging()

            reply = QMessageBox.question(
                self,
                "Logging Complete",
                f"Telemetry recording saved successfully!\n\n"
                f"File: {path}\nSamples: {count:,}\n\n"
                f"Would you like to analyze this recording in the Analytics tab now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply == QMessageBox.Yes:
                self.change_page(6)
                if hasattr(self, "analytics_page"):
                    self.analytics_page.load_dataset(path)
        else:
            interval = self.log_interval_combo.currentData() or 1.0
            out_file = self.logger.start_logging(interval_sec=interval)
            if out_file:
                fname = os.path.basename(out_file)
                self.log_file_lbl.setText(f"File: {fname}")
                self.log_file_lbl.setToolTip(out_file)

    def toggle_pause_resume(self):
        if not hasattr(self, "logger") or self.logger is None:
            return
        if self.logger.is_recording:
            self.logger.pause_logging()
        elif self.logger.is_paused:
            self.logger.resume_logging()

    def on_logging_interval_changed(self, index):
        sec = self.log_interval_combo.itemData(index)
        if sec and hasattr(self, "logger") and self.logger is not None:
            self.logger.set_sampling_interval(sec)

    def on_logger_status_changed(self, status):
        if status == TelemetryLogger.STATUS_RECORDING:
            self.log_status_badge.setText("● REC")
            self.log_status_badge.setStyleSheet("color: #e53935; font-size: 9px; font-weight: bold;")
            self.log_start_btn.setText("Stop Logging")
            self.log_start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #331515;
                    color: #ef5350;
                    border: 1px solid #662d2d;
                    border-radius: 3px;
                    padding: 6px;
                    font-size: 10px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #4a1e1e; }
            """)
            self.log_pause_btn.setEnabled(True)
            self.log_pause_btn.setText("Pause")
        elif status == TelemetryLogger.STATUS_PAUSED:
            self.log_status_badge.setText("⏸ PAUSED")
            self.log_status_badge.setStyleSheet("color: #ffaa00; font-size: 9px; font-weight: bold;")
            self.log_start_btn.setText("Stop Logging")
            self.log_pause_btn.setEnabled(True)
            self.log_pause_btn.setText("Resume")
        else:
            self.log_status_badge.setText("● IDLE")
            self.log_status_badge.setStyleSheet("color: #888888; font-size: 9px; font-weight: bold;")
            self.log_start_btn.setText("Start Logging")
            self.log_start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #153315;
                    color: #55d66f;
                    border: 1px solid #2d662d;
                    border-radius: 3px;
                    padding: 6px;
                    font-size: 10px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #1e4a1e; }
            """)
            self.log_pause_btn.setEnabled(False)
            self.log_pause_btn.setText("Pause")

    def on_logger_stats_updated(self, count, elapsed, path):
        import os
        hrs = int(elapsed) // 3600
        mins = (int(elapsed) % 3600) // 60
        secs = int(elapsed) % 60
        self.log_time_lbl.setText(f"Time: {hrs:02d}:{mins:02d}:{secs:02d}")
        self.log_recs_lbl.setText(f"Records: {count:,}")
        if path:
            self.log_file_lbl.setText(f"File: {os.path.basename(path)}")
            self.log_file_lbl.setToolTip(path)

    def on_logger_error(self, err_msg):
        QMessageBox.warning(self, "Telemetry Logger Error", err_msg)

    def closeEvent(self, event):
        """Clean shutdown: flush CSV telemetry, stop timers, terminate background monitors."""
        if hasattr(self, "logger") and self.logger is not None:
            if self.logger.is_recording or self.logger.is_paused:
                self.logger.stop_logging()

        if hasattr(self, "alert_timer") and self.alert_timer.isActive():
            self.alert_timer.stop()

        for i in range(self.pages.count()):
            page_widget = self.pages.widget(i)
            if hasattr(page_widget, "closeEvent"):
                try:
                    page_widget.close()
                except Exception:
                    pass

        event.accept()

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
