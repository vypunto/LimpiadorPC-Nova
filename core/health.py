from __future__ import annotations

import os
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .utils import format_size, get_drives, run_hidden, user_home


@dataclass
class CrashEvent:
    time: datetime | None
    source: str
    event_id: int
    level: str
    message: str
    category: str  # unexpected_shutdown | bugcheck | whea | power | other
    probable_cause_es: str


@dataclass
class HealthCheck:
    key: str
    title: str
    status: str  # ok | warn | bad | info
    detail: str


@dataclass
class HealthReport:
    events: list[CrashEvent] = field(default_factory=list)
    checks: list[HealthCheck] = field(default_factory=list)
    summary_es: str = ""
    needs_admin: bool = False
    admin_hint: str = ""
    raw_errors: list[str] = field(default_factory=list)


CAUSE_MAP = {
    "unexpected_shutdown": (
        "Apagado/reinicio inesperado. Suele indicar corte de luz, botón de reset, "
        "sobrecalentamiento, fallo de fuente o cuelgue grave del sistema."
    ),
    "bugcheck": (
        "Pantalla azul (BSOD). Suele apuntar a driver defectuoso, memoria RAM inestable "
        "o fallo de hardware. Revisa el código BugCheck y minidumps."
    ),
    "whea": (
        "Error de hardware reportado por Windows (WHEA). Puede ser CPU, RAM, "
        "placa o sobrecalentamiento."
    ),
    "power": (
        "Evento de alimentación/Kernel-Power. Reinicio brusco: alimentación, "
        "térmico o cuelgue del kernel."
    ),
    "update": (
        "Relacionado con actualizaciones de Windows. A veces reinicia o deja el sistema inestable."
    ),
    "other": "Evento crítico/error reciente; revisar el mensaje completo.",
}


def _parse_wevt_time(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        # 2024-01-15T18:22:01.1234567Z or with offset
        clean = text.replace("Z", "+00:00")
        if "." in clean:
            main, rest = clean.split(".", 1)
            frac = ""
            tz = ""
            for i, ch in enumerate(rest):
                if ch.isdigit():
                    frac += ch
                else:
                    tz = rest[i:]
                    break
            frac = (frac + "000000")[:6]
            clean = f"{main}.{frac}{tz or '+00:00'}"
        return datetime.fromisoformat(clean).astimezone().replace(tzinfo=None)
    except ValueError:
        return None


def _classify(provider: str, event_id: int, message: str) -> tuple[str, str]:
    p = (provider or "").lower()
    m = (message or "").lower()
    if event_id == 41 or "kernel-power" in p:
        return "power", CAUSE_MAP["power"]
    if event_id == 6008 or "unexpected" in m or "inesperado" in m:
        return "unexpected_shutdown", CAUSE_MAP["unexpected_shutdown"]
    # WER 1001 / SystemErrorReporting suele acompañar BSOD o fallos graves
    if "wer-systemerrorreporting" in p or "bugcheck" in p:
        if event_id in (1001, 1019) or "bugcheck" in m or "blue" in m:
            return "bugcheck", CAUSE_MAP["bugcheck"]
    if event_id == 1001 and ("bugcheck" in m or "blue screen" in m):
        return "bugcheck", CAUSE_MAP["bugcheck"]
    if "whea" in p:
        return "whea", CAUSE_MAP["whea"]
    if "windows update" in p or "wuaueng" in p:
        return "update", CAUSE_MAP["update"]
    if event_id == 1074:
        return "other", "Apagado/reinicio iniciado por un usuario o proceso (a menudo legitimo)."
    return "other", CAUSE_MAP["other"]


def _query_events_xml(log: str, xpath: str, max_events: int = 40) -> tuple[list[ET.Element], str | None]:
    cmd = [
        "wevtutil",
        "qe",
        log,
        "/q:" + xpath,
        f"/c:{max_events}",
        "/f:RenderedXml",
    ]
    try:
        proc = run_hidden(cmd, capture_output=True, timeout=90, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [], str(exc)

    def _dec(data: bytes) -> str:
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("mbcs", errors="replace")

    proc.stdout, proc.stderr = _dec(proc.stdout or b""), _dec(proc.stderr or b"")

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        return [], err or f"wevtutil código {proc.returncode}"

    out = proc.stdout.strip()
    if not out:
        return [], None

    # Multiple Event elements concatenated
    wrapped = f"<Events>{out}</Events>"
    try:
        root = ET.fromstring(wrapped)
    except ET.ParseError:
        # try single
        try:
            el = ET.fromstring(out)
            return [el], None
        except ET.ParseError as exc:
            return [], f"XML inválido: {exc}"

    return list(root), None


def _event_message(event_el: ET.Element) -> str:
    # RenderedXml often has RenderingInfo/Message
    for tag in ("Message",):
        for node in event_el.iter():
            if node.tag.endswith(tag) and node.text:
                return node.text.strip()
    # Fallback: EventData
    parts = []
    for node in event_el.iter():
        if node.tag.endswith("Data") and node.text:
            parts.append(node.text.strip())
    return " | ".join(parts[:12]) if parts else "(sin mensaje)"


def _event_meta(event_el: ET.Element) -> tuple[datetime | None, str, int, str]:
    ns = ""
    system = None
    for node in event_el.iter():
        if node.tag.endswith("System"):
            system = node
            break
    provider = ""
    event_id = 0
    level = "Error"
    when = None
    if system is not None:
        for child in system:
            if child.tag.endswith("Provider"):
                provider = child.attrib.get("Name", "")
            elif child.tag.endswith("EventID") and child.text:
                try:
                    event_id = int(child.text.split()[0])
                except ValueError:
                    event_id = 0
            elif child.tag.endswith("Level") and child.text:
                # 1 Critical, 2 Error, 3 Warning
                lvl = child.text.strip()
                level = {"1": "Critical", "2": "Error", "3": "Warning"}.get(lvl, lvl)
            elif child.tag.endswith("TimeCreated"):
                when = _parse_wevt_time(child.attrib.get("SystemTime"))
    return when, provider, event_id, level


def collect_crash_events(days: int = 30) -> tuple[list[CrashEvent], list[str], bool]:
    """Read System log for shutdown/BSOD/WHEA related events."""
    errors: list[str] = []
    needs_admin = False
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    # Focused queries — do not invent events
    queries = [
        (
            "System",
            f"*[System[(EventID=41 or EventID=6008 or EventID=1074 or EventID=1001) and TimeCreated[@SystemTime>='{since}']]]",
        ),
        (
            "System",
            f"*[System[Provider[@Name='Microsoft-Windows-WHEA-Logger'] and (Level=1 or Level=2) and TimeCreated[@SystemTime>='{since}']]]",
        ),
        (
            "System",
            f"*[System[Provider[@Name='Microsoft-Windows-WER-SystemErrorReporting'] and TimeCreated[@SystemTime>='{since}']]]",
        ),
    ]

    events: list[CrashEvent] = []
    seen: set[tuple] = set()

    for log, xpath in queries:
        els, err = _query_events_xml(log, xpath, max_events=50)
        if err:
            errors.append(f"{log}: {err}")
            low = err.lower()
            if "access" in low or "denied" in low or "acceso" in low:
                needs_admin = True
            continue
        for el in els:
            when, provider, eid, level = _event_meta(el)
            msg = _event_message(el)
            key = (when.isoformat() if when else "", provider, eid, msg[:80])
            if key in seen:
                continue
            seen.add(key)
            cat, cause = _classify(provider, eid, msg)
            events.append(
                CrashEvent(
                    time=when,
                    source=provider or log,
                    event_id=eid,
                    level=level,
                    message=msg[:500],
                    category=cat,
                    probable_cause_es=cause,
                )
            )

    events.sort(key=lambda e: e.time or datetime.min, reverse=True)
    return events, errors, needs_admin


def _minidump_check() -> HealthCheck:
    dump_dir = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Minidump"
    if not dump_dir.exists():
        return HealthCheck(
            "minidump",
            "Minidumps (BSOD)",
            "ok",
            "No hay carpeta Minidump o está vacía (buena señal si no hubo pantallas azules recientes).",
        )
    dumps = sorted(dump_dir.glob("*.dmp"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not dumps:
        return HealthCheck("minidump", "Minidumps (BSOD)", "ok", "Carpeta Minidump sin archivos .dmp.")
    latest = dumps[0]
    mtime = datetime.fromtimestamp(latest.stat().st_mtime)
    return HealthCheck(
        "minidump",
        "Minidumps (BSOD)",
        "bad" if len(dumps) >= 3 else "warn",
        f"{len(dumps)} volcado(s). Más reciente: {latest.name} ({mtime:%Y-%m-%d %H:%M}).",
    )


def _disk_checks() -> list[HealthCheck]:
    checks = []
    for letter, free, total in get_drives():
        pct = (free / total * 100) if total else 0
        status = "ok" if pct >= 15 else ("warn" if pct >= 8 else "bad")
        checks.append(
            HealthCheck(
                f"disk_{letter}",
                f"Espacio en {letter}",
                status,
                f"{format_size(free)} libres de {format_size(total)} ({pct:.0f}%).",
            )
        )
    return checks


def _memory_check() -> HealthCheck:
    try:
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
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

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        load = stat.dwMemoryLoad
        status = "ok" if load < 80 else ("warn" if load < 90 else "bad")
        return HealthCheck(
            "memory",
            "Memoria RAM",
            status,
            f"Uso aproximado {load}%. Libre {format_size(stat.ullAvailPhys)} de {format_size(stat.ullTotalPhys)}.",
        )
    except Exception as exc:  # noqa: BLE001
        return HealthCheck("memory", "Memoria RAM", "info", f"No se pudo leer: {exc}")


def _temp_check() -> HealthCheck:
    """Try thermal zone via PowerShell/WMI — may be unavailable."""
    ps = (
        "Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature "
        "-ErrorAction SilentlyContinue | Select-Object -First 3 CurrentTemperature | "
        "ForEach-Object { [math]::Round(($_.CurrentTemperature/10)-273.15,1) }"
    )
    try:
        proc = run_hidden(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
        lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
        temps = []
        for ln in lines:
            try:
                temps.append(float(ln.replace(",", ".")))
            except ValueError:
                continue
        if not temps:
            return HealthCheck(
                "temp",
                "Temperatura",
                "info",
                "No disponible por WMI en este PC (normal en muchos portátiles). "
                "Si se apaga a diario, revisa polvo/ventiladores y usa HWMonitor o similar.",
            )
        mx = max(temps)
        status = "ok" if mx < 80 else ("warn" if mx < 90 else "bad")
        return HealthCheck(
            "temp",
            "Temperatura",
            status,
            f"Zonas térmicas: {', '.join(f'{t:.0f}°C' for t in temps)} (máx {mx:.0f}°C).",
        )
    except (OSError, subprocess.TimeoutExpired):
        return HealthCheck("temp", "Temperatura", "info", "No se pudo consultar sensores térmicos.")


def _smart_check() -> HealthCheck:
    ps = (
        "Get-PhysicalDisk -ErrorAction SilentlyContinue | "
        "Select-Object FriendlyName, HealthStatus, OperationalStatus, MediaType | "
        "Format-Table -AutoSize | Out-String -Width 200"
    )
    try:
        proc = run_hidden(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        text = (proc.stdout or "").strip()
        if not text or "HealthStatus" not in text and "FriendlyName" not in text:
            return HealthCheck("smart", "Discos (salud)", "info", "No se pudo leer Get-PhysicalDisk.")
        low = text.lower()
        status = "ok"
        if "warning" in low or "unhealthy" in low:
            status = "bad"
        elif "unknown" in low:
            status = "warn"
        return HealthCheck("smart", "Discos (salud)", status, text[:500].strip())
    except (OSError, subprocess.TimeoutExpired) as exc:
        return HealthCheck("smart", "Discos (salud)", "info", f"No accesible: {exc}")


def _update_reboot_pending() -> HealthCheck:
    paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired",
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending",
    ]
    import winreg

    pending = False
    for p in paths:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, p)
            winreg.CloseKey(key)
            pending = True
            break
        except OSError:
            continue
    if pending:
        return HealthCheck(
            "wu_reboot",
            "Windows Update",
            "warn",
            "Hay un reinicio pendiente por actualizaciones. Puede causar inestabilidad hasta reiniciar bien.",
        )
    return HealthCheck("wu_reboot", "Windows Update", "ok", "No hay reinicio pendiente detectado.")


def _startup_heavy_hint() -> HealthCheck:
    # Count Run keys as a light proxy
    import winreg

    count = 0
    for root, path in (
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
    ):
        try:
            key = winreg.OpenKey(root, path)
            i = 0
            while True:
                try:
                    winreg.EnumValue(key, i)
                    count += 1
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except OSError:
            pass
    status = "ok" if count <= 8 else ("warn" if count <= 15 else "bad")
    return HealthCheck(
        "startup",
        "Programas al inicio",
        status,
        f"{count} entradas en claves Run. Revisa Administrador de tareas > Inicio si el arranque es lento.",
    )


def build_health_report(days: int = 30) -> HealthReport:
    events, errors, needs_admin = collect_crash_events(days=days)
    checks: list[HealthCheck] = []
    checks.extend(_disk_checks())
    checks.append(_memory_check())
    checks.append(_temp_check())
    checks.append(_smart_check())
    checks.append(_minidump_check())
    checks.append(_update_reboot_pending())
    checks.append(_startup_heavy_hint())

    # Summarize crashes without inventing
    unexpected = [e for e in events if e.category in ("power", "unexpected_shutdown", "bugcheck", "whea")]
    if not events and errors:
        summary = (
            "No se pudieron leer los registros de eventos con los datos actuales. "
            + ("Prueba a ejecutar Limpiador PC como administrador. " if needs_admin else "")
            + "Detalles: "
            + "; ".join(errors[:2])
        )
    elif not unexpected:
        summary = (
            f"En los últimos {days} días no aparecen (o no se leyeron) eventos claros de "
            "Kernel-Power 41 / 6008 / BugCheck / WHEA. Si el PC se apaga igual, ejecuta como admin "
            "o revisa el Visor de eventos manualmente (Sistema)."
        )
    else:
        latest = unexpected[0]
        when = latest.time.strftime("%Y-%m-%d %H:%M") if latest.time else "fecha desconocida"
        counts: dict[str, int] = {}
        for e in unexpected:
            counts[e.category] = counts.get(e.category, 0) + 1
        parts = ", ".join(f"{k}×{v}" for k, v in counts.items())
        summary = (
            f"Se encontraron {len(unexpected)} evento(s) relacionados con caídas ({parts}). "
            f"El más reciente: {when} — {latest.source} ID {latest.event_id}. "
            f"{latest.probable_cause_es}"
        )

    admin_hint = (
        "Clic derecho en iniciar.bat → Ejecutar como administrador, "
        "o abre PowerShell como admin y ejecuta: py -3 limpiador.py"
        if needs_admin
        else ""
    )

    return HealthReport(
        events=events,
        checks=checks,
        summary_es=summary,
        needs_admin=needs_admin,
        admin_hint=admin_hint,
        raw_errors=errors,
    )


def maintenance_suggestions() -> list[str]:
    return [
        "Limpia temporales y papelera desde la pestaña Limpieza (seguro).",
        "Si hay poco espacio (<10%), libera GB: archivos pesados y programas sin uso.",
        "Como administrador, puedes reparar sistema: DISM /Online /Cleanup-Image /RestoreHealth y luego sfc /scannow.",
        "Comprobar disco: chkdsk C: /scan (admin). Si pide reinicio, hazlo cuando puedas.",
        "Abre Administrador de tareas → Inicio y deshabilita lo que no necesites al arrancar.",
        "Si hay minidumps o BugCheck, anota el código y actualiza drivers de chipset/GPU desde el fabricante.",
        "Si WHEA o apagados al cargar CPU/GPU: limpia ventiladores y controla temperaturas.",
    ]
