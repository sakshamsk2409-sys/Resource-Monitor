import time
import math
import psutil
import concurrent.futures

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QGridLayout,
)

from dashboard import CarbonFiberBackground

try:
    import pynvml
    HAS_PYNVML = True
except ImportError:
    pynvml = None
    HAS_PYNVML = False


def single_core_stress_workload(iterations=2500000):
    count = 0
    for i in range(2, iterations):
        # Heavy floating point & math operation
        math.sin(i) * math.cos(i) + math.sqrt(i)
        count += 1
    return count


def multi_core_worker(n):
    return single_core_stress_workload(1000000)


class BenchmarkRunnerThread(QThread):
    progress_signal = Signal(int, str)
    finished_signal = Signal(dict)

    def run(self):
        scores = {}

        # 1. Single-Thread Test
        self.progress_signal.emit(15, "Running Single-Core CPU Benchmark...")
        t0 = time.time()
        single_core_stress_workload(2000000)
        dt_single = time.time() - t0
        single_score = int(10000 / max(0.01, dt_single))
        scores["single_core"] = single_score
        scores["dt_single"] = f"{dt_single:.2f} s"

        # 2. Multi-Thread Test
        self.progress_signal.emit(50, "Running Multi-Core CPU Stress Benchmark...")
        cores = psutil.cpu_count(logical=True) or 4
        t0 = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=cores) as executor:
            list(executor.map(multi_core_worker, range(cores * 2)))
        dt_multi = time.time() - t0
        multi_score = int((10000 * cores) / max(0.01, dt_multi))
        scores["multi_core"] = multi_score
        scores["dt_multi"] = f"{dt_multi:.2f} s"

        # 3. RAM Throughput Test
        self.progress_signal.emit(80, "Running Memory Read/Write Speed Benchmark...")
        t0 = time.time()
        block_size = 50 * 1024 * 1024  # 50 MB
        data = bytearray(block_size)
        for i in range(len(data)):
            data[i] = (i % 255)
        _ = bytes(data)
        dt_mem = time.time() - t0
        mem_speed_mb = (50.0 * 2) / max(0.001, dt_mem)
        mem_score = int(mem_speed_mb * 5)
        scores["memory_speed"] = f"{mem_speed_mb:.1f} MB/s"
        scores["memory_score"] = mem_score

        self.progress_signal.emit(100, "Benchmark Complete!")
        self.finished_signal.emit(scores)


class BenchmarkPage(CarbonFiberBackground):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.gpu_handle = None
        self.init_gpu()

        self.setup_ui()

    def init_gpu(self):
        if HAS_PYNVML and pynvml:
            try:
                pynvml.nvmlInit()
                if pynvml.nvmlDeviceGetCount() > 0:
                    self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            except Exception:
                pass

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(35, 30, 35, 30)
        main_layout.setSpacing(20)

        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        title = QLabel("HARDWARE BENCHMARK & STRESS TEST")
        title.setObjectName("page_title")

        subtitle = QLabel("Evaluate CPU Single-Core, Multi-Core & Memory Performance Scores")
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

        # Action Control Card
        control_card, control_layout = self.create_card("BENCHMARK CONTROLS")
        btn_layout = QHBoxLayout()

        self.run_btn = QPushButton("Run Full Benchmark Suite")
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff8f00; color: #000000; font-weight: bold; border-radius: 4px; padding: 10px 20px; font-size: 12px;
            }
            QPushButton:hover { background-color: #ffa726; }
        """)
        self.run_btn.clicked.connect(self.run_benchmark)
        btn_layout.addWidget(self.run_btn)
        btn_layout.addStretch()

        control_layout.addLayout(btn_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #0c0c0c; border: 1px solid #282828; border-radius: 4px; color: #ffffff; text-align: center; height: 22px;
            }
            QProgressBar::chunk { background-color: #ff8f00; }
        """)
        control_layout.addWidget(self.progress_bar)

        self.status_lbl = QLabel("Ready to run benchmark stress test.")
        self.status_lbl.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        control_layout.addWidget(self.status_lbl)

        content_layout.addWidget(control_card)

        # Scores Grid Row
        content_layout.addLayout(self.create_scores_row())

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

    def create_scores_row(self):
        row = QHBoxLayout()
        row.setSpacing(15)

        # 1. Single Core Score
        c1, l1 = self.create_card("SINGLE-CORE SCORE")
        self.single_score_lbl = QLabel("---")
        self.single_score_lbl.setStyleSheet("color: #ff8f00; font-size: 26px; font-weight: bold;")
        self.single_time_lbl = QLabel("Time: --")
        self.single_time_lbl.setStyleSheet("color: #888888; font-size: 11px;")
        l1.addWidget(self.single_score_lbl)
        l1.addWidget(self.single_time_lbl)
        row.addWidget(c1)

        # 2. Multi Core Score
        c2, l2 = self.create_card("MULTI-CORE SCORE")
        self.multi_score_lbl = QLabel("---")
        self.multi_score_lbl.setStyleSheet("color: #55d66f; font-size: 26px; font-weight: bold;")
        self.multi_time_lbl = QLabel("Time: --")
        self.multi_time_lbl.setStyleSheet("color: #888888; font-size: 11px;")
        l2.addWidget(self.multi_score_lbl)
        l2.addWidget(self.multi_time_lbl)
        row.addWidget(c2)

        # 3. Memory Speed Score
        c3, l3 = self.create_card("MEMORY THROUGHPUT")
        self.mem_score_lbl = QLabel("---")
        self.mem_score_lbl.setStyleSheet("color: #ab47bc; font-size: 26px; font-weight: bold;")
        self.mem_speed_lbl = QLabel("Speed: --")
        self.mem_speed_lbl.setStyleSheet("color: #888888; font-size: 11px;")
        l3.addWidget(self.mem_score_lbl)
        l3.addWidget(self.mem_speed_lbl)
        row.addWidget(c3)

        return row

    def run_benchmark(self):
        self.run_btn.setEnabled(False)
        self.progress_bar.setValue(5)
        self.status_lbl.setText("Initializing benchmark thread...")

        self.thread = BenchmarkRunnerThread()
        self.thread.progress_signal.connect(self.update_progress)
        self.thread.finished_signal.connect(self.benchmark_finished)
        self.thread.start()

    def update_progress(self, val, msg):
        self.progress_bar.setValue(val)
        self.status_lbl.setText(msg)

    def benchmark_finished(self, scores):
        self.single_score_lbl.setText(str(scores.get("single_core", "N/A")))
        self.single_time_lbl.setText(f"Duration: {scores.get('dt_single', 'N/A')}")

        self.multi_score_lbl.setText(str(scores.get("multi_core", "N/A")))
        self.multi_time_lbl.setText(f"Duration: {scores.get('dt_multi', 'N/A')}")

        self.mem_score_lbl.setText(str(scores.get("memory_score", "N/A")))
        self.mem_speed_lbl.setText(f"Speed: {scores.get('memory_speed', 'N/A')}")

        self.run_btn.setEnabled(True)
        self.status_lbl.setText("✅ Benchmark Suite Executed Successfully!")
