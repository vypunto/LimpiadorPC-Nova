"""Organizador de carpetas: propone un plan (con IA o con reglas locales) que el usuario revisa antes de aplicar.

Garantías: solo MUEVE archivos dentro de la carpeta elegida (nunca borra), no entra en
proyectos de código ni en carpetas de sistema, salta archivos recientes y guarda un
registro para deshacer. A la IA solo se le envían nombres, tamaños y fechas: nunca el
contenido de los archivos.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import time
from datetime import datetime
from pathlib import Path

from .history import DATA_DIR, record
from .unused import category_of
from .utils import is_protected, run_ps, user_home

CONFIG = DATA_DIR / "config.json"
UNDO = DATA_DIR / "organizador_deshacer.json"
MODEL = "claude-opus-5-5"
MAX_FILES = 2000
BATCH = 250
PROJECT_MARKERS = {".git", "package.json", "pyproject.toml", "requirements.txt", "cargo.toml", "go.mod", "pom.xml",
                   "build.gradle", "composer.json", "gemfile", ".sln", ".csproj", "node_modules", ".venv", "venv", ".vscode", ".idea"}
SKIP_NAMES = {"desktop.ini", "thumbs.db", ".ds_store"}
PARTIAL = {".crdownload", ".part", ".tmp", ".download", ".partial"}


# --- configuración de la clave (solo en este PC) ---------------------------

def _load_cfg() -> dict:
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def api_key() -> str:
    return os.environ.get("ANTHROPIC_API_KEY") or _load_cfg().get("anthropic_api_key", "")


def save_key(key: str) -> tuple[bool, str]:
    key = key.strip()
    if key and not key.startswith("sk-ant-"):
        return False, "La clave debe empezar por sk-ant-"
    cfg = _load_cfg()
    if key:
        cfg["anthropic_api_key"] = key
    else:
        cfg.pop("anthropic_api_key", None)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg), encoding="utf-8")
    return True, "Clave guardada en este equipo." if key else "Clave eliminada."


def pick_folder() -> str:
    code, out, _ = run_ps(
        "Add-Type -AssemblyName System.Windows.Forms;"
        "$f=New-Object System.Windows.Forms.Form -Property @{TopMost=$true};"
        "$d=New-Object System.Windows.Forms.FolderBrowserDialog;$d.Description='Elige la carpeta a organizar';"
        "if($d.ShowDialog($f) -eq 'OK'){$d.SelectedPath}", timeout=600)
    return out.strip() if code == 0 else ""


# --- análisis --------------------------------------------------------------

def check_folder(folder: Path) -> str | None:
    """Devuelve un motivo si la carpeta no se debe organizar."""
    if not folder.is_dir():
        return "La carpeta no existe."
    if is_protected(folder):
        return "Carpeta del sistema o raíz de disco: no se organiza para no romper nada."
    if folder.resolve() == user_home().resolve() or folder.resolve() == (user_home() / "AppData").resolve():
        return "Elige una carpeta concreta (Descargas, Documentos, Escritorio…), no tu carpeta de usuario entera."
    if _is_project(folder, strict=False):
        return "Es un proyecto de programación: moverle archivos lo rompería."
    return None


def _is_project(d: Path, strict: bool = True) -> bool:
    """strict (subcarpetas): basta un marcador. Raíz: .git o al menos dos marcadores."""
    try:
        hits = [c.name.lower() for c in d.iterdir() if c.name.lower() in PROJECT_MARKERS or c.suffix.lower() in (".sln", ".csproj")]
    except OSError:
        return True
    return bool(hits) if strict else (".git" in hits or len(hits) >= 2)


def scan(folder: Path, depth: int = 3) -> tuple[list[dict], list[str]]:
    """Archivos movibles + carpetas que se dejan intactas (proyectos, ocultas, apps)."""
    now = time.time()
    files, kept = [], []
    root_depth = len(folder.parts)
    for dirpath, dirnames, filenames in os.walk(folder):
        d = Path(dirpath)
        keep = []
        for name in dirnames:
            sub = d / name
            if name.startswith(".") or name.startswith("$") or sub.is_symlink() or _is_project(sub):
                kept.append(str(sub.relative_to(folder)))
                continue
            if len(sub.parts) - root_depth < depth:
                keep.append(name)
        dirnames[:] = keep
        for name in filenames:
            p = d / name
            if name.lower() in SKIP_NAMES or name.lower() in PROJECT_MARKERS or name.startswith("~$") or p.suffix.lower() in PARTIAL:
                continue
            try:
                st = p.stat()
            except OSError:
                continue
            if now - st.st_mtime < 3600:  # en uso o recién descargado
                continue
            files.append({"rel": str(p.relative_to(folder)), "size": st.st_size, "mtime": st.st_mtime})
            if len(files) >= MAX_FILES:
                return files, kept
    return files, kept


# --- plan con reglas locales ------------------------------------------------

RULES = [
    (re.compile(r"captura|screenshot|screen shot|recorte", re.I), "Imágenes/Capturas de pantalla"),
    (re.compile(r"factura|invoice|recibo|receipt|ticket|presupuesto", re.I), "Documentos/Facturas y recibos"),
    (re.compile(r"\bcv\b|curriculum|currículum|resume", re.I), "Documentos/Personal"),
    (re.compile(r"contrato|contract|nómina|nomina|payslip", re.I), "Documentos/Contratos y nóminas"),
    (re.compile(r"whatsapp", re.I), "Imágenes/WhatsApp"),
]


MONTHS = {m: i for i, ms in enumerate([("jan", "ene", "enero", "january"), ("feb", "febrero", "february"), ("mar", "marzo", "march"),
                                     ("apr", "abr", "abril", "april"), ("may", "mayo"), ("jun", "junio", "june"), ("jul", "julio", "july"),
                                     ("aug", "ago", "agosto", "august"), ("sep", "sept", "septiembre", "september"), ("oct", "octubre", "october"),
                                     ("nov", "noviembre", "november"), ("dec", "dic", "diciembre", "december")], 1) for m in ms}
_MON = r"(" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")"
DATE_PATTERNS = [
    # Jan_16_2026 / Nov 07 2025
    ("mdy", re.compile(r"(?<![a-z])" + _MON + r"[ _.\-]+(\d{1,2})[ _,.\-]+(20\d{2}|19\d{2})(?!\d)", re.I)),
    # 14 jul 2026 / 14-julio-2026
    ("dmy_txt", re.compile(r"(?<!\d)(\d{1,2})[ _.\-]+(?:de[ _])?" + _MON + r"[a-z]*[ _,.\-]+(?:de[ _])?(20\d{2}|19\d{2})(?!\d)", re.I)),
    # 2024-03-15 / 20240315 / 2024_03_15
    ("ymd", re.compile(r"(?<!\d)(20\d{2}|19\d{2})([-_.]?)(0[1-9]|1[0-2])\2(0[1-9]|[12]\d|3[01])(?!\d)")),
    # 15-03-2024
    ("dmy", re.compile(r"(?<!\d)(0[1-9]|[12]\d|3[01])[-_.](0[1-9]|1[0-2])[-_.](20\d{2})(?!\d)")),
]
TIME_RXS = [
    re.compile(r"(?<!\d)([01]?\d|2[0-3])[.:_\- ]([0-5]\d)[.:_\- ]([0-5]\d)(?!\d)"),
    re.compile(r"(?<!\d)([01]\d|2[0-3])([0-5]\d)([0-5]\d)(?!\d)"),
]
CAMERA = re.compile(r"^(img|dsc|dscn|dscf|pxl|vid|mvimg|photo|gopr|dji|_?dsc)[_\-]?\d", re.I)
NOISE = [
    re.compile(r"^screenshot[_-]?", re.I),
    re.compile(r"\b(whatsapp (image|video|audio)|imagen de whatsapp|video de whatsapp)\b", re.I),
    re.compile(r"\s*-\s*copia$|^copia de\s+|^copy of\s+|\s+copy$", re.I),
    re.compile(r"\b(at|a las|utc)\b", re.I),
]


def _date_from_name(stem: str) -> tuple[str | None, str]:
    for kind, rx in DATE_PATTERNS:
        m = rx.search(stem)
        if not m:
            continue
        g = m.groups()
        if kind == "mdy":
            y, mo, d = g[2], MONTHS[g[0].lower()], int(g[1])
        elif kind == "dmy_txt":
            y, mo, d = g[2], MONTHS[g[1].lower()], int(g[0])
        elif kind == "ymd":
            y, mo, d = g[0], int(g[2]), int(g[3])
        else:
            y, mo, d = g[2], int(g[1]), int(g[0])
        if not 1 <= d <= 31:
            continue
        return f"{y}-{int(mo):02d}-{d:02d}", stem[:m.start()] + " " + stem[m.end():]
    return None, stem


def suggest_name(name: str, mtime: float, category: str) -> tuple[str, str | None]:
    """(nombre limpio, fecha AAAA-MM-DD si se conoce). Fecha delante solo si viene en el nombre o es foto de cámara/captura."""
    p = Path(name)
    stem, ext = p.stem, p.suffix.lower()
    dup = re.search(r"\s*\((\d+)\)$", stem)  # se conserva (1), (2)… para no confundir
    if dup:
        stem = stem[:dup.start()]
    date, rest = _date_from_name(stem)
    is_capture = bool(re.search(r"captura|screenshot|recorte", stem, re.I))
    is_camera = bool(CAMERA.search(stem))
    hhmmss = ""
    if date:
        for trx in TIME_RXS:
            t = trx.search(rest)
            if t:
                hhmmss = f"{int(t.group(1)):02d}.{t.group(2)}.{t.group(3)}"
                rest = rest[:t.start()] + " " + rest[t.end():]
                break
    for rx in NOISE:
        rest = rx.sub(" ", rest)
    rest = re.sub(r"_+", " ", rest)
    rest = re.sub(r"(?<=[a-záéíóúñ])\.(?=[a-záéíóúñ])", " ", rest, flags=re.I)
    rest = re.sub(r"(\s*[-,]\s*){2,}", " - ", rest)
    rest = re.sub(r"\s{2,}", " ", rest).strip(" -._,")
    if is_capture:
        rest = "Captura"
    elif re.fullmatch(r"[\W\d_]*", rest or "") and not is_camera:
        rest = rest.strip()
    if not date and (is_camera or is_capture):
        date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
    label = rest
    parts = [x for x in (date, hhmmss, label) if x]
    new = " ".join(parts) if parts else p.stem
    if dup:
        new += f" ({dup.group(1)})"
    return new + ext, date


def local_plan(files: list[dict], rename: bool = True) -> list[dict]:
    plan = []
    for f in files:
        name = Path(f["rel"]).name
        cat = category_of(Path(name))
        new_name, date = suggest_name(name, f["mtime"], cat) if rename else (name, None)
        target = next((t for rx, t in RULES if rx.search(name)), None)
        if not target:
            if cat == "Otros":
                continue
            target = cat
            if cat in ("Imágenes", "Vídeos"):
                target += "/" + (date[:4] if date else str(datetime.fromtimestamp(f["mtime"]).year))
        plan.append({**f, "target": target, "why": "Regla local", "new_name": new_name})
    return plan


# --- plan con IA (Claude) ---------------------------------------------------

SCHEMA = {
    "type": "object",
    "properties": {
        "assignments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"i": {"type": "integer"}, "folder": {"type": "string"}},
                "required": ["i", "folder"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["assignments"],
    "additionalProperties": False,
}

SYSTEM = (
    "Organizas carpetas de un PC con Windows. Recibes una lista numerada de archivos (ruta relativa, tamaño, fecha) "
    "y devuelves para cada uno la subcarpeta de destino, relativa a la carpeta raíz, con barras '/'. "
    "Crea una estructura clara y estable en español, de 1 a 3 niveles (p. ej. 'Documentos/Facturas/2024', "
    "'Imágenes/Viajes', 'Instaladores'). Agrupa por tema o proyecto cuando el nombre lo indique y por tipo en otro caso. "
    "Reutiliza siempre las carpetas ya creadas que se te indiquen. Si un archivo ya está bien ubicado, devuelve su carpeta "
    "actual. Si no estás seguro, devuelve '' (se deja donde está)."
)


def ai_plan(files: list[dict], instructions: str, progress=None, stop=None) -> list[dict]:
    import anthropic

    key = api_key()
    if not key:
        raise PermissionError("Configura tu clave de API de Anthropic para usar la IA.")
    client = anthropic.Anthropic(api_key=key)
    folders: set[str] = set()
    plan: list[dict] = []
    for start in range(0, len(files), BATCH):
        if stop is not None and stop.is_set():
            break
        chunk = files[start:start + BATCH]
        if progress:
            progress(start / len(files), f"La IA está clasificando {start + 1}-{start + len(chunk)} de {len(files)}…")
        listing = "\n".join(
            f"{i}\t{f['rel']}\t{f['size'] // 1024} KB\t{datetime.fromtimestamp(f['mtime']):%Y-%m-%d}" for i, f in enumerate(chunk)
        )
        user = (f"Carpetas ya creadas: {', '.join(sorted(folders)) or '(ninguna)'}\n"
                + (f"Preferencias del usuario: {instructions.strip()}\n" if instructions.strip() else "")
                + f"\nArchivos:\n{listing}")
        try:
            resp = client.beta.messages.create(
                model=MODEL,
                max_tokens=16000,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                system=SYSTEM,
                output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
                messages=[{"role": "user", "content": user}],
            )
        except anthropic.AuthenticationError:
            raise PermissionError("La clave de API no es válida.") from None
        except anthropic.RateLimitError:
            raise RuntimeError("Límite de uso de la API alcanzado. Inténtalo en unos minutos.") from None
        except anthropic.APIConnectionError:
            raise RuntimeError("Sin conexión con la API de Anthropic.") from None
        except anthropic.APIStatusError as exc:
            raise RuntimeError(f"Error de la API ({exc.status_code}): {exc.message}") from None
        if resp.stop_reason == "refusal":
            raise RuntimeError("La IA rechazó clasificar este lote.")
        text = next((b.text for b in resp.content if b.type == "text"), "{}")
        try:
            data = json.loads(text).get("assignments", [])
        except ValueError:
            continue
        for a in data:
            i, target = a.get("i"), _clean_target(a.get("folder", ""))
            if not isinstance(i, int) or not 0 <= i < len(chunk) or not target:
                continue
            folders.add(target)
            plan.append({**chunk[i], "target": target, "why": "IA"})
    return plan


def _clean_target(t: str) -> str:
    parts = []
    for seg in str(t).replace("\\", "/").split("/"):
        seg = re.sub(r'[<>:"|?*\x00-\x1f]', "", seg).strip(" .")
        if seg and seg not in (".", ".."):
            parts.append(seg[:60])
    return "/".join(parts[:3])


# --- aplicar / deshacer -----------------------------------------------------

def finalize(folder: Path, plan: list[dict]) -> list[dict]:
    """Calcula destinos finales y descarta los que no cambian de sitio."""
    out = []
    taken: set[str] = set()  # nombres ya asignados en el plan (evita choques entre archivos)
    for p in plan:
        src = folder / p["rel"]
        name = p.get("new_name") or src.name
        dst = folder / p["target"] / name
        n = 2
        while str(dst).lower() in taken or (dst.exists() and dst.resolve() != src.resolve()):
            dst = dst.with_name(f"{Path(name).stem} ({n}){Path(name).suffix}")
            n += 1
        if dst.resolve() == src.resolve():
            continue
        taken.add(str(dst).lower())
        out.append({**p, "dst": str(dst.relative_to(folder)), "new_name": dst.name, "renamed": dst.name != src.name})
    return out


def apply(folder: Path, plan: list[dict], skip_targets: set[str]) -> dict:
    base = folder.resolve()
    moved, failed = [], 0
    for p in plan:
        if p["target"] in skip_targets:
            continue
        src, dst = (folder / p["rel"]).resolve(), (folder / p["dst"]).resolve()
        if base not in src.parents or base not in dst.parents or not src.is_file():
            failed += 1
            continue
        final, n = dst, 1
        while final.exists():
            final = dst.with_name(f"{dst.stem} ({n}){dst.suffix}")
            n += 1
        try:
            final.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(final))
            moved.append([str(src), str(final)])
        except OSError:
            failed += 1
    if moved:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        UNDO.write_text(json.dumps({"base": str(base), "moves": moved}, ensure_ascii=False), encoding="utf-8")
        record("Organizador", f"{len(moved)} archivos ordenados en {base}")
    return {"moved": len(moved), "failed": failed}


def undo() -> dict:
    try:
        data = json.loads(UNDO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"restored": 0, "message": "No hay ninguna organización que deshacer."}
    restored = 0
    for src, dst in reversed(data["moves"]):
        s, d = Path(src), Path(dst)
        if d.exists() and not s.exists():
            try:
                s.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(d), str(s))
                restored += 1
            except OSError:
                pass
    # quitar carpetas que quedaron vacías (solo las creadas por el organizador)
    for d in sorted({Path(dst).parent for _s, dst in data["moves"]}, key=lambda x: len(x.parts), reverse=True):
        while d.resolve() != Path(data["base"]) and d.exists():
            try:
                d.rmdir()
            except OSError:
                break
            d = d.parent
    UNDO.unlink(missing_ok=True)
    record("Deshacer organizador", f"{restored} archivos devueltos")
    return {"restored": restored, "message": f"{restored} archivos devueltos a su sitio original."}
