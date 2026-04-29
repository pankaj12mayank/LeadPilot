from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel

import config
from backend.app.api.deps import get_current_user
from backend.app.schemas.settings import SettingsResponse, SettingsUpdate
from backend.ollama_messaging.ollama_service import OllamaGenerateService
from backend.ollama_model_presets import OLLAMA_RECOMMENDED_CHAT_MODELS
from backend.services import external_llm_service, ollama_bootstrap, runtime_settings, settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


def _mask_settings(data: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(data)
    k = out.get("external_api_key")
    if k and str(k).strip():
        s = str(k)
        out["external_api_key"] = "********" if len(s) < 8 else f"…{s[-4:]}"
    return out


class TestOllamaBody(BaseModel):
    model_name: Optional[str] = None


class TestExternalBody(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


class DebugModeBody(BaseModel):
    enabled: bool


def _ollama_tags_url() -> str:
    u = str(getattr(config, "OLLAMA_URL", "") or "").strip().rstrip("/")
    if not u:
        u = "http://localhost:11434/api/generate"
    if u.endswith("/api/generate"):
        base = u[: -len("/api/generate")]
    else:
        base = re.sub(r"/api/generate/?$", "", u)
    return f"{base.rstrip('/')}/api/tags"


@router.get("/", response_model=SettingsResponse)
def get_settings(_user: dict = Depends(get_current_user)) -> SettingsResponse:
    raw = settings_service.load_settings()
    return SettingsResponse(data=_mask_settings(raw))


@router.patch("/", response_model=SettingsResponse)
def patch_settings(
    body: SettingsUpdate, _user: dict = Depends(get_current_user)
) -> SettingsResponse:
    patch: Dict[str, Any] = body.model_dump(exclude_unset=True)
    ek = patch.get("external_api_key")
    if ek is not None and ("*" in str(ek) or str(ek).startswith("…")):
        del patch["external_api_key"]
    merged = settings_service.patch_settings(patch)
    return SettingsResponse(data=_mask_settings(merged))


@router.get("/debug-mode")
def get_debug_mode(_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    return {"enabled": bool(runtime_settings.get_debug_mode())}


@router.patch("/debug-mode")
def set_debug_mode(body: DebugModeBody, _user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    merged = settings_service.patch_settings({"debug_mode": bool(body.enabled)})
    return {"enabled": bool(merged.get("debug_mode"))}


def _collect_model_names(data: Dict[str, Any]) -> set[str]:
    names: set[str] = set()
    if isinstance(data.get("models"), list):
        for m in data["models"]:
            if isinstance(m, dict) and m.get("name"):
                names.add(str(m["name"]))
    return names


def _model_present(names: set[str], model: str) -> bool:
    if model in names:
        return True
    return any(model in n or n.startswith(model) for n in names)


@router.post("/test-ollama")
def test_ollama(
    body: TestOllamaBody = TestOllamaBody(),
    _user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    model = (body.model_name or None) or runtime_settings.get_model_name() or "llama3"
    model = str(model).strip()
    tags_url = _ollama_tags_url()
    hints: List[str] = []
    auto_started = False

    data: Optional[Dict[str, Any]] = None
    first_err: Optional[BaseException] = None
    try:
        with httpx.Client(timeout=httpx.Timeout(15.0)) as client:
            r = client.get(tags_url)
            r.raise_for_status()
            raw = r.json()
            data = raw if isinstance(raw, dict) else None
    except Exception as e:  # noqa: BLE001
        first_err = e

    if data is None and first_err is None:
        return {
            "ok": False,
            "detail": f"Ollama at {tags_url} returned an unexpected response (expected JSON object with models).",
            "hints": ollama_bootstrap.install_and_run_hints(),
            "auto_started": False,
        }

    if data is None and first_err is not None:
        if ollama_bootstrap.looks_like_connection_refused(first_err):
            started, start_err = ollama_bootstrap.try_start_ollama_serve()
            if started:
                auto_started = True
                hints.append(
                    "Nothing was listening on the Ollama port; started `ollama serve` in the background. "
                    "If this test still fails, open a terminal yourself and run: ollama serve"
                )
            elif start_err == "not_found":
                return {
                    "ok": False,
                    "detail": f"Cannot reach Ollama at {tags_url}: {first_err}",
                    "hints": ollama_bootstrap.install_and_run_hints(),
                    "auto_started": False,
                }
            else:
                hints.append(f"Could not auto-start Ollama ({start_err}). Start it manually: ollama serve")
            # After a silent background start, wait longer — no extra terminal window.
            wait_secs = 45.0 if auto_started else 30.0
            data, wait_err = ollama_bootstrap.wait_for_ollama_tags(tags_url, total_seconds=wait_secs)
            if data is None:
                hints.extend(
                    [
                        "Still cannot reach Ollama. On Windows, open “Ollama” from the Start menu (tray app), or in PowerShell run: ollama serve",
                        "Then: ollama pull " + model,
                    ]
                )
                hints.extend(ollama_bootstrap.install_and_run_hints())
                return {
                    "ok": False,
                    "detail": f"Cannot reach Ollama at {tags_url}: {wait_err or first_err}",
                    "hints": hints,
                    "auto_started": auto_started,
                }
        else:
            return {
                "ok": False,
                "detail": f"Cannot reach Ollama at {tags_url}: {first_err}",
                "hints": [
                    "If Ollama runs on another machine or port, set OLLAMA_URL in your .env to its full /api/generate URL.",
                    *ollama_bootstrap.install_and_run_hints(),
                ],
                "auto_started": False,
            }

    if data is None:
        return {
            "ok": False,
            "detail": f"Cannot reach Ollama at {tags_url} (unexpected state).",
            "hints": ollama_bootstrap.install_and_run_hints(),
            "auto_started": auto_started,
        }
    names = _collect_model_names(data)
    pull_log = ""
    if not _model_present(names, model):

        def _refresh_names() -> None:
            nonlocal data, names
            try:
                with httpx.Client(timeout=httpx.Timeout(15.0)) as client:
                    r2 = client.get(tags_url)
                    r2.raise_for_status()
                    raw2 = r2.json()
                    if isinstance(raw2, dict):
                        data = raw2
                        names = _collect_model_names(data)
            except Exception as e:  # noqa: BLE001
                raise RuntimeError(str(e)) from e

        ok_pull, pull_log = ollama_bootstrap.run_ollama_pull(model)
        if ok_pull:
            hints.append(f"Pulled model `{model}` successfully.")
            try:
                _refresh_names()
            except RuntimeError as e:
                return {
                    "ok": False,
                    "detail": f"Pull reported success but could not re-read /api/tags: {e}",
                    "hints": hints,
                    "auto_started": auto_started,
                }
        if not _model_present(names, model):
            for alt in OLLAMA_RECOMMENDED_CHAT_MODELS:
                if alt == model:
                    continue
                ok_a, _ = ollama_bootstrap.run_ollama_pull(alt)
                if ok_a:
                    model = alt
                    hints.append(f"Using recommended model `{alt}` (pulled; primary was missing).")
                    try:
                        _refresh_names()
                    except RuntimeError:
                        pass
                    break
        if not _model_present(names, model):
            ph = [f"Run: ollama pull {model}", f"Or: ollama pull {OLLAMA_RECOMMENDED_CHAT_MODELS[0]}"]
            if "not found" in (pull_log or "").lower():
                ph.extend(ollama_bootstrap.install_and_run_hints())
            return {
                "ok": False,
                "detail": f"Model not available after auto-pull. Last: {pull_log or 'n/a'}",
                "available_sample": sorted(names)[:12],
                "hints": ph,
                "auto_started": auto_started,
            }

    if not _model_present(names, model):
        out_missing: Dict[str, Any] = {
            "ok": False,
            "detail": f"Model '{model}' not listed by Ollama after pull. Run: ollama pull {model}",
            "available_sample": sorted(names)[:12],
            "auto_started": auto_started,
        }
        if hints:
            out_missing["hints"] = hints
        return out_missing

    svc = OllamaGenerateService(timeout_seconds=45.0, max_retries=1)
    probe = svc.generate_text(model, "Reply with exactly: OK", system="Be brief.")
    ok = bool(probe and "ok" in probe.lower())
    out: Dict[str, Any] = {
        "ok": ok,
        "detail": "Ollama reachable; generate probe " + ("succeeded" if ok else "returned empty"),
        "auto_started": auto_started,
    }
    if hints:
        out["hints"] = hints
    return out


@router.post("/test-external-api")
def test_external_api(
    body: TestExternalBody = TestExternalBody(),
    _user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    b = body
    key = (b.api_key or runtime_settings.get_external_api_key()).strip()
    if not key:
        return {"ok": False, "detail": "API key is required (save it in settings or pass in test body)"}
    return external_llm_service.test_external_connection(
        base_url=b.base_url or runtime_settings.get_external_api_base_url(),
        api_key=key,
        model=b.model or runtime_settings.get_external_api_model(),
    )
