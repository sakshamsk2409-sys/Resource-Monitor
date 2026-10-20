# System Resource Monitor 📊

**Project Title:** System Resource Monitor  
**Technology:** Python, PySide6  
**Project Type:** Desktop Application  
**Domain:** System Monitoring & Performance Analysis

---

## 1. Introduction

The **System Resource Monitor** is a PySide6 desktop application that provides a centralized interface for monitoring system performance and resource utilization. It combines CPU, RAM, Disk, Network, and GPU metrics into a single cyber-styled interface with real-time visualization, process management, benchmarking, and report export.

---

## 2. Problem Statement

Users often need to monitor multiple system resources while running intensive workloads, but existing tools scatter information across different utilities. This project provides a single desktop application for real-time monitoring, visualization, process management, system information, and benchmarking.

---

## 3. Objectives

1. Real-time system monitoring desktop application
2. Monitor CPU, RAM, Disk, and Network utilization
3. Provide NVIDIA GPU telemetry when available
4. Display running processes and resource consumption
5. Provide detailed system configuration information
6. CPU benchmarking (single-core, multi-core, memory throughput)
7. Export telemetry as HTML/JSON reports
8. Mini always-on-top overlay for quick monitoring
9. Modular architecture for maintainability

---

## 4. Scope

**Included:** CPU, RAM, Disk, Network, NVIDIA GPU, process monitoring, hardware info, benchmarking, real-time graphs, report generation, mini overlay.

**Excluded:** Hardware modification, overclocking, replacing OS task manager, long-term cloud monitoring.

---

## 5. Technology Stack

| Component | Technology |
|-----------|------------|
| GUI | PySide6 >= 6.7, < 7 |
| System Monitoring | psutil >= 6.0, < 8 |
| Hardware Sensors | LibreHardwareMonitor (optional local executable) |
| Real-Time Graphs | PyQtGraph >= 0.13, < 1 |
| Charts | Matplotlib >= 3.9, < 4 |
| GPU Metrics | nvidia-ml-py >= 12.0, < 14 (optional) |
| Math | numpy >= 1.26, < 3 |

---

## 6. System Architecture

The application follows a **modular architecture** with separate Python modules for each feature area.

```
                    SYSTEM RESOURCE MONITOR
                              │
                              ▼
                         main.py
                              │
             ┌────────────────┼────────────────┐
             │                │                │
             ▼                ▼                ▼
        Dashboard         Memory          GPU Monitor
             │                │                │
             └────────────────┼────────────────┘
                              │
             ┌────────────────┼────────────────┐
             │                │                │
             ▼                ▼                ▼
       Network/Disk     Process Manager   System Config
             │                │                │
             └────────────────┼────────────────┘
                              │
                              ▼
                     System Monitoring Libraries
```

---

## 7. Module Descriptions

### 7.1 Main Application (`main.py`)
Entry point. Creates the main window, manages sidebar navigation, loads pages, applies the global dark cyber-themed stylesheet, handles refresh speed changes, overlay toggle, report export, and CPU/RAM alert checking.

### 7.2 Dashboard (`dashboard.py`)
Primary monitoring interface with 6 animated gauges (CPU Load, CPU Temp, RAM Load, GPU Core Load, GPU Memory, GPU Temp), telemetry cards, PyQtGraph history graphs, customizable per-gauge refresh presets, startup sweep animation, and automatic LibreHardwareMonitor launch on Windows.

### 7.3 Memory Analytics (`memory.py`)
Detailed RAM utilization with animated donut chart, per-application memory tracking with executable icons, view modes (Grouped, Top Processes, All Processes), RAM history graph, and background worker thread for non-blocking process scanning.

### 7.4 GPU Performance (`gpu_page.py`)
NVIDIA GPU telemetry via `nvidia-ml-py` (utilization, temperature, VRAM, power, clock) with Matplotlib history graphs. GPU core load on the dashboard is also supported via LibreHardwareMonitor (NVIDIA, AMD, Intel). Graceful fallback when no GPU is detected.

### 7.5 Network and Disk (`network_disk_page.py`)
Real-time upload/download speeds, disk read/write throughput, PyQtGraph history graphs, and an active network sockets table with local/remote addresses, status, and PID.

### 7.6 Process Manager (`process_manager.py`)
Live process table with PID, Name, Status, CPU %, RAM MB, RAM %, and User columns. Supports search/filter, terminate, and force-kill with confirmation dialogs. Color-coded high-usage indicators (🔥 high CPU, 💾 high RAM). Background worker thread for efficient scanning.

### 7.7 System Configuration (`system_config.py`)
Static and dynamic system info: OS, processor, memory, uptime (refreshed every 2s), disk partitions with usage warnings (>85% red), and network interfaces with IPv4, MAC, and link status.

### 7.8 Mini Overlay (`mini_overlay.py`)
Compact, always-on-top, frameless, draggable widget showing CPU, RAM, GPU Temperature, and Network throughput. Refresh interval syncs with the main window speed selector.

### 7.9 Benchmark (`benchmark_page.py`)
CPU single-core and multi-core stress tests plus memory throughput benchmark using `concurrent.futures`. Real-time progress tracking and score calculation.

### 7.10 Report Exporter (`report_exporter.py`)
Exports a full system telemetry snapshot to timestamped HTML and JSON files. HTML reports open automatically in the default browser.

---

## 8. Data Collection

Data flows from the OS through monitoring libraries into the PySide6 interface:

```text
Operating System
       ↓
psutil / nvidia-ml-py / LibreHardwareMonitor
       ↓
Python Application
       ↓
Processing / Formatting
       ↓
PySide6 Interface
       ↓
Charts / Gauges / Tables
```

CPU temperature uses a multi-source fallback: LibreHardwareMonitor web feed → psutil sensors → Windows WMI / PowerShell thermal zones.

---

## 9. Real-Time Monitoring

The application periodically refreshes displayed information:

```text
Collect Data → Process Data → Update Interface → Update Graph → Wait → Repeat
```

Historical values are maintained for graphs. Timer intervals are adjustable via the sidebar Refresh Speed dropdown, and individual gauges support custom refresh presets saved to `gauge_presets.json`.

---

## 10. User Interface Design

Cyber-styled interface with a carbon-fiber textured background, sidebar navigation, animated gauge dials with color-coded status (NORMAL / HIGH / REDLINE), and consistent dark theme across all pages.

| Information | Visualization |
|-------------|---------------|
| CPU usage | Gauge / graph |
| RAM usage | Gauge / donut chart |
| GPU usage | Graph / gauge |
| Network activity | Line graph + sockets table |
| Disk activity | Line graph |
| Processes | Table with indicators |
| System information | Information panels |

---

## 11. Design Decisions

1. **Modular Architecture** — Separate files per feature reduce complexity and enable independent development.
2. **PySide6** — Modern Qt-based GUI framework for Python.
3. **psutil** — Unified interface for CPU, memory, disk, network, and process information.
4. **PyQtGraph** — Efficient plotting for high-frequency real-time graph updates.
5. **Optional NVIDIA Monitoring** — Graceful fallback ensures the app works without an NVIDIA GPU.
6. **LibreHardwareMonitor Integration** — Optional local executable extends sensor coverage (CPU package temp, AMD/Intel GPU load) with fallback to psutil and Windows WMI.
7. **Background Workers** — QThread workers for memory and process scanning prevent UI blocking.
8. **Per-Gauge Refresh Presets** — Different metrics update at different rates; presets reduce unnecessary overhead.

---

## 12. Project Structure

```text
Resource-Monitor/
├── main.py
├── dashboard.py
├── memory.py
├── gpu_page.py
├── network_disk_page.py
├── process_manager.py
├── system_config.py
├── mini_overlay.py
├── benchmark_page.py
├── report_exporter.py
├── requirements.txt
├── README.md
├── Documentation.md
├── LICENSE
└── assets/
    └── audio/
        └── cockpit_startup.wav
```

---

## 13. Installation

```bash
git clone https://github.com/yourusername/System-Resource-Monitor.git
cd System-Resource-Monitor/Resource-Monitor
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate   # Linux / macOS
pip install -r requirements.txt
```

*(Optional, Windows)* Place `LibreHardwareMonitor.exe` at `.tools/LibreHardwareMonitor/` for extended sensor data.

Run:
```bash
python main.py
```

---

## 14. Requirements

- Python 3.8+
- PySide6, psutil, PyQtGraph, Matplotlib, numpy
- nvidia-ml-py (optional, for NVIDIA GPU metrics)
- LibreHardwareMonitor (optional, Windows only)

---

## 15. Testing

- **CPU/RAM:** Verify values change under load; alerts update in sidebar.
- **Disk/Network:** Perform file transfers and observe I/O graphs.
- **GPU:** Run GPU-intensive tasks and verify NVIDIA telemetry or LHM dashboard values.
- **Process Manager:** Search, terminate, and force-kill processes.
- **Benchmark:** Run full suite and verify progress and scores.
- **Report Exporter:** Verify HTML and JSON files are generated and HTML opens in browser.
- **Overlay:** Verify always-on-top behavior, dragging, and metric updates.

---

## 16. Limitations

1. NVIDIA telemetry requires compatible GPU and drivers.
2. AMD/Intel GPU details are limited to dashboard via LibreHardwareMonitor.
3. Benchmark scores vary with background load.
4. CPU temperature depends on available sensors.
5. Process termination requires appropriate permissions.
6. LibreHardwareMonitor is Windows-only.

---

## 17. Future Enhancements

- Dedicated AMD/Intel GPU pages
- Long-term history and trend analytics
- Configurable alerts and notifications
- CSV export
- System tray integration
- Customizable dashboard layouts
- GPU and storage benchmarks
- Advanced process analytics

---

## 18. Conclusion

The System Resource Monitor centralizes real-time system monitoring, visualization, process management, benchmarking, and reporting in a modular PySide6 application. It demonstrates practical use of PySide6, psutil, PyQtGraph, Matplotlib, nvidia-ml-py, and LibreHardwareMonitor.

---

## 19. Team Summary

| Member | Contribution |
|--------|--------------|
| **Madhoor** | GPU Performance |
| **Saksham** | Dashboard & Memory Analytics |
| **Kuntal** | System Configuration & Network/Disk |
| **Sid** | Documentation |
| **Manan** | Design Abstraction / Integration |

---

## 20. License

MIT License
