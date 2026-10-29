"""Prueba automática de Limpiador PC Nova (solo operaciones seguras: no borra nada tuyo).

Uso:  py -3 tools/prueba.py
Arranca el motor, comprueba cada función y las protecciones, y lo cierra al terminar.
"""
import json, os, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
proc = subprocess.Popen([sys.executable, str(ROOT / "limpiador.py"), "--no-window"], stdout=subprocess.PIPE, text=True, cwd=ROOT)
_url = proc.stdout.readline().strip()
PORT, KEY = _url.split(":")[2].split("/")[0], _url.split("k=")[1]
BASE = f"http://127.0.0.1:{PORT}"
results = []


def call(path, body=None):
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={"X-Nova-Key": KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())


def job(kind, params=None, timeout=600):
    j = call("/api/job", {"kind": kind, "params": params or {}})
    t0 = time.time()
    while j["state"] == "running" and time.time() - t0 < timeout:
        time.sleep(1)
        j = call("/api/job/" + j["id"])
    return j


def check(name, fn):
    t0 = time.time()
    try:
        info = fn()
        results.append(("OK", name, info, time.time() - t0))
    except Exception as exc:  # noqa: BLE001
        results.append(("FALLO", name, f"{type(exc).__name__}: {exc}", time.time() - t0))


def J(kind, summarize, params=None):
    def run():
        j = job(kind, params)
        if j["state"] != "done":
            raise RuntimeError(f"estado={j['state']} error={j['error']}")
        return summarize(j["result"])
    return run


# Lecturas directas
for p in ("/api/overview", "/api/metrics", "/api/processes", "/api/fixes", "/api/startup", "/api/autoclean", "/api/history", "/api/aiorg/config"):
    check("GET " + p, lambda p=p: f"{len(json.dumps(call(p)))} bytes")
# Trabajos de solo lectura
check("Salud", J("health", lambda r: f"{r['score']}/100, {len(r['report']['events'])} eventos"))
check("Diagnóstico", J("diagnosis", lambda r: " | ".join(p["title"][:40] for p in r["problems"])))
check("Análisis de limpieza", J("clean_scan", lambda r: f"{len(r['targets'])} categorías"))
check("Vista previa limpieza (Chrome)", lambda: f"{call('/api/clean/preview', {'key': 'chrome'}).get('count')} archivos")
check("Archivos grandes", J("large", lambda r: f"{len(r['files'])} archivos", {"min_mb": 500}))
check("Carpetas", J("folders", lambda r: f"{len(r['folders'])} carpetas"))
check("Sin usar", J("unused", lambda r: f"{len(r['files'])} archivos", {"days": 365, "min_mb": 50}))
check("Duplicados", J("dupes", lambda r: f"{len(r['groups'])} grupos", {"min_mb": 50}))
check("Buscar", J("search", lambda r: f"{len(r['hits'])} resultados", {"query": "factura"}))
check("Programas", J("programs", lambda r: f"{len(r['programs'])} programas"))
check("Defender", J("sec_status", lambda r: f"disponible={r['defender'].get('available')}, amenazas={len(r['threats'])}"))
check("Auditoría seguridad", J("sec_audit", lambda r: f"{len(r['findings'])} hallazgos"))
check("Basura desarrollo", J("devjunk", lambda r: f"{len(r['items'])} carpetas"))
check("Plan organizar Descargas", J("organize_plan", lambda r: f"{len(r['plan'])} archivos"))
for w in ("procs", "services", "tasks"):
    check(f"Segundo plano ({w})", J("bg", lambda r: f"{len(r['items'])} elementos", {"what": w}))
check("Organizador: plan local Descargas", J("aiorg", lambda r: f"{len(r['plan'])} movimientos", {"folder": str(Path.home() / "Downloads"), "mode": "local"}))
# Reparación inofensiva
check("Reparación: vaciar DNS (o rechazo sin admin)", lambda: (lambda j: f"código {j['result']['code']}" if j["state"] == "done" else ("rechazada sin permisos (correcto)" if "administrador" in j["error"] else (_ for _ in ()).throw(RuntimeError(j["error"]))))(job("fix", {"id": "dns"})))
# Protecciones
check("Bloqueo: papelera ruta no analizada", lambda: (lambda r: "bloqueado" if r["failed"] and not r["recycled"] else "¡NO BLOQUEADO!")(call("/api/files/recycle", {"paths": [r"C:\Windows\notepad.exe"]})))
check("Bloqueo: abrir web arbitraria", lambda: "bloqueado" if not call("/api/open", {"type": "url", "url": "https://example.com"})["ok"] else "¡NO BLOQUEADO!")
check("Bloqueo: organizar C:\\Windows", lambda: (lambda j: "bloqueado" if j["state"] == "error" else "¡NO BLOQUEADO!")(job("aiorg", {"folder": r"C:\Windows", "mode": "local"})))


# Organizador real (aplicar + deshacer) en carpeta de prueba propia
def organizer_roundtrip():
    d = Path(tempfile.mkdtemp(prefix="nova_org_"))
    names = ["IMG_20240315_101112.jpg", "factura_luz_2024.pdf", "envato_video_gen_Jan_16_2026_10_09_14.mp4", "notas.txt", "setup_app.exe"]
    old = time.time() - 10 * 86400
    for n in names:
        (d / n).write_bytes(b"x" * 100)
        os.utime(d / n, (old, old))
    j = job("aiorg", {"folder": str(d), "mode": "local", "rename": True})
    plan = j["result"]["plan"]
    out = call("/api/aiorg/apply", {"skip": []})
    after = sorted(str(p.relative_to(d)) for p in d.rglob("*") if p.is_file())
    und = call("/api/aiorg/undo", {})
    back = sorted(p.name for p in d.rglob("*") if p.is_file())
    dirs_left = [p for p in d.iterdir() if p.is_dir()]
    assert back == sorted(names), f"no se restauró: {back}"
    assert not dirs_left, f"quedaron carpetas: {dirs_left}"
    return f"plan {len(plan)}, movidos {out['moved']}, deshechos {und['restored']} · resultado: {after}"


check("Organizador: aplicar + deshacer (prueba)", organizer_roundtrip)
check("Registro de errores de la interfaz", lambda: "ok" if call("/api/clientlog", {"where": "prueba", "message": "error simulado por la prueba"})["ok"] else "fallo")
check("Informe técnico (anonimizado)", lambda: (lambda t: f"{len(t)} caracteres, error simulado incluido" if "error simulado" in t and os.environ.get("USERNAME", "zz").lower() not in t.lower().replace("<usuario>", "") else (_ for _ in ()).throw(RuntimeError("falta el error o aparece el usuario")))(call("/api/support", {})["text"]))

w = max(len(r[1]) for r in results)
for st, name, info, dt in results:
    print(f"{'✔' if st == 'OK' else '✘'} {name:<{w}}  {dt:5.1f}s  {info}")
ok = sum(r[0] == "OK" for r in results)
print(f"\n{ok}/{len(results)} correctas")
proc.terminate()
sys.exit(0 if ok == len(results) else 1)
