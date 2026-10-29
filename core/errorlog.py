"""Registro de errores e informe técnico para soporte.

Los errores se guardan en %LOCALAPPDATA%\\LimpiadorPC\\errores.log. El informe técnico reúne
versión, Windows y los últimos errores, con la carpeta de usuario anonimizada y sin claves.
"""
from __future__ import annotations

import os
import platform
import re
import sys
import traceback
from datetime import datetime

from .history import DATA_DIR

LOG = DATA_DIR / "errores.log"
MAX_BYTES = 512 * 1024


def _anon(text: str) -> str:
    """Quita datos personales: carpeta de usuario, nombre de usuario y claves de API."""
    home = os.environ.get("USERPROFILE", "")
    user = os.environ.get("USERNAME", "")
    if home:
        text = re.sub(re.escape(home), r"%USERPROFILE%", text, flags=re.I)
    if user and len(user) > 2:
        text = re.sub(rf"\b{re.escape(user)}\b", "<usuario>", text, flags=re.I)
    return re.sub(r"sk-ant-[A-Za-z0-9_\-]+", "sk-ant-***", text)


def log(where: str, message: str = "", exc: BaseException | None = None) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if LOG.exists() and LOG.stat().st_size > MAX_BYTES:
            LOG.replace(LOG.with_suffix(".old.log"))
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)) if exc else ""
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {where}: {message}\n{tb}")
    except OSError:
        pass


def recent(n: int = 60) -> str:
    try:
        return "\n".join(LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-n:])
    except OSError:
        return ""


def report(state, client: dict | None = None) -> str:
    from . import __version__
    from .sysinfo import static_info
    from .utils import is_admin, is_frozen

    info = static_info() or {}
    jobs = sorted(state.jobs.values(), key=lambda j: j.started)[-25:]
    lines = [
        "=== Informe técnico · Limpiador PC Nova ===",
        f"Fecha: {datetime.now():%Y-%m-%d %H:%M}",
        f"Versión: {__version__} ({'exe' if is_frozen() else 'python ' + platform.python_version()})",
        f"Windows: {info.get('os', platform.platform())} · build {info.get('build', '?')} · {platform.machine()}",
        f"Equipo: {info.get('maker', '')} {info.get('machine', '')} · CPU {info.get('cpu', '')}",
        f"Gráficos: {', '.join(info.get('gpus') or [])}",
        f"Administrador: {'sí' if is_admin() else 'no'} · Idioma: {os.environ.get('LANG') or __import__('locale').getlocale()[0]}",
    ]
    if client:
        lines.append(f"Interfaz: {client.get('ua', '')} · pantalla {client.get('screen', '')} · tema {client.get('theme', '')}")
    lines.append("\n--- Últimas tareas ---")
    for j in jobs:
        lines.append(f"{datetime.fromtimestamp(j.started):%H:%M:%S} {j.kind:<14} {j.state:<9} {round((j.finished or j.started) - j.started, 1)} s  {j.error}")
    lines.append("\n--- Últimos errores ---")
    lines.append(recent() or "(ninguno)")
    return _anon("\n".join(lines))
