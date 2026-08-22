# System Resource Monitor 📊

A modern, responsive, and feature-rich desktop application for monitoring system resource usage (CPU, RAM, Disk, Network, and GPU).

![Project Screenshot](./screenshots/system-resource-monitor-dashboard.png)

## Features

- **Dashboard View**: Real-time overview of system-wide usage.
- **Detailed Views**: Separate tabs for CPU, RAM, Disk, Network, and GPU.
- **Real-time Gauges**: Visual representation of current resource usage.
- **Process Monitoring**: Track individual process usage.
- **Dark Mode**: Built-in theme support.
- **Responsive Design**: Clean, modern UI.
- **Performance**: Optimized for real-time monitoring with minimal overhead.

## Tech Stack

- **Frontend**: Python 3.x with [Tkinter](https://docs.python.org/3/library/tk.html) (Standard GUI library for Python)
- **Visuals**: Custom styling using `ttkthemes` and standard Tkinter widgets.

## Installation

1.  **Clone the repository** (or download the source code):
    ```bash
    git clone <repository-url>
    cd Resource_Monitor
    ```

2.  **Run the application**:
    ```bash
    python system_monitor.py
    ```

## Configuration

All configuration is handled via the `config.py` file located in the root directory. You can adjust:

- **Theme**: `THEME = "clam"` (Change to `alt`, `default`, `classic`, etc.)
- **Update Interval**: `REFRESH_INTERVAL_MS = 1000` (Time in milliseconds between updates)

## Usage Guide

1.  **Open the Application**: Run `python system_monitor.py`.
2.  **Navigate**: Use the sidebar to switch between **Dashboard**, **CPU**, **RAM**, **Disk**, **Network**, and **GPU** views.
3.  **Monitor**: Observe the gauges and charts for real-time usage statistics.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

This project is licensed under the terms of the MIT license.

