"""Limpieza automática semanal mediante el Programador de tareas (usuario actual, sin admin)."""
from __future__ import annotations

import os

from .utils import app_command, run_hidden

TASK = "LimpiadorPC Nova - Limpieza semanal"
DAYS = {"MON": "lunes", "TUE": "martes", "WED": "miércoles", "THU": "jueves", "FRI": "viernes", "SAT": "sábado", "SUN": "domingo"}


def status() -> dict:
    p = run_hidden(["schtasks", "/query", "/tn", TASK, "/xml"], capture_output=True, check=False)
    if p.returncode != 0:
        return {"enabled": False}
    text = p.stdout.decode("utf-16", errors="replace") if p.stdout[:2] in (b"\xff\xfe", b"\xfe\xff") else p.stdout.decode("mbcs", errors="replace")
    names = {"Monday": "MON", "Tuesday": "TUE", "Wednesday": "WED", "Thursday": "THU", "Friday": "FRI", "Saturday": "SAT", "Sunday": "SUN"}
    day = next((v for k, v in names.items() if f"<{k} />" in text or f"<{k}/>" in text), "SUN")
    import re

    cmd = re.search(r"<Command>(.*?)</Command>", text, re.S)
    return {"enabled": True, "day": day, "command": (cmd.group(1).strip().strip('"') if cmd else "")}


def ensure_path() -> None:
    """Si el .exe (o la carpeta de la app) se movió, actualiza la tarea para que siga funcionando."""
    st = status()
    if not st.get("enabled"):
        return
    exe, _args = app_command("--auto-clean")
    if os.path.normcase(st.get("command", "")) != os.path.normcase(exe):
        ok, _msg = enable(st.get("day", "SUN"))
        if ok:
            from .history import record

            record("Limpieza automática", f"ruta actualizada a {exe}")


def enable(day: str = "SUN", hour: str = "12:00") -> tuple[bool, str]:
    if day not in DAYS:
        return False, "Día no válido."
    exe, args = app_command("--auto-clean")
    p = run_hidden(["schtasks", "/create", "/f", "/tn", TASK, "/sc", "WEEKLY", "/d", day, "/st", hour, "/tr", f'"{exe}" {args}'],
                   capture_output=True, check=False)
    if p.returncode != 0:
        return False, "No se pudo crear la tarea: " + p.stderr.decode("mbcs", errors="replace").strip()
    return True, f"Limpieza automática cada {DAYS[day]} a las {hour}."


def disable() -> tuple[bool, str]:
    p = run_hidden(["schtasks", "/delete", "/f", "/tn", TASK], capture_output=True, check=False)
    return p.returncode == 0, "Limpieza automática desactivada." if p.returncode == 0 else "No había tarea programada."


def auto_clean() -> int:
    """Lo que ejecuta la tarea: solo categorías seguras por defecto y sin permisos de admin."""
    from .cleaner import build_targets, clean_target
    from .history import record
    from .utils import format_size

    freed = 0
    for t in build_targets():
        if t.selected and not t.admin and not t.special:
            freed += clean_target(t)[0]
    record("Limpieza automática", format_size(freed))
    return freed
