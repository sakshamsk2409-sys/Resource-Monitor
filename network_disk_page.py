import time
import socket
import psutil
import pyqtgraph as pg

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QGridLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)

from dashboard import CarbonFiberBackground


class NetworkDiskPage(CarbonFiberBackground):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.last_time = time.time()
        self.last_net = psutil.net_io_counters()
        self.last_disk = psutil.disk_io_counters()

        self.up_history = []
        self.down_history = []
        self.read_history = []
        self.write_history = []

        self.setup_ui()

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_telemetry)
        self.timer.start()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(35, 30, 35, 30)
        main_layout.setSpacing(20)

        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        title = QLabel("NETWORK & DISK I/O TELEMETRY")
        title.setObjectName("page_title")

        subtitle = QLabel("Real-Time Bandwidth Speedometer, Disk Throughput & Active Socket Telemetry")
        subtitle.setObjectName("subtitle")

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)

        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 10, 10, 10)
        content_layout.setSpacing(20)

        # Metrics Row
        content_layout.addLayout(self.create_metrics_row())

        # Real-time Bandwidth Plot Card
        content_layout.addWidget(self.create_network_graph_card())

        # Real-time Disk I/O Plot Card
        content_layout.addWidget(self.create_disk_graph_card())

        # Active Sockets Table Card
        content_layout.addWidget(self.create_sockets_card())

        content_layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def create_card(self, title_text):
        card = QFrame()
        card.setObjectName("memory_panel")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(12)

        card_title = QLabel(title_text)
        card_title.setObjectName("section_title")
        card_layout.addWidget(card_title)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #222222; max-height: 1px;")
        card_layout.addWidget(sep)

        return card, card_layout

    def create_metrics_row(self):
        row = QHBoxLayout()
        row.setSpacing(15)

        # 1. Upload Speed
        c1, l1 = self.create_card("UPLOAD SPEED")
        self.upload_val = QLabel("0.00 KB/s")
        self.upload_val.setStyleSheet("color: #ff8f00; font-size: 20px; font-weight: bold;")
        l1.addWidget(self.upload_val)
        row.addWidget(c1)

        # 2. Download Speed
        c2, l2 = self.create_card("DOWNLOAD SPEED")
        self.download_val = QLabel("0.00 KB/s")
        self.download_val.setStyleSheet("color: #26a69a; font-size: 20px; font-weight: bold;")
        l2.addWidget(self.download_val)
        row.addWidget(c2)

        # 3. Disk Read Rate
        c3, l3 = self.create_card("DISK READ RATE")
        self.disk_read_val = QLabel("0.00 MB/s")
        self.disk_read_val.setStyleSheet("color: #ab47bc; font-size: 20px; font-weight: bold;")
        l3.addWidget(self.disk_read_val)
        row.addWidget(c3)

        # 4. Disk Write Rate
        c4, l4 = self.create_card("DISK WRITE RATE")
        self.disk_write_val = QLabel("0.00 MB/s")
        self.disk_write_val.setStyleSheet("color: #fdd835; font-size: 20px; font-weight: bold;")
        l4.addWidget(self.disk_write_val)
        row.addWidget(c4)

        return row

    def create_network_graph_card(self):
        card, layout = self.create_card("NETWORK BANDWIDTH SPEED (UPLOAD vs DOWNLOAD - KB/s)")

        self.net_graph = pg.PlotWidget()
        self.net_graph.setBackground("#050505")
        self.net_graph.showGrid(x=True, y=True, alpha=0.15)
        self.net_graph.setFixedHeight(180)

        self.up_curve = self.net_graph.plot(pen=pg.mkPen(color="#ff8f00", width=2), name="Upload (KB/s)")
        self.down_curve = self.net_graph.plot(pen=pg.mkPen(color="#26a69a", width=2), name="Download (KB/s)")

        layout.addWidget(self.net_graph)
        return card

    def create_disk_graph_card(self):
        card, layout = self.create_card("DISK I/O THROUGHPUT (READ vs WRITE - MB/s)")

        self.disk_graph = pg.PlotWidget()
        self.disk_graph.setBackground("#050505")
        self.disk_graph.showGrid(x=True, y=True, alpha=0.15)
        self.disk_graph.setFixedHeight(180)

        self.read_curve = self.disk_graph.plot(pen=pg.mkPen(color="#ab47bc", width=2), name="Read (MB/s)")
        self.write_curve = self.disk_graph.plot(pen=pg.mkPen(color="#fdd835", width=2), name="Write (MB/s)")

        layout.addWidget(self.disk_graph)
        return card

    def create_sockets_card(self):
        card, layout = self.create_card("ACTIVE NETWORK SOCKETS & CONNECTIONS")

        self.sock_table = QTableWidget()
        self.sock_table.setColumnCount(5)
        self.sock_table.setHorizontalHeaderLabels([
            "Local Address", "Remote Address", "Type", "Status", "PID / Process"
        ])
        self.sock_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sock_table.setMinimumHeight(200)
        self.sock_table.setStyleSheet("""
            QTableWidget {
                background-color: #050505;
                gridline-color: #1a1a1a;
                color: #cccccc;
                border: 1px solid #222222;
                font-size: 11px;
            }
            QTableWidget::item { padding: 5px; }
            QHeaderView::section {
                background-color: #0a0a0a;
                color: #ff8f00;
                font-weight: bold;
                padding: 6px;
                border: 1px solid #1c1c1c;
            }
        """)

        layout.addWidget(self.sock_table)
        return card

    def format_speed(self, bytes_per_sec):
        kb = bytes_per_sec / 1024.0
        if kb >= 1024:
            return f"{kb / 1024.0:.2f} MB/s"
        return f"{kb:.2f} KB/s"

    def update_telemetry(self):
        now = time.time()
        dt = now - self.last_time
        if dt <= 0:
            return
        self.last_time = now

        # Network IO
        curr_net = psutil.net_io_counters()
        bytes_sent_sec = (curr_net.bytes_sent - self.last_net.bytes_sent) / dt
        bytes_recv_sec = (curr_net.bytes_recv - self.last_net.bytes_recv) / dt
        self.last_net = curr_net

        up_kbs = bytes_sent_sec / 1024.0
        down_kbs = bytes_recv_sec / 1024.0

        self.upload_val.setText(self.format_speed(bytes_sent_sec))
        self.download_val.setText(self.format_speed(bytes_recv_sec))

        # Disk IO
        curr_disk = psutil.disk_io_counters()
        read_mb_sec = 0.0
        write_mb_sec = 0.0
        if curr_disk and self.last_disk:
            read_mb_sec = ((curr_disk.read_bytes - self.last_disk.read_bytes) / (1024 * 1024.0)) / dt
            write_mb_sec = ((curr_disk.write_bytes - self.last_disk.write_bytes) / (1024 * 1024.0)) / dt
            self.last_disk = curr_disk

        self.disk_read_val.setText(f"{max(0.0, read_mb_sec):.2f} MB/s")
        self.disk_write_val.setText(f"{max(0.0, write_mb_sec):.2f} MB/s")

        # History Plot Data
        self.up_history.append(max(0.0, up_kbs))
        self.down_history.append(max(0.0, down_kbs))
        self.read_history.append(max(0.0, read_mb_sec))
        self.write_history.append(max(0.0, write_mb_sec))

        if len(self.up_history) > 60:
            self.up_history.pop(0)
            self.down_history.pop(0)
            self.read_history.pop(0)
            self.write_history.pop(0)

        self.up_curve.setData(self.up_history)
        self.down_curve.setData(self.down_history)
        self.read_curve.setData(self.read_history)
        self.write_curve.setData(self.write_history)

        # Update Connections Sockets Table
        self.refresh_sockets()

    def refresh_sockets(self):
        try:
            conns = psutil.net_connections(kind="inet")
        except Exception:
            conns = []

        self.sock_table.setRowCount(min(len(conns), 15))

        for row, conn in enumerate(conns[:15]):
            laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "N/A"
            raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A"
            sock_type = "TCP" if conn.type == socket.SOCK_STREAM else "UDP"
            status = conn.status if conn.status else "N/A"
            pid_str = str(conn.pid) if conn.pid else "System"

            self.sock_table.setItem(row, 0, QTableWidgetItem(laddr))
            self.sock_table.setItem(row, 1, QTableWidgetItem(raddr))
            self.sock_table.setItem(row, 2, QTableWidgetItem(sock_type))

            st_item = QTableWidgetItem(status)
            st_color = "#55d66f" if status == "ESTABLISHED" else "#888888"
            st_item.setForeground(QColor(st_color))
            self.sock_table.setItem(row, 3, st_item)

            self.sock_table.setItem(row, 4, QTableWidgetItem(pid_str))
