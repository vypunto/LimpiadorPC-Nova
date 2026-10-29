from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path

from .utils import should_skip_dir


@dataclass
class FolderSize:
    path: Path
    size: int
    file_count: int


def top_folders(
    roots: list[Path],
    *,
    depth: int = 2,
    limit: int = 40,
    stop_event: threading.Event | None = None,
    progress_cb=None,
) -> list[FolderSize]:
    """Approximate largest folders by aggregating file sizes under each root/child."""
    totals: dict[str, list[int]] = {}  # path -> [size, files]

    def bump(key: str, size: int) -> None:
        if key not in totals:
            totals[key] = [0, 0]
        totals[key][0] += size
        totals[key][1] += 1

    scanned = 0
    for root in roots:
        if stop_event and stop_event.is_set():
            break
        if not root.exists():
            continue
        root_s = str(root.resolve()) if root.exists() else str(root)
        for dirpath, dirnames, filenames in os.walk(root_s, topdown=True, onerror=lambda _: None):
            if stop_event and stop_event.is_set():
                break
            dirnames[:] = [
                d
                for d in dirnames
                if not should_skip_dir(d) and not os.path.islink(os.path.join(dirpath, d))
            ]
            rel = os.path.relpath(dirpath, root_s)
            parts = [] if rel == "." else rel.split(os.sep)
            # Aggregate into root and first `depth` levels
            keys = [root_s]
            for i in range(min(depth, len(parts))):
                keys.append(os.path.join(root_s, *parts[: i + 1]))

            for name in filenames:
                fp = os.path.join(dirpath, name)
                try:
                    if os.path.islink(fp):
                        continue
                    size = os.path.getsize(fp)
                except OSError:
                    continue
                for k in keys:
                    bump(k, size)
                scanned += 1
                if progress_cb and scanned % 400 == 0:
                    progress_cb(scanned, dirpath)

    items = [
        FolderSize(path=Path(p), size=vals[0], file_count=vals[1])
        for p, vals in totals.items()
        if vals[0] > 0
    ]
    items.sort(key=lambda x: x.size, reverse=True)
    return items[:limit]
