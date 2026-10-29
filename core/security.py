"""Seguridad: estado de Microsoft Defender, análisis y auditoría de persistencia.

El análisis antimalware lo hace el motor de Defender (firmas reales). La
auditoría añade comprobaciones heurísticas de lo que el malware suele tocar:
inicio, tareas programadas, archivo hosts, proxy, firewall y UAC.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import winreg
from dataclasses import dataclass
from pathlib import Path

from .utils import NO_WINDOW, run_ps_json

MPCMD_CANDIDATES = [
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Windows Defender" / "MpCmdRun.exe",
]


@dataclass
class Finding:
    severity: str  # high | medium | low | ok
    area: str
    title: str
    detail: str
    path: str = ""


SUSPICIOUS_DIRS = (
    r"\appdata\local\temp",
    r"\windows\temp",
    r"\users\public",
    r"\programdata\\",
    r"\appdata\roaming\\",
    r"\downloads\\",
    r"\$recycle.bin",
)

# Ubicaciones normales de apps legítimas dentro de AppData/ProgramData
TRUSTED_FRAGMENTS = (
    r"\appdata\local\microsoft",
    r"\appdata\local\programs",
    r"\appdata\roaming\microsoft",
    r"\appdata\roaming\spotify",
    r"\appdata\roaming\zoom",
    r"\appdata\local\discord",
    r"\appdata\roaming\discord",
    r"\programdata\microsoft",
    r"\programdata\package cache",
    r"\appdata\roaming\dropbox",
    r"\appdata\local\google",
)

LOLBIN_PATTERNS = [
    (re.compile(r"powershell(\.exe)?\b.*(-enc|-encodedcommand|-e\s+[a-z0-9+/=]{20,})", re.I), "PowerShell con comando codificado"),
    (re.compile(r"powershell(\.exe)?\b.*(downloadstring|iwr|invoke-webrequest|frombase64string|hidden)", re.I), "PowerShell que descarga u oculta código"),
    (re.compile(r"\bmshta(\.exe)?\b", re.I), "mshta (ejecuta HTA/scripts remotos)"),
    (re.compile(r"\b(wscript|cscript)(\.exe)?\b.*\.(vbs|js|jse|vbe|wsf)", re.I), "Script VBS/JS al inicio"),
    (re.compile(r"\bregsvr32(\.exe)?\b.*(/i:|scrobj)", re.I), "regsvr32 con scriptlet"),
    (re.compile(r"\brundll32(\.exe)?\b.*(javascript:|http)", re.I), "rundll32 con script/URL"),
    (re.compile(r"\bcertutil(\.exe)?\b.*-urlcache", re.I), "certutil descargando archivos"),
    (re.compile(r"\bbitsadmin(\.exe)?\b.*/transfer", re.I), "bitsadmin descargando archivos"),
]


def _exe_from_command(cmd: str) -> str:
    cmd = os.path.expandvars(cmd.strip())
    if cmd.startswith('"'):
        end = cmd.find('"', 1)
        return cmd[1:end] if end > 0 else cmd.strip('"')
    m = re.match(r"(.+?\.(exe|bat|cmd|vbs|js|ps1|com|scr|lnk))\b", cmd, re.I)
    return m.group(1) if m else cmd.split(" ")[0]


def assess_command(cmd: str) -> tuple[str, str] | None:
    """Devuelve (severidad, motivo) si el comando de arranque parece sospechoso."""
    low = os.path.expandvars(cmd).lower()
    for rx, why in LOLBIN_PATTERNS:
        if rx.search(cmd):
            return "high", why
    exe = _exe_from_command(cmd).lower()
    if exe.endswith((".vbs", ".js", ".jse", ".vbe", ".wsf", ".scr", ".ps1")):
        return "medium", "Se ejecuta un script directamente al iniciar"
    if any(t in low for t in TRUSTED_FRAGMENTS):
        return None
    for d in SUSPICIOUS_DIRS:
        if d.rstrip("\\") in exe:
            if r"\temp" in d or "public" in d or "recycle" in d or "downloads" in d:
                return "high", "Ejecutable en una carpeta temporal o pública"
            name = Path(exe).stem
            if re.fullmatch(r"[a-z0-9]{8,}", name) and sum(ch.isdigit() for ch in name) >= 3:
                return "high", "Nombre aleatorio en AppData/ProgramData"
            return "low", "Ejecutable fuera de Program Files (habitual en algunas apps, revisa si no lo reconoces)"
    if exe and not os.path.exists(exe) and ("\\" in exe):
        return "low", "La entrada apunta a un archivo que ya no existe"
    return None


def _reg_values(hive, path: str) -> list[tuple[str, str]]:
    out = []
    try:
        key = winreg.OpenKey(hive, path)
    except OSError:
        return out
    i = 0
    while True:
        try:
            name, val, _ = winreg.EnumValue(key, i)
        except OSError:
            break
        out.append((str(name), str(val)))
        i += 1
    winreg.CloseKey(key)
    return out


def _reg_get(hive, path: str, name: str):
    try:
        key = winreg.OpenKey(hive, path)
        try:
            return winreg.QueryValueEx(key, name)[0]
        finally:
            winreg.CloseKey(key)
    except OSError:
        return None


def defender_status() -> dict:
    data = run_ps_json(
        "Get-MpComputerStatus | Select-Object AMServiceEnabled,AntivirusEnabled,RealTimeProtectionEnabled,"
        "IsTamperProtected,AntivirusSignatureAge,AntivirusSignatureVersion,"
        "@{n='SignatureUpdated';e={$_.AntivirusSignatureLastUpdated.ToString('yyyy-MM-dd HH:mm')}},"
        "QuickScanAge,FullScanAge,"
        "@{n='QuickScanEnd';e={if($_.QuickScanEndTime){$_.QuickScanEndTime.ToString('yyyy-MM-dd HH:mm')}}},"
        "@{n='FullScanEnd';e={if($_.FullScanEndTime){$_.FullScanEndTime.ToString('yyyy-MM-dd HH:mm')}}}",
        timeout=30,
    )
    if not isinstance(data, dict):
        return {"available": False}
    data["available"] = True
    # QuickScanAge = 4294967295 cuando nunca se ha hecho
    for k in ("QuickScanAge", "FullScanAge"):
        if isinstance(data.get(k), int) and data[k] > 100000:
            data[k] = None
    return data


def defender_threats() -> list[dict]:
    data = run_ps_json(
        "$names=@{}; Get-MpThreat -ErrorAction SilentlyContinue | ForEach-Object { $names[[string]$_.ThreatID]=@{n=$_.ThreatName;s=$_.SeverityID} };"
        "@(Get-MpThreatDetection -ErrorAction SilentlyContinue | Sort-Object InitialDetectionTime -Descending | Select-Object -First 30 | ForEach-Object {"
        " $t=$names[[string]$_.ThreatID]; [pscustomobject]@{"
        " name=$(if($t){$t.n}else{'ID '+$_.ThreatID}); severity=$(if($t){$t.s}else{0});"
        " when=$_.InitialDetectionTime.ToString('yyyy-MM-dd HH:mm'); status=[string]$_.ThreatStatusID;"
        " action=[string]$_.CleaningActionID; resources=@($_.Resources | Select-Object -First 3) } })",
        timeout=40,
    )
    if data is None:
        return []
    if isinstance(data, dict):
        data = [data]
    status_map = {"1": "Detectada", "2": "Limpiada", "3": "En cuarentena", "4": "Eliminada", "5": "Permitida",
                  "6": "Bloqueada", "102": "Error al limpiar", "103": "Error en cuarentena", "105": "Error al eliminar"}
    sev_map = {1: "Baja", 2: "Moderada", 4: "Alta", 5: "Grave"}
    for t in data:
        t["status_es"] = status_map.get(str(t.get("status")), "Gestionada")
        t["severity_es"] = sev_map.get(t.get("severity"), "—")
    return data


def mpcmdrun() -> Path | None:
    for c in MPCMD_CANDIDATES:
        if c.exists():
            return c
    return None


def run_defender(args: list[str], log, stop_event=None) -> int:
    exe = mpcmdrun()
    if exe is None:
        log("No se encontró MpCmdRun.exe (Microsoft Defender).", False)
        return 1
    argv = [str(exe), *args]
    log("› " + " ".join(argv[1:]), False)
    proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                            creationflags=NO_WINDOW)
    assert proc.stdout is not None
    for raw in iter(proc.stdout.readline, b""):
        line = raw.decode("utf-8", errors="replace").replace("\x00", "").strip()
        if line:
            log(line, False)
        if stop_event is not None and stop_event.is_set():
            proc.kill()
            log("Análisis cancelado.", False)
            return 1
    return proc.wait()


def _startup_findings() -> list[Finding]:
    findings: list[Finding] = []
    sources = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "Inicio (usuario)"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "RunOnce (usuario)"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "Inicio (equipo)"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "Inicio (equipo 32 bits)"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "RunOnce (equipo)"),
    ]
    for hive, path, label in sources:
        for name, cmd in _reg_values(hive, path):
            res = assess_command(cmd)
            if res:
                findings.append(Finding(res[0], "Inicio", f"{name}", f"{res[1]} · {label}", cmd))
    # Winlogon Shell/Userinit secuestrados
    shell = _reg_get(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows NT\CurrentVersion\Winlogon", "Shell")
    if shell and str(shell).strip().lower() not in ("explorer.exe", "explorer.exe,"):
        findings.append(Finding("high", "Sistema", "Winlogon Shell modificado", "Debería ser explorer.exe", str(shell)))
    userinit = _reg_get(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows NT\CurrentVersion\Winlogon", "Userinit")
    if userinit:
        parts = [p.strip().lower() for p in str(userinit).split(",") if p.strip()]
        if any(not p.endswith("userinit.exe") for p in parts):
            findings.append(Finding("high", "Sistema", "Userinit modificado", "Hay programas extra en el inicio de sesión", str(userinit)))
    # Carpetas de Inicio
    for folder in (
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup",
        Path(os.environ.get("ProgramData", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup",
    ):
        if not folder.exists():
            continue
        for f in folder.iterdir():
            if f.suffix.lower() in (".vbs", ".js", ".jse", ".vbe", ".wsf", ".bat", ".cmd", ".ps1", ".exe", ".scr"):
                sev = "medium" if f.suffix.lower() in (".exe", ".bat", ".cmd") else "high"
                findings.append(Finding(sev, "Inicio", f.name, "Archivo ejecutable o script en la carpeta Inicio", str(f)))
    return findings


def _task_findings() -> list[Finding]:
    data = run_ps_json(
        "@(Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.State -ne 'Disabled' -and $_.TaskPath -notlike '\\Microsoft\\*' } | ForEach-Object {"
        " $t=$_; foreach($a in $t.Actions){ if($a.Execute){ [pscustomobject]@{name=$t.TaskName; path=$t.TaskPath; cmd=(\"$($a.Execute) $($a.Arguments)\").Trim()} } } })",
        timeout=60,
    )
    if data is None:
        return []
    if isinstance(data, dict):
        data = [data]
    out = []
    for t in data:
        cmd = str(t.get("cmd", ""))
        res = assess_command(cmd)
        if res and res[0] != "low":
            out.append(Finding(res[0], "Tareas programadas", str(t.get("name")), res[1], cmd))
    return out


def _hosts_finding() -> list[Finding]:
    hosts = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "drivers" / "etc" / "hosts"
    try:
        lines = hosts.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    entries = []
    for ln in lines:
        ln = ln.split("#", 1)[0].strip()
        if not ln:
            continue
        parts = ln.split()
        if len(parts) >= 2 and parts[1].lower() not in ("localhost", "localhost.localdomain"):
            entries.append(ln)
    if not entries:
        return [Finding("ok", "Red", "Archivo hosts limpio", "Sin redirecciones de dominios.", str(hosts))]
    big = [e for e in entries if any(d in e.lower() for d in ("google", "microsoft", "windowsupdate", "bank", "paypal", "facebook", "apple"))]
    sev = "high" if big and not all(e.split()[0] in ("0.0.0.0", "127.0.0.1") for e in big) else "low"
    sample = "; ".join(entries[:4]) + (" …" if len(entries) > 4 else "")
    return [Finding(sev, "Red", f"Archivo hosts con {len(entries)} redirección(es)",
                    "Pueden ser de un bloqueador de anuncios o de malware que redirige webs.", sample)]


def _proxy_finding() -> list[Finding]:
    path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    enabled = _reg_get(winreg.HKEY_CURRENT_USER, path, "ProxyEnable")
    server = _reg_get(winreg.HKEY_CURRENT_USER, path, "ProxyServer")
    pac = _reg_get(winreg.HKEY_CURRENT_USER, path, "AutoConfigURL")
    if pac:
        return [Finding("medium", "Red", "Configuración automática de proxy (PAC)",
                        "Todo tu tráfico web pasa por un script. Correcto en empresas; sospechoso en casa.", str(pac))]
    if enabled:
        return [Finding("medium", "Red", "Proxy activado", "Tu navegación pasa por un servidor intermedio.", str(server or ""))]
    return [Finding("ok", "Red", "Sin proxy", "La conexión web va directa.")]


def _uac_finding() -> list[Finding]:
    lua = _reg_get(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Policies\System", "EnableLUA")
    prompt = _reg_get(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Policies\System", "ConsentPromptBehaviorAdmin")
    if lua == 0:
        return [Finding("high", "Sistema", "Control de cuentas (UAC) desactivado", "Cualquier programa obtiene permisos de administrador sin avisar.")]
    if prompt == 0:
        return [Finding("medium", "Sistema", "UAC no pide confirmación", "Los cambios con permisos de administrador se aprueban solos.")]
    return [Finding("ok", "Sistema", "Control de cuentas (UAC) activo", "Windows pide confirmación para cambios importantes.")]


def _firewall_finding() -> list[Finding]:
    data = run_ps_json("@(Get-NetFirewallProfile -ErrorAction SilentlyContinue | Select-Object Name,Enabled)", timeout=30)
    if data is None:
        return []
    if isinstance(data, dict):
        data = [data]
    off = [d.get("Name") for d in data if not d.get("Enabled")]
    if off:
        return [Finding("high", "Red", "Firewall desactivado", "Perfiles sin protección: " + ", ".join(map(str, off)))]
    return [Finding("ok", "Red", "Firewall activo", "Todos los perfiles (dominio, privado, público) protegidos.")]


def _exclusions_finding() -> list[Finding]:
    data = run_ps_json("Get-MpPreference | Select-Object ExclusionPath,ExclusionProcess,ExclusionExtension", timeout=30)
    if not isinstance(data, dict):
        return []
    items: list[str] = []
    for k in ("ExclusionPath", "ExclusionProcess", "ExclusionExtension"):
        v = data.get(k) or []
        if isinstance(v, str):
            v = [v]
        items.extend(str(x) for x in v if x and "N/A" not in str(x))
    if not items:
        return []
    risky = [i for i in items if re.fullmatch(r"[a-z]:\\?", i.lower()) or i.lower() in (".exe", ".dll", ".ps1")
             or r"\temp" in i.lower() or r"\users" == i.lower().rstrip("\\")[-6:]]
    sev = "high" if risky else "low"
    return [Finding(sev, "Antivirus", f"{len(items)} exclusión(es) en Defender",
                    "El malware a veces se añade a las exclusiones para no ser analizado.", "; ".join(items[:6]))]


RISKY_PERMS = {"<all_urls>", "*://*/*", "http://*/*", "https://*/*", "webRequest", "webRequestBlocking", "nativeMessaging",
               "debugger", "proxy", "management", "cookies", "history", "clipboardRead"}
KNOWN_RISKY_EXT = ("hola vpn", "hola free vpn", "urban vpn", "1clickvpn")
BROAD = {"<all_urls>", "*://*/*", "http://*/*", "https://*/*", "debugger", "proxy", "nativeMessaging"}


def _ext_name(ext_dir: Path, manifest: dict) -> str:
    name = str(manifest.get("name", ext_dir.parent.name))
    if name.startswith("__MSG_"):
        key = name[6:-2].lower()
        for lang in ("es", manifest.get("default_locale", "en"), "en"):
            try:
                msgs = json.loads((ext_dir / "_locales" / lang / "messages.json").read_text(encoding="utf-8-sig"))
            except (OSError, ValueError):
                continue
            for k, v in msgs.items():
                if k.lower() == key:
                    return str(v.get("message", name))
    return name


def _extension_findings() -> list[Finding]:
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    browsers = [("Chrome", local / "Google" / "Chrome" / "User Data"), ("Edge", local / "Microsoft" / "Edge" / "User Data"),
                ("Brave", local / "BraveSoftware" / "Brave-Browser" / "User Data")]
    out: list[Finding] = []
    total = 0
    for browser, ud in browsers:
        if not ud.exists():
            continue
        for prof in [p for p in ud.iterdir() if p.is_dir() and (p.name == "Default" or p.name.startswith("Profile "))]:
            settings: dict = {}
            for fn in ("Preferences", "Secure Preferences"):
                try:
                    settings.update(json.loads((prof / fn).read_text(encoding="utf-8", errors="replace")).get("extensions", {}).get("settings", {}))
                except (OSError, ValueError, AttributeError):
                    pass
            for ext_id, s in settings.items():
                if not isinstance(s, dict) or s.get("location") in (5, 10):  # componentes internos
                    continue
                vers = sorted((prof / "Extensions" / ext_id).glob("*/manifest.json"))
                if not vers:
                    continue
                try:
                    manifest = json.loads(vers[-1].read_text(encoding="utf-8-sig"))
                except (OSError, ValueError):
                    continue
                if manifest.get("theme"):
                    continue
                total += 1
                name = _ext_name(vers[-1].parent, manifest)
                perms = {p for p in manifest.get("permissions", []) + manifest.get("host_permissions", []) if isinstance(p, str)}
                for cs in manifest.get("content_scripts", []):
                    perms.update(m for m in cs.get("matches", []) if m in RISKY_PERMS)
                risky = sorted(perms & RISKY_PERMS)
                where = f"{browser} · {prof.name}"
                if s.get("location") == 4:
                    out.append(Finding("medium", "Navegador", name, f"Extensión cargada a mano (modo desarrollador) · {where}", ext_id))
                elif s.get("from_webstore") is False and s.get("location") != 1:
                    out.append(Finding("high" if risky else "medium", "Navegador", name,
                                       f"No procede de la tienda oficial; la instaló otro programa · {where}", ext_id))
                elif BROAD & set(risky):
                    out.append(Finding("low", "Navegador", name, f"Puede leer y cambiar las webs que visitas · {where}", ext_id))
    # Una entrada por extensión aunque esté en varios perfiles
    merged: dict[tuple[str, str], Finding] = {}
    for fd in out:
        reason, where = fd.detail.rsplit(" · ", 1) if " · " in fd.detail else (fd.detail, "")
        key = (fd.title, reason, where.split(" · ")[0])
        if any(k in fd.title.lower() for k in KNOWN_RISKY_EXT):
            fd.severity = "medium"
            reason = "Extensión conocida por compartir tu conexión o datos con terceros. " + reason
        if key in merged:
            merged[key].detail += ", " + where.split(" · ")[-1]
        else:
            fd.detail = f"{reason} · {where}"
            merged[key] = fd
    out = list(merged.values())
    out.append(Finding("ok", "Navegador", f"{total} extensiones revisadas", "Desinstala desde el navegador las que no reconozcas."))
    return out


def audit(progress=None) -> list[Finding]:
    steps = [
        ("Programas de inicio", _startup_findings),
        ("Tareas programadas", _task_findings),
        ("Extensiones del navegador", _extension_findings),
        ("Archivo hosts", _hosts_finding),
        ("Proxy", _proxy_finding),
        ("Control de cuentas", _uac_finding),
        ("Firewall", _firewall_finding),
        ("Exclusiones de Defender", _exclusions_finding),
    ]
    out: list[Finding] = []
    for i, (label, fn) in enumerate(steps):
        if progress:
            progress(i / len(steps), f"Revisando {label.lower()}…")
        try:
            out.extend(fn())
        except Exception as exc:  # noqa: BLE001
            out.append(Finding("low", "Auditoría", f"No se pudo revisar: {label}", str(exc)))
    order = {"high": 0, "medium": 1, "low": 2, "ok": 3}
    out.sort(key=lambda f: order.get(f.severity, 9))
    return out
