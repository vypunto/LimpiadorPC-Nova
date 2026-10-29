from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

from .health import HealthReport
from .utils import downloads_dir, format_size


def health_score(report: HealthReport) -> tuple[int, str]:
    """0-100 score based on checks + crash density. Transparent heuristics."""
    score = 100
    for c in report.checks:
        if c.status == "bad":
            score -= 12
        elif c.status == "warn":
            score -= 6
        elif c.status == "info":
            score -= 1
    crashy = [
        e
        for e in report.events
        if e.category in ("power", "unexpected_shutdown", "bugcheck", "whea")
    ]
    score -= min(40, len(crashy) * 4)
    score = max(0, min(100, score))
    if score >= 85:
        label = "Excelente"
    elif score >= 70:
        label = "Bien"
    elif score >= 50:
        label = "Regular"
    else:
        label = "Crítico"
    return score, label


def export_txt(report: HealthReport, path: Path | None = None) -> Path:
    score, label = health_score(report)
    out = path or (downloads_dir() / f"LimpiadorPC_informe_{datetime.now():%Y%m%d_%H%M}.txt")
    lines = [
        "Limpiador PC Pro — Informe de salud",
        f"Generado: {datetime.now():%Y-%m-%d %H:%M}",
        f"Puntuación: {score}/100 ({label})",
        "",
        "RESUMEN",
        report.summary_es,
        "",
        "COMPROBACIONES",
    ]
    for c in report.checks:
        lines.append(f"[{c.status.upper()}] {c.title}: {c.detail}")
    lines += ["", "TIMELINE DE CAÍDAS / EVENTOS"]
    if not report.events:
        lines.append("(Sin eventos leídos)")
    for e in report.events:
        when = e.time.strftime("%Y-%m-%d %H:%M") if e.time else "?"
        lines.append(
            f"{when} | {e.level} | {e.source} ID {e.event_id} | {e.category}"
        )
        lines.append(f"  Causa probable: {e.probable_cause_es}")
        lines.append(f"  {e.message[:300]}")
    if report.raw_errors:
        lines += ["", "ERRORES AL LEER LOGS"]
        lines.extend(report.raw_errors)
    if report.needs_admin:
        lines += ["", "ADMIN", report.admin_hint]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def export_html(report: HealthReport, path: Path | None = None, diagnosis: dict | None = None) -> Path:
    score, label = health_score(report)
    out = path or (downloads_dir() / f"LimpiadorPC_informe_{datetime.now():%Y%m%d_%H%M}.html")
    rows_checks = "".join(
        f"<tr><td>{html.escape(c.status)}</td><td>{html.escape(c.title)}</td>"
        f"<td>{html.escape(c.detail)}</td></tr>"
        for c in report.checks
    )
    rows_ev = "".join(
        "<tr>"
        f"<td>{html.escape(e.time.strftime('%Y-%m-%d %H:%M') if e.time else '?')}</td>"
        f"<td>{html.escape(e.source)} ({e.event_id})</td>"
        f"<td>{html.escape(e.category)}</td>"
        f"<td>{html.escape(e.probable_cause_es)}</td>"
        f"<td>{html.escape(e.message[:400])}</td>"
        "</tr>"
        for e in report.events
    )
    diag_html = ""
    for p in (diagnosis or {}).get("problems", []):
        steps = "".join(f"<li>{html.escape(s['text'])}" + (f" — <a href='{html.escape(s['action']['url'])}'>{html.escape(s['action']['url'])}</a>" if s.get("action", {}).get("type") == "url" else "") + "</li>" for s in p["steps"])
        ev = "".join(f"<li>{html.escape(e)}</li>" for e in p["evidence"])
        diag_html += f"<div class='prob {p['severity']}'><h3>{html.escape(p['title'])}</h3><p>{html.escape(p['why'])}</p><p class='muted'>Pruebas:</p><ul>{ev}</ul><p><b>Cómo solucionarlo</b></p><ol>{steps}</ol></div>"
    if diag_html:
        diag_html = "<h2>Diagnóstico y soluciones</h2>" + diag_html
    doc = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"/>
<title>Informe Limpiador PC Nova</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;background:#0f172a;color:#e2e8f0;margin:24px}}
h1,h2{{color:#f8fafc}} .score{{font-size:2rem;color:#38bdf8}}
table{{border-collapse:collapse;width:100%;margin:12px 0}}
td,th{{border:1px solid #334155;padding:8px;text-align:left;vertical-align:top}}
th{{background:#1e293b}} .muted{{color:#94a3b8}} a{{color:#5ef2d6}}
.prob{{border:1px solid #334155;border-left:4px solid #38bdf8;border-radius:10px;padding:4px 18px;margin:12px 0;background:#111c33}}
.prob.bad{{border-left-color:#fb7185}} .prob.warn{{border-left-color:#fbbf24}} li{{margin:4px 0}}
</style></head><body>
<h1>Limpiador PC Nova — Informe</h1>
<p class="muted">Generado {datetime.now():%Y-%m-%d %H:%M}</p>
<p class="score">{score}/100 — {html.escape(label)}</p>
<p>{html.escape(report.summary_es)}</p>
{diag_html}
<h2>Comprobaciones</h2>
<table><tr><th>Estado</th><th>Área</th><th>Detalle</th></tr>{rows_checks}</table>
<h2>Timeline de caídas</h2>
<table><tr><th>Fecha</th><th>Origen</th><th>Tipo</th><th>Causa probable</th><th>Mensaje</th></tr>
{rows_ev or '<tr><td colspan="5">Sin eventos</td></tr>'}
</table>
</body></html>"""
    out.write_text(doc, encoding="utf-8")
    return out
