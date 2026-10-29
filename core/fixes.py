"""Reparaciones y optimizaciones de Windows con comandos oficiales del sistema.

Cada reparación es una lista de pasos ("cmd", argv) o ("ps", script) que se
ejecutan en orden y cuya salida se transmite en directo a la interfaz.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field

from .utils import NO_WINDOW, decode_console


@dataclass
class Fix:
    id: str
    group: str
    title: str
    description: str
    steps: list[tuple[str, object]] = field(default_factory=list)
    admin: bool = False
    reboot: bool = False
    minutes: str = "<1 min"
    icon: str = "wrench"


SYS = os.environ.get("SystemRoot", r"C:\Windows")

_WU_RESET = r"""
$svcs='wuauserv','bits','cryptsvc','msiserver'
foreach($s in $svcs){ Write-Output "Deteniendo $s..."; Stop-Service $s -Force -ErrorAction SilentlyContinue }
$sd="$env:SystemRoot\SoftwareDistribution"; $cr="$env:SystemRoot\System32\catroot2"
foreach($p in @($sd,$cr)){
  if(Test-Path "$p.bak"){ Remove-Item "$p.bak" -Recurse -Force -ErrorAction SilentlyContinue }
  if(Test-Path $p){ Rename-Item $p "$p.bak" -ErrorAction SilentlyContinue; Write-Output "Renombrado $p -> $p.bak" }
}
foreach($s in $svcs){ Write-Output "Iniciando $s..."; Start-Service $s -ErrorAction SilentlyContinue }
Write-Output "Componentes de Windows Update restablecidos."
"""

_ICON_CACHE = r"""
Write-Output "Cerrando el Explorador..."
Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 800
$e="$env:LOCALAPPDATA\Microsoft\Windows\Explorer"
$n=0
Get-ChildItem $e -Filter 'iconcache_*.db' -ErrorAction SilentlyContinue | ForEach-Object { Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue; $n++ }
Get-ChildItem $e -Filter 'thumbcache_*.db' -ErrorAction SilentlyContinue | ForEach-Object { Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue; $n++ }
Remove-Item "$env:LOCALAPPDATA\IconCache.db" -Force -ErrorAction SilentlyContinue
Write-Output "$n archivos de caché eliminados."
Start-Process explorer.exe
Write-Output "Explorador reiniciado."
"""

FIXES: list[Fix] = [
    # --- Seguridad previa ---
    Fix(
        "restore_point", "Antes de nada", "Crear punto de restauración",
        "Guarda el estado actual de Windows para poder volver atrás si algo falla.",
        [("ps", "Enable-ComputerRestore -Drive \"$env:SystemDrive\\\" -ErrorAction SilentlyContinue;"
                "Checkpoint-Computer -Description 'Limpiador PC Nova' -RestorePointType MODIFY_SETTINGS;"
                "if($?){Write-Output 'Punto de restauración creado.'}")],
        admin=True, minutes="1-2 min", icon="shield",
    ),
    # --- Reparar sistema ---
    Fix(
        "sfc", "Reparar Windows", "Reparar archivos del sistema (SFC)",
        "Comprueba y restaura archivos protegidos de Windows dañados o modificados.",
        [("cmd", ["sfc", "/scannow"])], admin=True, minutes="5-15 min", icon="cpu",
    ),
    Fix(
        "dism", "Reparar Windows", "Restaurar imagen de Windows (DISM)",
        "Repara el almacén de componentes desde Windows Update. Ejecútalo si SFC no puede reparar.",
        [("cmd", ["DISM", "/Online", "/Cleanup-Image", "/RestoreHealth"])],
        admin=True, minutes="10-30 min", icon="layers",
    ),
    Fix(
        "chkdsk", "Reparar Windows", "Analizar el disco C: (CHKDSK)",
        "Busca errores del sistema de archivos sin desmontar el disco.",
        [("cmd", ["chkdsk", os.environ.get("SystemDrive", "C:"), "/scan"])],
        admin=True, minutes="2-10 min", icon="disk",
    ),
    Fix(
        "wu_reset", "Reparar Windows", "Restablecer Windows Update",
        "Para servicios, renombra SoftwareDistribution y catroot2 y vuelve a arrancar. Soluciona actualizaciones atascadas.",
        [("ps", _WU_RESET)], admin=True, minutes="1 min", icon="refresh",
    ),
    Fix(
        "reboot", "Reparar Windows", "Reiniciar el equipo",
        "Reinicia en 60 segundos para terminar actualizaciones e instalaciones de drivers. Guarda tu trabajo antes.",
        [("cmd", ["shutdown", "/r", "/t", "60", "/c", "Limpiador PC Nova: reinicio en 60 s. Guarda tu trabajo."])],
        reboot=True, icon="refresh",
    ),
    Fix(
        "reboot_cancel", "Reparar Windows", "Cancelar reinicio programado",
        "Anula un reinicio que se haya programado.",
        [("cmd", ["shutdown", "/a"])], icon="x",
    ),
    Fix(
        "wu_check", "Reparar Windows", "Buscar actualizaciones y drivers",
        "Abre Windows Update y lanza la búsqueda. Los drivers están en Opciones avanzadas > Actualizaciones opcionales.",
        [("ps", "Start-Process 'ms-settings:windowsupdate'; UsoClient StartInteractiveScan 2>$null; Write-Output 'Windows Update abierto.'")],
        icon="download",
    ),
    Fix(
        "store_reset", "Reparar Windows", "Restablecer Microsoft Store",
        "Vacía la caché de la Store cuando no descarga o no abre.",
        [("cmd", ["wsreset.exe", "-i"])], minutes="<1 min", icon="bag",
    ),
    Fix(
        "memtest", "Reparar Windows", "Diagnóstico de memoria RAM",
        "Programa la herramienta oficial de Windows para el próximo reinicio.",
        [("cmd", [os.path.join(SYS, "System32", "mdsched.exe")])], admin=True, reboot=True, icon="chip",
    ),
    # --- Explorador y escritorio ---
    Fix(
        "explorer", "Escritorio", "Reiniciar el Explorador",
        "Arregla barra de tareas, menú Inicio o escritorio congelados.",
        [("ps", "Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue; Start-Sleep -Milliseconds 800;"
                "Start-Process explorer.exe; Write-Output 'Explorador reiniciado.'")],
        icon="window",
    ),
    Fix(
        "icons", "Escritorio", "Reconstruir caché de iconos",
        "Soluciona iconos en blanco, incorrectos o miniaturas que no se actualizan.",
        [("ps", _ICON_CACHE)], icon="grid",
    ),
    Fix(
        "audio", "Escritorio", "Reiniciar servicios de audio",
        "Cuando no hay sonido o el dispositivo no responde.",
        [("ps", "Restart-Service AudioEndpointBuilder -Force; Restart-Service Audiosrv -Force; Write-Output 'Audio reiniciado.'")],
        admin=True, icon="sound",
    ),
    Fix(
        "spooler", "Escritorio", "Desatascar la impresora",
        "Vacía la cola de impresión y reinicia el servicio de cola.",
        [("ps", "Stop-Service Spooler -Force; Remove-Item \"$env:SystemRoot\\System32\\spool\\PRINTERS\\*\" -Force -ErrorAction SilentlyContinue;"
                "Start-Service Spooler; Write-Output 'Cola de impresión vaciada.'")],
        admin=True, icon="printer",
    ),
    # --- Red ---
    Fix(
        "dns", "Red e Internet", "Vaciar caché DNS",
        "Arregla webs que no cargan o apuntan a una dirección antigua.",
        [("cmd", ["ipconfig", "/flushdns"])], admin=True, icon="globe",
    ),
    Fix(
        "ip_renew", "Red e Internet", "Renovar dirección IP",
        "Libera y pide una nueva IP al router. La conexión se corta unos segundos.",
        [("cmd", ["ipconfig", "/release"]), ("cmd", ["ipconfig", "/renew"])], admin=True, icon="wifi",
    ),
    Fix(
        "net_reset", "Red e Internet", "Restablecer pila de red",
        "Reinicia Winsock y TCP/IP. Último recurso si no hay Internet.",
        [("cmd", ["netsh", "winsock", "reset"]), ("cmd", ["netsh", "int", "ip", "reset"])],
        admin=True, reboot=True, icon="network",
    ),
    Fix(
        "time_sync", "Red e Internet", "Sincronizar la hora",
        "La hora incorrecta rompe HTTPS, Windows Update y los inicios de sesión.",
        [("ps", "Start-Service w32time -ErrorAction SilentlyContinue; w32tm /resync /force")],
        admin=True, icon="clock",
    ),
    # --- Rendimiento ---
    Fix(
        "component_cleanup", "Rendimiento", "Compactar componentes de Windows",
        "Elimina versiones antiguas de actualizaciones del almacén WinSxS. Libera varios GB.",
        [("cmd", ["DISM", "/Online", "/Cleanup-Image", "/StartComponentCleanup"])],
        admin=True, minutes="5-20 min", icon="compress",
    ),
    Fix(
        "compactos", "Rendimiento", "Comprimir Windows (CompactOS)",
        "Comprime los archivos del sistema de forma transparente. Suele liberar 2-6 GB sin borrar nada; reversible.",
        [("cmd", ["compact", "/compactos:query"]), ("cmd", ["compact", "/compactos:always"])],
        admin=True, minutes="10-30 min", icon="compress",
    ),
    Fix(
        "trim", "Rendimiento", "Optimizar unidades (TRIM)",
        "Ejecuta TRIM en SSD o desfragmenta HDD según el tipo de disco.",
        [("ps", "Get-Volume | Where-Object { $_.DriveLetter -and $_.DriveType -eq 'Fixed' } | ForEach-Object {"
                " Write-Output \"Optimizando $($_.DriveLetter):\"; Optimize-Volume -DriveLetter $_.DriveLetter -Verbose 4>&1 }")],
        admin=True, minutes="1-10 min", icon="bolt",
    ),
    Fix(
        "power_high", "Rendimiento", "Plan de energía: alto rendimiento",
        "Máxima velocidad de CPU. Ideal enchufado; consume más batería.",
        [("cmd", ["powercfg", "/setactive", "SCHEME_MIN"]), ("cmd", ["powercfg", "/getactivescheme"])], icon="rocket",
    ),
    Fix(
        "power_balanced", "Rendimiento", "Plan de energía: equilibrado",
        "El recomendado por Windows para el día a día.",
        [("cmd", ["powercfg", "/setactive", "SCHEME_BALANCED"]), ("cmd", ["powercfg", "/getactivescheme"])], icon="leaf",
    ),
    Fix(
        "hibernate_off", "Rendimiento", "Desactivar hibernación",
        "Elimina hiberfil.sys (varios GB). Pierdes la hibernación y el inicio rápido.",
        [("cmd", ["powercfg", "/hibernate", "off"])], admin=True, icon="moon",
    ),
]

FIX_BY_ID = {f.id: f for f in FIXES}

REVERT = {
    "restore_point": "No cambia nada del sistema; solo guarda una copia del estado actual.",
    "sfc": "Solo restaura archivos originales de Windows. No hace falta revertir.",
    "dism": "Solo repara la imagen de Windows con archivos oficiales. No hace falta revertir.",
    "chkdsk": "Solo lee el disco y avisa de errores (/scan). No modifica nada.",
    "wu_reset": "Las carpetas antiguas quedan como SoftwareDistribution.bak y catroot2.bak. Punto de restauración previo.",
    "wu_check": "Solo abre Windows Update.",
    "reboot": "Cancélalo antes de 60 s con «Cancelar reinicio programado».",
    "reboot_cancel": "Solo anula el reinicio pendiente.",
    "store_reset": "Solo vacía la caché de la Store.",
    "memtest": "Cancela la prueba no reiniciando; no toca datos.",
    "explorer": "El Explorador vuelve a abrirse solo.",
    "icons": "Windows regenera las cachés de iconos y miniaturas.",
    "audio": "Solo reinicia servicios que ya existían.",
    "spooler": "Los trabajos de impresión pendientes se pierden; vuelve a imprimirlos.",
    "dns": "La caché DNS se rellena sola al navegar.",
    "ip_renew": "El router asigna una IP nueva automáticamente.",
    "net_reset": "Revertir: restaurar el punto creado antes. Puede que tengas que reconfigurar VPN o IP fija.",
    "time_sync": "Solo ajusta la hora con el servidor oficial.",
    "component_cleanup": "No reversible: ya no podrás desinstalar actualizaciones antiguas (las recientes sí).",
    "compactos": "Revertir: comando 'compact /compactos:never' (como administrador).",
    "trim": "Mantenimiento normal que Windows hace solo cada semana.",
    "power_high": "Revertir: 'Plan de energía: equilibrado'.",
    "power_balanced": "Es el plan por defecto de Windows.",
    "hibernate_off": "Revertir: comando 'powercfg /hibernate on' (como administrador).",
}


def describe_steps(fix: Fix) -> list[str]:
    out = []
    for kind, payload in fix.steps:
        if kind == "cmd":
            out.append(" ".join(payload))  # type: ignore[arg-type]
        else:
            out.append("PowerShell: " + " ".join(str(payload).split())[:220])
    return out


def run_fix(fix: Fix, log, stop_event=None) -> int:
    """Ejecuta los pasos y envía cada línea a log(text, replace_last). Devuelve el código final."""
    code = 0
    for kind, payload in fix.steps:
        if stop_event is not None and stop_event.is_set():
            log("Cancelado.", False)
            return 1
        if kind == "ps":
            argv = [
                "powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command",
                "[Console]::OutputEncoding=[Text.Encoding]::UTF8;$ProgressPreference='SilentlyContinue';" + str(payload),
            ]
            encoding = "utf-8"
        else:
            argv = list(payload)  # type: ignore[arg-type]
            encoding = None
        log("› " + (" ".join(argv) if kind == "cmd" else "PowerShell"), False)
        try:
            proc = subprocess.Popen(
                argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                creationflags=NO_WINDOW,
            )
        except OSError as exc:
            log(f"No se pudo ejecutar: {exc}", False)
            return 1
        buf = b""
        assert proc.stdout is not None
        while True:
            chunk = proc.stdout.read1(4096) if hasattr(proc.stdout, "read1") else proc.stdout.read(4096)
            if not chunk:
                break
            buf += chunk
            # Separar por \n y \r (las barras de progreso de sfc/DISM usan \r)
            while True:
                idx = min([i for i in (buf.find(b"\n"), buf.find(b"\r")) if i >= 0], default=-1)
                if idx < 0:
                    break
                sep = buf[idx:idx + 1]
                raw, buf = buf[:idx], buf[idx + 1:]
                text = raw.decode(encoding, errors="replace") if encoding else decode_console(raw)
                text = text.replace("\x00", "").rstrip()
                if text:
                    log(text, sep == b"\r")
            if stop_event is not None and stop_event.is_set():
                proc.kill()
                log("Cancelado.", False)
                return 1
        if buf.strip():
            text = buf.decode(encoding, errors="replace") if encoding else decode_console(buf)
            log(text.replace("\x00", "").strip(), False)
        code = proc.wait()
        if code != 0:
            log(f"Terminó con código {code}.", False)
    return code
