# System Resource Monitor 📊

A high-performance, cyber-styled PySide6 desktop application for real-time monitoring and benchmarking of system resources including CPU, RAM, Disk, Network, and NVIDIA GPU metrics.

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![PySide6](https://img.shields.io/badge/PySide6-6.7%2B-green)
![License](https://img.shields.io/badge/license-MIT-orange)

---

## ✨ Features

### 📈 Historical Analytics & Telemetry Pipeline (DVP Upgrade)
- Continuous GUI-integrated CSV telemetry logger with start/pause/resume/stop controls
- Configurable sampling intervals (0.25s, 0.5s, 1.0s, 2.0s, 5.0s)
- Comprehensive documented 19-column telemetry schema with true instantaneous rate calculations
- Robust Pandas & NumPy data preprocessing pipeline (cleaning, range masking, deduplication, time-gap auditing)
- Interactive PyQtGraph time-series with moving average smoothing and dynamic interpretations
- Matplotlib exploratory visualizations (Bivariate scatter regressions, histograms, Pearson correlation heatmap)
- Academic descriptive statistics (percentiles, peak detection, threshold breach streaks)
- Offline rule-based diagnostic engine with optional opt-in external AI (Gemini / OpenAI / Ollama)
- Automated publication-grade HTML & JSON analytics report exporter

### 🎛️ Dashboard
- Real-time CPU, RAM, Disk, and Network gauges with animated dials
- Live telemetry cards showing current usage percentages
- Rolling history graphs powered by PyQtGraph

### 🧠 Memory Analytics
- Live memory breakdown with donut chart visualization
- Per-process memory consumption tracking
- Active application resource monitoring

### 🎮 GPU Performance
- NVIDIA GPU temperature, utilization, and memory telemetry
- Real-time GPU usage graphs (requires `nvidia-ml-py`)
- Graceful fallback when no NVIDIA GPU is detected

### 🌐 Network & Disk
- Real-time network upload/download speeds
- Disk read/write throughput monitoring
- Historical I/O trend graphs

### 🖥️ System Configuration
- Comprehensive hardware specifications display
- Operating system, processor, and memory details
- Disk partition information and usage breakdown

### 📦 Report Exporter
- Export diagnostic system telemetry and comprehensive historical analytics to HTML or JSON reports
- Timestamped report files with embedded visualizations and viva-ready audit summaries

### 🖱️ Mini Overlay
- Compact, always-on-top widget for quick glance telemetry
- Draggable frameless overlay showing key metrics

### 🏁 Benchmark
- Single-core and multi-core CPU stress tests
- Real-time progress tracking during benchmark runs
- Score calculation based on workload timing

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| GUI Framework | [PySide6](https://pypi.org/project/PySide6/) (Qt for Python) |
| System Monitoring | [psutil](https://pypi.org/project/psutil/) |
| Hardware Monitoring | LibreHardwareMonitor |
| Real-Time Plotting | [pyqtgraph](https://pypi.org/project/pyqtgraph/) |
| Data Analytics | [pandas](https://pypi.org/project/pandas/), [numpy](https://pypi.org/project/numpy/) |
| Charts & Exports | [matplotlib](https://pypi.org/project/matplotlib/) |
| GPU Metrics | [nvidia-ml-py](https://pypi.org/project/nvidia-ml-py/) |

> **Note:** LibreHardwareMonitor requires manual setup on Windows:
> 1. Download the release from [LibreHardwareMonitor GitHub](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases)
> 2. Extract and place `LibreHardwareMonitor.exe` at `.tools/LibreHardwareMonitor/`
> 3. The app will automatically use the local sensor service on startup.

---

## 📋 Requirements

- Python **3.8 or higher**
- Windows / Linux / macOS (GUI tested on desktop environments)

---

## 🚀 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/System-Resource-Monitor.git
   cd System-Resource-Monitor/Resource-Monitor
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   venv\Scripts\activate   # Windows
   source venv/bin/activate   # Linux / macOS
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🎯 Usage

Run the application:
```bash
python main.py
```

---

## 📂 Project Structure

| File | Description |
|------|-------------|
| `main.py` | Application entry point, sidebar navigation, telemetry recorder controls, and global theme |
| `analytics_page.py` | Historical telemetry analytics dashboard with PyQtGraph & Matplotlib visualizations |
| `telemetry_logger.py` | Continuous non-blocking CSV telemetry logger with schema validation & rate calculations |
| `data_preprocessing.py` | Pandas & NumPy preprocessing pipeline, range masking, deduplication, and audit reports |
| `telemetry_statistics.py` | Descriptive statistics, percentile distributions, threshold streaks, and data interpretations |
| `ai_insights.py` | Offline rule-based diagnostic engine and optional external AI integration (Gemini/OpenAI/Ollama) |
| `dashboard.py` | Performance cockpit with real-time gauges and telemetry graphs |
| `memory.py` | Memory analytics with donut charts and process tracking |
| `gpu_page.py` | NVIDIA GPU performance telemetry page |
| `network_disk_page.py` | Network I/O and Disk I/O monitoring with real-time graphs |
| `system_config.py` | System hardware specifications and OS information |
| `mini_overlay.py` | Compact draggable always-on-top telemetry widget |
| `benchmark_page.py` | CPU single-core and multi-core benchmarking |
| `report_exporter.py` | HTML and JSON export for diagnostic snapshots and comprehensive analytics reports |
| `requirements.txt` | Python package dependencies |
| `DVP_PROJECT_REPORT.md` | Academic DVP project documentation, data dictionary, methodology, and viva guide |

---

## 📸 Screenshots

> *Coming soon — add screenshots of the Dashboard, Memory, and GPU pages here.*

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

1. Fork the project
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

*Built with PySide6, psutil, and PyQtGraph.*
