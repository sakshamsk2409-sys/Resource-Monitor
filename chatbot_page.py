"""Offline-first assistant page with optional external LLM support."""

from __future__ import annotations

from typing import Dict

import psutil
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ai_insights import AIInsightsManager
from dashboard import CarbonFiberBackground


def collect_system_metrics() -> Dict[str, float]:
    """Return aggregate telemetry suitable for local display or LLM context."""
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    network = psutil.net_io_counters()
    return {
        "cpu": psutil.cpu_percent(interval=None),
        "memory": memory.percent,
        "memory_available_gb": memory.available / (1024**3),
        "disk": disk.percent,
        "network_sent_mb": network.bytes_sent / (1024**2),
        "network_received_mb": network.bytes_recv / (1024**2),
    }


def build_local_response(message: str, metrics: Dict[str, float]) -> str:
    """Answer a monitoring question without sending data outside the computer."""
    text = message.strip().lower()
    if not text:
        return "Please ask about CPU, memory, disk, network, system health, or available commands."
    if text in {"help", "commands", "what can you do"}:
        return "I can report current CPU, memory, disk, and network totals. Try “system status”."
    if any(word in text for word in ("cpu", "processor", "load")):
        cpu = metrics["cpu"]
        advice = "Close intensive applications or inspect the Processes page." if cpu >= 85 else "There is comfortable CPU headroom."
        return f"CPU usage is {cpu:.1f}%. {advice}"
    if any(word in text for word in ("memory", "ram", "available")):
        memory = metrics["memory"]
        advice = "Consider closing unused applications to reduce paging risk." if memory >= 85 else f"Approximately {metrics['memory_available_gb']:.1f} GB remains available."
        return f"Memory usage is {memory:.1f}%. {advice}"
    if any(word in text for word in ("disk", "storage", "drive")):
        disk = metrics["disk"]
        advice = "Free space soon to avoid application and update issues." if disk >= 90 else "Storage headroom looks acceptable."
        return f"The primary drive is {disk:.1f}% full. {advice}"
    if any(word in text for word in ("network", "internet", "traffic")):
        return f"Since startup, this system has sent {metrics['network_sent_mb']:.1f} MB and received {metrics['network_received_mb']:.1f} MB."
    if any(word in text for word in ("status", "health", "healthy", "overview")):
        return f"Current status: CPU {metrics['cpu']:.1f}%, memory {metrics['memory']:.1f}%, disk {metrics['disk']:.1f}% full."
    return "I can answer questions about current CPU, memory, disk, and network usage. Try “system status” or type “help”."


class LLMWorker(QThread):
    """Run an external provider call without blocking the Qt event loop."""

    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, question: str, provider: str, api_key: str, model: str, parent=None):
        super().__init__(parent)
        self.question = question
        self.provider = provider
        self.api_key = api_key
        self.model = model

    def run(self) -> None:
        try:
            metrics = collect_system_metrics()
            result = AIInsightsManager.query_external_ai(
                {
                    "cpu_mean": metrics["cpu"],
                    "cpu_max": metrics["cpu"],
                    "cpu_p95": metrics["cpu"],
                    "ram_mean": metrics["memory"],
                    "ram_max": metrics["memory"],
                    "disk_peak_mb": "N/A",
                    "net_peak_kb": "N/A",
                    "record_count": 1,
                },
                provider=self.provider,
                api_key=self.api_key,
                model_name=self.model,
                user_question=self.question,
            )
            self.completed.emit(result["raw_response"])
        except (ValueError, RuntimeError, OSError, KeyError) as error:
            self.failed.emit(str(error))


class ChatbotPage(CarbonFiberBackground):
    """Assistant with deterministic offline and opt-in LLM modes."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._worker = None
        self._build_ui()
        self._add_message("Monitor Assistant", "Offline mode is active by default. Ask about system health or type “help”.")

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 30, 36, 30)
        layout.setSpacing(14)

        title = QLabel("MONITOR ASSISTANT")
        title.setStyleSheet("color: #ff8f00; font-size: 24px; font-weight: bold; letter-spacing: 2px;")
        layout.addWidget(title)
        subtitle = QLabel("Use offline guidance or connect an LLM provider for richer explanations.")
        subtitle.setStyleSheet("color: #999999; font-size: 12px;")
        layout.addWidget(subtitle)

        settings = QHBoxLayout()
        settings.addWidget(QLabel("Mode:"))
        self.provider = QComboBox()
        self.provider.addItem("Offline (no network)", "offline")
        self.provider.addItem("OpenAI", "openai")
        self.provider.addItem("Google Gemini", "gemini")
        self.provider.addItem("Local Ollama", "ollama")
        self.provider.currentIndexChanged.connect(self._update_provider_state)
        settings.addWidget(self.provider)
        settings.addWidget(QLabel("Model:"))
        self.model = QLineEdit("gpt-4o-mini")
        settings.addWidget(self.model)
        self.api_key = QLineEdit()
        self.api_key.setPlaceholderText("API key (not saved)")
        self.api_key.setEchoMode(QLineEdit.Password)
        settings.addWidget(self.api_key, 1)
        layout.addLayout(settings)

        self.transcript = QTextBrowser()
        self.transcript.setOpenExternalLinks(False)
        self.transcript.setStyleSheet("QTextBrowser { background: #101010; color: #dddddd; border: 1px solid #333333; border-radius: 6px; padding: 12px; font-size: 13px; }")
        layout.addWidget(self.transcript, 1)

        input_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask: How is my system performing?")
        self.input.returnPressed.connect(self._send_message)
        input_row.addWidget(self.input, 1)
        send_button = QPushButton("Ask Assistant")
        send_button.setObjectName("accent_button")
        send_button.clicked.connect(self._send_message)
        input_row.addWidget(send_button)
        layout.addLayout(input_row)

        privacy = QLabel("Offline mode never connects. LLM mode sends only aggregate metrics and your question; API keys are never saved.")
        privacy.setAlignment(Qt.AlignCenter)
        privacy.setStyleSheet("color: #6f6f6f; font-size: 10px;")
        layout.addWidget(privacy)
        self._update_provider_state()

    def _add_message(self, author: str, message: str) -> None:
        self.transcript.append(f"<b style='color:#ff8f00'>{author}</b><br>{message}")

    def _send_message(self) -> None:
        message = self.input.text().strip()
        if not message:
            return
        self._add_message("You", message)
        self.input.clear()
        provider = self.provider.currentData()
        if provider == "offline":
            self._add_message("Monitor Assistant", build_local_response(message, collect_system_metrics()))
            return
        if provider != "ollama" and not self.api_key.text().strip():
            self._add_message("Monitor Assistant", "An API key is required for the selected provider.")
            return
        self._set_busy(True)
        self._worker = LLMWorker(message, provider, self.api_key.text().strip(), self.model.text().strip(), self)
        self._worker.completed.connect(lambda response: self._add_message("LLM Assistant", response))
        self._worker.failed.connect(lambda error: self._add_message("LLM Assistant", f"Request failed: {error}"))
        self._worker.finished.connect(lambda: self._set_busy(False))
        self._worker.start()

    def _set_busy(self, busy: bool) -> None:
        for widget in (self.input, self.provider, self.model, self.api_key):
            widget.setEnabled(not busy)

    def _update_provider_state(self) -> None:
        offline = self.provider.currentData() == "offline"
        self.model.setEnabled(not offline)
        self.api_key.setEnabled(not offline)
