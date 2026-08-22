# System Resource Monitor 📊

A modern, high-performance PySide6 desktop application for real-time monitoring of system resource usage (CPU, RAM, Disk, Network, and GPU).

## Features

- **Performance Cockpit Dashboard**: Real-time telemetry, gauge visualization, and GPU telemetry.
- **Memory Analytics View**: Live memory breakdown, process memory donut chart, and active application resource consumption tracking.
- **System Telemetry**: Real-time graphs powered by PySide6 and PyQtGraph.
- **Sleek Cyber-Dark UI**: Carbon-fiber styling with hardware status indicators.

## Tech Stack

- **GUI Framework**: [PySide6](https://pypi.org/project/PySide6/) (Qt for Python)
- **Telemetry & Metrics**: [psutil](https://pypi.org/project/psutil/)
- **Real-Time Plotting**: [pyqtgraph](https://pypi.org/project/pyqtgraph/)
- **GPU Metrics**: [nvidia-ml-py](https://pypi.org/project/nvidia-ml-py/) (Optional for NVIDIA GPU support)

## Requirements & Installation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application**:
   ```bash
   python main.py
   ```

## Project Structure

- `main.py`: Main application entry point, sidebar navigation, and global UI theme.
- `dashboard.py`: Dashboard view with real-time gauges, performance graphs, and telemetry cards.
- `memory.py`: Detailed Memory view with memory donut chart and process tracking.
- `requirements.txt`: Python package dependencies.

## License

This project is licensed under the terms of the MIT license.
