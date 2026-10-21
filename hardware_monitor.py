"""Hardware Monitor integration supporting LibreHardwareMonitor and OS fallbacks.

Provides unified telemetry access for:
- CPU Load (%)
- CPU Temperature (°C)
- GPU Load (%)
- GPU Temperature (°C)

Integration layers (in priority order):
1. LibreHardwareMonitor Web Server (http://127.0.0.1:8085/data.json)
2. In-process LibreHardwareMonitorLib.dll via pythonnet (clr)
3. Windows WMI namespaces (root/LibreHardwareMonitor, root/OpenHardwareMonitor)
4. Operating system sensors (psutil, MSAcpi_ThermalZoneTemperature)
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

import psutil

# Check pythonnet availability
HAS_CLR = False
try:
    import clr
    HAS_CLR = True
except ImportError:
    HAS_CLR = False


class HardwareMonitorService:
    """Manages LibreHardwareMonitor lifecycle and extracts sensor telemetry."""

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._tools_dir = Path(__file__).resolve().parent / ".tools" / "LibreHardwareMonitor"
        self._exe_path = self._tools_dir / "LibreHardwareMonitor.exe"
        self._dll_path = self._tools_dir / "LibreHardwareMonitorLib.dll"
        self._config_path = self._tools_dir / "LibreHardwareMonitor.config"

        self.lhm_process = None
        self._lhm_tree_cached = None
        self._lhm_tree_cached_at = 0.0
        self._cache_ttl = 0.35  # seconds

        # In-process CLR Computer instance
        self._clr_computer = None
        self._clr_initialized = False

        # ACPI temperature cache
        self._acpi_temp_cached = None
        self._acpi_temp_cached_at = 0.0

        # Ensure config exists with web server enabled
        self._ensure_lhm_config()

        # Initialize CLR in-process library if available
        self._init_clr_library()

        # Start background LibreHardwareMonitor if present
        self.start_lhm()

    def _ensure_lhm_config(self):
        """Ensure LibreHardwareMonitor.config has the web server enabled on port 8085."""
        if not self._tools_dir.is_dir():
            return

        config_content = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<configuration>\n'
            '  <appSettings>\n'
            '    <add key="runWebServerMenuItem" value="true" />\n'
            '    <add key="listenerPort" value="8085" />\n'
            '    <add key="startMinMenuItem" value="true" />\n'
            '    <add key="minTrayMenuItem" value="true" />\n'
            '    <add key="minCloseMenuItem" value="true" />\n'
            '  </appSettings>\n'
            '</configuration>\n'
        )

        try:
            if not self._config_path.is_file():
                self._config_path.write_text(config_content, encoding="utf-8")
            else:
                existing = self._config_path.read_text(encoding="utf-8", errors="ignore")
                if "runWebServerMenuItem" not in existing or 'value="true"' not in existing:
                    self._config_path.write_text(config_content, encoding="utf-8")
        except OSError:
            pass

    def _init_clr_library(self):
        """Initialize in-process LibreHardwareMonitorLib.dll via pythonnet."""
        if not HAS_CLR or not sys.platform.startswith("win"):
            return
        if not self._dll_path.is_file():
            return
        if self._clr_initialized:
            return

        try:
            clr.AddReference(str(self._dll_path))
            from LibreHardwareMonitor.Hardware import Computer

            computer = Computer()
            computer.IsCpuEnabled = True
            computer.IsGpuEnabled = True
            computer.IsMotherboardEnabled = True
            computer.Open()

            self._clr_computer = computer
            self._clr_initialized = True
        except Exception:
            self._clr_computer = None
            self._clr_initialized = False

    def start_lhm(self):
        """Start the LibreHardwareMonitor executable if not already running."""
        if not sys.platform.startswith("win") or not self._exe_path.is_file():
            return

        # Check if web server is already responding
        if self.is_web_server_running():
            return

        # Check if process is already running in Task Manager
        for proc in psutil.process_iter(["name"]):
            try:
                name = proc.info.get("name") or ""
                if "librehardwaremonitor" in name.lower():
                    return
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Try to launch elevated via ShellExecute (prompts UAC if needed)
        try:
            import ctypes
            ret = ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                str(self._exe_path),
                None,
                str(self._tools_dir),
                0,  # SW_HIDE
            )
            if ret > 32:
                return
        except Exception:
            pass

        # Fallback: launch with RunAsInvoker to avoid WinError 740 elevation blocker
        try:
            env = os.environ.copy()
            env["__COMPAT_LAYER"] = "RunAsInvoker"
            self.lhm_process = subprocess.Popen(
                [str(self._exe_path)],
                cwd=str(self._tools_dir),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError:
            self.lhm_process = None

    def is_web_server_running(self):
        """Quick health check of the local LHM JSON feed."""
        try:
            with urlopen("http://127.0.0.1:8085/data.json", timeout=0.2) as resp:
                return resp.status == 200
        except (OSError, URLError, ValueError):
            return False

    def get_sensor_tree(self):
        """Fetch and cache sensor tree from local LibreHardwareMonitor web feed."""
        now = time.monotonic()
        if self._lhm_tree_cached is not None and (now - self._lhm_tree_cached_at) < self._cache_ttl:
            return self._lhm_tree_cached

        try:
            with urlopen("http://127.0.0.1:8085/data.json", timeout=0.3) as resp:
                data = json.load(resp)
                self._lhm_tree_cached = data
                self._lhm_tree_cached_at = now
                return data
        except (OSError, URLError, ValueError):
            self._lhm_tree_cached = None
            return None

    # =========================================================================
    # CPU TELEMETRY
    # =========================================================================

    @staticmethod
    def _is_cpu_node(node):
        """Identify if a JSON node corresponds to a physical CPU."""
        if not isinstance(node, dict):
            return False
        text = str(node.get("Text", "")).lower()
        img = str(node.get("ImageURL", "")).lower()

        if "cpu" in img:
            return True

        # Exclude GPUs
        if any(g in text for g in ("nvidia", "radeon", "geforce", "gpu", "graphics", "iris")):
            return False

        # Match known CPU architectures and vendors
        if any(c in text for c in ("intel", "amd", "ryzen", "core i", "xeon", "celeron", "pentium", "threadripper", "cpu", "processor")):
            return True

        # Check child SensorIds
        for child in node.get("Children", []):
            sid = str(child.get("SensorId", "")).lower()
            if "/intelcpu" in sid or "/amdcpu" in sid or "/cpu/" in sid:
                return True

        return False

    def _find_cpu_node(self, node):
        if not isinstance(node, dict):
            return None
        if self._is_cpu_node(node):
            return node
        for child in node.get("Children", []):
            found = self._find_cpu_node(child)
            if found is not None:
                return found
        return None

    @staticmethod
    def _collect_sensors(node, sensor_type):
        results = []
        if not isinstance(node, dict):
            return results
        if str(node.get("Type", "")).lower() == sensor_type.lower():
            name = str(node.get("Text", "")).lower()
            val_str = str(node.get("RawValue", node.get("Value", "")))
            try:
                # Strip units and trailing info
                clean_num = val_str.split()[0].replace("%", "").replace("°C", "").replace("°c", "").replace("C", "").strip()
                results.append((name, float(clean_num), str(node.get("SensorId", ""))))
            except (AttributeError, IndexError, ValueError):
                pass
        for child in node.get("Children", []):
            results.extend(HardwareMonitorService._collect_sensors(child, sensor_type))
        return results

    def get_lhm_web_cpu(self):
        """Query CPU load and temperature from LHM web feed."""
        sensor_tree = self.get_sensor_tree()
        if not sensor_tree:
            return None, None

        cpu_node = self._find_cpu_node(sensor_tree)
        if not cpu_node:
            return None, None

        loads = self._collect_sensors(cpu_node, "Load")
        temps = self._collect_sensors(cpu_node, "Temperature")

        # Extract CPU Load
        cpu_load = None
        for name, val, sid in loads:
            if name == "cpu total" or sid.endswith("/load/0"):
                cpu_load = val
                break
        if cpu_load is None and loads:
            cpu_load = max(val for _, val, _ in loads)

        # Extract CPU Temp
        cpu_temp = None
        clean_temps = [(n, v, s) for n, v, s in temps if "distance" not in n]
        for name, val, _ in clean_temps:
            if name == "cpu package":
                cpu_temp = val
                break
        if cpu_temp is None:
            for name, val, _ in clean_temps:
                if name == "core max":
                    cpu_temp = val
                    break
        if cpu_temp is None and clean_temps:
            cpu_temp = max(val for _, val, _ in clean_temps)

        return cpu_load, cpu_temp

    def get_clr_cpu(self):
        """Query CPU load and temperature directly from in-process LibreHardwareMonitorLib."""
        if not self._clr_computer or not self._clr_initialized:
            return None, None

        try:
            from LibreHardwareMonitor.Hardware import HardwareType, SensorType

            cpu_load = None
            cpu_temp = None

            for hardware in self._clr_computer.Hardware:
                if hardware.HardwareType == HardwareType.Cpu:
                    hardware.Update()
                    for sensor in hardware.Sensors:
                        if sensor.SensorType == SensorType.Load and sensor.Name == "CPU Total":
                            if sensor.Value is not None:
                                cpu_load = float(sensor.Value)
                        elif sensor.SensorType == SensorType.Temperature and sensor.Value is not None:
                            name = sensor.Name.lower()
                            if "distance" not in name:
                                val = float(sensor.Value)
                                if name == "cpu package":
                                    cpu_temp = val
                                elif cpu_temp is None:
                                    cpu_temp = val
            return cpu_load, cpu_temp
        except Exception:
            return None, None

    def get_wmi_cpu_temperature(self):
        """Query CPU temperature via Windows WMI sensor namespaces."""
        if not sys.platform.startswith("win"):
            return None

        now = time.monotonic()
        if (now - self._acpi_temp_cached_at) < 2.0:
            return self._acpi_temp_cached

        def run_powershell(command):
            try:
                res = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
                    capture_output=True,
                    text=True,
                    timeout=0.8,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                output = res.stdout.strip()
                if not output:
                    return []
                vals = json.loads(output)
                return vals if isinstance(vals, list) else [vals]
            except Exception:
                return []

        try:
            temperatures = [
                float(r)
                for r in run_powershell(
                    "$readings = @(); "
                    "foreach ($namespace in @('root/LibreHardwareMonitor', 'root/OpenHardwareMonitor')) { "
                    "try { $readings += Get-CimInstance -Namespace $namespace -ClassName Sensor -ErrorAction Stop | "
                    "Where-Object { $_.SensorType -eq 'Temperature' -and $_.Value -ne $null -and $_.Name -notlike '*Distance*' "
                    "-and ($_.Name -match 'CPU|Package|Core|Tdie|Tctl' -or $_.Identifier -match 'cpu') } "
                    "} catch {} }; "
                    "$readings | Select-Object -ExpandProperty Value | ConvertTo-Json -Compress"
                )
            ]
        except Exception:
            temperatures = []

        if not temperatures:
            try:
                readings = run_powershell(
                    "(Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature "
                    "| Select-Object -ExpandProperty CurrentTemperature | ConvertTo-Json -Compress)"
                )
                temperatures = [round((float(r) - 2732) / 10.0, 1) for r in readings if float(r) > 0]
            except Exception:
                temperatures = []

        self._acpi_temp_cached_at = now
        self._acpi_temp_cached = max(temperatures) if temperatures else None
        return self._acpi_temp_cached

    def get_psutil_cpu_temperature(self):
        """Query CPU temperature reported natively by psutil."""
        if not hasattr(psutil, "sensors_temperatures"):
            return self.get_wmi_cpu_temperature()

        try:
            sensor_groups = psutil.sensors_temperatures(fahrenheit=False)
        except Exception:
            return self.get_wmi_cpu_temperature()

        preferred_readings = []
        other_readings = []

        for group_name, readings in sensor_groups.items():
            group_is_cpu = any(k in group_name.lower() for k in ("coretemp", "cpu", "k10temp", "zenpower"))
            for reading in readings:
                current = getattr(reading, "current", None)
                if current is None:
                    continue
                label = getattr(reading, "label", "").lower()
                if any(k in label for k in ("package", "cpu", "tdie", "tctl")):
                    preferred_readings.append(current)
                elif group_is_cpu or "core" in label:
                    other_readings.append(current)

        if preferred_readings:
            return max(preferred_readings)
        if other_readings:
            return max(other_readings)

        return self.get_wmi_cpu_temperature()

    # =========================================================================
    # PUBLIC ACCESSORS
    # =========================================================================

    def get_cpu_load(self):
        """Return the live CPU load percentage (0.0 to 100.0).

        Tiers:
        1. LibreHardwareMonitor Web Server
        2. LibreHardwareMonitorLib.dll via CLR
        3. psutil.cpu_percent()
        """
        # Tier 1: Web server
        web_load, _ = self.get_lhm_web_cpu()
        if web_load is not None and 0.0 <= web_load <= 100.0:
            return round(float(web_load), 1)

        # Tier 2: In-process CLR
        clr_load, _ = self.get_clr_cpu()
        if clr_load is not None and 0.0 <= clr_load <= 100.0:
            return round(float(clr_load), 1)

        # Tier 3: psutil
        try:
            return round(float(psutil.cpu_percent(interval=None)), 1)
        except Exception:
            return 0.0

    def get_cpu_temperature(self):
        """Return the live CPU temperature in Celsius.

        Tiers:
        1. LibreHardwareMonitor Web Server
        2. LibreHardwareMonitorLib.dll via CLR
        3. LibreHardwareMonitor WMI / ACPI
        4. psutil sensors_temperatures()
        """
        # Tier 1: Web server
        _, web_temp = self.get_lhm_web_cpu()
        if web_temp is not None and web_temp > 0:
            return round(float(web_temp), 1)

        # Tier 2: In-process CLR
        _, clr_temp = self.get_clr_cpu()
        if clr_temp is not None and clr_temp > 0:
            return round(float(clr_temp), 1)

        # Tier 3 & 4: psutil and WMI/ACPI
        return self.get_psutil_cpu_temperature()

    def get_gpu_usage(self):
        """Return live GPU loads from LibreHardwareMonitor web server or CLR."""
        sensor_tree = self.get_sensor_tree()
        usage = []
        if sensor_tree:
            gpu_nodes = []

            def find_gpu_nodes(node):
                if not isinstance(node, dict):
                    return
                hw_type = str(node.get("HardwareType", "")).lower()
                text = str(node.get("Text", "")).lower()
                if "gpu" in hw_type or any(name in text for name in ("nvidia", "radeon", "graphics", "iris", "arc")):
                    gpu_nodes.append(node)
                for child in node.get("Children", []):
                    find_gpu_nodes(child)

            find_gpu_nodes(sensor_tree)
            for node in gpu_nodes:
                loads = self._collect_sensors(node, "Load")
                if loads:
                    preferred = [v for n, v, _ in loads if n in ("gpu core", "d3d 3d")]
                    usage.append(max(preferred if preferred else [v for _, v, _ in loads]))

        # CLR fallback for GPUs if web server not populated
        if not usage and self._clr_computer and self._clr_initialized:
            try:
                from LibreHardwareMonitor.Hardware import HardwareType, SensorType
                for h in self._clr_computer.Hardware:
                    if "gpu" in str(h.HardwareType).lower():
                        h.Update()
                        g_loads = []
                        for s in h.Sensors:
                            if s.SensorType == SensorType.Load and s.Value is not None:
                                name = s.Name.lower()
                                if any(k in name for k in ("core", "3d", "gpu")):
                                    g_loads.append(float(s.Value))
                        if g_loads:
                            usage.append(max(g_loads))
            except Exception:
                pass

        return usage[:2]

    def close(self):
        """Shut down resources and terminate background processes."""
        if self._clr_computer:
            try:
                self._clr_computer.Close()
            except Exception:
                pass
            self._clr_computer = None

        if self.lhm_process is not None and self.lhm_process.poll() is None:
            try:
                self.lhm_process.terminate()
            except Exception:
                pass
            self.lhm_process = None


# Module-level convenience functions
_default_monitor = None

def get_hardware_monitor():
    global _default_monitor
    if _default_monitor is None:
        _default_monitor = HardwareMonitorService.get_instance()
    return _default_monitor

