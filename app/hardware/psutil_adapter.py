"""
Thin wrapper around psutil.

This is the ONLY module allowed to import psutil directly. Everything
above this layer (monitoring, processing, services, GUI) should never
touch psutil directly - see the "Important Implementation Principle"
in the project context doc.
"""

import json
import os
import re
import subprocess
import time
from pathlib import Path

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
        net_io = self._get_network_counters()

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

    @staticmethod
    def _get_network_counters():
        try:
            counters = psutil.net_io_counters()
            if counters is not None:
                return counters
        except (AttributeError, OSError, NotImplementedError):
            pass

        try:
            per_nic = psutil.net_io_counters(pernic=True)
            if per_nic:
                for stats in per_nic.values():
                    if stats is not None:
                        return stats
        except (AttributeError, OSError, NotImplementedError):
            pass

        return None

    def get_cpu_temperature(self):
        """Returns CPU temp in Celsius, or None if unavailable on this platform."""
        try:
            temps = psutil.sensors_temperatures()
        except (AttributeError, NotImplementedError, OSError):
            temps = {}

        if temps:
            # Try common sensor label groupings across Linux/Windows/Mac
            for key in ("coretemp", "k10temp", "cpu_thermal", "acpitz", "cpu"):
                if key in temps and temps[key]:
                    return temps[key][0].current

            # Fallback: just grab the first sensor group available
            first_group = next(iter(temps.values()), None)
            if first_group:
                return first_group[0].current

        return self._get_hwinfo_temperature() or self._get_windows_temperature_fallback()

    def _get_hwinfo_temperature(self):
        """Use HWiNFO if it is installed and exposing hardware sensor data."""
        if not self._is_windows():
            return None

        candidates = self._find_hwinfo_executables()
        if not candidates:
            return None

        temp_dir = Path(os.getenv("TEMP", "C:/Windows/Temp"))
        temp_dir.mkdir(parents=True, exist_ok=True)
        export_path = temp_dir / "hwinfo_cpu_temp.json"

        for exe in candidates:
            for command in (
                [exe, "/sjson", str(export_path)],
                [exe, "/sjson", str(export_path), "/file"],
                [exe, "/shtml", str(temp_dir / "hwinfo_cpu_temp.html")],
            ):
                try:
                    subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
                except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
                    continue

                if export_path.exists():
                    temp = self._parse_hwinfo_temperature(export_path)
                    if temp is not None:
                        return temp

            if export_path.exists():
                export_path.unlink(missing_ok=True)

        return None

    @staticmethod
    def _find_hwinfo_executables():
        exact_paths = [
            Path(r"C:\Users\Admin\Downloads\hwi_851_6057\HWiNFO64.exe"),
            Path(r"C:\Users\Admin\Downloads\hwi_851_6057\HWiNFO32.exe"),
            Path(r"C:\Program Files\HWiNFO\HWiNFO64.exe"),
            Path(r"C:\Program Files\HWiNFO\HWiNFO.exe"),
            Path(r"C:\Program Files (x86)\HWiNFO\HWiNFO64.exe"),
            Path(r"C:\Program Files (x86)\HWiNFO\HWiNFO.exe"),
            Path(r"C:\Program Files (x86)\IObit\Driver Booster\13.6.0\HWiNFO\HWiNFO.exe"),
        ]
        return [str(path) for path in exact_paths if path.exists()]

    @staticmethod
    def _parse_hwinfo_temperature(path: Path):
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                payload = json.load(handle)
        except (OSError, ValueError, TypeError):
            return None

        def collect_candidates(node):
            candidates = []
            if isinstance(node, dict):
                text = ""
                for key, value in node.items():
                    lower_key = str(key).lower()
                    if lower_key in {"name", "label", "sensor", "description", "text"}:
                        text = str(value)
                    if lower_key in {"value", "temperature", "current", "reading"}:
                        try:
                            candidates.append(float(value))
                        except (TypeError, ValueError):
                            pass
                    candidates.extend(collect_candidates(value))
                if text and isinstance(node.get("Value"), (int, float)):
                    candidates.append(float(node["Value"]))
                if text and any(token in text.lower() for token in ("cpu", "core", "package", "processor")):
                    for key in ("Value", "Temperature", "Current", "Reading"):
                        value = node.get(key)
                        try:
                            candidates.append(float(value))
                        except (TypeError, ValueError):
                            pass
            elif isinstance(node, list):
                for item in node:
                    candidates.extend(collect_candidates(item))
            return candidates

        values = collect_candidates(payload)
        if not values:
            return None

        filtered = [v for v in values if -50 <= v <= 150]
        if not filtered:
            return None
        return round(max(filtered), 1)

    def _get_windows_temperature_fallback(self):
        """Fallback for Windows machines where psutil doesn't expose sensor data."""
        if not self._is_windows():
            return None

        # Try the Windows-native sensor classes first.
        power_shell_commands = [
            r'(Get-CimInstance -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue | Select-Object -First 1).CurrentTemperature',
            r'(Get-CimInstance -ClassName Win32_TemperatureProbe -ErrorAction SilentlyContinue | Select-Object -First 1).CurrentTemperature',
            r'(Get-WmiObject -Class Win32_PerfFormattedData_Counters_ThermalZoneInformation -ErrorAction SilentlyContinue | Select-Object -First 1).Temperature',
        ]

        for command in power_shell_commands:
            temp = self._power_shell_float(command)
            if temp is not None:
                return temp

        # Try Windows performance counters exposed by thermal-zone classes.
        counter_commands = [
            r"Get-Counter -ErrorAction SilentlyContinue -Counter '\Thermal Zone Information(*)\Temperature'",
            r"Get-Counter -ErrorAction SilentlyContinue -Counter '\Thermal Zone Information(*)\High Precision Temperature'",
        ]
        for command in counter_commands:
            temp = self._power_shell_float(command, parse_counter_output=True)
            if temp is not None:
                return temp

        # Some desktops/laptops expose temperature sensors through third-party monitors,
        # especially OpenHardwareMonitor / LibreHardwareMonitor / HWiNFO when installed.
        sensor_namespaces = [
            "root\\OpenHardwareMonitor",
            "root\\LibreHardwareMonitor",
        ]
        for namespace in sensor_namespaces:
            command = (
                f"Get-CimInstance -Namespace '{namespace}' -ClassName Sensor -ErrorAction SilentlyContinue "
                f"| Where-Object {{ $_.SensorType -eq 'Temperature' -and ($_.Name -match 'CPU|Core|Package|Processor') }} "
                f"| Sort-Object Value -Descending | Select-Object -First 1 -ExpandProperty Value"
            )
            temp = self._power_shell_float(command)
            if temp is not None:
                return temp

        return None

    @staticmethod
    def _is_windows() -> bool:
        import platform
        return platform.system().lower() == "windows"

    @staticmethod
    def _power_shell_float(command: str, parse_counter_output: bool = False):
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            return None

        if result.returncode != 0:
            return None

        output = result.stdout.strip()
        if not output:
            return None

        if parse_counter_output:
            values = []
            for line in output.splitlines():
                matches = re.findall(r"[-+]?\d+(?:\.\d+)?", line)
                for match in matches:
                    values.append(float(match))
            if not values:
                return None
            value = max(values)
        else:
            match = re.search(r"[-+]?\d+(?:\.\d+)?", output)
            if not match:
                return None
            value = float(match.group())

        # Windows thermal values are sometimes reported in tenths of Kelvin.
        if value > 200:
            value = (value / 10.0) - 273.15
        elif value > 100:
            value = value - 273.15

        if value < -100 or value > 200:
            return None
        return round(value, 1)

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
