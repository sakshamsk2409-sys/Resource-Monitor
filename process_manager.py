import psutil

from PySide6.QtCore import (
    Qt,
    QTimer,
    Signal,
    Slot,
    QObject,
    QThread,
)
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QAbstractItemView,
)

from dashboard import CarbonFiberBackground


# =========================================================
# BACKGROUND PROCESS WORKER
# =========================================================

class ProcessWorker(QObject):

    finished = Signal(list)
    scan_requested = Signal()

    def __init__(self):
        super().__init__()

        self.busy = False

        # IMPORTANT:
        # Signal is declared at class level above.
        self.scan_requested.connect(
            self.collect_processes
        )

    @Slot()
    def collect_processes(self):

        if self.busy:
            return

        self.busy = True

        new_data = []

        try:

            total_ram = psutil.virtual_memory().total

            for proc in psutil.process_iter(
                [
                    "pid",
                    "name",
                    "status",
                    "cpu_percent",
                    "memory_info",
                    "username",
                ]
            ):

                try:

                    info = proc.info

                    pid = info.get("pid")
                    name = (
                        info.get("name")
                        or "N/A"
                    )

                    status = (
                        info.get("status")
                        or "N/A"
                    )

                    # -------------------------
                    # CPU
                    # -------------------------

                    try:

                        cpu = proc.cpu_percent(
                            interval=None
                        )

                    except Exception:

                        cpu = 0.0

                    # -------------------------
                    # MEMORY
                    # -------------------------

                    try:

                        mem_info = info.get(
                            "memory_info"
                        )

                        if mem_info:

                            rss = mem_info.rss

                            rss_mb = (
                                rss
                                / (1024 * 1024)
                            )

                            mem_pct = (
                                rss
                                / total_ram
                                * 100
                                if total_ram
                                else 0.0
                            )

                        else:

                            rss_mb = 0.0
                            mem_pct = 0.0

                    except Exception:

                        rss_mb = 0.0
                        mem_pct = 0.0

                    # -------------------------
                    # USER
                    # -------------------------

                    username = (
                        info.get("username")
                        or "System"
                    )

                    new_data.append(
                        {
                            "pid": pid,
                            "name": name,
                            "status": status,
                            "cpu": cpu,
                            "rss_mb": rss_mb,
                            "mem_pct": mem_pct,
                            "user": username,
                        }
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

        finally:

            self.busy = False

        self.finished.emit(
            new_data
        )


# =========================================================
# PROCESS MANAGER PAGE
# =========================================================

class ProcessManagerPage(
    CarbonFiberBackground
):

    def __init__(
        self,
        parent=None
    ):

        super().__init__(parent)

        self.processes_data = []

        self.scan_pending = False

        self.setup_ui()

        # =================================================
        # WORKER THREAD
        # =================================================

        self.worker_thread = QThread(
            self
        )

        self.worker = ProcessWorker()

        self.worker.moveToThread(
            self.worker_thread
        )

        self.worker.finished.connect(
            self.process_scan_finished
        )

        self.worker_thread.finished.connect(
            self.worker.deleteLater
        )

        self.worker_thread.start()

        # =================================================
        # REFRESH TIMER
        # =================================================

        self.timer = QTimer(self)

        self.timer.setInterval(
            2000
        )

        self.timer.timeout.connect(
            self.request_process_scan
        )

        self.timer.start()

        # Initial scan
        QTimer.singleShot(
            100,
            self.request_process_scan
        )

    # =====================================================
    # REFRESH SETTINGS
    # =====================================================

    def set_refresh_interval(
        self,
        ms
    ):

        self.timer.setInterval(ms)

    def pause_timer(self):

        if self.timer.isActive():

            self.timer.stop()

    def resume_timer(self):

        if not self.timer.isActive():

            self.timer.start()

        self.request_process_scan()

    # =====================================================
    # REQUEST BACKGROUND SCAN
    # =====================================================

    def request_process_scan(self):

        if self.scan_pending:

            return

        if not self.worker_thread.isRunning():

            return

        self.scan_pending = True

        self.worker.scan_requested.emit()

    # =====================================================
    # RECEIVE WORKER RESULT
    # =====================================================

    @Slot(list)
    def process_scan_finished(
        self,
        new_data
    ):

        self.scan_pending = False

        self.processes_data = new_data

        self.filter_processes()

    # =====================================================
    # UI
    # =====================================================

    def setup_ui(self):

        main_layout = QVBoxLayout(
            self
        )

        main_layout.setContentsMargins(
            35,
            30,
            35,
            30
        )

        main_layout.setSpacing(15)

        # =================================================
        # HEADER
        # =================================================

        header_layout = QVBoxLayout()

        header_layout.setSpacing(4)

        title = QLabel(
            "PROCESS MANAGER"
        )

        title.setObjectName(
            "page_title"
        )

        subtitle = QLabel(
            "Monitor Running Tasks, "
            "Process Telemetry & "
            "Manage System Resources"
        )

        subtitle.setObjectName(
            "subtitle"
        )

        header_layout.addWidget(
            title
        )

        header_layout.addWidget(
            subtitle
        )

        main_layout.addLayout(
            header_layout
        )

        # =================================================
        # CONTROLS
        # =================================================

        controls_layout = QHBoxLayout()

        controls_layout.setSpacing(12)

        self.search_input = QLineEdit()

        self.search_input.setPlaceholderText(
            "🔍 Search process name or PID..."
        )

        self.search_input.setStyleSheet(
            """
            QLineEdit {
                background-color: #0b0b0b;
                border: 1px solid #303030;
                border-radius: 4px;
                padding: 8px 12px;
                color: #dddddd;
                font-size: 12px;
            }

            QLineEdit:focus {
                border: 1px solid #ff8f00;
            }
            """
        )

        self.search_input.textChanged.connect(
            self.filter_processes
        )

        controls_layout.addWidget(
            self.search_input,
            stretch=2
        )

        # -------------------------------------------------
        # REFRESH
        # -------------------------------------------------

        self.refresh_btn = QPushButton(
            "🔄 Refresh"
        )

        self.refresh_btn.setStyleSheet(
            self.get_btn_style(
                "#26a69a"
            )
        )

        self.refresh_btn.clicked.connect(
            self.request_process_scan
        )

        controls_layout.addWidget(
            self.refresh_btn
        )

        # -------------------------------------------------
        # TERMINATE
        # -------------------------------------------------

        self.terminate_btn = QPushButton(
            "⏹ End Task"
        )

        self.terminate_btn.setStyleSheet(
            self.get_btn_style(
                "#ff8f00"
            )
        )

        self.terminate_btn.clicked.connect(
            self.terminate_selected_process
        )

        controls_layout.addWidget(
            self.terminate_btn
        )

        # -------------------------------------------------
        # KILL
        # -------------------------------------------------

        self.kill_btn = QPushButton(
            "Force Kill"
        )

        self.kill_btn.setStyleSheet(
            self.get_btn_style(
                "#e53935"
            )
        )

        self.kill_btn.clicked.connect(
            self.kill_selected_process
        )

        controls_layout.addWidget(
            self.kill_btn
        )

        main_layout.addLayout(
            controls_layout
        )

        # =================================================
        # SUMMARY
        # =================================================

        self.summary_frame = QFrame()

        self.summary_frame.setStyleSheet(
            """
            QFrame {
                background-color: #090909;
                border: 1px solid #242424;
                border-radius: 4px;
                padding: 8px 15px;
            }
            """
        )

        summary_layout = QHBoxLayout(
            self.summary_frame
        )

        summary_layout.setContentsMargins(
            10,
            5,
            10,
            5
        )

        self.count_lbl = QLabel(
            "Total Processes: 0"
        )

        self.count_lbl.setStyleSheet(
            """
            color: #ffaa00;
            font-size: 11px;
            font-weight: bold;
            """
        )

        self.mem_summary_lbl = QLabel(
            "Monitored RAM: 0 MB"
        )

        self.mem_summary_lbl.setStyleSheet(
            """
            color: #ab47bc;
            font-size: 11px;
            font-weight: bold;
            """
        )

        summary_layout.addWidget(
            self.count_lbl
        )

        summary_layout.addStretch()

        summary_layout.addWidget(
            self.mem_summary_lbl
        )

        main_layout.addWidget(
            self.summary_frame
        )

        # =================================================
        # PROCESS TABLE
        # =================================================

        self.table = QTableWidget()

        self.table.setColumnCount(
            7
        )

        self.table.setHorizontalHeaderLabels(
            [
                "PID",
                "Process Name",
                "Status",
                "CPU %",
                "RAM (MB)",
                "RAM %",
                "User / Owner",
            ]
        )

        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        self.table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.ResizeToContents
        )

        self.table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )

        self.table.setSelectionMode(
            QAbstractItemView.SingleSelection
        )

        self.table.setSortingEnabled(
            True
        )

        self.table.setStyleSheet(
            """
            QTableWidget {
                background-color: #050505;
                gridline-color: #1a1a1a;
                color: #cccccc;
                border: 1px solid #222222;
                font-size: 11px;
            }

            QTableWidget::item {
                padding: 6px;
            }

            QTableWidget::item:selected {
                background-color: #262626;
                color: #ffaa00;
            }

            QHeaderView::section {
                background-color: #0a0a0a;
                color: #ff8f00;
                font-weight: bold;
                padding: 8px;
                border: 1px solid #1c1c1c;
            }
            """
        )

        main_layout.addWidget(
            self.table
        )

    # =====================================================
    # BUTTON STYLE
    # =====================================================

    def get_btn_style(
        self,
        color
    ):

        return f"""
            QPushButton {{
                background-color: #0b0b0b;
                color: {color};
                border: 1px solid {color};
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 11px;
            }}

            QPushButton:hover {{
                background-color: {color};
                color: #000000;
            }}
        """

    # =====================================================
    # SEARCH / FILTER
    # =====================================================

    def filter_processes(self):

        query = (
            self.search_input
            .text()
            .lower()
            .strip()
        )

        filtered = []

        for item in self.processes_data:

            if (
                not query
                or query in item["name"].lower()
                or query in str(item["pid"])
            ):

                filtered.append(
                    item
                )

        self.update_table(
            filtered
        )

    # =====================================================
    # TABLE UPDATE
    # =====================================================

    def update_table(
        self,
        filtered
    ):

        self.table.setUpdatesEnabled(
            False
        )

        self.table.setSortingEnabled(
            False
        )

        self.table.blockSignals(
            True
        )

        try:

            self.table.setRowCount(
                len(filtered)
            )

            total_rss = sum(
                item["rss_mb"]
                for item in filtered
            )

            for row, item in enumerate(
                filtered
            ):

                # -------------------------------------------------
                # PID
                # -------------------------------------------------

                pid_item = (
                    self.table.item(
                        row,
                        0
                    )
                )

                if pid_item is None:

                    pid_item = (
                        QTableWidgetItem()
                    )

                    self.table.setItem(
                        row,
                        0,
                        pid_item
                    )

                pid_item.setData(
                    Qt.DisplayRole,
                    item["pid"]
                )

                pid_item.setForeground(
                    QColor("#ffffff")
                )

                # -------------------------------------------------
                # NAME
                # -------------------------------------------------

                proc_name = item["name"]

                if item["cpu"] > 15:

                    proc_name = (
                        f"🔥 {proc_name}"
                    )

                elif item["rss_mb"] > 500:

                    proc_name = (
                        f"💾 {proc_name}"
                    )

                name_item = (
                    self.table.item(
                        row,
                        1
                    )
                )

                if name_item is None:

                    name_item = (
                        QTableWidgetItem()
                    )

                    self.table.setItem(
                        row,
                        1,
                        name_item
                    )

                name_item.setText(
                    proc_name
                )

                name_color = (
                    "#e53935"
                    if item["cpu"] > 15
                    else (
                        "#ff8f00"
                        if item["rss_mb"] > 500
                        else "#e0e0e0"
                    )
                )

                name_item.setForeground(
                    QColor(name_color)
                )

                name_item.setFont(
                    QFont(
                        "Segoe UI",
                        9,
                        QFont.Bold
                    )
                )

                # -------------------------------------------------
                # STATUS
                # -------------------------------------------------

                status_item = (
                    self.table.item(
                        row,
                        2
                    )
                )

                if status_item is None:

                    status_item = (
                        QTableWidgetItem()
                    )

                    self.table.setItem(
                        row,
                        2,
                        status_item
                    )

                status_item.setText(
                    item["status"]
                )

                status_color = (
                    "#55d66f"
                    if item["status"]
                    in (
                        "running",
                        "active",
                    )
                    else "#aaaaaa"
                )

                status_item.setForeground(
                    QColor(status_color)
                )

                # -------------------------------------------------
                # CPU
                # -------------------------------------------------

                cpu_item = (
                    self.table.item(
                        row,
                        3
                    )
                )

                if cpu_item is None:

                    cpu_item = (
                        QTableWidgetItem()
                    )

                    self.table.setItem(
                        row,
                        3,
                        cpu_item
                    )

                cpu_item.setData(
                    Qt.DisplayRole,
                    round(
                        item["cpu"],
                        1
                    )
                )

                cpu_item.setForeground(
                    QColor(
                        "#e53935"
                        if item["cpu"] > 20
                        else "#cccccc"
                    )
                )

                # -------------------------------------------------
                # RAM MB
                # -------------------------------------------------

                ram_item = (
                    self.table.item(
                        row,
                        4
                    )
                )

                if ram_item is None:

                    ram_item = (
                        QTableWidgetItem()
                    )

                    self.table.setItem(
                        row,
                        4,
                        ram_item
                    )

                ram_item.setData(
                    Qt.DisplayRole,
                    round(
                        item["rss_mb"],
                        1
                    )
                )

                ram_item.setForeground(
                    QColor("#ab47bc")
                )

                # -------------------------------------------------
                # RAM %
                # -------------------------------------------------

                ram_pct_item = (
                    self.table.item(
                        row,
                        5
                    )
                )

                if ram_pct_item is None:

                    ram_pct_item = (
                        QTableWidgetItem()
                    )

                    self.table.setItem(
                        row,
                        5,
                        ram_pct_item
                    )

                ram_pct_item.setData(
                    Qt.DisplayRole,
                    round(
                        item["mem_pct"],
                        1
                    )
                )

                ram_pct_item.setForeground(
                    QColor("#8bc34a")
                )

                # -------------------------------------------------
                # USER
                # -------------------------------------------------

                user_item = (
                    self.table.item(
                        row,
                        6
                    )
                )

                if user_item is None:

                    user_item = (
                        QTableWidgetItem()
                    )

                    self.table.setItem(
                        row,
                        6,
                        user_item
                    )

                user_item.setText(
                    item["user"]
                )

                user_item.setForeground(
                    QColor("#888888")
                )

            self.count_lbl.setText(
                f"Total Processes: {len(filtered)}"
            )

            self.mem_summary_lbl.setText(
                f"Monitored RAM: {total_rss:.1f} MB"
            )

        finally:

            self.table.blockSignals(
                False
            )

            self.table.setSortingEnabled(
                True
            )

            self.table.setUpdatesEnabled(
                True
            )

            self.table.viewport().update()

    # =====================================================
    # GET SELECTED PROCESS
    # =====================================================

    def get_selected_pid_name(self):

        selected = (
            self.table.selectedItems()
        )

        if not selected:

            return None, None

        row = selected[0].row()

        pid_item = (
            self.table.item(
                row,
                0
            )
        )

        name_item = (
            self.table.item(
                row,
                1
            )
        )

        if pid_item and name_item:

            try:

                pid = int(
                    pid_item.data(
                        Qt.DisplayRole
                    )
                )

            except (
                TypeError,
                ValueError,
            ):

                return None, None

            name = name_item.text()

            name = name.removeprefix(
                "🔥 "
            )

            name = name.removeprefix(
                "💾 "
            )

            return pid, name

        return None, None

    # =====================================================
    # TERMINATE
    # =====================================================

    def terminate_selected_process(
        self
    ):

        pid, name = (
            self.get_selected_pid_name()
        )

        if not pid:

            QMessageBox.information(
                self,
                "No Selection",
                (
                    "Please select a process "
                    "from the table first."
                ),
            )

            return

        reply = QMessageBox.question(
            self,
            "Confirm End Task",
            (
                f"Are you sure you want to "
                f"end task for process "
                f"'{name}' (PID: {pid})?"
            ),
            QMessageBox.Yes
            | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:

            try:

                proc = psutil.Process(
                    pid
                )

                proc.terminate()

                QMessageBox.information(
                    self,
                    "Task Terminated",
                    (
                        f"Process '{name}' "
                        f"(PID: {pid}) "
                        "termination signal sent."
                    ),
                )

                self.request_process_scan()

            except psutil.AccessDenied:

                QMessageBox.warning(
                    self,
                    "Access Denied",
                    (
                        f"Permission denied to "
                        f"terminate process "
                        f"'{name}' (PID: {pid}). "
                        "Run application as Administrator."
                    ),
                )

            except psutil.NoSuchProcess:

                QMessageBox.information(
                    self,
                    "Process Ended",
                    (
                        f"Process '{name}' "
                        f"(PID: {pid}) "
                        "has already ended."
                    ),
                )

                self.request_process_scan()

            except Exception as e:

                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to terminate process: {e}",
                )

    # =====================================================
    # FORCE KILL
    # =====================================================

    def kill_selected_process(
        self
    ):

        pid, name = (
            self.get_selected_pid_name()
        )

        if not pid:

            QMessageBox.information(
                self,
                "No Selection",
                (
                    "Please select a process "
                    "from the table first."
                ),
            )

            return

        reply = QMessageBox.question(
            self,
            "Confirm Force Kill",
            (
                f"Are you sure you want to "
                f"FORCE KILL process "
                f"'{name}' (PID: {pid})?"
            ),
            QMessageBox.Yes
            | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:

            try:

                proc = psutil.Process(
                    pid
                )

                proc.kill()

                QMessageBox.information(
                    self,
                    "Force Killed",
                    (
                        f"Process '{name}' "
                        f"(PID: {pid}) "
                        "was forcefully killed."
                    ),
                )

                self.request_process_scan()

            except psutil.AccessDenied:

                QMessageBox.warning(
                    self,
                    "Access Denied",
                    (
                        f"Permission denied to "
                        f"kill process '{name}' "
                        f"(PID: {pid}). "
                        "Run application as Administrator."
                    ),
                )

            except psutil.NoSuchProcess:

                QMessageBox.information(
                    self,
                    "Process Ended",
                    (
                        f"Process '{name}' "
                        f"(PID: {pid}) "
                        "has already ended."
                    ),
                )

                self.request_process_scan()

            except Exception as e:

                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to kill process: {e}",
                )

    # =====================================================
    # CLEANUP
    # =====================================================

    def closeEvent(
        self,
        event
    ):

        self.timer.stop()

        if self.worker_thread.isRunning():

            self.worker_thread.quit()

            if not self.worker_thread.wait(
                2000
            ):

                self.worker_thread.terminate()

                self.worker_thread.wait()

        event.accept()