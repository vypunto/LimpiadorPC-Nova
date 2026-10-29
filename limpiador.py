#!/usr/bin/env python3
"""Limpiador PC Nova — optimizador, reparador y protector para Windows.

Arranca un servidor local en 127.0.0.1 y abre la interfaz como ventana de
aplicación (Edge o Chrome en modo --app). Al cerrar la ventana, la app termina.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core import server  # noqa: E402
from core.utils import is_admin  # noqa: E402


def find_app_browser() -> str | None:
    env = os.environ
    candidates = [
        Path(env.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe",
        Path(env.get("ProgramFiles", r"C:\Program Files")) / "Microsoft/Edge/Application/msedge.exe",
        Path(env.get("ProgramFiles", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe",
        Path(env.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
        Path(env.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
        Path(env.get("ProgramFiles", r"C:\Program Files")) / "BraveSoftware/Brave-Browser/Application/brave.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


INSTANCE = Path(os.environ.get("LOCALAPPDATA", str(ROOT))) / "LimpiadorPC" / "instancia.json"


def app_profile() -> Path:
    profile = Path(os.environ.get("LOCALAPPDATA", str(ROOT))) / "LimpiadorPC" / ("ui-admin" if is_admin() else "ui")
    profile.mkdir(parents=True, exist_ok=True)
    return profile


def write_instance(url: str) -> None:
    try:
        INSTANCE.parent.mkdir(parents=True, exist_ok=True)
        INSTANCE.write_text(json.dumps({"url": url, "pid": os.getpid()}), encoding="utf-8")
    except OSError:
        pass


def clear_instance(url: str) -> None:
    try:
        if json.loads(INSTANCE.read_text(encoding="utf-8")).get("url") == url:
            INSTANCE.unlink()
    except (OSError, ValueError):
        pass


def running_instance() -> str | None:
    """URL de una instancia que ya está respondiendo, o None."""
    try:
        url = json.loads(INSTANCE.read_text(encoding="utf-8"))["url"]
    except (OSError, ValueError, KeyError):
        return None
    base, _, key = url.partition("/?k=")
    try:
        req = urllib.request.Request(base + "/api/ping", data=b"{}", headers={"X-Nova-Key": key, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=2) as r:
            return url if r.status == 200 else None
    except OSError:
        return None


def main() -> None:
    if "--auto-clean" in sys.argv:
        from core.schedule import auto_clean
        auto_clean()
        return
    # Una sola instancia: si la app ya está abierta, se abre otra ventana del mismo motor
    existing = running_instance()
    if existing and "--no-window" not in sys.argv:
        browser = find_app_browser()
        if browser:
            subprocess.Popen([browser, f"--app={existing}", f"--user-data-dir={app_profile()}", "--window-size=1380,880"])
        else:
            webbrowser.open(existing)
        return

    srv = server.make_server()
    port = srv.server_address[1]
    url = f"http://127.0.0.1:{port}/?k={server.TOKEN}"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    if "--no-window" not in sys.argv:
        write_instance(url)
    # Si el .exe se movio de carpeta, la limpieza automatica sigue apuntando bien
    from core.schedule import ensure_path
    threading.Thread(target=ensure_path, daemon=True).start()

    if "--no-window" in sys.argv:
        print(url, flush=True)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            return

    browser = find_app_browser()
    proc = None
    if browser:
        proc = subprocess.Popen([
            browser, f"--app={url}", f"--user-data-dir={app_profile()}", "--window-size=1380,880",
            "--no-first-run", "--no-default-browser-check", "--disable-features=Translate,msEdgeSidebarV2",
            "--disable-extensions", "--disable-sync",
        ])
    else:
        webbrowser.open(url)

    started = time.time()
    handed_off = False  # Chrome ya estaba abierto con este perfil y le pasó la ventana
    while True:
        time.sleep(1)
        now = time.time()
        st = server.STATE
        if proc is not None and not handed_off and proc.poll() is not None:
            if now - started < 10:
                handed_off = True  # el proceso salió enseguida: la ventana la gestiona otro Chrome
            else:
                break  # se cerró la ventana de la app
        # Respaldo: cierre explícito de la ventana o 20 min sin ninguna actividad
        if st.bye_at and now - st.bye_at > 6:
            break
        if (proc is None or handed_off) and now - st.last_ping > 1200:
            break
    clear_instance(url)  # lo primero: que una nueva apertura no se conecte a este motor que se cierra
    srv.shutdown()
    os._exit(0)  # no esperar a análisis que sigan en segundo plano


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — sin consola (.exe): que al menos quede registrado
        from core.errorlog import log

        log("arranque", str(exc), exc)
        raise
