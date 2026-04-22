"""Helpers to reach a local Ollama instance (start server, wait, pull model)."""

from __future__ import annotations

import os
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx


def _subprocess_kwargs() -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {}
    if os.name == "nt":
        cf = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if cf:
            kwargs["creationflags"] = cf
    return kwargs


def looks_like_connection_refused(exc: BaseException) -> bool:
    """True when Ollama is likely not listening (vs wrong URL, DNS, TLS, etc.)."""
    if isinstance(exc, httpx.ConnectError):
        return True
    if isinstance(exc, OSError):
        if getattr(exc, "winerror", None) == 10061:
            return True
        if getattr(exc, "errno", None) in (61, 111):  # ECONNREFUSED
            return True
    msg = str(exc).lower()
    if "10061" in msg or "actively refused" in msg or "connection refused" in msg:
        return True
    cause = getattr(exc, "__cause__", None) or getattr(exc, "__context__", None)
    if cause is not None and cause is not exc:
        return looks_like_connection_refused(cause)
    return False


def try_open_visible_ollama_terminal_windows() -> bool:
    """Open a new ``cmd`` window running ``ollama serve`` (user can see logs). Windows only."""
    if os.name != "nt":
        return False
    try:
        subprocess.Popen(
            ["cmd", "/c", "start", "cmd", "/k", "ollama serve"],
            shell=False,
        )
        return True
    except OSError:
        return False


def try_start_ollama_serve() -> Tuple[bool, Optional[str]]:
    """
    Start ``ollama serve`` detached (same idea as ``modules.ai_enricher.ensure_ollama_ready``).
    Returns (popen_succeeded, error_message_if_failed).
    """
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            **_subprocess_kwargs(),
        )
        return True, None
    except FileNotFoundError:
        return False, "not_found"
    except Exception as e:  # noqa: BLE001 — surface any spawn failure
        return False, str(e)


def wait_for_ollama_tags(tags_url: str, *, total_seconds: float = 28.0, interval: float = 0.75) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Poll ``GET /api/tags`` until success or timeout. Returns (json_dict, last_error)."""
    deadline = time.monotonic() + total_seconds
    last_err = "timeout waiting for Ollama"
    while time.monotonic() < deadline:
        try:
            with httpx.Client(timeout=httpx.Timeout(8.0)) as client:
                r = client.get(tags_url)
                r.raise_for_status()
                data = r.json()
                if isinstance(data, dict):
                    return data, None
                last_err = "unexpected JSON from /api/tags"
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
        time.sleep(interval)
    return None, last_err


def run_ollama_pull(model: str, *, timeout_seconds: float = 600.0) -> Tuple[bool, str]:
    """Run ``ollama pull <model>``. Returns (success, stderr_or_stdout_tail)."""
    try:
        proc = subprocess.run(
            ["ollama", "pull", model],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            **_subprocess_kwargs(),
        )
        tail = (proc.stderr or proc.stdout or "")[-800:].strip()
        return proc.returncode == 0, tail or f"exit {proc.returncode}"
    except FileNotFoundError:
        return False, "ollama CLI not found in PATH"
    except subprocess.TimeoutExpired:
        return False, f"ollama pull timed out after {int(timeout_seconds)}s — try again or run manually in a terminal"
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def install_and_run_hints() -> List[str]:
    return [
        "Install Ollama: https://ollama.com/download (Windows: run the installer, then use Start menu “Ollama” so the app runs in the tray).",
        "In PowerShell or CMD (after install): ollama serve   — leave it running, or rely on the Ollama app.",
        "Pull a model: ollama pull llama3   — then run “Test Ollama connection” again.",
        "If the URL is not localhost, set OLLAMA_URL in LeadPilot’s .env to your host’s /api/generate URL.",
    ]
