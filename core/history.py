"""Historial de acciones (qué se limpió, borró o cambió y cuándo)."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "LimpiadorPC"
LOG = DATA_DIR / "historial.log"


def record(action: str, detail: str = "") -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {action} | {detail}\n")
    except OSError:
        pass


def recent(limit: int = 80) -> list[str]:
    try:
        return LOG.read_text(encoding="utf-8").splitlines()[-limit:][::-1]
    except OSError:
        return []
