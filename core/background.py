"""Lo que corre en segundo plano: procesos de apps, servicios y tareas programadas de terceros."""
from __future__ import annotations

import re

from .utils import run_ps, run_ps_json

# Nunca se cierran desde la app (sistema, antivirus o la propia app)
PROTECTED_PROCS = {"explorer", "msmpeng", "securityhealthservice", "limpiadorpc-nova", "python", "pythonw", "py", "pyw",
                   "csrss", "winlogon", "lsass", "services", "smss", "wininit", "dwm", "svchost", "sihost", "ctfmon"}
# Servicios, tareas e inicio que no se dejan tocar: hardware, drivers, red y seguridad
ESSENTIAL = re.compile(
    r"audio|realtek|rtk|dolby|waves|nahimic|nvidia|nvcontainer|amd|radeon|intel|igfx|driver|bluetooth|wlan|wifi|wireless|"
    r"network|ethernet|killer|synaptics|elan|touchpad|precision|thunderbolt|battery|power|acpi|asus|armoury|lenovo|vantage|"
    r"\bhp\b|dell|msi|razer|logi|corsair|security|defender|antivirus|mcafee|norton|avast|avg|eset|kaspersky|bitdefender|malwarebytes|"
    r"firewall|vpn|wireguard|openvpn|backup|veeam|tpm|bitlocker|vmware|virtualbox|hyper-v|docker|wsl",
    re.I,
)


def is_essential(*texts: str) -> bool:
    return any(t and ESSENTIAL.search(t) for t in texts)


SAFE_NAME = re.compile(r"^[\w .()+\-]{1,120}$")


def _as_list(data) -> list:
    if data is None:
        return []
    return data if isinstance(data, list) else [data]


def processes() -> list[dict]:
    data = run_ps_json(
        "@(Get-Process | Where-Object { $_.Path -and $_.Path -notlike \"$env:SystemRoot\\*\" } | Group-Object ProcessName | ForEach-Object {"
        " $g=$_.Group; $f=$g[0]; [pscustomobject]@{ name=$_.Name; count=$_.Count;"
        " mem=($g | Measure-Object WorkingSet64 -Sum).Sum; cpu=[math]::Round(($g | Measure-Object CPU -Sum).Sum,0);"
        " path=$f.Path; company=[string]$f.Company; desc=[string]$f.Description;"
        " window=[bool]($g | Where-Object { $_.MainWindowHandle -ne 0 }) } })",
        timeout=40,
    )
    out = []
    for p in _as_list(data):
        p["protected"] = p.get("name", "").lower() in PROTECTED_PROCS
        out.append(p)
    out.sort(key=lambda p: p.get("mem") or 0, reverse=True)
    return out


def kill(name: str) -> tuple[bool, str]:
    if not SAFE_NAME.match(name) or name.lower() in PROTECTED_PROCS:
        return False, "Este proceso está protegido."
    code, _out, err = run_ps(f"Stop-Process -Name '{name}' -Force -ErrorAction Stop", timeout=20)
    if code != 0:
        return False, "No se pudo cerrar (puede necesitar admin): " + err.strip().splitlines()[0] if err.strip() else "No se pudo cerrar."
    return True, f"{name} cerrado. Volverá a abrirse si está en el inicio o lo abres tú."


def services() -> list[dict]:
    data = run_ps_json(
        "@(Get-CimInstance Win32_Service | Where-Object { $_.PathName -and $_.PathName -notmatch '\\\\Windows\\\\(System32|SysWOW64|servicing)\\\\'"
        " -and $_.PathName -notmatch 'Windows Defender|Microsoft\\\\Windows Defender' } | ForEach-Object {"
        " [pscustomobject]@{ name=$_.Name; display=$_.DisplayName; state=$_.State; mode=$_.StartMode; path=$_.PathName; desc=[string]$_.Description } })",
        timeout=40,
    )
    items = _as_list(data)
    for s in items:
        s["essential"] = is_essential(s.get("name"), s.get("display"), s.get("path"))
    order = {"Auto": 0, "Manual": 1, "Disabled": 2}
    items.sort(key=lambda s: (order.get(s.get("mode"), 3), str(s.get("display")).lower()))
    return items


def set_service(name: str, mode: str) -> tuple[bool, str]:
    if mode not in ("Automatic", "Manual") or not SAFE_NAME.match(name):
        return False, "Opción no permitida."
    if mode == "Manual":
        info = next((s for s in services() if s.get("name") == name), None)
        if info is None or info["essential"]:
            return False, "Servicio esencial (hardware, red o seguridad): bloqueado para proteger tu PC."
    code, _o, err = run_ps(f"Set-Service -Name '{name}' -StartupType {mode} -ErrorAction Stop", timeout=20)
    if code != 0:
        return False, "Necesita permisos de administrador." if "denied" in err.lower() or "acceso" in err.lower() else (err.strip()[:160] or "No se pudo cambiar.")
    return True, f"{name}: inicio {'automático' if mode == 'Automatic' else 'manual (arranca solo cuando se necesita)'}."


def tasks() -> list[dict]:
    data = run_ps_json(
        "@(Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.TaskPath -notlike '\\Microsoft\\*' } | ForEach-Object {"
        " [pscustomobject]@{ name=$_.TaskName; path=$_.TaskPath; state=[string]$_.State; author=[string]$_.Author;"
        " cmd=(($_.Actions | ForEach-Object { \"$($_.Execute) $($_.Arguments)\" }) -join ' ; ').Trim() } })",
        timeout=60,
    )
    items = _as_list(data)
    for t in items:
        t["essential"] = is_essential(t.get("name"), t.get("path"), t.get("cmd"), t.get("author"))
    items.sort(key=lambda t: (t.get("state") == "Disabled", str(t.get("name")).lower()))
    return items


def set_task(path: str, name: str, enabled: bool) -> tuple[bool, str]:
    if not SAFE_NAME.match(name) or not re.match(r"^\\[\w .\\\-]*$", path):
        return False, "Tarea no válida."
    if not enabled:
        info = next((t for t in tasks() if t.get("name") == name and t.get("path") == path), None)
        if info is None or info["essential"]:
            return False, "Tarea esencial (hardware, red o seguridad): bloqueada para proteger tu PC."
    verb = "Enable" if enabled else "Disable"
    code, _o, err = run_ps(f"{verb}-ScheduledTask -TaskPath '{path}' -TaskName '{name}' -ErrorAction Stop | Out-Null", timeout=20)
    if code != 0:
        return False, "Necesita permisos de administrador." if "denied" in err.lower() or "acceso" in err.lower() else (err.strip()[:160] or "No se pudo cambiar.")
    return True, f"Tarea {'activada' if enabled else 'desactivada'}: {name}"
