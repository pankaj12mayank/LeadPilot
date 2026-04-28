"""
LinkedIn people search -> one Excel file (default: linkedin_leads.xlsx, set LEADS_FILE in .env).

Flow (by design):
1) Browser opens (feed by default, not a pre-filled search). Log in.
2) Second prompt: you run **People** search and filters; then press Enter (or wait if API) - **only then** /in/ links are collected.
3) Attach mode: start Chrome with remote debugging, e.g.:
     "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" ^
       --remote-debugging-port=9222 --user-data-dir="D:\\selenium\\li_profile"
4) This script attaches to that browser (session reuse), scrolls/paginates the *current*
   results, opens each profile with human-like delays, scrapes + company page, runs AI,
   writes one output file.

Env: .env.example — MAX_LEADS, ASK_MAX_LEADS=1, AI_BACKEND, OLLAMA_*, optional -n N on CLI.
"""

import os
import random
import re
import sys
import time
from collections import OrderedDict
from pathlib import Path

from .execution_report import print_pipeline_footer
from .linkedin_session_cache import get_linkedin_session_info, print_session_status_at_start, touch_linkedin_session_ok
from .scraper_core import (
    UNLOCKED_MESSAGE,
    click_next_search_page,
    close_except_handle,
    collect_profile_hrefs_on_page,
    connect_selenium_chrome,
    detect_agency_type,
    env_attach_existing_chrome,
    env_remote_debug_port,
    extract_company_size_overview,
    extract_name_role_company,
    generate_problem_seen,
    generate_solution,
    is_company_page_locked_premium,
    is_premium_or_locked_profile,
    push_lead_to_backend,
    save_leads_file,
    scroll_search_page,
    _env_bool,
    _env_int,
    _env_str,
    pick_proxy_url,
)

# ======================
# CONFIG
# ======================
# Lead count: set MAX_LEADS in .env, or MAX_PROFILES (alias), or use --max-leads / ASK_MAX_LEADS=1
def _configured_max_leads() -> int:
    cap = _env_int("MAX_LEADS_CAP", 500)
    raw = _env_str("MAX_LEADS", None) or _env_str("MAX_PROFILES", None)
    if raw:
        try:
            n = int(raw)
        except ValueError:
            n = 20
    else:
        n = 20
    return max(1, min(n, cap))


# Human-like but slightly tighter than older 4–9s; override via DELAY_MIN / DELAY_MAX
DELAY_MIN = int(os.environ.get("DELAY_MIN", "3"))
DELAY_MAX = int(os.environ.get("DELAY_MAX", "7"))
if DELAY_MIN > DELAY_MAX:
    DELAY_MIN, DELAY_MAX = min(DELAY_MIN, DELAY_MAX), max(DELAY_MIN, DELAY_MAX)
SCROLL_ROUNDS_PER_PAGE = int(os.environ.get("SCROLL_ROUNDS_PER_PAGE", "4"))
MAX_SEARCH_PAGES = int(os.environ.get("MAX_SEARCH_PAGES", "8"))
MAX_EXTRA_TABS = int(os.environ.get("MAX_EXTRA_TABS", "1"))

# Port is stable; attach mode must be read at runtime (CLI e.g. --launch-chrome sets env after import).
REMOTE_DEBUG_PORT = env_remote_debug_port()


def _profile_tab_settle_s() -> float:
    try:
        v = float(_env_str("PROFILE_TAB_SETTLE", "1.4") or "1.4")
        return max(0.3, min(v, 5.0))
    except ValueError:
        return 1.4
START_URL = _env_str(
    "START_URL", "https://www.linkedin.com/search/results/people/"
) or "https://www.linkedin.com/search/results/people/"
# Launch mode: open feed (or this URL) first so the scraper does not pre-load a default search result page.
LEADPILOT_INITIAL_URL_DEFAULT = "https://www.linkedin.com/feed/"

# Single output: Excel only (no separate CSV). Name without app branding.
LEADS_FILE = _env_str("LEADS_FILE", "linkedin_leads.xlsx") or "linkedin_leads.xlsx"

LNN_BASE_URL = _env_str("LNN_BASE_URL", None) or _env_str("VITE_API_URL", None)
LNN_API_TOKEN = _env_str("LNN_API_TOKEN", None)
LNN_WORKSPACE_ID = int(os.environ.get("LNN_WORKSPACE_ID", "0") or 0)
LNN_IS_ADMIN = _env_bool("LNN_IS_ADMIN", default=False)
LNN_PUSH = _env_bool("LNN_PUSH", default=False)
ASK_MAX_LEADS = _env_bool("ASK_MAX_LEADS", default=False)


def _should_quit_launch_chrome(*, row_count: int, driver: object | None, attach: bool) -> bool:
    """
    Launch mode normally quits Chrome so the subprocess ends. If the run collected 0 rows (often: user
    still logging in), do **not** close the browser by default — that was closing Chrome while typing.
    LEADPILOT_QUIT_CHROME_AFTER_RUN=0 = never auto-close. LEADPILOT_NO_QUIT_ON_ZERO_ROWS=0 = always quit (old behavior).
    """
    if attach:
        return False
    if _env_bool("LEADPILOT_ALWAYS_LEAVE_BROWSER_OPEN", False):
        return False
    if not _env_bool("LEADPILOT_QUIT_CHROME_AFTER_RUN", True):
        return False
    try:
        if driver is not None:
            u = str(driver.current_url or "")  # type: ignore[attr-defined]
            if _linkedin_on_signin_or_challenge(u):
                return False
    except Exception:
        pass
    if row_count == 0 and _env_bool("LEADPILOT_NO_QUIT_ON_ZERO_ROWS", True):
        return False
    return True


def human_delay() -> None:
    time.sleep(random.randint(DELAY_MIN, DELAY_MAX))


def _linkedin_on_signin_or_challenge(url: str) -> bool:
    """True while LinkedIn is likely showing login, 2FA, or checkpoint (not on usable search/feed)."""
    u = (url or "").lower()
    if "linkedin.com" not in u and "licdn" not in u:
        return False
    gates = (
        "/login",
        "checkpoint",
        "authwall",
        "uas/login",
        "/challenge",
        "singlesignon",
        "breeze",
        "join/",
    )
    if any(g in u for g in gates):
        return True
    if u.rstrip("/").endswith("linkedin.com") and "/feed" not in u and "/search" not in u and "/messaging" not in u:
        return "login" in u
    return False


def _wait_past_linkedin_signin(
    driver: object, *, max_seconds: float | None = None, label: str = "pre-search"
) -> None:
    """
    Block until the active tab is past login/challenge or *max_seconds* elapses.
    Stops the \"15s then scrape\" race where Chrome is closed while the user is still typing a password.
    """
    if max_seconds is None:
        try:
            max_seconds = float(_env_str("LEADPILOT_LOGIN_MAX_WAIT_SECONDS", "600") or "600")
        except ValueError:
            max_seconds = 600.0
    max_seconds = max(10.0, min(max_seconds, 3600.0))
    t0 = time.time()
    last_log = 0.0
    while time.time() - t0 < max_seconds:
        try:
            cur = driver.current_url  # type: ignore[attr-defined]
        except Exception:
            return
        if not _linkedin_on_signin_or_challenge(str(cur or "")):
            if label:
                print(
                    f"  [{label}] Sign-in / challenge page cleared - continuing (waited {time.time() - t0:.0f}s).\n",
                    flush=True,
                )
            return
        now = time.time() - t0
        if now - last_log >= 25.0:
            last_log = now
            rem = max_seconds - now
            print(
                f"  [wait] LinkedIn sign-in or security check in progress - take your time "
                f"({int(rem)}s max). URL: {str(cur)[:88]}...\n",
                flush=True,
            )
        time.sleep(2.2)
    try:
        cur2 = str(driver.current_url)  # type: ignore[attr-defined]
    except Exception:
        cur2 = ""
    print(
        f"  [wait] {label}: still on gate after {int(max_seconds)}s. Proceeding anyway - if scrape finds 0 rows, log in and re-run. Current: {cur2[:100]!s}\n",
        flush=True,
    )


def _open_people_search_if_feed(driver: object) -> None:
    """If enabled, from feed/mynetwork jump to People search. Default: off (user runs search manually)."""
    if not _env_bool("LEADPILOT_AUTO_OPEN_PEOPLE_SEARCH", False):
        return
    try:
        cur = (driver.current_url or "").lower()  # type: ignore[attr-defined]
    except Exception:
        return
    if "search/results/people" in cur or "search/people" in cur:
        return
    if "login" in cur or "checkpoint" in cur or "authwall" in cur:
        return
    # Typical post-login landing pages (not already on People search)
    if "feed" in cur or "/mynetwork" in cur or re.search(
        r"linkedin\.com/feed/?$", (driver.current_url or ""), re.I
    ):  # type: ignore[attr-defined]
        try:
            print("  [nav] Opening People search (LEADPILOT_AUTO_OPEN_PEOPLE_SEARCH=1)...\n", flush=True)
            driver.get(START_URL)  # type: ignore[attr-defined]
            time.sleep(1.2)
        except Exception:
            pass


def _wait_to_start_lead_capture(driver: object) -> None:
    """
    Second gate: no ``build_profile_queue`` / profile scraping before this.
    User finishes People search in Chrome, then confirms here (TTY) or waits (non-TTY / API).
    """
    sc_delay = float((_env_str("LEADPILOT_START_CAPTURE_DELAY_SECONDS", "90") or "90").strip() or "90")
    sc_delay = max(5.0, min(sc_delay, 600.0))
    skip_sc = _env_bool("LEADPILOT_SKIP_START_CAPTURE_PROMPT", False) or not sys.stdin.isatty()
    print(
        "\n"
        "5) **Start lead capture (this is the real start)**\n"
        "   In Chrome: go to **People** search, set filters (keyword, location, 2nd degree, etc.)\n"
        "   and scroll so **search result cards** for the people you want are on screen in the current tab.\n"
        "   The scraper does not collect /in/ links before you confirm the next step.\n",
        flush=True,
    )
    if skip_sc:
        print(
            f"   Auto-continue: no TTY or LEADPILOT_SKIP_START_CAPTURE_PROMPT=1. "
            f"Finish your search in the next {int(sc_delay)}s - then the run will read **this tab only**.\n",
            flush=True,
        )
        time.sleep(sc_delay)
    else:
        print(
            "   When you are on the **correct** People search results page, press **Enter** here to START capturing leads.\n",
            flush=True,
        )
        try:
            input()
        except EOFError:
            print(
                f"  (stdin closed - waiting {int(sc_delay)}s, then starting capture.)\n",
                flush=True,
            )
            time.sleep(sc_delay)
    try:
        _ = driver.current_window_handle  # type: ignore[attr-defined]
    except Exception:
        pass


def _enforce_session_validity_gate() -> None:
    """
    Global LinkedIn session control:
    - check session_created_at age at run start
    - if expired/missing, pause execution for manual login
    - refresh local session timestamp after user confirms
    """
    info = get_linkedin_session_info()
    if info.within_policy:
        return
    wait_s = float((_env_str("LEADPILOT_SESSION_REFRESH_WAIT_SECONDS", "90") or "90").strip() or "90")
    wait_s = max(10.0, min(wait_s, 900.0))
    print(
        "\n"
        "  [session gate] LinkedIn session is expired or missing.\n"
        "  [session gate] Execution paused. Complete manual login in Chrome, then continue.\n"
        "  [session gate] Credentials are never stored by this system.\n",
        flush=True,
    )
    if sys.stdin.isatty():
        print("  [session gate] Press Enter after manual login succeeds.\n", flush=True)
        try:
            input()
        except EOFError:
            time.sleep(wait_s)
    else:
        print(
            f"  [session gate] Non-interactive run: waiting {int(wait_s)}s for manual login before continue.\n",
            flush=True,
        )
        time.sleep(wait_s)
    touch_linkedin_session_ok()
    after = get_linkedin_session_info()
    print(f"  [session gate] Session timestamp refreshed. {after.message}\n", flush=True)


def cdp_anti_det(driver: object) -> None:
    if not env_attach_existing_chrome():
        try:
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
                },
            )
        except Exception:
            pass


def build_profile_queue(driver, max_n: int) -> list[str]:
    ordered: "OrderedDict[str, None]" = OrderedDict()
    for page_i in range(MAX_SEARCH_PAGES):
        print(f"  [search] page {page_i + 1}/{MAX_SEARCH_PAGES}, scrolling...", flush=True)
        scroll_search_page(driver, SCROLL_ROUNDS_PER_PAGE)
        time.sleep(0.5)
        for h in collect_profile_hrefs_on_page(driver):
            if h not in ordered:
                ordered[h] = None
        print(
            f"  [search] collected {len(ordered)} unique /in/ links (cap {max_n})",
            flush=True,
        )
        if len(ordered) >= max_n:
            break
        if not click_next_search_page(driver):
            print("  [search] no more pages (or Next not found).", flush=True)
            break
        time.sleep(1.5)
    return list(ordered)[:max_n]


def _cap_extra_browser_windows(driver: object, search_handle: str) -> None:
    """Keep at most MAX_BROWSER_TABS windows (min 3: search + profile + company)."""
    cap = max(3, min(_env_int("MAX_BROWSER_TABS", 3), 10))
    for _ in range(24):
        handles = list(driver.window_handles)
        if len(handles) <= cap:
            try:
                driver.switch_to.window(search_handle)
            except Exception:
                pass
            return
        victim = None
        for w in reversed(handles):
            if w != search_handle:
                victim = w
                break
        if not victim:
            return
        try:
            driver.switch_to.window(victim)
            driver.close()
        except Exception:
            return


def scrape_one_lead(driver: object, profile_url: str, search_handle: str) -> dict:
    from selenium.common.exceptions import WebDriverException

    max_tries = max(1, _env_int("PROFILE_SCRAPE_RETRIES", 3))
    settle = _profile_tab_settle_s()
    last_err: str | None = None

    for attempt in range(1, max_tries + 1):
        data: dict = {
            "Name": "",
            "Company": "",
            "Role": "",
            "Profile Link": profile_url,
            "Agency Type": "",
            "Team Size": "",
            "Problem Seen": "",
            "Last Active": "N/A",
            "Connection Sent (Date)": "",
            "Replied (Y/N)": "N",
            "Status": "new",
            "Solution": "",
            "email_synthetic": None,
        }
        overview = ""

        def back_to_search() -> None:
            close_except_handle(driver, search_handle)

        try:
            driver.switch_to.window(search_handle)
            _cap_extra_browser_windows(driver, search_handle)
            driver.execute_script("window.open(arguments[0], '_blank');", profile_url)
            driver.switch_to.window(driver.window_handles[-1])
            time.sleep(settle)
            human_delay()

            if is_premium_or_locked_profile(driver):
                print(f"[locked] Not unlocked / Premium: {profile_url}", flush=True)
                data["Problem Seen"] = UNLOCKED_MESSAGE
                data["Solution"] = f"— ({UNLOCKED_MESSAGE})"
                back_to_search()
                return data

            name, role, comp, clink = extract_name_role_company(driver)
            if not (name or "").strip():
                time.sleep(1.6)
                driver.execute_script("window.scrollTo(0, 500);")
                time.sleep(0.45)
                name, role, comp, clink = extract_name_role_company(driver)
            data["Name"] = name
            data["Role"] = role
            data["Company"] = comp
            data["Agency Type"] = detect_agency_type(f"{role} {comp} {name}")

            if clink and MAX_EXTRA_TABS > 0:
                driver.execute_script("window.open(arguments[0], '_blank');", clink)
                driver.switch_to.window(driver.window_handles[-1])
                time.sleep(max(0.4, settle * 0.7))
                human_delay()
                if is_company_page_locked_premium(
                    driver
                ) or is_premium_or_locked_profile(driver):
                    print("[locked] Company page not fully visible - team/overview skipped.", flush=True)
                    data["Team Size"] = ""
                    overview = ""
                else:
                    data["Team Size"], overview = extract_company_size_overview(driver)
            else:
                data["Team Size"] = ""
                overview = ""
                if not (name or role):
                    overview = (data.get("Role", "") or "") + " " + (data.get("Company", "") or "")

            data["Problem Seen"] = generate_problem_seen(overview, role, comp)
            data["Solution"] = generate_solution(
                overview, data["Problem Seen"], name, comp, role
            )

            back_to_search()
            return data
        except WebDriverException as e:
            last_err = str(e)[:200]
            print(
                f"[error] WebDriver (attempt {attempt}/{max_tries}): {e!s}",
                flush=True,
            )
            back_to_search()
            if attempt < max_tries:
                time.sleep(1.0 + 0.5 * attempt)
                continue
            data["Problem Seen"] = last_err
            data["Solution"] = "— (error during scrape)"
            return data
        except Exception as e:  # noqa: BLE001
            print("[error] Exception:", e, flush=True)
            back_to_search()
            data["Problem Seen"] = str(e)[:200]
            data["Solution"] = "— (error during scrape)"
            return data
    raise RuntimeError("scrape_one_lead: internal error (no return path)")


def _clamp_leads(n: int) -> int:
    cap = _env_int("MAX_LEADS_CAP", 500)
    return max(1, min(int(n), cap))


def _ask_lead_limit_interactive() -> int:
    """After browser is ready: prompt for count (used when ASK_MAX_LEADS=1)."""
    cap = _env_int("MAX_LEADS_CAP", 500)
    base = _configured_max_leads()
    try:
        s = input(
            f"\nHow many leads to scrape? [default: {base}, max: {cap}] (Enter = default) "
        ).strip()
    except EOFError:
        s = ""
    if not s:
        return base
    try:
        n = int(s)
    except ValueError:
        print(f"  Invalid number - using default {base}.", flush=True)
        n = base
    return _clamp_leads(n)


def collect_linkedin_leads(
    lead_limit: int | None = None,
    *,
    ask_limit_after_browser_ready: bool = False,
) -> list[dict]:
    """
    Open browser (or attach), wait for user on People search, optionally prompt for N, then collect rows.
    Does not write files. Used by LeadPilot and by run().
    """
    attach = env_attach_existing_chrome()
    driver = connect_selenium_chrome()
    if not attach:
        if _env_bool("LEADPILOT_OPEN_PEOPLE_ON_LAUNCH", False):
            driver.get(START_URL)
        else:
            init = _env_str("LEADPILOT_INITIAL_URL", LEADPILOT_INITIAL_URL_DEFAULT) or LEADPILOT_INITIAL_URL_DEFAULT
            driver.get(init)
    cdp_anti_det(driver)
    print_session_status_at_start()
    _enforce_session_validity_gate()

    delay_s = float((_env_str("LEADPILOT_READY_DELAY_SECONDS", "12") or "12").strip() or "12")
    delay_s = max(2.0, min(delay_s, 120.0))
    skip_prompt = _env_bool("LEADPILOT_SKIP_READY_PROMPT", False) or not sys.stdin.isatty()
    print(
        "\n"
        "1) In Chrome, log in to LinkedIn if you need to.\n"
        "2) You will set **People** search and filters in a later step (not yet - no lead capture yet).\n"
        "3) Keep this browser window; do not close it.\n",
        flush=True,
    )
    if skip_prompt:
        print(
            f"4) Auto-continue: LEADPILOT_SKIP_READY_PROMPT or no TTY. "
            f"Log in and wait for the feed; next messages control when **capture** starts ({int(delay_s)}s)...\n",
            flush=True,
        )
        time.sleep(delay_s)
    else:
        print(
            "4) When you are logged in (feed or home is fine), press **Enter** to continue to the *start capture* step.\n",
            flush=True,
        )
        try:
            input()
        except EOFError:
            print(
                f"  (stdin closed - waiting {int(delay_s)}s, then continuing.)\n",
                flush=True,
            )
            time.sleep(delay_s)

    # Wait for login / 2FA / checkpoint to finish (API runs used to continue after 12–15s and then quit Chrome on 0 rows).
    _wait_past_linkedin_signin(driver, label="after ready timer")
    _open_people_search_if_feed(driver)
    if _linkedin_on_signin_or_challenge(str(driver.current_url or "")):
        _wait_past_linkedin_signin(
            driver,
            label="after People search open",
        )

    cur_url = (driver.current_url or "").lower()
    if "linkedin.com" in cur_url and "search/results" not in cur_url and "search/people" not in cur_url:
        print(
            "  [WARN] Current tab is not a People *search results* page yet (that is OK before step 5). "
            f"URL: {(driver.current_url or '')[:96]}\n",
            flush=True,
        )

    # Second gate: user runs People search, then starts capture. No /in/ queue before this.
    _wait_to_start_lead_capture(driver)
    try:
        search_handle = driver.current_window_handle
    except Exception:  # noqa: BLE001
        search_handle = None  # type: ignore[assignment]
    if not search_handle:
        raise RuntimeError("No browser window handle - cannot continue.")

    if ask_limit_after_browser_ready:
        lead_limit = _ask_lead_limit_interactive()
    if lead_limit is None:
        lead_limit = _configured_max_leads()
    lead_limit = _clamp_leads(lead_limit)

    print(
        f"Lead limit this run: {lead_limit}  (MAX_LEADS / --max-leads / ask)\n",
        flush=True,
    )

    if not attach and "/search" not in (driver.current_url or ""):
        print("Tip: use a People search results URL (or set ATTACH_EXISTING_CHROME=1).", flush=True)

    # Tab in focus after step 5 is the search results tab - refresh handle before collecting links.
    try:
        search_handle = driver.current_window_handle
    except Exception:  # noqa: BLE001
        pass
    data: list[dict] = []
    try:
        queue = build_profile_queue(driver, max_n=lead_limit * 2)
        if not queue:
            print("No /in/ links. Stay on the **people** results page with visible cards.", flush=True)
        to_do = queue[:lead_limit]
        print(f"\nScraping up to {len(to_do)} profiles (slower, human-like delays)...\n", flush=True)
        for i, url in enumerate(to_do, 1):
            print(f"--- [{i}/{len(to_do)}] {url}", flush=True)
            row = scrape_one_lead(driver, url, search_handle)
            if row and row.get("Profile Link"):
                data.append(row)
                label = (row.get("Name") or "").strip() or "(name not parsed)"
                print(f"  OK {label}", flush=True)
    finally:
        if attach:
            print("Attach mode: left your Chrome open.", flush=True)
        elif _should_quit_launch_chrome(
            row_count=len(data), driver=driver, attach=attach
        ):
            try:
                driver.quit()
            except Exception:
                pass
        else:
            try:
                print(
                    "Chrome left open (0 leads, sign-in still showing, or LEADPILOT_NO_QUIT_ON_ZERO_ROWS=1 / LEADPILOT_QUIT_CHROME_AFTER_RUN=0).",
                    flush=True,
                )
            except Exception:
                pass

    if data:
        touch_linkedin_session_ok()
        after = get_linkedin_session_info()
        print(
            f"  [LinkedIn session] Cache updated (last run time saved). {after.message}\n",
            flush=True,
        )
    return data


def run(*, max_leads_override: int | None = None) -> None:
    if not _env_bool("SKIP_PREFLIGHT", default=False):
        from .preflight import run_verification

        if not run_verification():
            print(
                "Preflight failed. Fix the items above, or set SKIP_PREFLIGHT=1 to continue "
                "without checks (not recommended).",
                flush=True,
            )
            sys.exit(1)

    pxy = pick_proxy_url()
    attach = env_attach_existing_chrome()
    if pxy and not attach:
        print("Proxy (session):", pxy[:48], "...", flush=True)
    if attach and pxy:
        print("Note: proxy is ignored in attach mode (use system/VPN on host).", flush=True)

    if max_leads_override is not None:
        data = collect_linkedin_leads(
            _clamp_leads(max_leads_override), ask_limit_after_browser_ready=False
        )
    elif ASK_MAX_LEADS:
        data = collect_linkedin_leads(ask_limit_after_browser_ready=True)
    else:
        data = collect_linkedin_leads(_configured_max_leads(), ask_limit_after_browser_ready=False)

    if not data:
        print("No rows written. Check filters, 2nd-degree results, and that profiles load.")
        print_pipeline_footer(
            success=False,
            error="No rows collected (empty search or all profiles skipped).",
            rows=0,
        )
        return

    _repo = Path(__file__).resolve().parents[2]
    out_path = str(_repo / os.path.basename(LEADS_FILE))
    try:
        save_leads_file(data, out_path)
    except OSError as e:
        print_pipeline_footer(
            success=False,
            error=f"Excel write failed: {e!s}",
            rows=len(data),
            output_excel=out_path,
        )
        raise
    print(f"\nSaved: {out_path}", flush=True)

    if LNN_PUSH and LNN_BASE_URL and LNN_API_TOKEN:
        if LNN_IS_ADMIN and LNN_WORKSPACE_ID < 1:
            print("LNN_IS_ADMIN=1 needs LNN_WORKSPACE_ID. Skipping API push.", flush=True)
        else:
            print("LNN_PUSH: posting...", flush=True)
            wid = LNN_WORKSPACE_ID if LNN_IS_ADMIN else max(1, LNN_WORKSPACE_ID)
            for row in data:
                ok, msg = push_lead_to_backend(
                    row,
                    LNN_BASE_URL,
                    LNN_API_TOKEN,
                    wid,
                    is_admin=LNN_IS_ADMIN,
                )
                print(" ", row.get("Name", ""), "->", "ok" if ok else msg[:120], flush=True)

    print(f"Done. {len(data)} lead(s) -> {os.path.basename(LEADS_FILE)} (Excel only).")
    print_pipeline_footer(
        success=True,
        rows=len(data),
        output_excel=out_path,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="LinkedIn people search scraper (attach to Chrome, export Excel).",
    )
    parser.add_argument(
        "-n",
        "--max-leads",
        type=int,
        default=None,
        metavar="N",
        help="Scrape at most N leads (overrides MAX_LEADS in .env and ASK_MAX_LEADS).",
    )
    parser.add_argument(
        "-v",
        "--verify-only",
        "--check",
        action="store_true",
        help="Run health checks only, then exit.",
    )
    parser.add_argument(
        "extra",
        nargs="?",
        default="",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()
    if args.verify_only:
        from .preflight import run_verification

        sys.exit(0 if run_verification() else 1)
    ex = (args.extra or "").strip()
    if ex:
        el = ex.lower()
        if el in ("verify", "check", "v"):
            from .preflight import run_verification

            sys.exit(0 if run_verification() else 1)
        if ex.isdigit():
            run(max_leads_override=int(ex))
            sys.exit(0)
        print(f"Unknown argument: {ex!r}  (use: -n N, or: verify / check for preflight)", file=sys.stderr)
        sys.exit(2)
    run(max_leads_override=args.max_leads)
