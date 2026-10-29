"""Información del equipo y métricas en vivo (CPU, RAM, discos, procesos)."""
from __future__ import annotations

import csv
import ctypes
import io
import threading
import time
from ctypes import wintypes

from .utils import get_drives, run_hidden, run_ps_json


class _FILETIME(ctypes.Structure):
    _fields_ = [("lo", wintypes.DWORD), ("hi", wintypes.DWORD)]


def _ft(ft: _FILETIME) -> int:
    return (ft.hi << 32) | ft.lo


class _MEMSTAT(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def memory() -> dict:
    st = _MEMSTAT()
    st.dwLength = ctypes.sizeof(_MEMSTAT)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))
    return {
        "load": int(st.dwMemoryLoad),
        "total": int(st.ullTotalPhys),
        "available": int(st.ullAvailPhys),
    }


class CpuSampler:
    """% de CPU a partir de GetSystemTimes entre dos llamadas."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last = self._times()

    @staticmethod
    def _times() -> tuple[int, int, int]:
        idle, kernel, user = _FILETIME(), _FILETIME(), _FILETIME()
        ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user))
        return _ft(idle), _ft(kernel), _ft(user)

    def percent(self) -> float:
        with self._lock:
            now = self._times()
            di = now[0] - self._last[0]
            total = (now[1] - self._last[1]) + (now[2] - self._last[2])
            self._last = now
        if total <= 0:
            return 0.0
        return max(0.0, min(100.0, (1 - di / total) * 100))


CPU = CpuSampler()


def uptime_seconds() -> int:
    return int(ctypes.windll.kernel32.GetTickCount64() // 1000)


def metrics() -> dict:
    return {
        "cpu": round(CPU.percent(), 1),
        "mem": memory(),
        "disks": [{"letter": l, "free": f, "total": t} for l, f, t in get_drives()],
        "uptime": uptime_seconds(),
        "ts": time.time(),
    }


_static_cache: dict | None = None


def static_info() -> dict:
    """Datos que no cambian (una sola llamada a PowerShell, cacheada)."""
    global _static_cache
    if _static_cache is not None:
        return _static_cache
    data = run_ps_json(
        "$os=Get-CimInstance Win32_OperatingSystem;"
        "$cs=Get-CimInstance Win32_ComputerSystem;"
        "$cpu=Get-CimInstance Win32_Processor | Select-Object -First 1;"
        "$gpu=@(Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name });"
        "$disk=@(Get-PhysicalDisk -ErrorAction SilentlyContinue | ForEach-Object { @{name=$_.FriendlyName; media=[string]$_.MediaType; health=[string]$_.HealthStatus; size=$_.Size} });"
        "[pscustomobject]@{os=$os.Caption; build=$os.BuildNumber; version=$os.Version; machine=$cs.Model;"
        " maker=$cs.Manufacturer; host=$env:COMPUTERNAME; user=$env:USERNAME; fullName=[string](Get-LocalUser -Name $env:USERNAME -ErrorAction SilentlyContinue).FullName; cpu=$cpu.Name.Trim();"
        " cores=$cpu.NumberOfCores; threads=$cpu.NumberOfLogicalProcessors; gpus=$gpu; disks=$disk;"
        " installDate=$os.InstallDate.ToString('yyyy-MM-dd')}",
        timeout=40,
    )
    _static_cache = data or {}
    return _static_cache


def top_processes(limit: int = 8) -> list[dict]:
    """Procesos que más memoria usan (agrupados por nombre)."""
    try:
        proc = run_hidden(["tasklist", "/fo", "csv", "/nh"], capture_output=True, timeout=15, check=False)
    except OSError:
        return []
    text = proc.stdout.decode("mbcs", errors="replace")
    groups: dict[str, dict] = {}
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 5:
            continue
        name = row[0]
        digits = "".join(ch for ch in row[4] if ch.isdigit())
        kb = int(digits) if digits else 0
        g = groups.setdefault(name.lower(), {"name": name, "mem": 0, "count": 0})
        g["mem"] += kb * 1024
        g["count"] += 1
    items = sorted(groups.values(), key=lambda g: g["mem"], reverse=True)
    return [g for g in items if g["name"].lower() not in ("system idle process", "memory compression")][:limit]
