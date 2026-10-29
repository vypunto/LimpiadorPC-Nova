from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

from .utils import iter_files


@dataclass
class LargeFile:
    path: Path
    size: int


def find_large_files(
    roots: list[Path],
    *,
    min_bytes: int = 200 * 1024 * 1024,
    limit: int = 100,
    stop_event: threading.Event | None = None,
    progress_cb=None,
) -> list[LargeFile]:
    found: list[LargeFile] = []
    for path, size in iter_files(
        roots,
        min_size=min_bytes,
        stop_event=stop_event,
        skip_system=True,
        progress_cb=progress_cb,
    ):
        found.append(LargeFile(path=path, size=size))
    found.sort(key=lambda f: f.size, reverse=True)
    return found[:limit]
