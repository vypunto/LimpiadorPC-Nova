"""Smally: asistente de la app. Con clave de API responde con Claude usando el estado real del PC."""
from __future__ import annotations

from .ai_organize import MODEL, api_key
from .utils import format_size

APP_GUIDE = """
Eres Smally, la mascota y asistente experto de «Limpiador PC Nova», una app de Windows para optimizar,
limpiar, reparar y proteger el PC. Hablas en español, cercano, claro y breve (máx. ~150 palabras salvo que pidan
detalle). Usa listas cortas cuando ayuden. Nunca inventes datos del equipo: usa solo el ESTADO DEL PC que se te da;
si falta un dato, di en qué sección obtenerlo. No puedes ejecutar acciones: explica qué hacer y en qué sección.
Para llevar al usuario a una sección añade al final etiquetas [[ir:ID]] (máx. 3) con estos ID:
soluciones, panel, limpieza, espacio, duplicados, organizador, seguridad, reparar, salud, inicio, programas, buscar.
- soluciones: problemas detectados con causa, pruebas y plan paso a paso con botones (abrir la web del driver,
  ajustes, reparaciones). Remite aquí para arreglar caídas, pantallas azules y avisos.

QUÉ HACE CADA SECCIÓN
- panel: salud 0-100, CPU/RAM en vivo, discos, procesos, recomendaciones y «Optimizar ahora» (limpieza segura +
  vaciar caché DNS + diagnóstico de salud; nunca toca documentos ni programas).
- limpieza: temporales (solo de más de 24 h), papelera (desmarcada; borrado definitivo), miniaturas, informes de error,
  volcados (desmarcados: sirven para investigar pantallas azules), Windows Update (admin), cachés de navegadores
  (no borra contraseñas, historial ni cookies), GPU NVIDIA/AMD/DirectX, Discord, Steam, Spotify, npm/pip/yarn/Go/NuGet.
  Botón «Detalles» con lo que se borra y lista real de archivos. Limpieza automática semanal opcional.
- espacio: archivos grandes, carpetas pesadas, archivos sin usar (90 días-2 años), «Desarrollo» (node_modules, venv,
  cachés de build: van a la Papelera; luego hay que reinstalar dependencias) y «Organizar Descargas» (reversible).
- duplicados: copias idénticas verificadas por hash completo; sugiere conservar la más antigua; van a la Papelera.
- organizador: elige carpeta; reglas locales o IA; propone carpetas y nombres limpios con vista «Así quedará»;
  solo mueve (nunca borra), no toca proyectos de código, reversible con «Deshacer».
- seguridad: Microsoft Defender (estado, análisis rápido/completo, firmas, historial de amenazas) y auditoría:
  programas de inicio y tareas sospechosas, hosts, proxy, UAC, firewall, exclusiones y extensiones del navegador.
- reparar: punto de restauración (automático antes de las reparaciones delicadas), SFC, DISM, CHKDSK /scan,
  restablecer Windows Update, buscar actualizaciones y drivers, Store, Explorador, caché de iconos, audio, impresora,
  DNS, renovar IP, restablecer red (afecta a VPN), sincronizar hora, compactar WinSxS, CompactOS (libera 2-6 GB,
  reversible), TRIM, planes de energía, desactivar hibernación. Muchas necesitan «Ejecutar como admin».
  Orden si Windows falla: punto de restauración → SFC → DISM → SFC → CHKDSK.
- salud: apagados inesperados (Kernel-Power 41, 6008), pantallas azules (BugCheck), errores de hardware (WHEA),
  minidumps, discos, RAM, temperatura, reinicio pendiente; exportar informe HTML.
- inicio (Inicio y fondo): programas al arrancar (reversible), apps abiertas (cerrar), servicios de terceros (solo
  Automático↔Manual) y tareas programadas. Lo esencial (audio, drivers, red, seguridad) lleva candado y no se puede tocar.
- programas: instalados, tamaño, «sin uso» (>180 días), abre el desinstalador oficial.
- buscar: búsqueda por nombre en tus carpetas.
- Extras: modo día/noche (botón sol/luna), historial de acciones (barra lateral), avisos ?/! con riesgos.

PRINCIPIOS: seguridad ante todo; recomienda lo reversible primero; desaconseja «limpiadores de registro»,
«aceleradores de RAM» y desactivar Defender. Si hay caídas o pantallas azules: actualizar drivers de gráficos y chipset,
test de memoria, revisar temperaturas y fuente. Si el disco va lleno: Limpieza → Espacio/Desarrollo → CompactOS.
"""


def build_context(state) -> str:
    """Resumen del estado real del PC a partir de lo que la app ya ha analizado."""
    from . import sysinfo
    from .report import health_score

    lines = []
    info = sysinfo.static_info() or {}
    m = sysinfo.metrics()
    lines.append(f"Equipo: {info.get('maker', '')} {info.get('machine', '')} · {info.get('os', '')} build {info.get('build', '')}")
    lines.append(f"CPU: {info.get('cpu', '')} · GPU: {', '.join(info.get('gpus') or [])} · RAM {format_size(m['mem']['total'])} (uso {m['mem']['load']}%) · CPU {m['cpu']:.0f}%")
    lines.append("Discos: " + "; ".join(f"{d['letter']} {format_size(d['free'])} libres de {format_size(d['total'])}" for d in m["disks"]))
    lines.append(f"Encendido desde hace {m['uptime'] // 3600} h")

    def last(kind):
        js = [j for j in state.jobs.values() if j.kind == kind and j.state == "done" and j.result]
        return max(js, key=lambda j: j.started).result if js else None

    if state.health_report is not None:
        r = state.health_report
        score, label = health_score(r)
        lines.append(f"Salud: {score}/100 ({label}). {r.summary_es}")
        lines += [f"- [{c.status}] {c.title}: {c.detail[:160]}" for c in r.checks if c.status in ("bad", "warn")]
        crash = [e for e in r.events if e.category in ("power", "unexpected_shutdown", "bugcheck", "whea")]
        if crash:
            lines.append(f"Caídas en 30 días: {len(crash)}; últimas: " + "; ".join(
                f"{e.time:%Y-%m-%d %H:%M} {e.source} #{e.event_id}" for e in crash[:5] if e.time))
    else:
        lines.append("Salud: aún no diagnosticada.")
    if state.health_report is not None:
        from .diagnose import diagnose

        for p in diagnose(state.health_report, m)["problems"][:4]:
            lines.append(f"PROBLEMA [{p['severity']}]: {p['title']}. {p['why']} Pasos: " + " | ".join(s["text"] for s in p["steps"]))
    cs = last("clean_scan")
    if cs:
        t = [x for x in cs["targets"] if x.get("size")]
        sel = sum(x["size"] for x in t if x["selected"] and not x.get("locked"))
        lines.append(f"Basura seleccionable sin riesgo: {format_size(sel)}. Mayores: " + ", ".join(
            f"{x['title']} {format_size(x['size'])}" for x in sorted(t, key=lambda x: -x["size"])[:6]))
    sa = last("sec_audit")
    if sa:
        fs = [f for f in sa["findings"] if f.severity in ("high", "medium")]
        lines.append("Seguridad (hallazgos): " + ("; ".join(f"[{f.severity}] {f.title} ({f.area})" for f in fs[:10]) or "sin hallazgos relevantes"))
    ss = last("sec_status")
    if ss and ss.get("defender", {}).get("available"):
        d = ss["defender"]
        lines.append(f"Defender: tiempo real {'activo' if d.get('RealTimeProtectionEnabled') else 'APAGADO'}, firmas de hace {d.get('AntivirusSignatureAge')} días, último análisis rápido hace {d.get('QuickScanAge')} días. Amenazas registradas: {len(ss.get('threats') or [])}")
    try:
        from .startup import list_startup_run_entries

        on = [s for s in list_startup_run_entries() if s.enabled]
        lines.append(f"Al inicio ({len(on)}): " + ", ".join(f"{s.name} ({s.impact})" for s in on[:15]))
    except Exception:  # noqa: BLE001
        pass
    dj = last("devjunk")
    if dj:
        lines.append(f"Basura de desarrollo: {len(dj['items'])} carpetas, {format_size(sum(i['size'] for i in dj['items']))}")
    return "\n".join(lines)


def chat(messages: list[dict], state) -> dict:
    import anthropic

    key = api_key()
    if not key:
        return {"ok": False, "need_key": True}
    clean = []
    for msg in messages[-16:]:
        role = msg.get("role")
        text = str(msg.get("content", ""))[:4000]
        if role in ("user", "assistant") and text.strip():
            clean.append({"role": role, "content": text})
    while clean and clean[0]["role"] != "user":
        clean.pop(0)
    if not clean:
        return {"ok": False, "text": "Escríbeme tu pregunta."}
    system = [
        {"type": "text", "text": APP_GUIDE, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": "ESTADO DEL PC (datos reales de la app):\n" + build_context(state)},
    ]
    client = anthropic.Anthropic(api_key=key)
    try:
        resp = client.beta.messages.create(
            model=MODEL,
            max_tokens=4000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=system,
            output_config={"effort": "medium"},
            messages=clean,
        )
    except anthropic.AuthenticationError:
        return {"ok": False, "text": "Tu clave de API no es válida. Revísala en Organizador IA."}
    except anthropic.RateLimitError:
        return {"ok": False, "text": "He alcanzado el límite de uso de la API. Prueba en un minuto."}
    except anthropic.APIConnectionError:
        return {"ok": False, "text": "No tengo conexión con la API ahora mismo; te respondo con lo que sé sin Internet.", "offline": True}
    except anthropic.APIStatusError as exc:
        return {"ok": False, "text": f"Error de la API ({exc.status_code})."}
    if resp.stop_reason == "refusal":
        return {"ok": True, "text": "Esa pregunta no puedo responderla. Pregúntame sobre tu PC o la app."}
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    return {"ok": True, "text": text or "No tengo respuesta para eso."}

