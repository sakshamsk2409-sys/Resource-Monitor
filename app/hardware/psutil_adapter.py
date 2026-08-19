"""
Thin wrapper around psutil.

This is the ONLY module allowed to import psutil directly. Everything
above this layer (monitoring, processing, services, GUI) should never
touch psutil directly - see the "Important Implementation Principle"
in the project context doc.
"""

import time
import psutil


class PsutilAdapter:
    """Wraps psutil calls and turns cumulative counters into per-second rates."""

    def __init__(self):
        self._last_disk_io = psutil.disk_io_counters()
        self._last_net_io = psutil.net_io_counters()
        self._last_sample_time = time.time()

        # Warm up cpu_percent() so the first real reading isn't 0.0
        psutil.cpu_percent(interval=None)

    def get_cpu_usage(self) -> float:
        """Overall CPU utilization percentage (0-100)."""
        return psutil.cpu_percent(interval=None)

    def get_memory(self) -> dict:
        vm = psutil.virtual_memory()
        return {
            "ram_usage": vm.percent,
            "ram_used_gb": round(vm.used / (1024 ** 3), 2),
            "ram_total_gb": round(vm.total / (1024 ** 3), 2),
        }

    def get_disk_and_network_rates(self) -> dict:
        """
        Returns disk read/write and network up/down throughput in MB/s,
        computed from the delta between this call and the previous one.
        """
        now = time.time()
        elapsed = max(now - self._last_sample_time, 1e-6)

        disk_io = psutil.disk_io_counters()
        net_io = psutil.net_io_counters()

        disk_read_mb_s = 0.0
        disk_write_mb_s = 0.0
        if disk_io and self._last_disk_io:
            disk_read_mb_s = self._bytes_to_mb_s(
                disk_io.read_bytes - self._last_disk_io.read_bytes, elapsed
            )
            disk_write_mb_s = self._bytes_to_mb_s(
                disk_io.write_bytes - self._last_disk_io.write_bytes, elapsed
            )

        net_up_mb_s = 0.0
        net_down_mb_s = 0.0
        if net_io and self._last_net_io:
            net_up_mb_s = self._bytes_to_mb_s(
                net_io.bytes_sent - self._last_net_io.bytes_sent, elapsed
            )
            net_down_mb_s = self._bytes_to_mb_s(
                net_io.bytes_recv - self._last_net_io.bytes_recv, elapsed
            )

        self._last_disk_io = disk_io
        self._last_net_io = net_io
        self._last_sample_time = now

        return {
            "disk_read_mb_s": disk_read_mb_s,
            "disk_write_mb_s": disk_write_mb_s,
            "network_upload_mb_s": net_up_mb_s,
            "network_download_mb_s": net_down_mb_s,
        }

    def get_cpu_temperature(self):
        """Returns CPU temp in Celsius, or None if unavailable on this platform."""
        try:
            temps = psutil.sensors_temperatures()
        except (AttributeError, NotImplementedError):
            return None

        if not temps:
            return None

        # Try common sensor label groupings across Linux/Windows/Mac
        for key in ("coretemp", "k10temp", "cpu_thermal", "acpitz"):
            if key in temps and temps[key]:
                return temps[key][0].current

        # Fallback: just grab the first sensor group available
        first_group = next(iter(temps.values()), None)
        if first_group:
            return first_group[0].current
        return None

    def get_system_info(self) -> dict:
        import platform

        uname = platform.uname()
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time

        battery = None
        try:
            batt = psutil.sensors_battery()
            if batt:
                battery = {
                    "percent": batt.percent,
                    "plugged_in": batt.power_plugged,
                }
        except (AttributeError, NotImplementedError):
            battery = None

        return {
            "os": f"{uname.system} {uname.release}",
            "architecture": uname.machine,
            "cpu": uname.processor or platform.processor() or "Unknown",
            "cpu_cores_physical": psutil.cpu_count(logical=False),
            "cpu_cores_logical": psutil.cpu_count(logical=True),
            "uptime_seconds": uptime_seconds,
            "battery": battery,
        }

    @staticmethod
    def _bytes_to_mb_s(delta_bytes: int, elapsed_seconds: float) -> float:
        mb_per_s = (delta_bytes / (1024 ** 2)) / elapsed_seconds
        return round(max(mb_per_s, 0.0), 3)
