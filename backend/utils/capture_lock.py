"""Exclusive lock so only one manual capture runs at a time (Windows-friendly)."""

from __future__ import annotations

import os
from pathlib import Path
from types import TracebackType


class CaptureLock:
    """
    Hold an OS-level exclusive create lock by keeping the lock file open.

    Uses mode ``x`` so a second process fails immediately with ``FileExistsError``.
    """

    def __init__(self, lock_path: str | Path) -> None:
        self._path = Path(lock_path)
        self._fh: object | None = None

    def __enter__(self) -> "CaptureLock":
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._fh = open(self._path, "x", encoding="utf-8")
        except FileExistsError as e:
            hint = self._read_stale_pid()
            msg = "Another LeadPilot safe capture is already running."
            if hint is not None:
                msg += f" (lock PID hint: {hint})"
            raise RuntimeError(msg) from e
        assert self._fh is not None
        self._fh.write(str(os.getpid()))
        self._fh.flush()
        return self

    def _read_stale_pid(self) -> str | None:
        try:
            return self._path.read_text(encoding="utf-8").strip() or None
        except OSError:
            return None

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._fh is not None:
            try:
                self._fh.close()
            except OSError:
                pass
            self._fh = None
        try:
            self._path.unlink(missing_ok=True)
        except OSError:
            pass
