"""Telemetry Logger module for System Resource Monitor.

This module provides continuous, non-blocking hardware telemetry logging to CSV
files according to a strictly defined, documented schema. It calculates true rates
from cumulative system counters, handles missing sensors gracefully by logging empty
fields (instead of zero), and stops cleanly upon application exit.
"""

import os
import csv
import time
import datetime
import psutil
from pathlib import Path
from PySide6.QtCore import QObject, QTimer, Signal, Slot

try:
    import pynvml
    HAS_PYNVML = True
except ImportError:
    pynvml = None
    HAS_PYNVML = False

from urllib.request import urlopen
from urllib.error import URLError
import json


# =====================================================================
# DOCUMENTED CSV SCHEMA & METADATA
# =====================================================================

SCHEMA_COLUMNS = [
    "timestamp",
    "cpu_usage_percent",
    "cpu_temperature_c",
    "ram_used_bytes",
    "ram_available_bytes",
    "ram_usage_percent",
    "gpu_usage_percent",
    "gpu_temperature_c",
    "gpu_memory_used_bytes",
    "gpu_memory_total_bytes",
    "gpu_index",
    "gpu_name",
    "disk_read_bytes_per_sec",
    "disk_write_bytes_per_sec",
    "network_sent_bytes_per_sec",
    "network_received_bytes_per_sec",
    "process_count",
    "battery_percent",
    "power_plugged",
]

COLUMN_METADATA = {
    "timestamp": {
        "unit": "ISO-8601 string",
        "description": "Local ISO timestamp of sample collection (YYYY-MM-DD HH:MM:SS.mmm)",
        "type": "datetime",
    },
    "cpu_usage_percent": {
        "unit": "%",
        "description": "Total CPU utilization percentage across all cores (0.0 - 100.0)",
        "type": "float",
    },
    "cpu_temperature_c": {
        "unit": "°C",
        "description": "CPU package / core max temperature in Celsius. Empty if sensor unavailable.",
        "type": "float",
    },
    "ram_used_bytes": {
        "unit": "bytes",
        "description": "Physical RAM currently allocated and in use",
        "type": "integer",
    },
    "ram_available_bytes": {
        "unit": "bytes",
        "description": "Physical RAM available for allocation without swapping",
        "type": "integer",
    },
    "ram_usage_percent": {
        "unit": "%",
        "description": "RAM utilization percentage relative to total physical RAM (0.0 - 100.0)",
        "type": "float",
    },
    "gpu_usage_percent": {
        "unit": "%",
        "description": "NVIDIA / Primary GPU core workload percentage (0.0 - 100.0). Empty if unavailable.",
        "type": "float",
    },
    "gpu_temperature_c": {
        "unit": "°C",
        "description": "Primary GPU die temperature in Celsius. Empty if unavailable.",
        "type": "float",
    },
    "gpu_memory_used_bytes": {
        "unit": "bytes",
        "description": "Dedicated GPU VRAM currently in use. Empty if unavailable.",
        "type": "integer",
    },
    "gpu_memory_total_bytes": {
        "unit": "bytes",
        "description": "Total dedicated GPU VRAM installed. Empty if unavailable.",
        "type": "integer",
    },
    "gpu_index": {
        "unit": "index",
        "description": "Zero-based hardware index of the monitored GPU adapter (e.g., 0).",
        "type": "integer",
    },
    "gpu_name": {
        "unit": "string",
        "description": "Hardware model identifier of the GPU adapter.",
        "type": "string",
    },
    "disk_read_bytes_per_sec": {
        "unit": "bytes/sec",
        "description": "Storage read throughput computed as delta(read_bytes) / delta(time). Empty on first sample or counter reset.",
        "type": "float",
    },
    "disk_write_bytes_per_sec": {
        "unit": "bytes/sec",
        "description": "Storage write throughput computed as delta(write_bytes) / delta(time). Empty on first sample or counter reset.",
        "type": "float",
    },
    "network_sent_bytes_per_sec": {
        "unit": "bytes/sec",
        "description": "Network outbound bandwidth computed as delta(bytes_sent) / delta(time). Empty on first sample or counter reset.",
        "type": "float",
    },
    "network_received_bytes_per_sec": {
        "unit": "bytes/sec",
        "description": "Network inbound bandwidth computed as delta(bytes_recv) / delta(time). Empty on first sample or counter reset.",
        "type": "float",
    },
    "process_count": {
        "unit": "count",
        "description": "Current number of active system processes.",
        "type": "integer",
    },
    "battery_percent": {
        "unit": "%",
        "description": "Remaining battery capacity percentage (0.0 - 100.0). Empty if no battery present.",
        "type": "float",
    },
    "power_plugged": {
        "unit": "boolean",
        "description": "1 if AC power is connected, 0 if on battery power. Empty if no battery system.",
        "type": "integer",
    },
}


# =====================================================================
# TELEMETRY SAMPLER
# =====================================================================

class TelemetrySampler:
    """Samples hardware metrics and computes valid instantaneous rates."""

    def __init__(self, temperature_provider=None, cpu_provider=None):
        self.temperature_provider = temperature_provider
        self.cpu_provider = cpu_provider

        # NVML initialization
        self.gpu_available = False
        self.gpu_handle = None
        self.gpu_name = None
        self._init_nvml()

        # Cumulative counter tracking for rate computation
        self._last_time = None
        self._last_disk = None
        self._last_net = None

        # Prime CPU percent measurement
        psutil.cpu_percent(interval=None)

    def _init_nvml(self):
        if not HAS_PYNVML or not pynvml:
            return
        try:
            pynvml.nvmlInit()
            count = pynvml.nvmlDeviceGetCount()
            if count > 0:
                self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                self.gpu_available = True
                name = pynvml.nvmlDeviceGetName(self.gpu_handle)
                if isinstance(name, bytes):
                    name = name.decode("utf-8", errors="ignore")
                self.gpu_name = str(name)
        except Exception:
            self.gpu_available = False
            self.gpu_handle = None

    def reset_counters(self):
        """Reset historical counters so the next sample establishes a fresh baseline."""
        self._last_time = None
        self._last_disk = None
        self._last_net = None

    def _get_cpu_temperature(self):
        """Query CPU temperature via provider callback or local fallbacks."""
        if self.temperature_provider and callable(self.temperature_provider):
            try:
                temp = self.temperature_provider()
                if temp is not None and temp > 0:
                    return round(float(temp), 1)
            except Exception:
                pass

        # Try LHM web server if running
        try:
            with urlopen("http://127.0.0.1:8085/data.json", timeout=0.15) as resp:
                sensor_tree = json.load(resp)
                # Traverse tree for CPU package
                def find_temp(node):
                    if not isinstance(node, dict):
                        return None
                    if node.get("Type") == "Temperature" and "distance" not in node.get("Text", "").lower():
                        try:
                            raw = node.get("RawValue", node.get("Value", ""))
                            val = float(str(raw).split()[0])
                            if "cpu" in node.get("Text", "").lower() or "package" in node.get("Text", "").lower():
                                return val
                        except Exception:
                            pass
                    for child in node.get("Children", []):
                        found = find_temp(child)
                        if found is not None:
                            return found
                    return None
                val = find_temp(sensor_tree)
                if val is not None:
                    return round(val, 1)
        except Exception:
            pass

        # Fallback to psutil if available on this platform
        if hasattr(psutil, "sensors_temperatures"):
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        for entry in entries:
                            if getattr(entry, "current", None) is not None:
                                return round(float(entry.current), 1)
            except Exception:
                pass

        return None

    def sample(self) -> dict:
        """Collect one timestamped telemetry record conforming to SCHEMA_COLUMNS.
        
        Unavailable values are returned as None (which serialize to empty string in CSV).
        """
        now = time.time()
        iso_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        # 1. CPU
        try:
            if self.cpu_provider and callable(self.cpu_provider):
                val = self.cpu_provider()
                cpu_usage = round(float(val), 1) if val is not None else round(float(psutil.cpu_percent(interval=None)), 1)
            else:
                cpu_usage = round(float(psutil.cpu_percent(interval=None)), 1)
        except Exception:
            try:
                cpu_usage = round(float(psutil.cpu_percent(interval=None)), 1)
            except Exception:
                cpu_usage = None

        cpu_temp = self._get_cpu_temperature()

        # 2. RAM
        try:
            vm = psutil.virtual_memory()
            ram_used = int(vm.used)
            ram_available = int(vm.available)
            ram_usage = round(float(vm.percent), 1)
        except Exception:
            ram_used = None
            ram_available = None
            ram_usage = None

        # 3. GPU
        gpu_usage = None
        gpu_temp = None
        gpu_mem_used = None
        gpu_mem_total = None
        gpu_idx = None
        gpu_name = None

        if self.gpu_available and self.gpu_handle:
            gpu_idx = 0
            gpu_name = self.gpu_name
            try:
                util = pynvml.nvmlDeviceGetUtilizationRates(self.gpu_handle)
                gpu_usage = round(float(util.gpu), 1)
            except Exception:
                pass

            try:
                temp = pynvml.nvmlDeviceGetTemperature(self.gpu_handle, pynvml.NVML_TEMPERATURE_GPU)
                gpu_temp = round(float(temp), 1)
            except Exception:
                pass

            try:
                mem = pynvml.nvmlDeviceGetMemoryInfo(self.gpu_handle)
                gpu_mem_used = int(mem.used)
                gpu_mem_total = int(mem.total)
            except Exception:
                pass

        # 4. Storage Throughput (bytes/sec)
        disk_read_sec = None
        disk_write_sec = None
        try:
            curr_disk = psutil.disk_io_counters()
        except Exception:
            curr_disk = None

        # 5. Network Throughput (bytes/sec)
        net_sent_sec = None
        net_recv_sec = None
        try:
            curr_net = psutil.net_io_counters()
        except Exception:
            curr_net = None

        # Calculate throughput rates if we have previous baseline
        if self._last_time is not None:
            dt = now - self._last_time
            if dt > 0.05:  # Ensure meaningful time step
                # Disk rates
                if curr_disk and self._last_disk:
                    delta_read = curr_disk.read_bytes - self._last_disk.read_bytes
                    delta_write = curr_disk.write_bytes - self._last_disk.write_bytes
                    if delta_read >= 0 and delta_write >= 0:
                        disk_read_sec = round(delta_read / dt, 2)
                        disk_write_sec = round(delta_write / dt, 2)
                    else:
                        # Counter reset or wrap occurred; omit rate for this sample
                        pass

                # Network rates
                if curr_net and self._last_net:
                    delta_sent = curr_net.bytes_sent - self._last_net.bytes_sent
                    delta_recv = curr_net.bytes_recv - self._last_net.bytes_recv
                    if delta_sent >= 0 and delta_recv >= 0:
                        net_sent_sec = round(delta_sent / dt, 2)
                        net_recv_sec = round(delta_recv / dt, 2)
                    else:
                        # Counter reset occurred
                        pass

        # Update last baselines
        self._last_time = now
        self._last_disk = curr_disk
        self._last_net = curr_net

        # 6. Process count
        try:
            proc_count = len(psutil.pids())
        except Exception:
            proc_count = None

        # 7. Battery
        battery_pct = None
        power_plugged = None
        try:
            batt = psutil.sensors_battery()
            if batt is not None:
                battery_pct = round(float(batt.percent), 1)
                power_plugged = 1 if batt.power_plugged else 0
        except Exception:
            pass

        return {
            "timestamp": iso_timestamp,
            "cpu_usage_percent": cpu_usage,
            "cpu_temperature_c": cpu_temp,
            "ram_used_bytes": ram_used,
            "ram_available_bytes": ram_available,
            "ram_usage_percent": ram_usage,
            "gpu_usage_percent": gpu_usage,
            "gpu_temperature_c": gpu_temp,
            "gpu_memory_used_bytes": gpu_mem_used,
            "gpu_memory_total_bytes": gpu_mem_total,
            "gpu_index": gpu_idx,
            "gpu_name": gpu_name,
            "disk_read_bytes_per_sec": disk_read_sec,
            "disk_write_bytes_per_sec": disk_write_sec,
            "network_sent_bytes_per_sec": net_sent_sec,
            "network_received_bytes_per_sec": net_recv_sec,
            "process_count": proc_count,
            "battery_percent": battery_pct,
            "power_plugged": power_plugged,
        }


# =====================================================================
# REUSABLE TELEMETRY LOGGER (GUI INTEGRATED)
# =====================================================================

class TelemetryLogger(QObject):
    """Manages CSV logging sessions cleanly without blocking the UI thread."""

    STATUS_STOPPED = "STOPPED"
    STATUS_RECORDING = "RECORDING"
    STATUS_PAUSED = "PAUSED"

    sample_logged = Signal(dict)
    status_changed = Signal(str)
    stats_updated = Signal(int, float, str)  # record_count, elapsed_seconds, file_path
    error_occurred = Signal(str)

    def __init__(self, temperature_provider=None, cpu_provider=None, parent=None):
        super().__init__(parent)
        self.sampler = TelemetrySampler(temperature_provider=temperature_provider, cpu_provider=cpu_provider)

        self._status = self.STATUS_STOPPED
        self._file = None
        self._writer = None
        self._file_path = None
        self._record_count = 0
        self._elapsed_seconds = 0.0
        self._sampling_interval = 1.0  # seconds

        self._last_tick_time = None

        # Dedicated QTimer for sampling cadence
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer_tick)

    # -----------------------------------------------------------------
    # State inspection
    # -----------------------------------------------------------------

    @property
    def status(self) -> str:
        return self._status

    @property
    def is_recording(self) -> bool:
        return self._status == self.STATUS_RECORDING

    @property
    def is_paused(self) -> bool:
        return self._status == self.STATUS_PAUSED

    @property
    def is_stopped(self) -> bool:
        return self._status == self.STATUS_STOPPED

    @property
    def record_count(self) -> int:
        return self._record_count

    @property
    def elapsed_seconds(self) -> float:
        return self._elapsed_seconds

    @property
    def file_path(self) -> str:
        return self._file_path or ""

    @property
    def sampling_interval(self) -> float:
        return self._sampling_interval

    # -----------------------------------------------------------------
    # Control API
    # -----------------------------------------------------------------

    def set_sampling_interval(self, interval_sec: float):
        """Set the sampling interval in seconds (e.g. 0.25, 0.5, 1.0, 2.0)."""
        self._sampling_interval = max(0.1, float(interval_sec))
        if self._timer.isActive():
            self._timer.setInterval(int(self._sampling_interval * 1000))

    def start_logging(self, file_path: str = None, interval_sec: float = None) -> str:
        """Start a new logging session.
        
        If file_path is None, creates a timestamped file in data/logs/.
        Returns the absolute path to the active CSV file.
        """
        if self.is_recording:
            return self._file_path

        if interval_sec is not None:
            self.set_sampling_interval(interval_sec)

        # If resuming from pause on same file, delegate to resume_logging
        if self.is_paused and self._file is not None and (file_path is None or file_path == self._file_path):
            self.resume_logging()
            return self._file_path

        # Clean up any existing file handle
        self._close_file()

        # Determine target file path
        if not file_path:
            log_dir = Path("data") / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            target_path = log_dir / f"resource_log_{timestamp}.csv"
        else:
            target_path = Path(file_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)

        self._file_path = str(target_path.resolve())

        try:
            # Check if file exists and has content to avoid duplicate headers
            file_exists = target_path.exists() and target_path.stat().st_size > 0

            # Open file with UTF-8 encoding and newline='' for CSV compliance
            self._file = open(self._file_path, "a", newline="", encoding="utf-8")
            self._writer = csv.DictWriter(
                self._file,
                fieldnames=SCHEMA_COLUMNS,
                restval="",
                extrasaction="ignore"
            )

            if not file_exists:
                self._writer.writeheader()
                self._file.flush()

            self._record_count = 0
            self._elapsed_seconds = 0.0
            self._last_tick_time = time.time()
            self.sampler.reset_counters()

            self._status = self.STATUS_RECORDING
            self.status_changed.emit(self._status)
            self.stats_updated.emit(self._record_count, self._elapsed_seconds, self._file_path)

            self._timer.start(int(self._sampling_interval * 1000))
            return self._file_path

        except Exception as e:
            self._close_file()
            self._status = self.STATUS_STOPPED
            self.status_changed.emit(self._status)
            self.error_occurred.emit(f"Failed to start CSV logging: {e}")
            return ""

    def pause_logging(self):
        """Temporarily pause recording without closing the file or resetting counts."""
        if not self.is_recording:
            return

        self._timer.stop()
        if self._file:
            try:
                self._file.flush()
            except Exception:
                pass

        self._status = self.STATUS_PAUSED
        self._last_tick_time = None
        self.status_changed.emit(self._status)

    def resume_logging(self):
        """Resume recording after a pause."""
        if not self.is_paused or self._file is None:
            return

        self.sampler.reset_counters()
        self._last_tick_time = time.time()
        self._status = self.STATUS_RECORDING
        self.status_changed.emit(self._status)
        self._timer.start(int(self._sampling_interval * 1000))

    def stop_logging(self):
        """Permanently stop logging, flush data and close file cleanly."""
        if self.is_stopped:
            return

        self._timer.stop()
        self._close_file()
        self._status = self.STATUS_STOPPED
        self._last_tick_time = None
        self.status_changed.emit(self._status)
        self.stats_updated.emit(self._record_count, self._elapsed_seconds, self._file_path or "")

    def _close_file(self):
        if self._file:
            try:
                self._file.flush()
                self._file.close()
            except Exception:
                pass
            finally:
                self._file = None
                self._writer = None

    # -----------------------------------------------------------------
    # Timer tick handler
    # -----------------------------------------------------------------

    @Slot()
    def _on_timer_tick(self):
        if not self.is_recording or not self._file or not self._writer:
            return

        now = time.time()
        if self._last_tick_time is not None:
            self._elapsed_seconds += (now - self._last_tick_time)
        self._last_tick_time = now

        try:
            record = self.sampler.sample()

            # Format record values for CSV serialization: None -> ""
            row_dict = {}
            for col in SCHEMA_COLUMNS:
                val = record.get(col)
                if val is None:
                    row_dict[col] = ""
                else:
                    row_dict[col] = val

            self._writer.writerow(row_dict)
            self._file.flush()

            self._record_count += 1
            self.sample_logged.emit(record)
            self.stats_updated.emit(self._record_count, self._elapsed_seconds, self._file_path)

        except Exception as e:
            self.error_occurred.emit(f"Error writing telemetry sample: {e}")
            # If disk write failure, safely stop
            if isinstance(e, (OSError, IOError)):
                self.stop_logging()
