# System Resource Monitor

A Windows desktop application for real-time CPU, GPU, motherboard, and fan telemetry. It uses LibreHardwareMonitor through Python.NET and provides live charts, temperature alerts, CSV logging, and interactive HTML reports.

## Features

- Live hardware sensor readings
- CPU/GPU temperature, load, and fan-speed charts
- Configurable polling interval and temperature alert limit
- Windows notifications for high temperatures
- CSV telemetry logging
- Interactive Plotly HTML report export

## Requirements

- Windows 10 or later
- Python 3.10+
- The included `LibreHardwareMonitorLib.dll` in the same folder as the application

## Installation

Clone the repository and open a PowerShell terminal in its folder:

```powershell
git clone https://github.com/sakshamsk2409-sys/System-Resource-Monitor.git
cd System-Resource-Monitor
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run

```powershell
python advanced_hardware_monitor.py
```

If the app cannot access sensors, run PowerShell as Administrator and start it again.

## Output files

When logging is enabled, the application creates `hardware_log_*.csv` files. After logging stops, choose **Export HTML Report** to create `hardware_log_*_report.html`. These generated files are intentionally not committed to Git.

## Project files

| File | Purpose |
| --- | --- |
| `advanced_hardware_monitor.py` | Main desktop application |
| `LibreHardwareMonitorLib.dll` | Hardware-sensor backend |
| `requirements.txt` | Python dependencies |

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE).

