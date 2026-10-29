"""Archivos que no se usan desde hace tiempo (por fecha de último acceso/modificación)."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path

from .utils import iter_files

CATEGORIES = {
    "Instaladores": {".exe", ".msi", ".msix", ".appx", ".msixbundle"},
    "Imágenes de disco": {".iso", ".img", ".vhd", ".vhdx", ".vmdk"},
    "Comprimidos": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"},
    "Vídeos": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".m4v"},
    "Audio": {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"},
    "Imágenes": {".jpg", ".jpeg", ".png", ".gif", ".heic", ".raw", ".cr2", ".nef", ".psd", ".tif", ".tiff", ".webp"},
    "Documentos": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".odt", ".csv"},
}


def category_of(path: Path) -> str:
    ext = path.suffix.lower()
    for cat, exts in CATEGORIES.items():
        if ext in exts:
            return cat
    return "Otros"


@dataclass
class UnusedFile:
    path: Path
    size: int
    last_used: float
    days: int
    category: str


def find_unused(
    roots: list[Path],
    *,
    days: int = 365,
    min_bytes: int = 10 * 1024 * 1024,
    limit: int = 500,
    stop_event: threading.Event | None = None,
    progress_cb=None,
) -> list[UnusedFile]:
    now = time.time()
    cutoff = now - days * 86400
    out: list[UnusedFile] = []
    for path, size in iter_files(roots, min_size=min_bytes, stop_event=stop_event, progress_cb=progress_cb):
        try:
            st = path.stat()
        except OSError:
            continue
        # NTFS no siempre actualiza atime: usamos la fecha más reciente de las dos
        last = max(st.st_atime, st.st_mtime)
        if last > cutoff:
            continue
        out.append(UnusedFile(path, size, last, int((now - last) // 86400), category_of(path)))
    out.sort(key=lambda f: f.size, reverse=True)
    return out[:limit]
