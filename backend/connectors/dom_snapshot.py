"""One-shot read of visible DOM text and common meta tags (no scrolling, no navigation)."""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page


def snapshot_visible_page(page: Page) -> dict[str, Any]:
    """
    Return a JSON-serializable snapshot of the **current** page only.

    Uses a single ``page.evaluate`` call (synchronous Playwright API).
    """
    return page.evaluate(
        """() => {
      const text = (s) => (s || '').trim();
      const pick = (sel) => {
        const el = document.querySelector(sel);
        return el ? text(el.textContent) : '';
      };
      const metas = {};
      for (const m of document.querySelectorAll('meta[property^="og:"], meta[name^="og:"]')) {
        const raw = m.getAttribute('property') || m.getAttribute('name') || '';
        const k = raw.replace(/^og:/i, '');
        const v = m.getAttribute('content');
        if (k && v) metas[k] = v;
      }
      const bodyText = (document.body && document.body.innerText) ? document.body.innerText : '';
      return {
        url: location.href,
        title: text(document.title),
        h1: pick('h1'),
        h2: pick('h2'),
        og: metas,
        textSample: text(bodyText).slice(0, 20000),
      };
    }"""
    )
