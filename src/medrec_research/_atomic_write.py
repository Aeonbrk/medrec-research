"""Atomic file write utilities to prevent corruption on crash/interrupt."""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path


def atomic_write(path: Path, content: str) -> None:
    """Write file atomically to prevent corruption on crash/interrupt.

    Uses the classic temp-file + atomic-rename pattern:
    1. Write to temporary file in same directory
    2. Flush and fsync to ensure durability
    3. Rename temp file to target (atomic operation on POSIX)

    This ensures the file is never partially written, even on crash or power loss.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", text=True)
    try:
        # Use fdopen to wrap fd as file object - handles short writes automatically
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk before rename

        # Atomic rename - if crash happens here, temp file remains but target is intact
        os.replace(tmp_path, path)
    except Exception:
        # Clean up temp file on any failure
        with contextlib.suppress(Exception):
            os.unlink(tmp_path)
        raise
