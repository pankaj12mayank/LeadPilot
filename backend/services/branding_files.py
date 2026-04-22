"""Save admin-uploaded logo and favicon under ``config.BRANDING_UPLOAD_DIR``."""

from __future__ import annotations

from pathlib import Path

import config

_LOGO_EXT = frozenset({".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"})
_FAV_EXT = frozenset({".ico", ".png", ".svg"})


def _ext_from_name(name: str) -> str:
    return Path(name or "").suffix.lower()


def save_branding_logo(filename: str, data: bytes) -> str:
    ext = _ext_from_name(filename) or ".png"
    if ext not in _LOGO_EXT:
        raise ValueError("unsupported_logo_type")
    return _write_kind("logo", ext, data)


def save_branding_favicon(filename: str, data: bytes) -> str:
    ext = _ext_from_name(filename) or ".ico"
    if ext not in _FAV_EXT:
        raise ValueError("unsupported_favicon_type")
    return _write_kind("favicon", ext, data)


def _write_kind(kind: str, ext: str, data: bytes) -> str:
    root = Path(config.BRANDING_UPLOAD_DIR)
    root.mkdir(parents=True, exist_ok=True)
    for p in root.glob(f"{kind}.*"):
        try:
            p.unlink()
        except OSError:
            pass
    out = root / f"{kind}{ext}"
    out.write_bytes(data)
    return f"/branding/{out.name}"


def clear_branding_logo() -> None:
    _clear_glob("logo.*")


def clear_branding_favicon() -> None:
    _clear_glob("favicon.*")


def _clear_glob(pattern: str) -> None:
    root = Path(config.BRANDING_UPLOAD_DIR)
    if not root.is_dir():
        return
    for p in root.glob(pattern):
        try:
            p.unlink()
        except OSError:
            pass
