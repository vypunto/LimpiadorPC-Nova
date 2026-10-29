"""Accesos directos en el escritorio y el menú Inicio (sin instalador)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from .utils import app_command, is_frozen, known_folder, run_ps


def create() -> tuple[bool, str]:
    exe, args = app_command()
    icon = sys.executable if is_frozen() else str(Path(__file__).resolve().parents[1] / "tools" / "nova.ico")
    workdir = str(Path(exe).parent if is_frozen() else Path(__file__).resolve().parents[1])
    places = {
        "escritorio": known_folder("Desktop"),
        "menú Inicio": Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
    }
    made = []
    for label, folder in places.items():
        if not folder.exists():
            continue
        lnk = folder / "Limpiador PC Nova.lnk"
        q = lambda s: str(s).replace("'", "''")  # noqa: E731 — comillas para PowerShell
        code, _out, err = run_ps(
            f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{q(lnk)}');"
            f"$s.TargetPath='{q(exe)}';$s.Arguments='{q(args)}';$s.WorkingDirectory='{q(workdir)}';"
            f"$s.IconLocation='{q(icon)}';$s.Description='Optimiza, limpia, repara y protege tu PC';$s.Save()",
            timeout=30,
        )
        if code == 0 and lnk.exists():
            made.append(label)
    if not made:
        return False, "No se pudieron crear los accesos directos."
    return True, "Acceso directo creado en " + " y ".join(made) + "."
