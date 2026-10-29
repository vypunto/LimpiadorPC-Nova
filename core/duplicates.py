from __future__ import annotations

import hashlib
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .utils import iter_files, quick_file_fingerprint


@dataclass
class DuplicateGroup:
    fingerprint: str
    size: int
    paths: list[Path]
    mtimes: list[float] = field(default_factory=list)

    @property
    def wasted(self) -> int:
        if len(self.paths) < 2:
            return 0
        return self.size * (len(self.paths) - 1)


def _full_hash(path: Path, stop_event: threading.Event | None = None) -> str | None:
    h = hashlib.blake2b(digest_size=20)
    try:
        with path.open("rb") as f:
            while True:
                if stop_event and stop_event.is_set():
                    return None
                data = f.read(4 * 1024 * 1024)
                if not data:
                    break
                h.update(data)
    except OSError:
        return None
    return h.hexdigest()


def find_duplicates(
    roots: list[Path],
    *,
    min_bytes: int = 1024 * 1024,
    stop_event: threading.Event | None = None,
    progress_cb=None,
    hash_progress=None,
) -> list[DuplicateGroup]:
    """Tamaño → huella rápida (inicio+final) → hash completo. Solo agrupa copias idénticas byte a byte."""
    by_size: dict[int, list[Path]] = defaultdict(list)
    for path, size in iter_files(
        roots,
        min_size=min_bytes,
        stop_event=stop_event,
        skip_system=True,
        progress_cb=progress_cb,
    ):
        by_size[size].append(path)

    candidates: list[tuple[int, list[Path]]] = []
    for size, paths in by_size.items():
        if stop_event and stop_event.is_set():
            break
        if len(paths) < 2:
            continue
        by_fp: dict[str, list[Path]] = defaultdict(list)
        for p in paths:
            by_fp[quick_file_fingerprint(p, size)].append(p)
        candidates.extend((size, pl) for pl in by_fp.values() if len(pl) >= 2)

    total = sum(len(pl) for _, pl in candidates) or 1
    done = 0
    groups: list[DuplicateGroup] = []
    for size, plist in candidates:
        if stop_event and stop_event.is_set():
            break
        by_hash: dict[str, list[Path]] = defaultdict(list)
        for p in plist:
            h = _full_hash(p, stop_event)
            done += 1
            if hash_progress:
                hash_progress(done / total, str(p))
            if h:
                by_hash[h].append(p)
        for h, same in by_hash.items():
            if len(same) < 2:
                continue
            mt = []
            for p in same:
                try:
                    mt.append(p.stat().st_mtime)
                except OSError:
                    mt.append(0.0)
            # El más antiguo primero: es el que se sugiere conservar
            pairs = sorted(zip(same, mt), key=lambda x: (x[1], len(str(x[0]))))
            groups.append(DuplicateGroup(h, size, [p for p, _ in pairs], [m for _, m in pairs]))

    groups.sort(key=lambda g: g.wasted, reverse=True)
    return groups


def flag_drive_local_pairs(groups: list[DuplicateGroup]) -> list[DuplicateGroup]:
    """Pone primero los grupos que tienen copia en Google Drive y en el PC (sea cual sea la letra de Drive)."""
    from .drive import is_drive_path

    def score(g: DuplicateGroup) -> tuple[int, int]:
        has_g = any(is_drive_path(p) for p in g.paths)
        has_local = any(not is_drive_path(p) for p in g.paths)
        return (1 if has_g and has_local else 0, g.wasted)

    return sorted(groups, key=score, reverse=True)
