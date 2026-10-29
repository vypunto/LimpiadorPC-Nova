"""Organizar Descargas por tipo (reversible) y encontrar basura de proyectos de desarrollo."""
from __future__ import annotations

import json
import os
import shutil
import threading
import time
from pathlib import Path

from .history import DATA_DIR, record
from .unused import CATEGORIES
from .utils import downloads_dir, user_home

UNDO_FILE = DATA_DIR / "organizar_deshacer.json"
PARTIAL = {".crdownload", ".part", ".tmp", ".download", ".partial"}


def plan_downloads(folder: Path | None = None) -> list[dict]:
    """Archivos sueltos de Descargas → subcarpeta por categoría. No toca carpetas ni descargas en curso."""
    folder = folder or downloads_dir()
    now = time.time()
    plan = []
    for f in folder.iterdir():
        try:
            if not f.is_file() or f.suffix.lower() in PARTIAL or now - f.stat().st_mtime < 3600:
                continue
            size = f.stat().st_size
        except OSError:
            continue
        cat = next((c for c, exts in CATEGORIES.items() if f.suffix.lower() in exts), None)
        if cat:
            plan.append({"src": str(f), "dst": str(folder / cat / f.name), "category": cat, "size": size})
    return plan


def _free_name(dst: Path) -> Path:
    i = 1
    out = dst
    while out.exists():
        out = dst.with_name(f"{dst.stem} ({i}){dst.suffix}")
        i += 1
    return out


def apply_plan(plan: list[dict]) -> dict:
    base = downloads_dir().resolve()
    moved, failed = [], 0
    for item in plan:
        src, dst = Path(item["src"]), Path(item["dst"])
        # Solo dentro de Descargas
        if src.resolve().parent != base or dst.resolve().parent.parent != base:
            failed += 1
            continue
        try:
            dst.parent.mkdir(exist_ok=True)
            final = _free_name(dst)
            shutil.move(str(src), str(final))
            moved.append([str(src), str(final)])
        except OSError:
            failed += 1
    if moved:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        UNDO_FILE.write_text(json.dumps(moved, ensure_ascii=False), encoding="utf-8")
        record("Organizar Descargas", f"{len(moved)} archivos movidos a subcarpetas")
    return {"moved": len(moved), "failed": failed}


def undo() -> dict:
    try:
        moves = json.loads(UNDO_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"restored": 0, "message": "No hay nada que deshacer."}
    restored = 0
    for src, dst in moves:
        s, d = Path(src), Path(dst)
        if d.exists() and not s.exists():
            try:
                shutil.move(str(d), str(s))
                restored += 1
            except OSError:
                pass
    for d in {Path(dst).parent for _s, dst in moves}:
        try:
            d.rmdir()  # solo si quedó vacía
        except OSError:
            pass
    UNDO_FILE.unlink(missing_ok=True)
    record("Deshacer organizar", f"{restored} archivos devueltos")
    return {"restored": restored, "message": f"{restored} archivos devueltos a su sitio."}


# --- Basura de desarrollo ---------------------------------------------------

def _dev_kind(path: str, name: str) -> str | None:
    n = name.lower()
    if n == "node_modules":
        return "Dependencias Node (node_modules)"
    if n in (".venv", "venv", "env") and os.path.exists(os.path.join(path, name, "pyvenv.cfg")):
        return "Entorno virtual Python"
    if n == "__pycache__":
        return "Caché de Python"
    if n in (".next", ".nuxt", ".parcel-cache", ".turbo", ".angular"):
        return "Caché de build web"
    if n == "target" and os.path.exists(os.path.join(path, "Cargo.toml")):
        return "Compilación Rust (target)"
    if n == ".gradle" and os.path.exists(os.path.join(path, "settings.gradle")):
        return "Caché de Gradle"
    return None


def _size(path: str, stop) -> int:
    total = 0
    for root, dirs, files in os.walk(path, onerror=lambda _: None):
        if stop and stop.is_set():
            break
        for f in files:
            try:
                total += os.lstat(os.path.join(root, f)).st_size
            except OSError:
                pass
    return total


def find_dev_junk(stop_event: threading.Event | None = None, progress=None) -> list[dict]:
    home = user_home()
    roots = [p for p in home.iterdir() if p.is_dir() and not p.name.startswith(".") and p.name.lower() not in ("appdata", "onedrive")]
    out = []
    for root in roots:
        for dirpath, dirnames, _files in os.walk(root, onerror=lambda _: None):
            if stop_event and stop_event.is_set():
                return out
            keep = []
            for d in dirnames:
                kind = _dev_kind(dirpath, d)
                full = os.path.join(dirpath, d)
                if kind:
                    if progress:
                        progress(f"Midiendo {full}")
                    size = _size(full, stop_event)
                    if size > 1024 * 1024:
                        try:
                            mt = os.stat(dirpath).st_mtime
                        except OSError:
                            mt = 0
                        out.append({"path": full, "kind": kind, "size": size, "project": os.path.basename(dirpath), "mtime": mt})
                elif not d.startswith(".") and not os.path.islink(full) and d.lower() not in ("appdata",):
                    keep.append(d)
            dirnames[:] = keep
    out.sort(key=lambda x: x["size"], reverse=True)
    return out
