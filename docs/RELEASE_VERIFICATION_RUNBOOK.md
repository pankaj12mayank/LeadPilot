# Release Verification Runbook

This runbook gives a repeatable way to prove "100% implemented" status for a prompt or release.

## Single Command

From repo root:

```bash
python scripts/verify_release.py --quick
```

For a wider pass:

```bash
python scripts/verify_release.py --full
```

The command generates a markdown proof file at:

- `logs/release-proof.md`

---

## What It Verifies

## 1) Backend critical regressions

- Auth flow and role checks
- User isolation and plan-aware config checks
- Company ingestion service reliability
- Debug validation endpoint
- Explorer filter/enrichment known regression guard

## 2) Frontend smoke tests

- Search/Mode flow tests (LinkedIn/Directory/Explorer interactions covered by test targets)

## 3) Output proof format

- Step-by-step pass/fail table
- Exit code and timings
- Final summary line for release decision

---

## Endpoint Smoke Checklist (manual, 2-3 minutes)

Run app:

```bash
python scripts/run_system.py
```

Then verify:

- `GET /health` -> `status: ok|degraded` payload exists
- `GET /validation` (auth required) -> `pipeline_checks`, `db_checks`, `source_checks`
- Login works from UI
- `Lead generation` page shows 3 modes:
  - LinkedIn Mode
  - Directory Mode
  - Explorer Mode
- Directory fetch creates visible leads in Leads page
- Explorer "Find Decision Makers" can create lead (with valid LinkedIn URL)
- Admin pages expose:
  - Dashboard
  - Users
  - Channels
  - AI Settings
  - Logs

---

## UI Acceptance Checklist

- User sees only own leads
- Buyer/user/admin role gating behaves correctly
- Channel switches are branded and readable
- Loading, success, and error toasts appear for key actions
- Empty states are explicit (no silent failures)

---

## Definition of Done (for future prompts)

Prompt can be marked "100% implemented" only when all are true:

1. Requested behavior is implemented in code.
2. No existing module regression is introduced.
3. `python scripts/verify_release.py --quick` passes.
4. Any prompt-specific failing test is fixed or justified with explicit follow-up.
5. Final report includes proof references (tests + files changed).
