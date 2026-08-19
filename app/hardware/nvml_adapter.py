"""
Thin wrapper around NVIDIA's NVML library (via the pynvml package).

Gracefully degrades to "unavailable" if pynvml isn't installed or there's
no NVIDIA GPU / driver present - this should never crash the app.
"""

import os
import shutil
import subprocess


class NvmlAdapter:
    def __init__(self):
        self._available = False
        self._fallback_available = False
        self._handle = None
        self._pynvml = None

        try:
            import pynvml  # imported lazily so the whole app works without it

            pynvml.nvmlInit()
            self._pynvml = pynvml
            self._handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            self._available = True
        except Exception:
            self._available = False

    @property
    def available(self) -> bool:
        return self._available or self._fallback_available

    def get_gpu_telemetry(self):
        """Returns a dict of GPU metrics, or None if no NVIDIA GPU is available."""
        if self._available and self._pynvml and self._handle:
            try:
                pynvml = self._pynvml
                handle = self._handle
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)

                return {
                    "gpu_usage": float(util.gpu),
                    "vram_usage": round((mem.used / mem.total) * 100, 2) if mem.total else 0.0,
                    "vram_used_gb": round(mem.used / (1024 ** 3), 2),
                    "vram_total_gb": round(mem.total / (1024 ** 3), 2),
                    "gpu_temperature": float(temp),
                }
            except Exception:
                pass

        telemetry = self._read_gpu_telemetry_via_nvidia_smi()
        if telemetry:
            self._fallback_available = True
        return telemetry

    def _read_gpu_telemetry_via_nvidia_smi(self):
        candidates = ["nvidia-smi"]
        for path in (
            r"C:\Windows\System32\nvidia-smi.exe",
            r"C:\Program Files\NVIDIA Corporation\NVIDIA System Information\nvidia-smi.exe",
        ):
            if os.path.exists(path):
                candidates.append(path)

        for exe in candidates:
            try:
                result = subprocess.run(
                    [exe, "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                     "--format=csv,noheader,nounits"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
            except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
                continue

            if result.returncode != 0 or not result.stdout.strip():
                continue

            try:
                values = [part.strip() for part in result.stdout.strip().splitlines()[0].split(",")]
                gpu_usage = float(values[0])
                mem_used = float(values[1])
                mem_total = float(values[2])
                gpu_temperature = float(values[3])
            except (IndexError, ValueError):
                continue

            memory_total = max(mem_total, 1.0)
            return {
                "gpu_usage": gpu_usage,
                "vram_usage": round((mem_used / memory_total) * 100, 2),
                "vram_used_gb": round(mem_used / 1024, 2),
                "vram_total_gb": round(mem_total / 1024, 2),
                "gpu_temperature": gpu_temperature,
            }

        return None

    def shutdown(self):
        if self._available and self._pynvml:
            try:
                self._pynvml.nvmlShutdown()
            except Exception:
                pass
