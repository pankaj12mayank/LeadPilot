from __future__ import annotations

import os

import requests
import config
import subprocess
import time
from backend.utils.logger import get_logger

from backend.services import runtime_settings


logger = get_logger(__name__)


def ensure_ollama_ready():
    for _ in range(3):
        try:
            requests.get("http://localhost:11434", timeout=2)
            return
        except Exception:
            time.sleep(1)

    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        logger.error("Failed to start Ollama server")
        return

    for _ in range(10):
        try:
            requests.get("http://localhost:11434", timeout=2)
            break
        except Exception:
            time.sleep(1)

    try:
        subprocess.run(
            ["ollama", "pull", runtime_settings.get_model_name()],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        logger.error("Failed to pull model")


def _call_ollama(prompt: str) -> str | None:
    """Return model text or None on failure."""
    if runtime_settings.get_free_api_mode():
        return None

    if not runtime_settings.get_use_ollama():
        return None

    ensure_ollama_ready()

    try:
        model = runtime_settings.get_model_name()
        logger.info(f"Sending request to Ollama with model: {model}")
        response = requests.post(
            config.OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        if "response" in data and data["response"]:
            return str(data["response"]).strip()
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        logger.error("Ollama connection failed — using fallback copy")
    except Exception:
        logger.error("Invalid response from Ollama — using fallback copy")
    return None


def _fallback_subject(lead: dict) -> str:
    name = lead.get("name") or "there"
    company = str(lead.get("company") or "").strip()
    plat = str(lead.get("platform") or "").replace("_", " ").title()
    if company:
        return f"Quick intro — {name} @ {company}"
    return f"Collaboration idea for {name} ({plat})"


def _fallback_message(lead: dict) -> str:
    name = lead.get("name") or "there"
    platform = lead.get("platform") or "your platform"
    subj = str(lead.get("subject") or "").strip()
    sub_line = f" (re: {subj})" if subj else ""
    return (
        f"Hi {name},\n\n"
        f"I came across your profile on {platform}{sub_line} and wanted to reach out. "
        f"We build high-quality web, app, and AI solutions for growing teams.\n\n"
        f"If you're open to a brief chat, reply here and we can find a time.\n\n"
        f"Best regards"
    )


def generate_subject(lead: dict) -> str:
    if runtime_settings.get_free_api_mode():
        return _fallback_subject(lead)

    try:
        prompt_path = os.path.join(
            getattr(config, "PROMPTS_DIR", "prompts"), "subject_prompt.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()
        final_prompt = (
            template.replace("{name}", str(lead.get("name", "") or ""))
            .replace("{platform}", str(lead.get("platform", "") or ""))
            .replace("{company}", str(lead.get("company", "") or ""))
            .replace("{notes}", str(lead.get("notes", "") or ""))
        )
        text = _call_ollama(final_prompt)
        if text:
            one_line = " ".join(text.split())[:200]
            return one_line
    except Exception:
        logger.error("Subject generation failed — using fallback")
    return _fallback_subject(lead)


def generate_message(lead: dict) -> str:
    if runtime_settings.get_free_api_mode():
        return _fallback_message(lead)

    try:
        prompt_path = os.path.join(
            getattr(config, "PROMPTS_DIR", "prompts"), "message_prompt.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()

        final_prompt = (
            template.replace("{name}", str(lead.get("name", "") or ""))
            .replace("{platform}", str(lead.get("platform", "") or ""))
            .replace("{subject}", str(lead.get("subject", "") or ""))
        )

        text = _call_ollama(final_prompt)
        if text:
            return text
    except Exception:
        logger.error("Message generation failed — using fallback")

    return _fallback_message(lead)
