# Data Visualization Using Python (DVP) Mini-Project Report
## Real-Time System Telemetry Monitoring and Historical Analytics Suite

---

### Project Metadata
- **Project Title**: Autonomous Real-Time System Telemetry Monitoring and Historical Analytics Engine
- **Course**: Data Visualization Using Python (DVP)
- **Primary Frameworks**: PySide6 (Qt for Python), Pandas, NumPy, PyQtGraph, Matplotlib
- **Telemetry Sensors**: OS Hardware Interfaces (`psutil`, NVIDIA NVML, LibreHardwareMonitor Web API, Windows ACPI)
- **Author**: Senior Systems & Visualization Engineering Student

---

## 1. Executive Summary & Problem Statement

Modern computing environments require continuous visibility into physical and virtual resource utilization to diagnose performance bottlenecks, thermal throttling, memory leaks, and I/O saturation. While conventional monitoring tools (e.g., Windows Task Manager) provide fleeting real-time views, they lack:
1. **Continuous Local Telemetry Archival**: The ability to log high-resolution hardware counters to structured, reproducible CSV formats without external cloud agents.
2. **Post-Collection Data Preprocessing Pipelines**: Automated routines for time-series cleaning, timestamp alignment, duplicate detection, range enforcement, and rate derivation.
3. **Multi-Scale Statistical Analysis**: Descriptive percentile distributions, threshold breach durations, and cross-resource Pearson correlation heatmaps.
4. **Data-Driven Narrative Synthesis**: Automated contextual interpretations that connect empirical measurements (e.g., thermal lag relative to CPU bursts) without fabricating observations or conflating correlation with causation.

This project delivers a dual-capability application: a cyber-styled, real-time GUI performance cockpit and an integrated historical analytics engine capable of loading, preprocessing, visualizing, interpreting, and exporting telemetry data.

---

## 2. Authentic Telemetry Data Source Documentation

### 2.1 Authenticity & Provenance
In compliance with academic standards, **all telemetry generated and analyzed by this application originates from authentic local hardware sensors and operating system performance counters**. It is **not** a scraped or falsely attributed Kaggle dataset.

### 2.2 Telemetry Collection Mechanism
1. **Central Processor (CPU)**: Sampled via the Windows/OS kernel scheduler interface exposed through Python's `psutil.cpu_percent(interval=None)` non-blocking API.
2. **Thermal Sensors**:
   - Primary: Querying the local LibreHardwareMonitor JSON endpoint (`http://127.0.0.1:8085/data.json`) which interfaces directly with motherboard Super I/O and processor DTS (Digital Thermal Sensor) registers.
   - Secondary Fallback: Direct Windows Management Instrumentation (WMI) ACPI thermal zones (`MSAcpi_ThermalZoneTemperature`) queried via non-blocking PowerShell subroutines.
3. **Random Access Memory (RAM)**: Monitored through `psutil.virtual_memory()`, collecting physical memory allocated (`used`), available physical memory (`available`), and relative commit percentage (`percent`).
4. **Graphics Processor (NVIDIA GPU)**: Monitored via the NVIDIA Management Library (`pynvml`), directly reading PCIe board temperature, SM core load, and dedicated framebuffer VRAM utilization.
5. **Storage & Network Bandwidth Rates**: Cumulative physical hardware byte counters (`psutil.disk_io_counters()` and `psutil.net_io_counters()`) are sampled periodically. Instantaneous rates are calculated using backward finite difference:
   $$\text{Rate} = \frac{\Delta \text{Bytes}}{\Delta t} = \frac{\text{Bytes}_{t} - \text{Bytes}_{t - \Delta t}}{t - (t - \Delta t)}$$
   The pipeline explicitly accounts for the initial observation (where rate is undefined), counter resets/wraps (where $\Delta \text{Bytes} < 0$), and irregular time intervals.
6. **External Dataset Compatibility**: The analytics pipeline supports importing compatible external CSV datasets (e.g., server telemetry benchmarks, Kaggle cloud monitoring datasets) by validating schema columns and timestamp formats dynamically upon import.

---

## 3. CSV Telemetry Schema & Data Dictionary

All telemetry records captured by the logger strictly adhere to the following 19-column schema:

| Column Name | Data Type | Physical Unit | Description & Missingness Rule |
|-------------|-----------|---------------|--------------------------------|
| `timestamp` | String | ISO-8601 | Local timestamp (`YYYY-MM-DD HH:MM:SS.mmm`). Cannot be null. |
| `cpu_usage_percent` | Float | % | Total CPU utilization across all logical cores ($0.0 - 100.0\%$). |
| `cpu_temperature_c` | Float | °C | CPU package or core max temperature. Logged as empty string `""` if thermal sensor unavailable. |
| `ram_used_bytes` | Integer | Bytes | Physical RAM currently allocated by OS and user processes. |
| `ram_available_bytes` | Integer | Bytes | Physical RAM available for allocation without paging. |
| `ram_usage_percent` | Float | % | Physical RAM utilization percentage ($0.0 - 100.0\%$). |
| `gpu_usage_percent` | Float | % | Primary GPU compute core workload. Empty if no GPU present. |
| `gpu_temperature_c` | Float | °C | Primary GPU die temperature. Empty if no GPU present. |
| `gpu_memory_used_bytes` | Integer | Bytes | Dedicated GPU VRAM allocated. Empty if no GPU present. |
| `gpu_memory_total_bytes` | Integer | Bytes | Total dedicated GPU VRAM capacity. Empty if no GPU present. |
| `gpu_index` | Integer | Index | Zero-based GPU adapter index (default 0). |
| `gpu_name` | String | String | GPU model name (e.g., `NVIDIA GeForce RTX 4060`). |
| `disk_read_bytes_per_sec` | Float | Bytes/s | Storage read throughput. Empty on sample 0 or counter wrap. |
| `disk_write_bytes_per_sec` | Float | Bytes/s | Storage write throughput. Empty on sample 0 or counter wrap. |
| `network_sent_bytes_per_sec` | Float | Bytes/s | Outbound network bandwidth. Empty on sample 0 or counter wrap. |
| `network_received_bytes_per_sec` | Float | Bytes/s | Inbound network bandwidth. Empty on sample 0 or counter wrap. |
| `process_count` | Integer | Count | Total active processes currently executing. |
| `battery_percent` | Float | % | Remaining battery percentage. Empty on AC desktop computers. |
| `power_plugged` | Integer | Boolean | `1` if AC connected, `0` if battery. Empty if no battery system. |

---

## 4. Python Data Preprocessing Pipeline (`data_preprocessing.py`)

The preprocessing module implements a transparent, reproducible pipeline using **Pandas** and **NumPy**. It produces two datasets: the immutable `raw_df` and the fully processed `cleaned_df`, alongside an academic audit report.

```
[Raw CSV File] 
      │
      ▼
1. Validation & Loading ────► Schema conformance & header parsing
      │
      ▼
2. Temporal Alignment   ────► Parse ISO datetime64[ns], drop unparseable rows, chronological sort
      │
      ▼
3. Duplicate Filtering  ────► Exact row deduplication & timestamp collision resolution
      │
      ▼
4. Range Constraints    ────► Mask out-of-bounds percentages (<0% or >100%) to NaN
      │                       Mask negative throughput rates (<0 Bytes/s) to NaN
      ▼
5. Interval Auditing    ────► Time-delta distribution, irregular interval & gap identification (>2.5x median)
      │
      ▼
6. Feature Engineering  ────► Compute RAM/GPU GB, Storage MB/s, Network KB/s, Total throughputs
      │
      ▼
7. Signal Smoothing     ────► Configurable Rolling Moving Averages & Exponential Moving Averages (EMA)
      │
      ▼
[Cleaned Dataset & Audit Summary Report]
```

### 4.1 Audit Summary Metrics
The pipeline emits an exhaustive audit summary containing:
- Original vs. final cleaned record counts with retention percentages.
- Exact duplicate rows and timestamp collisions flagged and resolved.
- Invalid readings detected by category (e.g., anomalous temperature readings $>135^\circ\text{C}$).
- Detailed missing value inventory per column with percentage breakdown.
- Nominal sampling cadence (median, mean, standard deviation, and detected gap intervals).

---

## 5. Statistical Computations & Interpretations (`telemetry_statistics.py`)

### 5.1 Descriptive Statistics
For every continuous metric, the engine computes:
$$\text{Mean} = \bar{x} = \frac{1}{n} \sum_{i=1}^n x_i, \quad \text{Std Dev} = s = \sqrt{\frac{1}{n-1} \sum_{i=1}^n (x_i - \bar{x})^2}$$
In addition to Median, Minimum, Maximum, and Percentiles ($P_{25}, P_{75}, P_{95}, P_{99}$), providing insight into tail latency and peak resource demand.

### 5.2 Threshold Breach Analysis
The engine evaluates configurable operating thresholds:
- High CPU load ($>80.0\%$)
- Memory exhaustion risk ($>85.0\%$)
- Elevated thermal junction ($>80.0^\circ\text{C}$)
- Storage saturation ($>50.0\text{ MB/s}$)

For each threshold, the system computes total breach samples, estimated duration in seconds, percentage of observation time, and the **longest contiguous streak** above threshold.

### 5.3 Pearson Correlation Matrix
For all continuous numeric columns exhibiting non-zero variance, Pearson's product-moment correlation coefficient is computed:
$$r_{xy} = \frac{\sum (x_i - \bar{x})(y_i - \bar{y})}{\sqrt{\sum (x_i - \bar{x})^2 \sum (y_i - \bar{y})^2}}$$
Notable relationships ($|r| \ge 0.40$) are automatically highlighted and categorized as Moderate ($0.40 \le |r| < 0.70$) or Strong ($|r| \ge 0.70$).

### 5.4 Dynamic Interpretation Engine
Interpretations are synthesized strictly from computed empirical figures:
- **Workload Drift**: First-order linear regression slope determines whether CPU usage is systematically trending upwards, declining, or oscillating stably.
- **Thermal Lag**: Compares the timestamp of peak CPU stress with peak thermal response to demonstrate physical thermal inertia.
- **Memory Growth**: Evaluates working set expansion ($\Delta \text{RAM}$) to identify dynamic memory allocation vs. stable resident behavior.
- **Causality Disclaimer**: Explicitly emphasizes that correlation does not establish unidirectional causality.

---

## 6. Visualization Architecture

| Visualization | Library | Aesthetic & Functional Rationale |
|---------------|---------|----------------------------------|
| **CPU Utilization & Trend** | PyQtGraph | Interactive panning and zooming; dual curve rendering instantaneous load alongside rolling 5-sample moving average. |
| **Physical Memory Allocation** | PyQtGraph | Real-time tracking of memory pressure with clean grid lines and boundary scaling. |
| **Thermal Dynamics** | PyQtGraph | Simultaneous visualization of CPU and GPU temperatures with an explicit $80^\circ\text{C}$ critical threshold reference line. |
| **Storage & Network I/O** | PyQtGraph | Multi-trace comparison of Read vs. Write throughput and Download vs. Upload bandwidth. |
| **Bivariate Cross-Comparison** | Matplotlib | Scatter plot with linear regression fit line displaying paired co-variation (e.g., CPU % vs. RAM %). |
| **Resource Distributions** | Matplotlib | Dual histograms displaying probability density with vertical mean and median reference lines. |
| **Correlation Heatmap** | Matplotlib | Full-matrix heatmap annotated with two-decimal Pearson correlation coefficients and color-scaled diverging gradients. |

---

## 7. AI Insights & Diagnostic Extensions (`ai_insights.py`)

1. **Default Mode (100% Offline Rule-Based)**:
   - Evaluates CPU saturation, thermal headroom, memory allocation drift, and I/O bottlenecks deterministically.
   - Requires no API key, internet access, or external dependencies.
2. **Optional Opt-In External LLM Mode**:
   - Explicit user consent required before transmission.
   - **Data Minimization Principle**: Transmits only high-level aggregated statistical summaries (min, max, mean, percentiles). No raw telemetry, host usernames, network addresses, or file names are ever transmitted.
   - Supports Google Gemini API, OpenAI-compatible APIs, and local Ollama (`http://localhost:11434`).
   - Clear badge indicators distinguish rule-based diagnostics from AI-generated outputs.

---

## 8. Report Exporter Architecture (`report_exporter.py`)

The application generates comprehensive, publication-quality HTML and JSON diagnostic reports:
- Embedded base64 PNG charts (standalone, single-file distribution without external asset dependencies).
- Preprocessing audit tables and data quality inventories.
- Formatted descriptive statistics tables and threshold breach summaries.
- Empirical narrative interpretations and academic limitations.

---

## 9. Viva Voce Defense Guide (Frequently Asked Questions)

### Q1: How did you compute disk read/write throughput from cumulative counters?
> **Answer**: `psutil.disk_io_counters()` returns monotonic cumulative bytes transferred since system boot. To derive instantaneous throughput in bytes/second, we take the difference between consecutive samples divided by elapsed delta-time ($\Delta \text{Bytes} / \Delta t$). The first sample cannot yield a rate because no prior baseline exists, so it is cleanly represented as a missing observation (`NaN`) rather than fabricating a zero. Furthermore, counter wraps and resets are detected ($\Delta \text{Bytes} < 0$) and handled without emitting invalid negative throughput.

### Q2: Why use both PyQtGraph and Matplotlib?
> **Answer**: PyQtGraph is optimized for hardware-accelerated, real-time Qt rendering, allowing users to zoom, pan, and inspect time-series signals at 60 FPS without UI latency. Matplotlib is used for static exploratory visualizations (bivariate regression scatter plots, density histograms, and Pearson correlation heatmaps) and produces high-resolution raster images for export into the standalone HTML report.

### Q3: What is the difference between your raw and cleaned datasets?
> **Answer**: In accordance with data science best practices, raw input data is immutable. The preprocessing pipeline parses timestamps, sorts chronologically, removes duplicate records, masks out-of-bounds percentages ($<0\%$ or $>100\%$) and negative rates to `NaN`, calculates derived units (GB, MB/s, KB/s), and optionally computes rolling averages. Both datasets and the complete audit report are accessible to the user.

### Q4: How does your application ensure thread safety and GUI responsiveness?
> **Answer**: Intensive operations—such as CSV parsing, preprocessing computations, and external report generation—are executed inside dedicated `QThread` workers. The GUI thread receives processed results via thread-safe Qt Signals and Slots, preventing any application freezing. On window close, `closeEvent` terminates active worker threads, flushes CSV buffers, closes open file descriptors, and stops background subprocesses cleanly.

---

## 10. References & Standards
1. Python Software Foundation. *Python Language Reference, version 3.12*. https://www.python.org/
2. The Qt Company. *PySide6 - Official Python bindings for Qt*. https://doc.qt.io/qtforpython/
3. McKinney, W. *Data Structures for Statistical Computing in Python*. Proceedings of the 9th Python in Science Conference, 2010.
4. Hunter, J. D. *Matplotlib: A 2D Graphics Environment*. Computing in Science & Engineering, 9(3), 90-95, 2007.
5. Giampaolo Rodola. *psutil: Cross-platform lib for process and system monitoring in Python*. https://github.com/giampaolo/psutil
6. NVIDIA Corporation. *NVIDIA Management Library (NVML)*. https://developer.nvidia.com/management-library-nvml
7. LibreHardwareMonitor Project. *LibreHardwareMonitor Open Hardware Telemetry*. https://github.com/LibreHardwareMonitor/LibreHardwareMonitor
