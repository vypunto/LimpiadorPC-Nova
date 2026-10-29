"""Convierte el informe de salud en problemas concretos con un plan de solución paso a paso.

Cada paso puede llevar una acción que la app ejecuta de forma segura:
  {"type": "fix", "id": ...}      reparación del catálogo (pide confirmación en la interfaz)
  {"type": "url", "url": ...}     abre una web oficial en el navegador
  {"type": "settings", "uri": ...} abre una página de Configuración de Windows (ms-settings:)
  {"type": "tool", "id": ...}     abre una herramienta de Windows (Administrador de dispositivos…)
  {"type": "page", "id": ...}     navega a una sección de la app
"""
from __future__ import annotations

import os
import re
from collections import Counter
from datetime import datetime

from .utils import format_size, google_drive_letters, run_ps_json

# Drivers frecuentes en pantallazos → componente
DRIVERS = {
    "amdkmdag.sys": ("gpu_amd", "driver de gráficos AMD Radeon"),
    "atikmdag.sys": ("gpu_amd", "driver de gráficos AMD Radeon"),
    "atikmpag.sys": ("gpu_amd", "driver de gráficos AMD Radeon"),
    "nvlddmkm.sys": ("gpu_nvidia", "driver de gráficos NVIDIA"),
    "igdkmd64.sys": ("gpu_intel", "driver de gráficos Intel"),
    "igdkmdn64.sys": ("gpu_intel", "driver de gráficos Intel"),
    "dxgkrnl.sys": ("gpu", "subsistema de gráficos de Windows (DirectX)"),
    "dxgmms2.sys": ("gpu", "subsistema de gráficos de Windows (DirectX)"),
    "netwtw10.sys": ("wifi", "driver Wi-Fi Intel"), "netwtw14.sys": ("wifi", "driver Wi-Fi Intel"),
    "netwtw08.sys": ("wifi", "driver Wi-Fi Intel"), "rtwlane.sys": ("wifi", "driver Wi-Fi Realtek"),
    "rtwlane6.sys": ("wifi", "driver Wi-Fi Realtek"), "athw10x.sys": ("wifi", "driver Wi-Fi Qualcomm"),
    "rt640x64.sys": ("lan", "driver de red Realtek"), "e1d68x64.sys": ("lan", "driver de red Intel"),
    "storport.sys": ("storage", "controlador de almacenamiento"), "stornvme.sys": ("storage", "controlador del SSD NVMe"),
    "iastora.sys": ("storage", "Intel Rapid Storage"), "amdpsp.sys": ("chipset", "chipset AMD (PSP)"),
    "amdppm.sys": ("chipset", "gestión de energía del procesador AMD"),
    "ntoskrnl.exe": ("kernel", "núcleo de Windows (causa genérica)"),
}
CODES = {
    "0x000000d1": ("DRIVER_IRQL_NOT_LESS_OR_EQUAL", "Un driver accedió a memoria que no debía. Casi siempre es un driver defectuoso o incompatible."),
    "0x0000000a": ("IRQL_NOT_LESS_OR_EQUAL", "Un driver o la memoria RAM accedieron a una dirección no válida."),
    "0x00000116": ("VIDEO_TDR_FAILURE", "La tarjeta gráfica dejó de responder y Windows no pudo recuperarla."),
    "0x00000117": ("VIDEO_TDR_TIMEOUT", "La tarjeta gráfica tardó demasiado en responder."),
    "0x00000050": ("PAGE_FAULT_IN_NONPAGED_AREA", "Se leyó memoria inexistente: driver, RAM o disco."),
    "0x0000001a": ("MEMORY_MANAGEMENT", "Fallo grave en la gestión de memoria: suele ser RAM defectuosa."),
    "0x0000003b": ("SYSTEM_SERVICE_EXCEPTION", "Excepción en un servicio del sistema, a menudo por un driver."),
    "0x0000007e": ("SYSTEM_THREAD_EXCEPTION_NOT_HANDLED", "Un driver lanzó un error no controlado."),
    "0x00000124": ("WHEA_UNCORRECTABLE_ERROR", "Error de hardware: CPU, RAM, temperatura o voltaje."),
    "0x0000009f": ("DRIVER_POWER_STATE_FAILURE", "Un driver falló al entrar o salir de suspensión."),
    "0x00000133": ("DPC_WATCHDOG_VIOLATION", "Un driver o el SSD dejó el sistema bloqueado demasiado tiempo."),
    "0x000000ef": ("CRITICAL_PROCESS_DIED", "Murió un proceso esencial de Windows: archivos del sistema o disco."),
    "0x0000007a": ("KERNEL_DATA_INPAGE_ERROR", "No se pudo leer datos del disco: revisa el SSD/HDD."),
    "0x00000139": ("KERNEL_SECURITY_CHECK_FAILURE", "Corrupción detectada: driver o archivos del sistema."),
}
SUPPORT = {
    "micro-star": ("MSI", "https://www.msi.com/support"), "msi": ("MSI", "https://www.msi.com/support"),
    "lenovo": ("Lenovo", "https://pcsupport.lenovo.com"), "hp": ("HP", "https://support.hp.com/drivers"),
    "hewlett": ("HP", "https://support.hp.com/drivers"), "dell": ("Dell", "https://www.dell.com/support"),
    "asus": ("ASUS", "https://www.asus.com/support/download-center/"), "acer": ("Acer", "https://www.acer.com/support"),
    "gigabyte": ("Gigabyte", "https://www.gigabyte.com/Support"), "samsung": ("Samsung", "https://www.samsung.com/support/"),
    "microsoft": ("Microsoft Surface", "https://support.microsoft.com/surface"), "huawei": ("Huawei", "https://consumer.huawei.com/support/"),
}
URLS = {
    "amd": "https://www.amd.com/es/support/download/drivers.html",
    "amd_cleanup": "https://www.amd.com/es/resources/support-articles/faqs/GPU-601.html",
    "nvidia": "https://www.nvidia.com/es-es/drivers/",
    "intel": "https://www.intel.es/content/www/es/es/support/detect.html",
}
CRASH = ("power", "unexpected_shutdown", "bugcheck", "whea")


def video_drivers() -> list[dict]:
    data = run_ps_json(
        "@(Get-CimInstance Win32_VideoController | ForEach-Object { [pscustomobject]@{ name=$_.Name; version=$_.DriverVersion;"
        " date=$(if($_.DriverDate){$_.DriverDate.ToString('yyyy-MM-dd')}else{''}) } })", timeout=30)
    if data is None:
        return []
    return data if isinstance(data, list) else [data]


def _maker() -> tuple[str, str, str]:
    from .sysinfo import static_info

    info = static_info() or {}
    maker, model = str(info.get("maker", "")), str(info.get("machine", ""))
    low = maker.lower()
    for k, (name, url) in SUPPORT.items():
        if k in low:
            return name, model, url
    return maker or "tu fabricante", model, ""


def _steps(*items) -> list[dict]:
    return [{"text": t, "action": a} if a else {"text": t} for t, a in items]


def crash_problem(report) -> dict | None:
    crashes = [e for e in report.events if e.category in CRASH]
    if not crashes:
        return None
    codes, drivers = Counter(), Counter()
    for e in report.events:
        m = re.search(r"0x[0-9a-fA-F]{8}", e.message)
        if m and e.category == "bugcheck":
            codes[m.group(0).lower()] += 1
        d = re.search(r"([\w\-]+\.(sys|exe))", e.message, re.I)
        if d and e.category == "bugcheck" and d.group(1).lower() in DRIVERS:
            drivers[d.group(1).lower()] += 1
    bsods = codes.total()
    others = len({(e.time.date() if e.time else None) for e in crashes})
    maker, model, support_url = _maker()
    top_driver = drivers.most_common(1)[0][0] if drivers else None
    top_code = codes.most_common(1)[0][0] if codes else None
    comp, comp_name = DRIVERS.get(top_driver, ("unknown", ""))
    code_name, code_why = CODES.get(top_code, ("", ""))
    vids = video_drivers()

    evidence = []
    if bsods:
        evidence.append(f"{bsods} pantallas azules en 30 días" + (f", la mayoría con el código {top_code} ({code_name})" if top_code else ""))
    if top_driver:
        evidence.append(f"Windows señala {drivers[top_driver]} veces el archivo {top_driver}: {comp_name}")
    evidence.append(f"Hubo caídas en {others} días distintos")
    old_note = ""
    for v in vids:
        evidence.append(f"Driver instalado: {v.get('name')} · versión {v.get('version')} · fecha {v.get('date') or '?'}")
        vend = {"gpu_amd": ("amd", "radeon"), "gpu_nvidia": ("nvidia",), "gpu_intel": ("intel",)}.get(comp, ())
        if v.get("date") and any(k in str(v.get("name", "")).lower() for k in vend):
            years = (datetime.now() - datetime.strptime(v["date"], "%Y-%m-%d")).days / 365
            if years >= 1:
                old_note = f" Tu driver es de {v['date'][:7].replace('-', '/')} (hace {years:.0f} año{'s' if years >= 1.5 else ''}): está desactualizado, lo que refuerza el diagnóstico."

    sup = (f"Descarga el driver oficial de {maker} para tu modelo «{model}» (página de soporte → Drivers).",
           {"type": "url", "url": support_url} if support_url else None)
    if comp == "gpu_amd":
        title = "Las pantallas azules las provoca el driver de gráficos AMD"
        why = (f"{code_why} Todas apuntan a {top_driver}, el driver de la gráfica AMD Radeon integrada. "
               "Al ser siempre el mismo driver, lo más probable es un driver dañado o una versión que no se lleva bien "
               "con la gráfica NVIDIA del portátil. Se soluciona reinstalándolo limpio." + old_note)
        steps = _steps(
            ("Crea un punto de restauración por si quieres volver atrás.", {"type": "fix", "id": "restore_point"}),
            ("Reinicia para terminar cualquier actualización pendiente de Windows.", {"type": "fix", "id": "reboot"}),
            sup,
            ("Si en la web del fabricante el driver es muy antiguo, descarga el más reciente de AMD (AMD Software: Adrenalin, gráficos Radeon integrados).", {"type": "url", "url": URLS["amd"]}),
            ("Descarga «AMD Cleanup Utility», ejecútalo para quitar el driver actual y reinicia.", {"type": "url", "url": URLS["amd_cleanup"]}),
            ("Instala el driver que descargaste y reinicia otra vez.", None),
            ("Actualiza también el driver NVIDIA y la BIOS desde la web del fabricante (versiones que no casan causan este error).", {"type": "url", "url": support_url or URLS["nvidia"]}),
            ("Revisa en Windows Update → Actualizaciones opcionales si hay drivers pendientes.", {"type": "settings", "uri": "ms-settings:windowsupdate-optionalupdates"}),
            ("Si vuelve a pasar tras reinstalar: pasa el diagnóstico de memoria RAM.", {"type": "fix", "id": "memtest"}),
        )
    elif comp in ("gpu_nvidia", "gpu_intel", "gpu"):
        vendor = {"gpu_nvidia": "nvidia", "gpu_intel": "intel"}.get(comp, "nvidia")
        title = f"Las pantallas azules las provoca el {comp_name}"
        why = f"{code_why} Windows señala {top_driver}. Reinstalar limpio el driver de gráficos suele solucionarlo." + old_note
        steps = _steps(
            ("Crea un punto de restauración.", {"type": "fix", "id": "restore_point"}),
            sup,
            ("O descarga el driver más reciente del fabricante de la gráfica.", {"type": "url", "url": URLS[vendor]}),
            ("En el Administrador de dispositivos → Adaptadores de pantalla, desinstala el driver actual y reinicia.", {"type": "tool", "id": "devmgmt"}),
            ("Instala el driver descargado y reinicia.", None),
            ("Si persiste: diagnóstico de memoria RAM.", {"type": "fix", "id": "memtest"}),
        )
    elif comp in ("wifi", "lan"):
        title = f"Las pantallas azules las provoca el {comp_name}"
        why = f"{code_why} Windows señala {top_driver}."
        steps = _steps(sup, ("Actualiza o reinstala el adaptador de red desde el Administrador de dispositivos.", {"type": "tool", "id": "devmgmt"}),
                       ("Revisa actualizaciones opcionales de drivers.", {"type": "settings", "uri": "ms-settings:windowsupdate-optionalupdates"}))
    elif top_code in ("0x0000001a", "0x00000124") or comp == "kernel":
        title = "Las pantallas azules apuntan a memoria RAM o hardware"
        why = (code_why or "El error no señala un driver concreto.") + " Conviene descartar la RAM, la temperatura y los archivos del sistema."
        steps = _steps(("Diagnóstico de memoria RAM (reinicia el equipo).", {"type": "fix", "id": "memtest"}),
                       ("Repara archivos del sistema con SFC.", {"type": "fix", "id": "sfc"}),
                       ("Si SFC no puede reparar, ejecuta DISM y luego SFC otra vez.", {"type": "fix", "id": "dism"}),
                       ("Limpia ventiladores y comprueba temperaturas (HWMonitor).", None),
                       sup)
    else:
        title = "El equipo se apaga o reinicia de golpe"
        why = ("Hay apagados inesperados sin un driver claro. Las causas típicas son el sobrecalentamiento, "
               "la batería o el cargador, o un cuelgue grave.")
        steps = _steps(("Comprueba temperaturas y limpia ventiladores.", None),
                       ("Actualiza drivers y BIOS desde la web del fabricante.", {"type": "url", "url": support_url} if support_url else None),
                       ("Repara archivos del sistema (SFC).", {"type": "fix", "id": "sfc"}),
                       ("Diagnóstico de memoria RAM.", {"type": "fix", "id": "memtest"}))
    return {"id": "crashes", "severity": "bad", "title": title, "why": why, "evidence": evidence, "steps": steps,
            "summary": f"{code_name or 'Caídas'} · {top_driver or 'sin driver claro'}"}


def other_problems(report, metrics: dict) -> list[dict]:
    out = []
    chk = {c.key: c for c in report.checks}
    if chk.get("wu_reboot") and chk["wu_reboot"].status != "ok":
        out.append({"id": "reboot", "severity": "warn", "title": "Windows tiene un reinicio pendiente",
                    "why": "Hay actualizaciones a medio instalar. Hasta que reinicies, Windows puede ir inestable.",
                    "evidence": [chk["wu_reboot"].detail],
                    "steps": _steps(("Guarda tu trabajo y reinicia (tienes 60 s para cancelar).", {"type": "fix", "id": "reboot"}))})
    if chk.get("minidump") and chk["minidump"].status != "ok":
        out.append({"id": "dumps", "severity": "info", "title": "Hay volcados de pantallas azules guardados",
                    "why": "Ocupan espacio y sirven para investigar. Cuando el problema esté resuelto puedes borrarlos desde Limpieza.",
                    "evidence": [chk["minidump"].detail], "steps": _steps(("Bórralos en Limpieza → Volcados de memoria cuando ya no los necesites.", {"type": "page", "id": "limpieza"}))})
    mem = metrics.get("mem", {})
    if mem.get("load", 0) >= 80:
        out.append({"id": "ram", "severity": "warn", "title": f"La memoria RAM va al {mem['load']}%",
                    "why": "Con la RAM casi llena Windows usa el disco como memoria y todo va lento.",
                    "evidence": [f"Libre {format_size(mem['available'])} de {format_size(mem['total'])}"],
                    "steps": _steps(("Mira qué apps abiertas consumen más y cierra las que no uses.", {"type": "page", "id": "inicio"}),
                                    ("Quita del inicio lo que no necesites al encender.", {"type": "page", "id": "inicio"}),
                                    ("En Chrome, cierra pestañas o activa Ahorro de memoria (Configuración → Rendimiento).", None))})
    for c in report.checks:
        if c.key.startswith("disk_") and c.status != "ok":
            out.append({"id": c.key, "severity": c.status, "title": f"Poco espacio en {c.title.split()[-1]}",
                        "why": "Con menos del 15 % libre Windows se ralentiza y las actualizaciones fallan.", "evidence": [c.detail],
                        "steps": _steps(("Limpieza segura de basura.", {"type": "page", "id": "limpieza"}),
                                        ("Busca archivos grandes, sin usar y basura de desarrollo.", {"type": "page", "id": "espacio"}),
                                        *([("Comprime Windows con CompactOS (2-6 GB, reversible).", {"type": "fix", "id": "compactos"})]
                                          if c.key == "disk_" + os.environ.get("SystemDrive", "C:") else
                                          [("Es la unidad de Google Drive: activa «Transmitir archivos» en sus preferencias para no guardar copias locales.", None)]
                                          if c.key[5:] in google_drive_letters() else
                                          [("Mueve a otro disco o a la nube lo que no uses a diario.", None)]))})
    if chk.get("smart") and chk["smart"].status == "bad":
        out.append({"id": "disk_health", "severity": "bad", "title": "El disco informa de problemas de salud",
                    "why": "Un disco que falla puede perder datos. Haz copia de seguridad cuanto antes.", "evidence": [chk["smart"].detail[:200]],
                    "steps": _steps(("Haz copia de seguridad de tus archivos importantes YA.", None), ("Analiza el disco con CHKDSK.", {"type": "fix", "id": "chkdsk"}))})
    return out


def diagnose(report, metrics: dict) -> dict:
    problems = []
    cp = crash_problem(report)
    if cp:
        problems.append(cp)
    problems += other_problems(report, metrics)
    order = {"bad": 0, "warn": 1, "info": 2}
    problems.sort(key=lambda p: order.get(p["severity"], 3))
    urls = {s["action"]["url"] for p in problems for s in p["steps"] if s.get("action", {}).get("type") == "url"}
    return {"problems": problems, "urls": sorted(urls)}
