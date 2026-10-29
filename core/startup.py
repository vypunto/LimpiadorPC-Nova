from __future__ import annotations

import os
import winreg
from dataclasses import dataclass
from pathlib import Path


@dataclass
class StartupItem:
    name: str
    command: str
    location: str
    hive: str
    enabled: bool
    impact: str  # bajo | medio | alto (heurística)
    approved: str = "Run"


HEAVY_HINTS = (
    "steam",
    "discord",
    "spotify",
    "adobe",
    "ccxprocess",
    "creativ cloud",
    "teams",
    "slack",
    "epic",
    "origin",
    "ubisoft",
    "itunes",
    "onedrive",
    "dropbox",
    "googledrive",
    "drivefs",
    "nvidia",
    "amd",
    "corsair",
    "logitech",
    "razerv",
    "ituneshelper",
    "skype",
    "zoom",
)


def _impact(name: str, command: str) -> str:
    blob = f"{name} {command}".lower()
    if any(h in blob for h in HEAVY_HINTS):
        return "alto"
    if "update" in blob or "helper" in blob or "tray" in blob:
        return "medio"
    return "bajo"


RUN_SOURCES = [
    # (hive, ruta Run, etiqueta, clave StartupApproved)
    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "Registro · usuario", "Run"),
    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "Registro · equipo", "Run"),
    (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "Registro · equipo (32 bits)", "Run32"),
]
APPROVED_BASE = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved"


def _startup_folders() -> list[tuple[int, Path, str]]:
    return [
        (winreg.HKEY_CURRENT_USER,
         Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup",
         "Carpeta Inicio · usuario"),
        (winreg.HKEY_LOCAL_MACHINE,
         Path(os.environ.get("ProgramData", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup",
         "Carpeta Inicio · equipo"),
    ]


def _approved_state(hive, sub: str) -> dict[str, bool]:
    """name.lower() -> habilitado. El bit bajo del primer byte a 1 significa deshabilitado."""
    states: dict[str, bool] = {}
    try:
        key = winreg.OpenKey(hive, APPROVED_BASE + "\\" + sub)
    except OSError:
        return states
    i = 0
    while True:
        try:
            name, value, _ = winreg.EnumValue(key, i)
            i += 1
        except OSError:
            break
        if isinstance(value, bytes) and value:
            states[str(name).lower()] = not (value[0] & 1)
    winreg.CloseKey(key)
    return states


def list_startup_run_entries() -> list[StartupItem]:
    items: list[StartupItem] = []
    for hive, path, label, approved in RUN_SOURCES:
        states = _approved_state(hive, approved)
        try:
            key = winreg.OpenKey(hive, path)
        except OSError:
            continue
        i = 0
        while True:
            try:
                name, value, _ = winreg.EnumValue(key, i)
                i += 1
            except OSError:
                break
            cmd = str(value)
            items.append(
                StartupItem(
                    name=str(name),
                    command=cmd,
                    location=label,
                    hive="HKCU" if hive == winreg.HKEY_CURRENT_USER else "HKLM",
                    enabled=states.get(str(name).lower(), True),
                    impact=_impact(str(name), cmd),
                    approved=approved,
                )
            )
        winreg.CloseKey(key)

    for hive, folder, label in _startup_folders():
        if not folder.exists():
            continue
        states = _approved_state(hive, "StartupFolder")
        for f in folder.iterdir():
            if f.name.lower() == "desktop.ini" or not f.is_file():
                continue
            items.append(
                StartupItem(
                    name=f.name,
                    command=str(f),
                    location=label,
                    hive="HKCU" if hive == winreg.HKEY_CURRENT_USER else "HKLM",
                    enabled=states.get(f.name.lower(), True),
                    impact=_impact(f.stem, str(f)),
                    approved="StartupFolder",
                )
            )

    impact_order = {"alto": 0, "medio": 1, "bajo": 2}
    items.sort(key=lambda x: (not x.enabled, impact_order.get(x.impact, 9), x.name.lower()))
    return items


def set_startup_enabled(name: str, hive_name: str, approved: str, enabled: bool) -> tuple[bool, str]:
    """Activa/desactiva igual que el Administrador de tareas (reversible, no borra la entrada)."""
    import struct
    import time

    from .background import is_essential

    if not enabled and (is_essential(name) or name.lower() in ("securityhealth", "windowsdefender")):
        return False, "Entrada esencial (hardware o seguridad): bloqueada para proteger tu PC."
    hive = winreg.HKEY_CURRENT_USER if hive_name == "HKCU" else winreg.HKEY_LOCAL_MACHINE
    if approved not in ("Run", "Run32", "StartupFolder"):
        return False, "Ubicación no válida."
    if enabled:
        data = bytes([2]) + bytes(11)
    else:
        filetime = int((time.time() + 11644473600) * 10_000_000)
        data = bytes([3, 0, 0, 0]) + struct.pack("<Q", filetime)
    try:
        key = winreg.CreateKeyEx(hive, APPROVED_BASE + "\\" + approved, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, name, 0, winreg.REG_BINARY, data)
        winreg.CloseKey(key)
    except PermissionError:
        return False, "Esta entrada es de todo el equipo: reinicia la app como administrador para cambiarla."
    except OSError as exc:
        return False, f"No se pudo cambiar: {exc}"
    return True, ("Activado" if enabled else "Desactivado") + f" al inicio: {name}"
