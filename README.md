# Resource Monitor — MVP

A minimal end-to-end desktop system monitor: live CPU / RAM / GPU / VRAM /
Disk / Network stats in tiles, plus a rolling multi-series graph.

This is the MVP slice of the full project described in
`RESOURCE_MONITOR_CONTEXT.txt` — one GUI tab, backed by a clean layered
architecture that the rest of the app (System Config, Memory, GPU
Performance tabs, alerts, history, export, external logs) can grow into.

## Architecture

```
GUI (main_window.py)
  -> TelemetryService        (services/telemetry_service.py)
    -> Collector              (monitoring/collector.py)
      -> PsutilAdapter        (hardware/psutil_adapter.py)
      -> NvmlAdapter          (hardware/nvml_adapter.py, optional GPU)
```

The GUI never touches `psutil` or `pynvml` directly — it only calls
`TelemetryService.get_current_metrics()` / `.get_system_info()`. This
matches the "Important Implementation Principle" from the project spec,
so swapping the GUI framework or adding SQLite history later won't
require touching the collection logic.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

> `pynvml` is only needed if you have an NVIDIA GPU. On systems without
> one (or without the package installed), GPU/VRAM tiles show "N/A" —
> the app degrades gracefully rather than crashing.

## Run

```bash
python -m app.main
```

## What's included in this MVP

- CPU usage
- RAM usage (used / total / percent)
- Disk read/write throughput (MB/s)
- Network upload/download throughput (MB/s)
- CPU temperature (where the OS/sensors expose it)
- GPU usage / VRAM usage / GPU temperature (NVIDIA only, via NVML)
- System info (OS, architecture, CPU, core count, uptime, battery)
- Live tiles + a 60-second rolling CPU/RAM/GPU graph (PyQtGraph)

## What's intentionally NOT in this MVP

Per the project's phased scope, these are left for the next pass:

- The other 3 GUI tabs (System Configuration, Memory, GPU Performance)
- SQLite history / persistence
- Alerts / thresholds
- Export (CSV/JSON)
- External log ingestion
- Process-level monitoring (per-process CPU/RAM)

## Folder structure

```
app/
├── main.py                    # entry point
├── core/
│   ├── models.py              # Telemetry dataclass
│   └── constants.py
├── hardware/
│   ├── psutil_adapter.py      # only file that imports psutil
│   └── nvml_adapter.py        # only file that imports pynvml
├── monitoring/
│   └── collector.py           # combines adapters into one Telemetry sample
├── services/
│   └── telemetry_service.py   # clean interface + rolling history buffer
└── gui/
    └── main_window.py         # PySide6 + PyQtGraph live view
```
