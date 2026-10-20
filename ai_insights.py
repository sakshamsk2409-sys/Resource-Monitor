"""Optional AI Insights Module for System Resource Monitor.

This module provides an offline-first rule-based analytics engine by default,
with an optional opt-in external AI integration (Gemini, OpenAI, or local Ollama)
that respects user consent, aggregates data safely, and operates without exposing credentials.
"""

import json
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
import pandas as pd


class AIInsightsManager:
    """Provides rule-based insights by default and optional LLM-assisted diagnosis."""

    @staticmethod
    def generate_rule_based_insights(
        df: pd.DataFrame,
        stats: Dict[str, Any],
        interpretations: Dict[str, Any],
        thresholds: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compute structured diagnostics and system engineering recommendations 100% offline."""
        insights = []
        recommendations = []

        # 1. CPU Assessment
        cpu_stat = stats.get("cpu_usage_percent", {})
        if cpu_stat:
            mean_cpu = cpu_stat.get("mean", 0)
            max_cpu = cpu_stat.get("max", 0)
            p95_cpu = cpu_stat.get("p95", 0)

            if mean_cpu > 70.0 or p95_cpu > 85.0:
                insights.append(
                    f"**Heavy CPU Saturation Detected**: Average CPU usage stood at {mean_cpu}% (p95: {p95_cpu}%). "
                    f"Workloads frequently saturated multi-core compute capacity."
                )
                recommendations.append("Profile high-CPU background threads and consider process affinity or concurrency limits.")
            elif max_cpu > 85.0 and mean_cpu < 40.0:
                insights.append(
                    f"**Transient CPU Bursting**: While average utilization was modest ({mean_cpu}%), "
                    f"short-duration spikes peaked at {max_cpu}%."
                )
                recommendations.append("CPU performance is well-dimensioned for general tasks; spikes indicate bursty IO or compilation workloads.")
            else:
                insights.append(f"**Optimal CPU Headroom**: Stable average workload ({mean_cpu}%) with healthy reserve capacity.")

        # 2. Thermal Assessment
        temp_stat = stats.get("cpu_temperature_c", {})
        if temp_stat:
            max_temp = temp_stat.get("max", 0)
            mean_temp = temp_stat.get("mean", 0)
            if max_temp >= 85.0:
                insights.append(
                    f"**Elevated Thermal Boundary**: CPU temperature peaked at {max_temp} °C (mean {mean_temp} °C). "
                    f"Approaching vendor junction limits (TjMax) may induce thermal throttling."
                )
                recommendations.append("Inspect chassis airflow, dust accumulation, or thermal paste contact if temperatures sustain above 85°C.")
            else:
                insights.append(f"**Satisfactory Cooling Dynamics**: Peak CPU temperature remained bounded at {max_temp} °C.")

        # 3. Memory Pressure
        ram_stat = stats.get("ram_usage_percent", {})
        if ram_stat:
            max_ram = ram_stat.get("max", 0)
            min_ram = ram_stat.get("min", 0)
            if max_ram >= 88.0:
                insights.append(
                    f"**Severe Memory Pressure Risk**: Maximum RAM commit reached {max_ram}%. "
                    f"High probability of disk swap/pagefile thrashing."
                )
                recommendations.append("Close heavy browser tabs or unneeded resident background applications to reclaim working set memory.")
            elif (max_ram - min_ram) > 20.0:
                insights.append(
                    f"**Dynamic Memory Allocation Drift**: RAM usage varied widely from {min_ram}% to {max_ram}%, "
                    f"signaling significant memory allocation during active procedures."
                )
            else:
                insights.append(f"**Stable Resident Memory**: RAM usage remained predictable (mean {ram_stat.get('mean', 0)}%).")

        # 4. Storage & Network IO Bottlenecks
        disk_stat = stats.get("disk_total_mb_per_sec", {})
        if disk_stat and disk_stat.get("max", 0) > 80.0:
            insights.append(
                f"**Storage I/O Surge**: Peak disk throughput reached {disk_stat.get('max')} MB/s. "
                f"Storage operations could temporarily block disk-bound tasks."
            )

        if not recommendations:
            recommendations.append("Telemetry profiles indicate healthy balanced system performance without immediate bottlenecks.")

        return {
            "mode": "RULE_BASED",
            "badge": "Offline Rule-Based Engine",
            "is_ai_generated": False,
            "disclaimer": "Diagnostic findings computed deterministically from empirical telemetry statistics.",
            "insights": insights,
            "recommendations": recommendations,
        }

    @staticmethod
    def query_external_ai(
        summary_payload: Dict[str, Any],
        provider: str = "gemini",
        api_key: str = "",
        model_name: str = "gemini-1.5-flash",
        custom_endpoint: str = "",
    ) -> Dict[str, Any]:
        """Optionally transmit sanitized, aggregated statistics to an external LLM for synthesis.
        
        Zero raw telemetry, personal files, or network addresses are ever transmitted.
        Only aggregated numerical statistics (mean, min, max, percentiles) are included in the prompt.
        """
        if not api_key and provider != "ollama":
            raise ValueError("API Key is required to invoke external AI service.")

        sanitized_summary_text = (
            f"Hardware Telemetry Summary:\n"
            f"- CPU Usage: Mean {summary_payload.get('cpu_mean')}%, Max {summary_payload.get('cpu_max')}%, 95th {summary_payload.get('cpu_p95')}%\n"
            f"- RAM Usage: Mean {summary_payload.get('ram_mean')}%, Max {summary_payload.get('ram_max')}%\n"
            f"- CPU Temp: Max {summary_payload.get('cpu_temp_max', 'N/A')} °C\n"
            f"- Peak Disk Throughput: {summary_payload.get('disk_peak_mb', 'N/A')} MB/s\n"
            f"- Peak Network: {summary_payload.get('net_peak_kb', 'N/A')} KB/s\n"
            f"- Duration: {summary_payload.get('duration_sec', 'N/A')} seconds ({summary_payload.get('record_count', 0)} samples)"
        )

        system_prompt = (
            "You are a systems performance engineer. Analyze the following aggregated telemetry summary and "
            "provide 3 concise diagnostic observations and 2 actionable engineering recommendations. "
            "Return your response formatted in clean markdown bullet points. Do not make up hypothetical specs."
        )

        user_content = f"{system_prompt}\n\n{sanitized_summary_text}"

        try:
            if provider.lower() == "gemini":
                # Google Gemini REST API v1beta
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                body = {
                    "contents": [{"parts": [{"text": user_content}]}],
                    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 600},
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(body).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=12) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    text = res_data["candidates"][0]["content"]["parts"][0]["text"]

            elif provider.lower() == "openai":
                # OpenAI Chat Completions API
                endpoint = custom_endpoint or "https://api.openai.com/v1/chat/completions"
                body = {
                    "model": model_name or "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are a senior system performance analyst."},
                        {"role": "user", "content": user_content},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 500,
                }
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(body).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=12) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    text = res_data["choices"][0]["message"]["content"]

            elif provider.lower() == "ollama":
                # Local Ollama endpoint (e.g. http://localhost:11434/api/generate)
                endpoint = custom_endpoint or "http://localhost:11434/api/generate"
                body = {
                    "model": model_name or "llama3",
                    "prompt": user_content,
                    "stream": False,
                }
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(body).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=15) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    text = res_data.get("response", "")
            else:
                raise ValueError(f"Unsupported AI provider: {provider}")

            return {
                "mode": "AI_GENERATED",
                "badge": f"AI-Generated ({provider.upper()} - {model_name})",
                "is_ai_generated": True,
                "disclaimer": "This analysis was generated by an external LLM using aggregated telemetry metrics.",
                "raw_response": text,
                "insights": [line.strip("- *# ") for line in text.split("\n") if line.strip().startswith(("-", "*", "1.", "2.", "3."))][:4],
                "recommendations": [line.strip("- *# ") for line in text.split("\n") if "recommend" in line.lower() or "suggest" in line.lower()][:2],
            }

        except Exception as e:
            raise RuntimeError(f"AI Service query failed: {e}")
