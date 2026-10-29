from __future__ import annotations

import json
import os
import winreg
from dataclasses import dataclass
from pathlib import Path

from .utils import google_drive_letters, known_folder, user_home


@dataclass
class DriveInfo:
    roots: list[Path]
    account_token: str | None
    syncing: bool
    notes: list[str]
    prefs_raw: str | None = None


def _reg_value(path: str, name: str) -> str | None:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path)
        try:
            val, _ = winreg.QueryValueEx(key, name)
            return str(val)
        finally:
            winreg.CloseKey(key)
    except OSError:
        return None


def detect_drive_roots() -> list[Path]:
    """Carpetas de Google Drive en ESTE PC: la unidad que monta Drive (sea cual sea su letra) y la carpeta espejo."""
    home = user_home()
    candidates: list[Path] = []
    for letter in google_drive_letters():
        for sub in ("Mi unidad", "My Drive", ""):
            candidates.append(Path(f"{letter}\\") / sub if sub else Path(f"{letter}\\"))
    candidates += [home / "Google Drive", home / "Google Drive" / "Mi unidad", home / "Google Drive" / "My Drive", home / "Mi unidad", home / "My Drive"]

    seen: set[str] = set()
    roots: list[Path] = []
    for p in candidates:
        try:
            if not p.exists():
                continue
            key = str(p.resolve()).lower()
        except OSError:
            key = str(p).lower()
        if key in seen or any(key.startswith(s + "\\") for s in seen):
            continue
        seen.add(key)
        roots.append(p)
    # Si existe «Mi unidad», no hace falta escanear la raíz entera (evita duplicar resultados)
    return [r for r in roots if not (r.parent == r and any(x.parent == r for x in roots))]


def is_drive_path(path: str) -> bool:
    low = str(path).lower()
    return any(low.startswith(l.lower()) for l in google_drive_letters()) or "\\google drive\\" in low


def get_drive_info() -> DriveInfo:
    notes: list[str] = []
    token = _reg_value(r"Software\Google\DriveFS", "CurrentAccountToken")
    prefs = _reg_value(r"Software\Google\DriveFS", "PerAccountPreferences")
    drivefs_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "DriveFS"
    syncing = drivefs_dir.exists()
    notes.append("Google Drive para escritorio detectado." if syncing else "Google Drive para escritorio no está instalado en este PC.")
    if token:
        notes.append("Cuenta de Drive activa.")
    if prefs:
        try:
            n = len(json.loads(prefs).get("per_account_preferences", []))
            notes.append(f"Preferencias por cuenta: {n} entrada(s).")
        except json.JSONDecodeError:
            pass
    roots = detect_drive_roots()
    letters = google_drive_letters()
    if roots:
        notes.append("Se analizará: " + ", ".join(str(r) for r in roots[:6]))
    elif syncing:
        notes.append("Drive está instalado pero no se encontró su unidad. Ábrelo y vuelve a analizar.")
    if letters:
        notes.append("Aviso: si sincronizas Documentos o Escritorio con Drive en modo espejo, los archivos pueden ocupar espacio dos veces.")
    return DriveInfo(roots=roots, account_token=token, syncing=syncing, notes=notes, prefs_raw=prefs)


def default_scan_roots(include_drive: bool = True) -> list[Path]:
    """Carpetas personales reales de este PC (aunque estén en OneDrive u otro disco)."""
    roots: list[Path] = []
    seen: set[str] = set()
    for name in ("Downloads", "Documents", "Desktop", "Videos", "Pictures", "Music"):
        p = known_folder(name)
        k = str(p).lower()
        if p.exists() and k not in seen:
            seen.add(k)
            roots.append(p)
    if include_drive:
        roots.extend(detect_drive_roots())
    return roots
