from __future__ import annotations

import os
import winreg
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class InstalledProgram:
    name: str
    publisher: str
    version: str
    install_date: datetime | None
    install_location: str
    uninstall_string: str
    estimated_size_kb: int | None
    last_exe_mtime: datetime | None
    days_since_touch: int | None
    likely_unused: bool


def _parse_install_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    raw = str(raw).strip()
    for fmt in ("%Y%m%d", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw[:10] if fmt == "%Y-%m-%d" else raw[:8] if fmt == "%Y%m%d" else raw, fmt)
        except ValueError:
            continue
    return None


def _exe_mtime(location: str) -> datetime | None:
    if not location:
        return None
    root = Path(location.strip().strip('"'))
    if not root.exists():
        return None
    newest = None
    try:
        if root.is_file():
            return datetime.fromtimestamp(root.stat().st_mtime)
        # Look at a few executables without deep walk
        for pattern in ("*.exe", "*/*.exe"):
            for exe in root.glob(pattern):
                try:
                    mt = datetime.fromtimestamp(exe.stat().st_mtime)
                except OSError:
                    continue
                if newest is None or mt > newest:
                    newest = mt
    except OSError:
        return None
    return newest


def _enum_uninstall(root, path: str) -> list[InstalledProgram]:
    programs: list[InstalledProgram] = []
    try:
        key = winreg.OpenKey(root, path)
    except OSError:
        return programs

    i = 0
    while True:
        try:
            sub = winreg.EnumKey(key, i)
            i += 1
        except OSError:
            break
        try:
            sk = winreg.OpenKey(key, sub)
        except OSError:
            continue
        def get(name: str, default: str = "") -> str:
            try:
                val, _ = winreg.QueryValueEx(sk, name)
                return str(val) if val is not None else default
            except OSError:
                return default

        name = get("DisplayName")
        if not name:
            winreg.CloseKey(sk)
            continue
        # Skip updates/hotfixes noise
        lower = name.lower()
        if "update for" in lower or "security update" in lower or name.startswith("KB"):
            winreg.CloseKey(sk)
            continue

        publisher = get("Publisher")
        version = get("DisplayVersion")
        location = get("InstallLocation")
        uninstall = get("UninstallString")
        install_date = _parse_install_date(get("InstallDate") or None)
        size_kb = None
        try:
            raw_size, _ = winreg.QueryValueEx(sk, "EstimatedSize")
            size_kb = int(raw_size)
        except OSError:
            size_kb = None

        exe_mt = _exe_mtime(location)
        touch = exe_mt or install_date
        days = (datetime.now() - touch).days if touch else None
        likely = bool(days is not None and days >= 180)

        programs.append(
            InstalledProgram(
                name=name,
                publisher=publisher,
                version=version,
                install_date=install_date,
                install_location=location,
                uninstall_string=uninstall,
                estimated_size_kb=size_kb,
                last_exe_mtime=exe_mt,
                days_since_touch=days,
                likely_unused=likely,
            )
        )
        winreg.CloseKey(sk)

    winreg.CloseKey(key)
    return programs


def list_installed_programs(unused_days: int = 180) -> list[InstalledProgram]:
    roots = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    all_p: list[InstalledProgram] = []
    seen: set[str] = set()
    cutoff = unused_days
    for root, path in roots:
        for prog in _enum_uninstall(root, path):
            key = prog.name.lower()
            if key in seen:
                continue
            seen.add(key)
            if prog.days_since_touch is not None:
                prog.likely_unused = prog.days_since_touch >= cutoff
            all_p.append(prog)

    all_p.sort(key=lambda p: (not p.likely_unused, -(p.days_since_touch or -1), p.name.lower()))
    return all_p


def uninstall_program(uninstall_string: str) -> tuple[bool, str]:
    """Lanza el desinstalador oficial del programa (el usuario confirma en su asistente)."""
    import subprocess

    cmd = (uninstall_string or "").strip()
    if not cmd:
        return False, "Este programa no tiene desinstalador registrado."
    low = cmd.lower()
    if "msiexec" in low:
        cmd = cmd.replace("/I{", "/X{").replace("/i{", "/X{")
    try:
        subprocess.Popen(cmd, shell=True)
        return True, "Se abrió el desinstalador del programa."
    except OSError as exc:
        return False, f"No se pudo abrir el desinstalador: {exc}"
