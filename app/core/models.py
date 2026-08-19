"""Core data models shared across the app."""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional


@dataclass
class Telemetry:
    """A single snapshot of system resource state."""

    timestamp: str
    cpu_usage: float
    ram_usage: float
    ram_used_gb: float
    ram_total_gb: float
    disk_read_mb_s: float
    disk_write_mb_s: float
    network_upload_mb_s: float
    network_download_mb_s: float
    cpu_temperature: Optional[float] = None
    gpu_usage: Optional[float] = None
    vram_usage: Optional[float] = None
    gpu_temperature: Optional[float] = None

    @staticmethod
    def now_timestamp() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict:
        return asdict(self)
