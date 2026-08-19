"""
Thin wrapper around NVIDIA's NVML library (via the pynvml package).

Gracefully degrades to "unavailable" if pynvml isn't installed or there's
no NVIDIA GPU / driver present - this should never crash the app.
"""


class NvmlAdapter:
    def __init__(self):
        self._available = False
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
        return self._available

    def get_gpu_telemetry(self):
        """Returns a dict of GPU metrics, or None if no NVIDIA GPU is available."""
        if not self._available:
            return None

        pynvml = self._pynvml
        handle = self._handle

        try:
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
            return None

    def shutdown(self):
        if self._available and self._pynvml:
            try:
                self._pynvml.nvmlShutdown()
            except Exception:
                pass
