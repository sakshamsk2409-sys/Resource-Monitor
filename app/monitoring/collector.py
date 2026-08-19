"""Combines the hardware adapters into a single raw telemetry sample."""

from app.core.models import Telemetry
from app.hardware.psutil_adapter import PsutilAdapter
from app.hardware.nvml_adapter import NvmlAdapter


class Collector:
    def __init__(self):
        self._psutil_adapter = PsutilAdapter()
        self._nvml_adapter = NvmlAdapter()

    @property
    def gpu_available(self) -> bool:
        return self._nvml_adapter.available

    def collect(self) -> Telemetry:
        cpu_usage = self._psutil_adapter.get_cpu_usage()
        mem = self._psutil_adapter.get_memory()
        io_rates = self._psutil_adapter.get_disk_and_network_rates()
        cpu_temp = self._psutil_adapter.get_cpu_temperature()

        gpu_data = self._nvml_adapter.get_gpu_telemetry()
        gpu_usage = gpu_data["gpu_usage"] if gpu_data else None
        vram_usage = gpu_data["vram_usage"] if gpu_data else None
        gpu_temp = gpu_data["gpu_temperature"] if gpu_data else None

        return Telemetry(
            timestamp=Telemetry.now_timestamp(),
            cpu_usage=cpu_usage,
            ram_usage=mem["ram_usage"],
            ram_used_gb=mem["ram_used_gb"],
            ram_total_gb=mem["ram_total_gb"],
            disk_read_mb_s=io_rates["disk_read_mb_s"],
            disk_write_mb_s=io_rates["disk_write_mb_s"],
            network_upload_mb_s=io_rates["network_upload_mb_s"],
            network_download_mb_s=io_rates["network_download_mb_s"],
            cpu_temperature=cpu_temp,
            gpu_usage=gpu_usage,
            vram_usage=vram_usage,
            gpu_temperature=gpu_temp,
        )

    def get_system_info(self) -> dict:
        return self._psutil_adapter.get_system_info()

    def shutdown(self):
        self._nvml_adapter.shutdown()
