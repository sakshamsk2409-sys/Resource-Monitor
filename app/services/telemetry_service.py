"""
Clean service layer between the GUI and the monitoring/hardware layers.

The GUI should ONLY ever call methods on TelemetryService - never reach
down into monitoring, hardware, or psutil/pynvml directly.
"""

from collections import deque

from app.core.constants import HISTORY_LENGTH
from app.core.models import Telemetry
from app.monitoring.collector import Collector


class TelemetryService:
    def __init__(self):
        self._collector = Collector()
        self._history: deque[Telemetry] = deque(maxlen=HISTORY_LENGTH)

    @property
    def gpu_available(self) -> bool:
        return self._collector.gpu_available

    def get_current_metrics(self) -> Telemetry:
        """Collects a fresh sample, stores it in history, and returns it."""
        sample = self._collector.collect()
        self._history.append(sample)
        return sample

    def get_history(self) -> list[Telemetry]:
        return list(self._history)

    def get_system_info(self) -> dict:
        return self._collector.get_system_info()

    def shutdown(self):
        self._collector.shutdown()
