from __future__ import annotations

import time
from typing import Any, Optional

import httpx

import config
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def _ollama_generate_url() -> str:
    url = str(getattr(config, "OLLAMA_URL", "") or "").strip()
    if url:
        return url
    return "http://localhost:11434/api/generate"


def _timeout_seconds() -> float:
    return float(getattr(config, "OLLAMA_TIMEOUT_SECONDS", 120) or 120)


def _max_retries() -> int:
    return max(1, int(getattr(config, "OLLAMA_MAX_RETRIES", 3) or 3))


def _retry_backoff_seconds(attempt: int) -> float:
    return min(8.0, 0.5 * (2**attempt))


class OllamaGenerateService:
    """HTTP client for Ollama ``/api/generate`` with retries and timeouts."""

    def __init__(
        self,
        *,
        generate_url: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        self._url = generate_url or _ollama_generate_url()
        self._timeout = timeout_seconds if timeout_seconds is not None else _timeout_seconds()
        self._retries = max_retries if max_retries is not None else _max_retries()

    def generate_text(self, model: str, prompt: str, *, system: str = "") -> Optional[str]:
        """Return model text or None on failure after retries."""
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        last_err: Optional[BaseException] = None
        for attempt in range(self._retries):
            try:
                with httpx.Client(timeout=httpx.Timeout(self._timeout)) as client:
                    r = client.post(self._url, json=payload)
                    r.raise_for_status()
                    data = r.json()
                text = data.get("response") if isinstance(data, dict) else None
                if text and str(text).strip():
                    if attempt > 0:
                        logger.info("Ollama succeeded after %s retries", attempt)
                    return str(text).strip()
                logger.warning("Ollama returned empty response (model=%s)", model)
            except httpx.TimeoutException as e:
                last_err = e
                logger.warning(
                    "Ollama timeout (attempt %s/%s, model=%s)",
                    attempt + 1,
                    self._retries,
                    model,
                )
            except httpx.ConnectError as e:
                last_err = e
                logger.warning(
                    "Ollama connection error (attempt %s/%s): %s",
                    attempt + 1,
                    self._retries,
                    e,
                )
            except httpx.HTTPStatusError as e:
                last_err = e
                logger.warning(
                    "Ollama HTTP %s (attempt %s/%s): %s",
                    e.response.status_code,
                    attempt + 1,
                    self._retries,
                    e.response.text[:200],
                )
            except Exception as e:
                last_err = e
                logger.warning("Ollama unexpected error (attempt %s/%s): %s", attempt + 1, self._retries, e)

            if attempt + 1 < self._retries:
                time.sleep(_retry_backoff_seconds(attempt))

        logger.error("Ollama failed after %s attempts; last error: %s", self._retries, last_err)
        return None
