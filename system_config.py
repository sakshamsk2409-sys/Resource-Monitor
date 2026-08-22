import datetime
import os
import platform
import socket
import psutil

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
)

from dashboard import CarbonFiberBackground


class SystemConfigPage(CarbonFiberBackground):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

        # Update dynamic metrics (like uptime & dynamic drive usage) periodically
        self.timer = QTimer(self)
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.refresh_dynamic_info)
        self.timer.start()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(35, 30, 35, 30)
        main_layout.setSpacing(20)

        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        title = QLabel("SYSTEM CONFIGURATION")
        title.setObjectName("page_title")

        subtitle = QLabel("Comprehensive Hardware Specifications & Operating System Telemetry")
        subtitle.setObjectName("subtitle")

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)

        # Scroll Area for Content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 10, 10, 10)
        content_layout.setSpacing(20)

        # Row 1: OS Info & Processor Specs
        row1 = QHBoxLayout()
        row1.setSpacing(20)

        row1.addWidget(self.create_os_card())
        row1.addWidget(self.create_cpu_card())
        content_layout.addLayout(row1)

        # Row 2: Memory & System Uptime Cards
        row2 = QHBoxLayout()
        row2.setSpacing(20)

        row2.addWidget(self.create_memory_card())
        row2.addWidget(self.create_uptime_card())
        content_layout.addLayout(row2)

        # Row 3: Storage Partitions
        content_layout.addWidget(self.create_storage_card())

        # Row 4: Network Adapters
        content_layout.addWidget(self.create_network_card())

        content_layout.addStretch()
        scroll.setWidget(content_widget)
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

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #222222; max-height: 1px;")
        card_layout.addWidget(sep)

        return card, card_layout

    def add_info_row(self, layout, label_text, value_text):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #888888; font-size: 11px; font-weight: bold;")

        val = QLabel(str(value_text))
        val.setStyleSheet("color: #e0e0e0; font-size: 11px; font-weight: bold;")
        val.setTextInteractionFlags(Qt.TextSelectableByMouse)

        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(val)
        layout.addLayout(row)

    def create_os_card(self):
        card, layout = self.create_card("OPERATING SYSTEM & ENVIRONMENT")

        os_name = platform.system()
        os_rel = platform.release()
        os_ver = platform.version()
        arch = platform.machine()
        hostname = socket.gethostname()

        try:
            ip_addr = socket.gethostbyname(hostname)
        except Exception:
            ip_addr = "127.0.0.1"

        self.add_info_row(layout, "OS Name", os_name)
        self.add_info_row(layout, "OS Release", os_rel)
        self.add_info_row(layout, "Build Version", os_ver)
        self.add_info_row(layout, "Architecture", arch)
        self.add_info_row(layout, "Hostname", hostname)
        self.add_info_row(layout, "Primary Host IP", ip_addr)
        self.add_info_row(layout, "Python Version", platform.python_version())

        layout.addStretch()
        return card

    def create_cpu_card(self):
        card, layout = self.create_card("PROCESSOR & HARDWARE ARCHITECTURE")

        cpu_brand = platform.processor() or "x86/x64 Family Processor"
        phys_cores = psutil.cpu_count(logical=False) or "N/A"
        log_cores = psutil.cpu_count(logical=True) or "N/A"

        try:
            freq = psutil.cpu_freq()
            freq_max = f"{freq.max:.0f} MHz" if freq and freq.max else "N/A"
            freq_cur = f"{freq.current:.0f} MHz" if freq and freq.current else "N/A"
        except Exception:
            freq_max = "N/A"
            freq_cur = "N/A"

        self.add_info_row(layout, "Processor Model", cpu_brand)
        self.add_info_row(layout, "Physical Cores", phys_cores)
        self.add_info_row(layout, "Logical Threads", log_cores)
        self.add_info_row(layout, "Max Frequency", freq_max)
        self.add_info_row(layout, "Base/Current Clock", freq_cur)

        layout.addStretch()
        return card

    def create_memory_card(self):
        card, layout = self.create_card("SYSTEM MEMORY SUMMARY")

        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()

        total_gb = f"{vm.total / (1024**3):.2f} GB"
        swap_gb = f"{swap.total / (1024**3):.2f} GB"

        self.add_info_row(layout, "Total Physical RAM", total_gb)
        self.add_info_row(layout, "Swap Space Total", swap_gb)

        self.ram_avail_lbl = QLabel()
        self.ram_avail_lbl.setStyleSheet("color: #55d66f; font-size: 11px; font-weight: bold;")

        self.refresh_memory_info()

        row = QHBoxLayout()
        lbl = QLabel("Available RAM")
        lbl.setStyleSheet("color: #888888; font-size: 11px; font-weight: bold;")
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(self.ram_avail_lbl)
        layout.addLayout(row)

        layout.addStretch()
        return card

    def create_uptime_card(self):
        card, layout = self.create_card("SYSTEM BOOT & UPTIME")

        boot_timestamp = psutil.boot_time()
        boot_dt = datetime.datetime.fromtimestamp(boot_timestamp)

        self.add_info_row(layout, "Boot Time", boot_dt.strftime("%Y-%m-%d %H:%M:%S"))

        self.uptime_lbl = QLabel()
        self.uptime_lbl.setStyleSheet("color: #ffaa00; font-size: 11px; font-weight: bold;")

        row = QHBoxLayout()
        lbl = QLabel("Active System Uptime")
        lbl.setStyleSheet("color: #888888; font-size: 11px; font-weight: bold;")
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(self.uptime_lbl)
        layout.addLayout(row)

        self.refresh_uptime()

        layout.addStretch()
        return card

    def create_storage_card(self):
        card, layout = self.create_card("STORAGE DRIVES & PARTITIONS")

        grid = QGridLayout()
        grid.setSpacing(10)

        # Header
        headers = ["Drive / Mount", "File System", "Total Size", "Used Space", "Free Space", "Usage"]
        for col, h in enumerate(headers):
            lbl = QLabel(h)
            lbl.setStyleSheet("color: #ff8f00; font-size: 10px; font-weight: bold;")
            grid.addWidget(lbl, 0, col)

        row_idx = 1
        try:
            partitions = psutil.disk_partitions(all=False)
            for p in partitions:
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    mount_lbl = QLabel(p.mountpoint)
                    mount_lbl.setStyleSheet("color: #ffffff; font-weight: bold;")

                    fstype_lbl = QLabel(p.fstype or "N/A")
                    fstype_lbl.setStyleSheet("color: #aaaaaa;")

                    total_lbl = QLabel(f"{usage.total / (1024**3):.1f} GB")
                    total_lbl.setStyleSheet("color: #cccccc;")

                    used_lbl = QLabel(f"{usage.used / (1024**3):.1f} GB")
                    used_lbl.setStyleSheet("color: #cccccc;")

                    free_lbl = QLabel(f"{usage.free / (1024**3):.1f} GB")
                    free_lbl.setStyleSheet("color: #55d66f;")

                    pct_lbl = QLabel(f"{usage.percent:.1f}%")
                    pct_color = "#e53935" if usage.percent > 85 else "#55d66f"
                    pct_lbl.setStyleSheet(f"color: {pct_color}; font-weight: bold;")

                    grid.addWidget(mount_lbl, row_idx, 0)
                    grid.addWidget(fstype_lbl, row_idx, 1)
                    grid.addWidget(total_lbl, row_idx, 2)
                    grid.addWidget(used_lbl, row_idx, 3)
                    grid.addWidget(free_lbl, row_idx, 4)
                    grid.addWidget(pct_lbl, row_idx, 5)
                    row_idx += 1
                except Exception:
                    continue
        except Exception:
            pass

        layout.addLayout(grid)
        return card

    def create_network_card(self):
        card, layout = self.create_card("NETWORK INTERFACES & ADAPTERS")

        grid = QGridLayout()
        grid.setSpacing(10)

        headers = ["Interface Name", "IPv4 Address", "MAC Address", "Status"]
        for col, h in enumerate(headers):
            lbl = QLabel(h)
            lbl.setStyleSheet("color: #ff8f00; font-size: 10px; font-weight: bold;")
            grid.addWidget(lbl, 0, col)

        row_idx = 1
        try:
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()

            for iface_name, net_addrs in addrs.items():
                ipv4 = "N/A"
                mac = "N/A"
                for addr in net_addrs:
                    if addr.family == socket.AF_INET:
                        ipv4 = addr.address
                    elif hasattr(psutil, "AF_LINK") and addr.family == psutil.AF_LINK:
                        mac = addr.address

                is_up = stats[iface_name].isup if iface_name in stats else False
                status_str = "● UP" if is_up else "○ DOWN"
                status_color = "#55d66f" if is_up else "#666666"

                name_lbl = QLabel(iface_name)
                name_lbl.setStyleSheet("color: #ffffff; font-weight: bold;")

                ip_lbl = QLabel(ipv4)
                ip_lbl.setStyleSheet("color: #cccccc;")

                mac_lbl = QLabel(mac)
                mac_lbl.setStyleSheet("color: #888888;")

                st_lbl = QLabel(status_str)
                st_lbl.setStyleSheet(f"color: {status_color}; font-weight: bold;")

                grid.addWidget(name_lbl, row_idx, 0)
                grid.addWidget(ip_lbl, row_idx, 1)
                grid.addWidget(mac_lbl, row_idx, 2)
                grid.addWidget(st_lbl, row_idx, 3)
                row_idx += 1
        except Exception:
            pass

        layout.addLayout(grid)
        return card

    def refresh_memory_info(self):
        try:
            vm = psutil.virtual_memory()
            avail_gb = vm.available / (1024**3)
            self.ram_avail_lbl.setText(f"{avail_gb:.2f} GB ({100 - vm.percent:.1f}% free)")
        except Exception:
            pass

    def refresh_uptime(self):
        try:
            uptime_seconds = datetime.datetime.now().timestamp() - psutil.boot_time()
            hours, remainder = divmod(int(uptime_seconds), 3600)
            minutes, seconds = divmod(remainder, 60)
            days, hours = divmod(hours, 24)
            self.uptime_lbl.setText(f"{days}d {hours}h {minutes}m {seconds}s")
        except Exception:
            pass

    def refresh_dynamic_info(self):
        self.refresh_memory_info()
        self.refresh_uptime()
