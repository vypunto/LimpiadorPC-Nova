"""Servidor local (solo 127.0.0.1) que expone el núcleo a la interfaz web.

Las tareas largas se ejecutan como "jobs" en hilos; la interfaz consulta su
progreso. Toda petición a /api exige la clave aleatoria de la sesión.
"""
from __future__ import annotations

import dataclasses
import json
import mimetypes
import secrets
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from . import __app_name__, __version__
from . import security, sysinfo
from .cleaner import build_targets, clean_target, measure_target, preview_target
from .drive import default_scan_roots, get_drive_info
from .duplicates import find_duplicates, flag_drive_local_pairs
from .fixes import FIX_BY_ID, FIXES, REVERT, describe_steps, run_fix
from .folders import top_folders
from . import ai_organize, background, diagnose, errorlog, history, organize, schedule, shortcuts, smally
from .health import build_health_report, maintenance_suggestions
from .large_files import find_large_files
from .programs import list_installed_programs, uninstall_program
from .report import export_html, health_score
from .search import search_files
from .startup import list_startup_run_entries, set_startup_enabled
from .unused import find_unused
from .utils import format_size, is_admin, is_protected, open_in_explorer, relaunch_as_admin, send_to_recycle

UI_DIR = (Path(getattr(sys, "_MEIPASS", "")) if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]) / "ui"
APP_SCRIPT = Path(__file__).resolve().parents[1] / "limpiador.py"


def to_jsonable(obj):
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat(timespec="minutes")
    return obj


# --------------------------------------------------------------------------- jobs

class Job:
    def __init__(self, kind: str) -> None:
        self.id = uuid.uuid4().hex[:12]
        self.kind = kind
        self.state = "running"
        self.progress: float | None = None
        self.message = ""
        self.lines: list[str] = []
        self.result = None
        self.error = ""
        self.stop = threading.Event()
        self.started = time.time()
        self.finished: float | None = None
        self.lock = threading.Lock()

    def log(self, text: str, replace_last: bool = False) -> None:
        with self.lock:
            if replace_last and self.lines:
                self.lines[-1] = text
            else:
                self.lines.append(text)
                if len(self.lines) > 3000:
                    del self.lines[:1000]

    def set(self, progress: float | None = None, message: str | None = None) -> None:
        if progress is not None:
            self.progress = max(0.0, min(1.0, progress))
        if message is not None:
            self.message = message

    def snapshot(self) -> dict:
        with self.lock:
            lines = self.lines[-400:]
        return {
            "id": self.id,
            "kind": self.kind,
            "state": self.state,
            "progress": self.progress,
            "message": self.message,
            "log": lines,
            "result": to_jsonable(self.result),
            "error": self.error,
            "elapsed": round((self.finished or time.time()) - self.started, 1),
        }


class State:
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}
        self.allowed_paths: set[str] = set()
        self.programs: dict[str, str] = {}
        self.health_report = None
        self.restore_done = False
        self.organize_plan: list = []
        self.aiorg: dict = {}
        self.diag_urls: set = set()
        self.last_ping = time.time()
        self.bye_at: float | None = None
        self.lock = threading.Lock()

    def allow(self, paths) -> None:
        with self.lock:
            for p in paths:
                self.allowed_paths.add(str(p).lower())


STATE = State()


def _progress_counter(job: Job, label: str):
    def cb(count, path):
        job.set(message=f"{label} · {count:,} archivos · {Path(str(path)).parent}".replace(",", "."))
    return cb


def _roots(params: dict) -> list[Path]:
    custom = params.get("roots") or []
    if custom:
        return [Path(p) for p in custom if Path(p).exists()]
    return default_scan_roots(include_drive=bool(params.get("include_drive")))


def job_health(job: Job, params: dict):
    job.set(0.1, "Leyendo el Visor de eventos y sensores…")
    report = build_health_report(days=int(params.get("days", 30)))
    STATE.health_report = report
    score, label = health_score(report)
    return {"score": score, "label": label, "report": report, "tips": maintenance_suggestions()}


def _target_dict(t, size=None):
    return {
        "key": t.key, "title": t.title, "description": t.description, "group": t.group,
        "admin": t.admin, "selected": t.selected, "size": size,
        "paths": [str(p) for p in t.paths][:6],
    }


def job_clean_scan(job: Job, params: dict):
    targets = build_targets()
    admin = is_admin()
    rows = [_target_dict(t) for t in targets]
    for r in rows:
        if r["admin"] and not admin:
            r["locked"] = True
    job.result = {"targets": rows, "admin": admin}
    done = 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {pool.submit(measure_target, t, job.stop): i for i, t in enumerate(targets)}
        for fut in as_completed(futs):
            i = futs[fut]
            try:
                rows[i]["size"] = fut.result()
            except Exception:  # noqa: BLE001
                rows[i]["size"] = 0
            done += 1
            job.set(done / len(targets), f"Analizado: {rows[i]['title']}")
    return job.result


def job_clean_run(job: Job, params: dict):
    keys = set(params.get("keys") or [])
    targets = [t for t in build_targets() if t.key in keys]
    freed = errors = 0
    details = []
    for i, t in enumerate(targets):
        if job.stop.is_set():
            break
        job.set(i / max(1, len(targets)), f"Limpiando {t.title}…")
        f, e = clean_target(t)
        freed += f
        errors += e
        details.append({"key": t.key, "title": t.title, "freed": f, "errors": e})
        job.log(f"{t.title}: {format_size(f)} liberados" + (f" ({e} en uso, omitidos)" if e else ""))
    job.set(1, "Limpieza completada")
    history.record("Limpieza", f"{format_size(freed)} · " + ", ".join(d["title"] for d in details))
    return {"freed": freed, "errors": errors, "details": details}


def job_large(job: Job, params: dict):
    files = find_large_files(
        _roots(params), min_bytes=int(params.get("min_mb", 200)) * 1024 * 1024, limit=300,
        stop_event=job.stop, progress_cb=_progress_counter(job, "Buscando archivos grandes"),
    )
    STATE.allow(f.path for f in files)
    out = []
    for f in files:
        try:
            mt = f.path.stat().st_mtime
        except OSError:
            mt = 0
        out.append({"path": str(f.path), "size": f.size, "mtime": mt})
    return {"files": out}


def job_folders(job: Job, params: dict):
    items = top_folders(_roots(params), depth=2, limit=60, stop_event=job.stop,
                        progress_cb=_progress_counter(job, "Midiendo carpetas"))
    return {"folders": items}


def job_unused(job: Job, params: dict):
    files = find_unused(
        _roots(params), days=int(params.get("days", 365)), min_bytes=int(params.get("min_mb", 10)) * 1024 * 1024,
        stop_event=job.stop, progress_cb=_progress_counter(job, "Buscando archivos sin uso"),
    )
    STATE.allow(f.path for f in files)
    return {"files": files}


def job_dupes(job: Job, params: dict):
    def hp(frac, path):
        job.set(frac, f"Verificando contenido · {Path(path).name}")

    groups = find_duplicates(
        _roots(params), min_bytes=int(params.get("min_mb", 1)) * 1024 * 1024, stop_event=job.stop,
        progress_cb=_progress_counter(job, "Indexando"), hash_progress=hp,
    )
    groups = flag_drive_local_pairs(groups)[:400]
    for g in groups:
        STATE.allow(g.paths)
    return {
        "groups": [{"size": g.size, "wasted": g.wasted, "paths": [str(p) for p in g.paths], "mtimes": g.mtimes}
                   for g in groups],
        "drive": get_drive_info().notes if params.get("include_drive") else [],
    }


def job_search(job: Job, params: dict):
    q = str(params.get("query", "")).strip()
    hits = search_files(q, _roots(params), limit=300, stop_event=job.stop,
                        progress_cb=lambda n, p: job.set(message=f"{n} resultados · {p}"))
    STATE.allow(h.path for h in hits if h.kind == "file")
    return {"hits": hits}


def job_programs(job: Job, params: dict):
    job.set(0.2, "Leyendo programas instalados…")
    progs = list_installed_programs()
    STATE.programs = {p.name: p.uninstall_string for p in progs}
    return {"programs": [
        {k: v for k, v in to_jsonable(p).items() if k != "uninstall_string"} | {"can_uninstall": bool(p.uninstall_string)}
        for p in progs
    ]}


def job_sec_status(job: Job, params: dict):
    job.set(0.3, "Consultando Microsoft Defender…")
    status = security.defender_status()
    job.set(0.7, "Leyendo historial de amenazas…")
    threats = security.defender_threats() if status.get("available") else []
    return {"defender": status, "threats": threats}


def job_sec_audit(job: Job, params: dict):
    return {"findings": security.audit(progress=job.set)}


def job_sec_scan(job: Job, params: dict):
    kind = params.get("type", "quick")
    scan_type = {"quick": "1", "full": "2"}.get(kind, "1")
    job.set(None, "Análisis completo de Defender en curso (puede tardar mucho)…" if kind == "full"
            else "Análisis rápido de Defender en curso…")
    code = security.run_defender(["-Scan", "-ScanType", scan_type], job.log, job.stop)
    threats = security.defender_threats()
    return {"code": code, "threats": threats}


def job_sec_update(job: Job, params: dict):
    job.set(None, "Actualizando firmas de Defender…")
    code = security.run_defender(["-SignatureUpdate"], job.log, job.stop)
    return {"code": code, "defender": security.defender_status()}


RESTORE_FIRST = {"sfc", "dism", "wu_reset", "net_reset", "component_cleanup", "hibernate_off", "spooler"}


def job_fix(job: Job, params: dict):
    fix = FIX_BY_ID.get(str(params.get("id")))
    if fix is None:
        raise ValueError("Reparación desconocida")
    if fix.admin and not is_admin():
        raise PermissionError("Esta reparación necesita permisos de administrador.")
    if fix.id in RESTORE_FIRST and not STATE.restore_done:
        job.set(None, "Creando punto de restauración de seguridad…")
        rc = run_fix(FIX_BY_ID["restore_point"], job.log, job.stop)
        STATE.restore_done = True
        job.log("✓ Punto de restauración listo" if rc == 0 else
                "Aviso: Windows no creó el punto (solo permite uno cada 24 h o está desactivado). Continuando…")
    job.set(None, f"{fix.title}…")
    code = run_fix(fix, job.log, job.stop)
    history.record("Reparación", f"{fix.title} (código {code})")
    return {"code": code, "reboot": fix.reboot, "title": fix.title}


def job_optimize(job: Job, params: dict):
    """Optimización 1-clic: limpieza segura + DNS + diagnóstico. Nada destructivo."""
    admin = is_admin()
    targets = [t for t in build_targets() if t.selected and (admin or not t.admin) and t.key != "recycle"]
    freed = 0
    total_steps = len(targets) + 2
    job.result = {"freed": 0}
    for i, t in enumerate(targets):
        if job.stop.is_set():
            break
        job.set(i / total_steps, f"Limpiando {t.title}…")
        try:
            f, _e = clean_target(t)
        except Exception as exc:  # noqa: BLE001  — un paso no debe tumbar el resto
            job.log(f"⚠ {t.title}: {exc}")
            continue
        freed += f
        job.result = {"freed": freed}
        if f:
            job.log(f"✓ {t.title} — {format_size(f)}")
    job.set(len(targets) / total_steps, "Vaciando caché DNS…")
    if not admin:
        job.log("· Caché DNS: omitido (Windows pide permisos de administrador)")
    else:
        try:
            rc = run_fix(FIX_BY_ID["dns"], lambda *_: None)
            job.log("✓ Caché DNS renovada" if rc == 0 else f"⚠ Caché DNS: Windows devolvió el código {rc}")
        except Exception as exc:  # noqa: BLE001
            job.log(f"⚠ DNS: {exc}")
    job.set((len(targets) + 1) / total_steps, "Diagnosticando la salud del equipo…")
    score, label = None, "—"
    try:
        report = build_health_report(days=30)
        STATE.health_report = report
        score, label = health_score(report)
        job.log(f"✓ Diagnóstico: {score}/100 ({label})")
    except Exception as exc:  # noqa: BLE001
        job.log(f"⚠ Diagnóstico: {exc}")
    history.record("Optimizar ahora", f"{format_size(freed)} liberados · salud {score}/100")
    job.set(1, "Optimización completada")
    return {"freed": freed, "score": score, "label": label}


def job_devjunk(job: Job, params: dict):
    items = organize.find_dev_junk(job.stop, progress=lambda m: job.set(message=m))
    STATE.allow(i["path"] for i in items)
    return {"items": items}


def job_organize_plan(job: Job, params: dict):
    plan = organize.plan_downloads()
    STATE.organize_plan = plan
    return {"plan": plan}


def job_bg(job: Job, params: dict):
    what = params.get("what", "procs")
    job.set(None, "Leyendo lo que se ejecuta en segundo plano…")
    if what == "services":
        return {"items": background.services()}
    if what == "tasks":
        return {"items": background.tasks()}
    return {"items": background.processes()}


def job_aiorg(job: Job, params: dict):
    folder = Path(str(params.get("folder", "")).strip().strip('"'))
    why = ai_organize.check_folder(folder)
    if why:
        raise ValueError(why)
    job.set(None, "Analizando la carpeta…")
    files, kept = ai_organize.scan(folder)
    if not files:
        return {"folder": str(folder), "plan": [], "kept": kept, "scanned": 0}
    if params.get("mode") == "ai":
        plan = ai_organize.ai_plan(files, str(params.get("instructions", "")), progress=job.set, stop=job.stop)
    else:
        plan = ai_organize.local_plan(files, rename=bool(params.get("rename", True)))
    plan = ai_organize.finalize(folder, plan)
    STATE.aiorg = {"folder": str(folder), "plan": plan}
    return {"folder": str(folder), "plan": plan, "kept": kept, "scanned": len(files), "capped": len(files) >= ai_organize.MAX_FILES}


def job_diagnosis(job: Job, params: dict):
    if STATE.health_report is None or params.get("refresh"):
        job.set(None, "Leyendo el Visor de eventos…")
        STATE.health_report = build_health_report(days=30)
    job.set(None, "Buscando la causa y las soluciones…")
    d = diagnose.diagnose(STATE.health_report, sysinfo.metrics())
    STATE.diag_urls = set(d["urls"])
    return d


TOOLS = {"devmgmt": "devmgmt.msc", "eventvwr": "eventvwr.msc", "msconfig": "msconfig.exe"}


def act_support_save(body: dict):
    from .utils import downloads_dir

    path = downloads_dir() / f"LimpiadorPC_informe_tecnico_{datetime.now():%Y%m%d_%H%M}.txt"
    path.write_text(errorlog.report(STATE, body.get("client") or {}), encoding="utf-8")
    open_in_explorer(path)
    return {"ok": True, "path": str(path)}


def act_open(body: dict):
    import os as _os

    kind = body.get("type")
    if kind == "url" and body.get("url") in STATE.diag_urls:
        _os.startfile(body["url"])  # type: ignore[attr-defined]
    elif kind == "settings" and str(body.get("uri", "")).startswith("ms-settings:") and len(str(body["uri"])) < 80:
        _os.startfile(body["uri"])  # type: ignore[attr-defined]
    elif kind == "tool" and body.get("id") in TOOLS:
        _os.startfile(TOOLS[body["id"]])  # type: ignore[attr-defined]
    else:
        return {"ok": False, "message": "Acción no permitida."}
    return {"ok": True}


JOBS = {
    "diagnosis": job_diagnosis,
    "aiorg": job_aiorg,
    "devjunk": job_devjunk,
    "organize_plan": job_organize_plan,
    "bg": job_bg,
    "health": job_health,
    "clean_scan": job_clean_scan,
    "clean_run": job_clean_run,
    "large": job_large,
    "folders": job_folders,
    "unused": job_unused,
    "dupes": job_dupes,
    "search": job_search,
    "programs": job_programs,
    "sec_status": job_sec_status,
    "sec_audit": job_sec_audit,
    "sec_scan": job_sec_scan,
    "sec_update": job_sec_update,
    "fix": job_fix,
    "optimize": job_optimize,
}

# Tareas que no deben correr dos veces a la vez
EXCLUSIVE = {"clean_run", "optimize", "fix", "sec_scan", "sec_update"}


def start_job(kind: str, params: dict) -> Job:
    if kind not in JOBS:
        raise ValueError(f"Tarea desconocida: {kind}")
    if kind in EXCLUSIVE:
        for j in STATE.jobs.values():
            if j.kind in EXCLUSIVE and j.state == "running":
                raise RuntimeError("Ya hay una tarea de mantenimiento en curso. Espera a que termine.")
    job = Job(kind)
    STATE.jobs[job.id] = job

    def run():
        try:
            res = JOBS[kind](job, params)
            job.result = res
            job.state = "cancelled" if job.stop.is_set() else "done"
        except Exception as exc:  # noqa: BLE001
            job.error = str(exc) or exc.__class__.__name__
            job.state = "error"
            history.record("ERROR " + kind, job.error[:300])
            errorlog.log(f"tarea {kind}", job.error, exc)
        finally:
            job.finished = time.time()

    threading.Thread(target=run, daemon=True, name=f"job-{kind}").start()
    return job


# ------------------------------------------------------------------------ actions

def act_recycle(body: dict):
    done, failed = [], []
    for raw in body.get("paths") or []:
        p = Path(raw)
        if str(p).lower() not in STATE.allowed_paths or is_protected(p):
            failed.append({"path": raw, "why": "Ruta no permitida"})
            continue
        try:
            size = p.stat().st_size if p.is_file() else int(body.get("sizes", {}).get(raw, 0))
        except OSError:
            size = 0
        if send_to_recycle(p):
            done.append({"path": raw, "size": size})
        else:
            failed.append({"path": raw, "why": "En uso, sin permisos o la unidad no tiene Papelera"})
    if done:
        history.record("Papelera", f"{len(done)} archivos · " + "; ".join(d["path"] for d in done[:20]))
    return {"recycled": done, "failed": failed, "freed": sum(d["size"] for d in done)}


def _rec(action: str, ok: bool, msg: str) -> dict:
    if ok:
        history.record(action, msg)
    return {"ok": ok, "message": msg}


def act_reveal(body: dict):
    p = Path(str(body.get("path", "")))
    if p.exists():
        open_in_explorer(p)
        return {"ok": True}
    return {"ok": False}


def act_uninstall(body: dict):
    name = str(body.get("name", ""))
    if name not in STATE.programs:
        return {"ok": False, "message": "Vuelve a cargar la lista de programas."}
    ok, msg = uninstall_program(STATE.programs[name])
    return {"ok": ok, "message": msg}


def act_startup_toggle(body: dict):
    ok, msg = set_startup_enabled(str(body["name"]), str(body["hive"]), str(body["approved"]), bool(body["enabled"]))
    if ok:
        history.record("Inicio", msg)
    return {"ok": ok, "message": msg}


def act_elevate(body: dict):
    ok = relaunch_as_admin(APP_SCRIPT)
    if ok:
        threading.Timer(1.5, lambda: SERVER and SERVER.shutdown()).start()
    return {"ok": ok}


def act_report(body: dict):
    if STATE.health_report is None:
        STATE.health_report = build_health_report(days=30)
    path = export_html(STATE.health_report, diagnosis=diagnose.diagnose(STATE.health_report, sysinfo.metrics()))
    open_in_explorer(path)
    return {"ok": True, "path": str(path)}


def overview():
    info = sysinfo.static_info()
    return {
        "app": __app_name__, "version": __version__, "admin": is_admin(),
        "system": info, "metrics": sysinfo.metrics(),
    }


def fixes_catalog():
    return {"admin": is_admin(), "fixes": [
        {"id": f.id, "group": f.group, "title": f.title, "description": f.description, "admin": f.admin,
         "reboot": f.reboot, "minutes": f.minutes, "icon": f.icon, "commands": describe_steps(f),
         "revert": REVERT.get(f.id, ""), "restore_first": f.id in RESTORE_FIRST} for f in FIXES
    ]}


def startup_list():
    items = list_startup_run_entries()
    out = []
    for it in items:
        d = to_jsonable(it)
        d["suspicious"] = security.assess_command(it.command)
        d["essential"] = background.is_essential(it.name) or it.name.lower() in ("securityhealth", "windowsdefender")
        out.append(d)
    return {"items": out, "admin": is_admin()}


GET_ROUTES = {
    "/api/overview": overview,
    "/api/metrics": sysinfo.metrics,
    "/api/processes": lambda: {"processes": sysinfo.top_processes(10)},
    "/api/fixes": fixes_catalog,
    "/api/startup": startup_list,
    "/api/autoclean": schedule.status,
    "/api/aiorg/config": lambda: {"has_key": bool(ai_organize.api_key()), "model": ai_organize.MODEL},
    "/api/history": lambda: {"lines": history.recent()},
}

POST_ROUTES = {
    "/api/files/recycle": act_recycle,
    "/api/files/reveal": act_reveal,
    "/api/programs/uninstall": act_uninstall,
    "/api/startup/toggle": act_startup_toggle,
    "/api/elevate": act_elevate,
    "/api/report": act_report,
    "/api/open": act_open,
    "/api/shortcuts": lambda b: dict(zip(("ok", "message"), shortcuts.create())),
    "/api/clientlog": lambda b: errorlog.log("interfaz " + str(b.get("where", ""))[:80],
                                            str(b.get("message", ""))[:500] + "\n" + str(b.get("stack", ""))[:2000]) or {"ok": True},
    "/api/support": lambda b: {"text": errorlog.report(STATE, b.get("client") or {})},
    "/api/support/save": act_support_save,
    "/api/aiorg/pick": lambda b: {"folder": ai_organize.pick_folder()},
    "/api/aiorg/key": lambda b: dict(zip(("ok", "message"), ai_organize.save_key(str(b.get("key", ""))))),
    "/api/aiorg/apply": lambda b: ai_organize.apply(Path(STATE.aiorg["folder"]), STATE.aiorg["plan"], set(b.get("skip") or []))
        if STATE.aiorg else {"moved": 0, "failed": 0},
    "/api/aiorg/undo": lambda b: ai_organize.undo(),
    "/api/smally/chat": lambda b: smally.chat(b.get("messages") or [], STATE),
    "/api/clean/preview": lambda b: next((preview_target(t) for t in build_targets() if t.key == b.get("key")), {"files": []}),
    "/api/organize/apply": lambda b: organize.apply_plan(STATE.organize_plan),
    "/api/organize/undo": lambda b: organize.undo(),
    "/api/proc/kill": lambda b: _rec("Cerrar proceso", *background.kill(str(b.get("name", "")))),
    "/api/service/set": lambda b: _rec("Servicio", *background.set_service(str(b.get("name", "")), str(b.get("mode", "")))),
    "/api/task/set": lambda b: _rec("Tarea programada", *background.set_task(str(b.get("path", "")), str(b.get("name", "")), bool(b.get("enabled")))),
    "/api/autoclean": lambda b: dict(zip(("ok", "message"),
                                         schedule.enable(str(b.get("day", "SUN"))) if b.get("enabled") else schedule.disable())),
}


# ------------------------------------------------------------------------- server

TOKEN = secrets.token_urlsafe(24)
SERVER: ThreadingHTTPServer | None = None


class Handler(BaseHTTPRequestHandler):
    server_version = "Nova/1"

    def log_message(self, *_args):  # silencio
        pass

    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def _send(self, code: int, body: bytes, ctype: str = "application/json; charset=utf-8") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data, code: int = 200) -> None:
        self._send(code, json.dumps(to_jsonable(data), ensure_ascii=False).encode("utf-8"))

    def _authed(self) -> bool:
        return secrets.compare_digest(self.headers.get("X-Nova-Key", ""), TOKEN)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > 5_000_000:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}

    def do_GET(self):  # noqa: N802
        if not self._host_ok():
            return self._send(403, b"{}")
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            if not self._authed():
                return self._json({"error": "unauthorized"}, 401)
            STATE.last_ping = time.time()
            STATE.bye_at = None
            if path.startswith("/api/job/"):
                job = STATE.jobs.get(path.rsplit("/", 1)[-1])
                return self._json(job.snapshot() if job else {"error": "not found"}, 200 if job else 404)
            fn = GET_ROUTES.get(path)
            if fn is None:
                return self._json({"error": "not found"}, 404)
            try:
                return self._json(fn())
            except Exception as exc:  # noqa: BLE001
                errorlog.log(f"GET {path}", str(exc), exc)
                return self._json({"error": str(exc)}, 500)
        # estáticos
        rel = "index.html" if path in ("/", "") else path.lstrip("/")
        target = (UI_DIR / rel).resolve()
        if UI_DIR.resolve() not in target.parents or not target.is_file():
            return self._send(404, b"not found", "text/plain")
        ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype.endswith("javascript"):
            ctype += "; charset=utf-8"
        self._send(200, target.read_bytes(), ctype)

    def do_POST(self):  # noqa: N802
        if not self._host_ok():
            return self._send(403, b"{}")
        path = urlparse(self.path).path
        if path == "/api/bye":  # sendBeacon al cerrar la ventana (sin cabeceras propias)
            STATE.bye_at = time.time()
            return self._send(204, b"")
        if not self._authed():
            return self._json({"error": "unauthorized"}, 401)
        STATE.last_ping = time.time()
        STATE.bye_at = None
        body = self._body()
        try:
            if path == "/api/ping":
                return self._json({"ok": True})
            if path == "/api/job":
                job = start_job(str(body.get("kind")), body.get("params") or {})
                return self._json(job.snapshot())
            if path.startswith("/api/job/") and path.endswith("/cancel"):
                job = STATE.jobs.get(path.split("/")[3])
                if job:
                    job.stop.set()
                return self._json({"ok": bool(job)})
            fn = POST_ROUTES.get(path)
            if fn is None:
                return self._json({"error": "not found"}, 404)
            return self._json(fn(body))
        except Exception as exc:  # noqa: BLE001
            errorlog.log(f"POST {path}", str(exc), exc)
            return self._json({"error": str(exc)}, 400)


def make_server(port: int = 0) -> ThreadingHTTPServer:
    global SERVER
    ThreadingHTTPServer.request_queue_size = 128  # el arranque lanza muchas peticiones a la vez
    SERVER = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    SERVER.daemon_threads = True
    return SERVER
