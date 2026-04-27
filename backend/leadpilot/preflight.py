"""
One-shot system checks before the LinkedIn scraper run.

From repo root:  python -m backend.leadpilot.lead_scraper --verify-only
"""

from __future__ import annotations

import importlib
import os
import socket
import sys
import tempfile
from pathlib import Path

from .scraper_core import (
    DEFAULT_OLLAMA_MODEL,
    SOLUTION_HEADER,
    env_attach_existing_chrome,
    env_remote_debug_port,
    get_ai_backend,
    get_solution_backend,
    save_leads_file,
    _env_bool,
    _env_int,
    _env_str,
    pick_proxy_url,
)


def _ok(msg: str) -> None:
    print(f"  [OK] {msg}", flush=True)


def _warn(msg: str) -> None:
    print(f"  [WARN] {msg}", flush=True)


def _fail(msg: str) -> None:
    print(f"  [FAIL] {msg}", flush=True)


def _check_python() -> bool:
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        _fail(f"Python 3.10+ required (this is {v.major}.{v.minor})")
        return False
    _ok(f"Python {v.major}.{v.minor}.{v.micro}")
    return True


def _check_imports(attach: bool, leads_file: str) -> bool:
    need = [
        "selenium",
        "pandas",
        "openpyxl",
        "httpx",
    ]
    for name in need:
        try:
            importlib.import_module(name)
            _ok(f"import {name}")
        except Exception as e:
            _fail(f"import {name}: {e!s}")
            return False
    try:
        importlib.import_module("dotenv")
        _ok("import dotenv (optional but recommended)")
    except Exception:
        _warn("python-dotenv not found - .env may not auto-load; pip install python-dotenv")
    if not attach:
        px = pick_proxy_url()
        if px:
            _ok(f"proxy will be used: {px[:50]}...")
    return True


def _port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.close()
        return True
    except OSError:
        return False


def _lenient_preflight() -> bool:
    """If True, Ollama/Chrome optional checks only warn; scraper can still run. Set LEADPILOT_STRICT_PREFLIGHT=1 to hard-fail."""
    return not _env_bool("LEADPILOT_STRICT_PREFLIGHT", False)


def _check_selenium_chrome_smoke(*, lenient: bool) -> bool:
    """
    In launch mode, start Chrome once in headless (Selenium 4.6+ auto driver) and quit.
    Set LEADPILOT_SKIP_CHROME_SMOKE=1 to skip (CI or when Chrome is not installed on this machine).
    """
    if _env_bool("LEADPILOT_SKIP_CHROME_SMOKE", False):
        _warn("LEADPILOT_SKIP_CHROME_SMOKE=1 — skipped Chrome + WebDriver smoke test")
        return True
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
    except Exception as e:
        _fail(f"selenium / Chrome options import failed: {e!s}")
        return False
    try:
        import selenium

        sv = getattr(selenium, "__version__", "?")
    except Exception:
        sv = "?"
    _ok(f"selenium import OK (package version {sv}; 4.6+ uses Selenium Manager for matching ChromeDriver)")

    opt = Options()
    opt.add_argument("--headless=new")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-dev-shm-usage")
    opt.add_argument("--disable-gpu")
    opt.add_argument("--window-size=1280,800")
    driver = None
    try:
        driver = webdriver.Chrome(options=opt)
        v = (driver.capabilities or {}).get("browserVersion") or "?"
        _ok(f"Chrome + WebDriver smoke: browserVersion={v!r} (OK for launch mode)")
    except Exception as e:  # noqa: BLE001
        msg = (
            "Could not start Chrome for Selenium (headless smoke test). "
            f"Details: {e!s}\n"
            "  Fix: install Google Chrome (stable);  pip install -U 'selenium>=4.15' ;\n"
            f"  Or set LEADPILOT_SKIP_CHROME_SMOKE=1. Attach mode: Chrome on port {_env_int('REMOTE_DEBUG_PORT', 9222)}."
        )
        if lenient:
            _warn(msg + " (lenient preflight: continuing; scrape may still work when a browser opens.)")
            return True
        _fail(msg)
        return False
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
    return True


def _check_chrome_attach(port: int) -> bool:
    if not _port_open("127.0.0.1", port):
        _fail(
            f"Nothing listening on 127.0.0.1:{port} - attach mode needs Chrome already running with remote debugging."
        )
        _warn(
            f"Start Chrome first, e.g.:\n"
            f'  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" ^\n'
            f"    --remote-debugging-port={port} --user-data-dir=\"D:\\\\selenium\\\\li_profile\"\n"
            f"  Then log into LinkedIn in that window."
        )
        _warn(
            "Or re-run:  python -m backend.leadpilot --launch-chrome  (same as ATTACH_EXISTING_CHROME=0 for that run), "
            "or set ATTACH_EXISTING_CHROME=0 in .env / scraper.env."
        )
        return False
    _ok(f"Remote debugging port {port} is open (attach mode ready)")
    return True


def _check_ai(*, lenient: bool) -> bool:
    b = get_ai_backend()
    s = get_solution_backend()
    _ok(f"AI_BACKEND={b!r}  SOLUTION_AI_BACKEND={s!r}")
    if b == "api" or s == "api":
        key = _env_str("OPENAI_API_KEY", None)
        if not key:
            if lenient:
                _warn("AI is api but OPENAI_API_KEY is empty — lenient: continuing; scoring may use fallbacks")
                return True
            _fail("AI_BACKEND or SOLUTION is api but OPENAI_API_KEY is empty")
            return False
        _ok("OPENAI_API_KEY is set")
        try:
            importlib.import_module("openai")
            _ok("import openai")
        except Exception as e:
            if lenient:
                _warn(f"openai package: {e!s} (lenient: continuing)")
                return True
            _fail(f"openai package: {e!s}")
            return False
    if b == "ollama" or s == "ollama":
        try:
            import httpx
        except Exception as e:
            if lenient:
                _warn(f"httpx required for Ollama: {e!s} (lenient: continuing)")
                return True
            _fail(f"httpx required for Ollama: {e!s}")
            return False
        base = (_env_str("OLLAMA_BASE_URL", "http://127.0.0.1:11434") or "").rstrip("/")
        try:
            r = httpx.Client(timeout=8.0).get(f"{base}/api/tags")
        except Exception as e:
            w = (
                f"Ollama not reachable at {base}: {e!s} — start: ollama serve ; "
                f"ollama pull {(_env_str('OLLAMA_MODEL', DEFAULT_OLLAMA_MODEL) or 'llama3').split(':')[0]}"
            )
            if lenient:
                _warn(w + " (lenient preflight: lead scrape still allowed; AI features may be weak)")
                return True
            _fail(
                f"Ollama not reachable at {base}: {e!s}\n"
                f"  Fix: start the Ollama app (tray) or in a terminal:  ollama serve\n"
                f"  Then:  ollama pull {(_env_str('OLLAMA_MODEL', DEFAULT_OLLAMA_MODEL) or 'llama3').split(':')[0]}"
            )
            return False
        if r.status_code != 200:
            if lenient:
                _warn(f"Ollama {base}/api/tags -> HTTP {r.status_code} (lenient: continuing)")
                return True
            _fail(f"Ollama {base}/api/tags -> HTTP {r.status_code}")
            return False
        _ok(f"Ollama responds at {base}")
        model = _env_str("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL) or DEFAULT_OLLAMA_MODEL
        data = r.json() or {}
        names: list[str] = []
        for m in data.get("models", []):
            if isinstance(m, dict) and m.get("name"):
                names.append(m["name"])
        if not names:
            _warn(
                "Ollama has no models yet. Run:  ollama pull " + (model.split(":")[0] or "llama3")
            )
        elif not any(model in n or n.startswith(model) for n in names):
            _warn(
                f"Model {model!r} not obvious in ollama list. Available include: {names[:5]}... "
                f"Try: ollama pull {model}"
            )
        else:
            _ok(f"Ollama model {model!r} appears available")
        _ok("Tip: keep 'ollama serve' running (or Ollama app) while scraping / scoring")
    if b == "none" and s == "none":
        _warn("AI is off - Problem/Solution will use rules / placeholders only")
    return True


def _check_output_path(script_dir: str, leads_file: str) -> bool:
    out = os.path.join(script_dir, os.path.basename(leads_file))
    parent = os.path.dirname(os.path.abspath(out)) or "."
    if not os.path.isdir(parent):
        try:
            os.makedirs(parent, exist_ok=True)
        except OSError as e:
            _fail(f"Cannot create output directory {parent!r}: {e}")
            return False
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=parent,
            prefix="._leadstest_",
            suffix=".tmp",
            delete=False,
        ) as t:
            tmp = t.name
        os.unlink(tmp)
    except OSError as e:
        _fail(f"Output folder not writable ({parent!r}): {e}")
        return False
    _ok(f"Output folder writable -> {out}")
    try:
        dummy: list[dict] = [
            {
                "Name": "Test",
                "Company": "Co",
                "Role": "Role",
                "Profile Link": "https://www.linkedin.com/in/test",
                "Agency Type": "Other",
                "Team Size": "",
                "Problem Seen": "—",
                "Last Active": "N/A",
                "Solution": "—",
            }
        ]
        test_path = out + ".verify_tmp.xlsx"
        save_leads_file(dummy, test_path)
        os.unlink(test_path)
        _ok("save_leads_file() smoke test passed")
    except Exception as e:
        _fail(f"save_leads_file() failed: {e!s}")
        return False
    return True


def _check_remote_api_push() -> bool:
    if not _env_bool("LNN_PUSH", False):
        _ok("LNN_PUSH=0 (remote API push off)")
        return True
    base = _env_str("LNN_BASE_URL", None) or _env_str("VITE_API_URL", None)
    token = _env_str("LNN_API_TOKEN", None)
    if not base or not token:
        _fail("LNN_PUSH=1 but LNN_BASE_URL or LNN_API_TOKEN missing")
        return False
    admin = _env_bool("LNN_IS_ADMIN", False)
    wid = _env_int("LNN_WORKSPACE_ID", 0)
    if admin and wid < 1:
        _fail("LNN_IS_ADMIN=1 requires LNN_WORKSPACE_ID >= 1")
        return False
    _ok("LNN_* env looks complete for LNN_PUSH")
    try:
        import httpx

        r = httpx.Client(timeout=5.0).get(base.rstrip("/") + "/docs")
        if r.status_code < 500:
            _ok(f"Backend {base!r} responds (e.g. /docs or /openapi.json)")
        else:
            _warn(f"Backend returned HTTP {r.status_code} - check URL and server")
    except Exception as e:
        _warn(f"Could not reach {base!r} ({e!s}) - start server if you need push")
    return True


def _repo_root() -> str:
    """Package is backend/leadpilot — repo root is two levels up (same as lead_scraper output paths)."""
    return str(Path(__file__).resolve().parents[2])


def run_verification() -> bool:
    """Run all checks. Return True if no hard failures (warnings allowed)."""
    repo = _repo_root()
    lenient = _lenient_preflight()
    port = env_remote_debug_port()
    leads = _env_str("LEADS_FILE", "linkedin_leads.xlsx") or "linkedin_leads.xlsx"
    attach = env_attach_existing_chrome()
    # If attach requested but no debugger, fall back to launch (Chrome opened by Selenium) for this process.
    if attach and not _port_open("127.0.0.1", port):
        _warn(
            f"No listener on 127.0.0.1:{port} — auto-switching to launch mode (Selenium opens Chrome; "
            f"set ATTACH_EXISTING_CHROME=0 in scraper.env to make this the default, or start Chrome with "
            f"--remote-debugging-port={port} to use attach.)"
        )
        os.environ["ATTACH_EXISTING_CHROME"] = "0"
        attach = False

    print("\n========== PREFLIGHT ==========\n", flush=True)
    if lenient:
        print(
            "  [INFO] Lenient preflight: optional checks (Ollama, Chrome smoke) may warn but not block. "
            "Set LEADPILOT_STRICT_PREFLIGHT=1 in scraper.env to fail on those.",
            flush=True,
        )
    section = "1) Python & imports"
    print(section, flush=True)
    if not _check_python():
        return False
    if not _check_imports(attach, leads):
        return False

    print("\n2) Chrome / Selenium", flush=True)
    v = (os.environ.get("ATTACH_EXISTING_CHROME") or "").strip()
    mode = "attach (port %s must be open)" % port if attach else "launch (Selenium will open Chrome)"
    print("  [INFO] ATTACH_EXISTING_CHROME=%s -> %s" % (v or ("1" if attach else "0 (default)"), mode), flush=True)
    if attach:
        if not _check_chrome_attach(port):
            return False
    else:
        _ok("Launch mode: Selenium will start Chrome (Selenium 4.6+ resolves ChromeDriver).")
        if not _check_selenium_chrome_smoke(lenient=lenient):
            return False

    print("\n3) AI (Ollama / API)", flush=True)
    if not _check_ai(lenient=lenient):
        return False

    print("\n4) Output file", flush=True)
    if not _check_output_path(repo, leads):
        return False

    print("\n5) Optional API push (LNN_*)", flush=True)
    if not _check_remote_api_push():
        return False

    sh = SOLUTION_HEADER[:50] + "..." if len(SOLUTION_HEADER) > 50 else SOLUTION_HEADER
    _ok(f"export column for Solution: {sh}")
    print("\n========== PREFLIGHT OK ==========\n", flush=True)
    return True


if __name__ == "__main__":
    sys.exit(0 if run_verification() else 1)
