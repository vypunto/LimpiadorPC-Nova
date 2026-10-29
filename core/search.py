from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path

from .utils import should_skip_dir


@dataclass
class SearchHit:
    path: Path
    size: int
    kind: str  # file | folder | program


def search_files(
    query: str,
    roots: list[Path],
    *,
    limit: int = 200,
    stop_event: threading.Event | None = None,
    progress_cb=None,
) -> list[SearchHit]:
    q = query.strip().lower()
    if not q:
        return []
    hits: list[SearchHit] = []
    count = 0
    for root in roots:
        if stop_event and stop_event.is_set():
            break
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(str(root), topdown=True, onerror=lambda _: None):
            if stop_event and stop_event.is_set():
                break
            dirnames[:] = [
                d
                for d in dirnames
                if not should_skip_dir(d)
                and not os.path.islink(os.path.join(dirpath, d))
            ]
            # folders
            base = os.path.basename(dirpath).lower()
            if q in base:
                try:
                    hits.append(SearchHit(path=Path(dirpath), size=0, kind="folder"))
                except OSError:
                    pass
            for name in filenames:
                if q not in name.lower():
                    continue
                fp = os.path.join(dirpath, name)
                try:
                    size = os.path.getsize(fp)
                except OSError:
                    size = 0
                hits.append(SearchHit(path=Path(fp), size=size, kind="file"))
                if len(hits) >= limit:
                    return hits
            count += 1
            if progress_cb and count % 50 == 0:
                progress_cb(len(hits), dirpath)
    return hits
