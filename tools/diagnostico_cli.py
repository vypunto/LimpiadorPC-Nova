"""Diagnóstico rápido por consola (sin GUI) para verificar eventos de caída."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.health import build_health_report  # noqa: E402
from core.report import health_score  # noqa: E402


def main() -> None:
    report = build_health_report(days=45)
    score, label = health_score(report)
    print(f"SCORE {score}/100 ({label})")
    print(report.summary_es)
    print("--- CHECKS ---")
    for c in report.checks:
        print(f"[{c.status}] {c.title}: {c.detail}")
    print("--- EVENTS ---")
    if not report.events:
        print("(ninguno leído)")
    for e in report.events[:25]:
        when = e.time.strftime("%Y-%m-%d %H:%M") if e.time else "?"
        print(f"{when} | {e.source} #{e.event_id} | {e.category} | {e.probable_cause_es[:100]}")
    if report.raw_errors:
        print("--- ERRORS ---")
        for err in report.raw_errors:
            print(err)
    if report.needs_admin:
        print("NEEDS_ADMIN:", report.admin_hint)


if __name__ == "__main__":
    main()
