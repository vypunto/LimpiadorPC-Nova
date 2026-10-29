from __future__ import annotations

import os
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path

from .utils import run_hidden


def _dir_size(path: Path, stop_event: threading.Event | None = None, min_age: int = 0) -> int:
    import time

    cutoff = time.time() - min_age
    total = 0
    if not path.exists():
        return 0
    try:
        if path.is_file():
            return path.stat().st_size
    except OSError:
        return 0
    for root, dirs, files in os.walk(path, topdown=True, onerror=lambda _: None):
        if stop_event and stop_event.is_set():
            break
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d)) and not (min_age and _skip_dir(d))]
        for name in files:
            if stop_event and stop_event.is_set():
                break
            fp = os.path.join(root, name)
            try:
                if os.path.islink(fp):
                    continue
                st = os.stat(fp)
                if min_age and max(st.st_mtime, st.st_ctime) > cutoff:
                    continue
                total += st.st_size
            except OSError:
                continue
    return total


@dataclass
class CleanTarget:
    key: str
    title: str
    description: str
    paths: list[Path] = field(default_factory=list)
    size: int = 0
    selected: bool = True
    special: str | None = None
    group: str = "Sistema"
    admin: bool = False


CHROMIUM_CACHE_DIRS = (
    "Cache",
    "Code Cache",
    "GPUCache",
    "DawnCache",
    "DawnGraphiteCache",
    "DawnWebGPUCache",
)


def _chromium_paths(user_data: Path) -> list[Path]:
    """Cachés de todos los perfiles (Default, Profile 1, ...) de un navegador Chromium."""
    if not user_data.exists():
        return []
    paths: list[Path] = [user_data / "ShaderCache", user_data / "GrShaderCache"]
    try:
        profiles = [p for p in user_data.iterdir() if p.is_dir() and (p.name == "Default" or p.name.startswith("Profile "))]
    except OSError:
        profiles = []
    for prof in profiles:
        paths.extend(prof / d for d in CHROMIUM_CACHE_DIRS)
    return paths


def build_targets() -> list[CleanTarget]:
    home = Path(os.path.expanduser("~"))
    local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
    locallow = home / "AppData" / "LocalLow"
    roaming = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
    temp = Path(os.environ.get("TEMP", local / "Temp"))
    windir = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    progdata = Path(os.environ.get("ProgramData", r"C:\ProgramData"))

    firefox_profiles = local / "Mozilla" / "Firefox" / "Profiles"
    targets = [
        # --- Sistema ---
        CleanTarget("temp_user", "Temporales de usuario", "Carpeta TEMP de tu sesión (solo archivos de más de 24 h).", [temp]),
        CleanTarget("temp_win", "Temporales de Windows", r"C:\Windows\Temp.", [windir / "Temp"], admin=True),
        CleanTarget("recycle", "Papelera de reciclaje", "Borra para siempre lo que haya en la papelera (incluidos duplicados que hayas enviado).", special="recycle", selected=False),
        CleanTarget(
            "thumbnails",
            "Caché de miniaturas e iconos",
            "Vistas previas del Explorador; se regeneran solas.",
            [local / "Microsoft" / "Windows" / "Explorer"],
        ),
        CleanTarget(
            "wer",
            "Informes de errores (WER)",
            "Informes de fallos ya enviados o en cola.",
            [
                local / "Microsoft" / "Windows" / "WER",
                progdata / "Microsoft" / "Windows" / "WER" / "ReportArchive",
                progdata / "Microsoft" / "Windows" / "WER" / "ReportQueue",
            ],
        ),
        CleanTarget(
            "crashdumps",
            "Volcados de memoria",
            "CrashDumps y Minidump. Exporta el informe de Salud antes si investigas pantallas azules.",
            [local / "CrashDumps", windir / "Minidump"],
            selected=False,
        ),
        CleanTarget(
            "wu_download",
            "Descargas de Windows Update",
            r"Instaladores ya aplicados (SoftwareDistribution\Download).",
            [windir / "SoftwareDistribution" / "Download"],
            admin=True,
        ),
        CleanTarget(
            "delivery",
            "Optimización de distribución",
            "Caché de actualizaciones compartida con otros PCs.",
            [windir / "ServiceProfiles" / "NetworkService" / "AppData" / "Local" / "Microsoft" / "Windows" / "DeliveryOptimization" / "Cache"],
            admin=True,
        ),
        CleanTarget(
            "recent",
            "Lista de recientes",
            "Solo accesos directos de 'Recientes'; no borra tus archivos.",
            [roaming / "Microsoft" / "Windows" / "Recent"],
            selected=False,
        ),
        # --- Navegadores ---
        CleanTarget("chrome", "Google Chrome", "Caché de todos los perfiles. Cierra Chrome antes.",
                    _chromium_paths(local / "Google" / "Chrome" / "User Data"), group="Navegadores"),
        CleanTarget("edge", "Microsoft Edge", "Caché de todos los perfiles. Cierra Edge antes.",
                    _chromium_paths(local / "Microsoft" / "Edge" / "User Data"), group="Navegadores"),
        CleanTarget("brave", "Brave", "Caché de todos los perfiles.",
                    _chromium_paths(local / "BraveSoftware" / "Brave-Browser" / "User Data"), group="Navegadores"),
        CleanTarget("opera", "Opera / Opera GX", "Caché del navegador.",
                    [local / "Opera Software" / n / "Cache" for n in ("Opera Stable", "Opera GX Stable")], group="Navegadores"),
        CleanTarget("firefox", "Firefox", "Caché de todos los perfiles. Cierra Firefox antes.",
                    list(firefox_profiles.glob("*/cache2")) if firefox_profiles.exists() else [], group="Navegadores"),
        # --- Apps y GPU ---
        CleanTarget("shader", "Caché de sombreadores DirectX", "Se reconstruye al abrir juegos.",
                    [local / "D3DSCache"], group="Apps y juegos"),
        CleanTarget("nvidia", "Caché NVIDIA", "DXCache / GLCache del driver.",
                    [local / "NVIDIA" / "DXCache", local / "NVIDIA" / "GLCache", locallow / "NVIDIA" / "PerDriverVersion" / "DXCache"],
                    group="Apps y juegos"),
        CleanTarget("amd", "Caché AMD", "Cachés de sombreadores del driver Radeon.",
                    [local / "AMD" / n for n in ("DxCache", "DxcCache", "GLCache", "VkCache")], group="Apps y juegos"),
        CleanTarget("discord", "Discord", "Caché de imágenes y código. Cierra Discord antes.",
                    [roaming / "discord" / n for n in ("Cache", "Code Cache", "GPUCache")], group="Apps y juegos"),
        CleanTarget("spotify", "Spotify", "Canciones en caché (no las descargadas).",
                    [local / "Spotify" / "Data"], group="Apps y juegos", selected=False),
        CleanTarget("steam", "Steam (navegador interno)", "Caché web de la tienda Steam.",
                    [local / "Steam" / "htmlcache"], group="Apps y juegos"),
        # --- Desarrollo ---
        CleanTarget("npm", "Caché de npm", "Paquetes descargados por Node/npm.",
                    [Path(os.environ.get("npm_config_cache", local / "npm-cache"))], group="Desarrollo"),
        CleanTarget("pip", "Caché de pip", "Wheels descargados por pip.", [local / "pip" / "Cache"], group="Desarrollo"),
        CleanTarget("yarn", "Caché de Yarn", "Paquetes descargados por Yarn.", [local / "Yarn" / "Cache"], group="Desarrollo"),
        CleanTarget("gobuild", "Caché de Go", "Artefactos de compilación de Go.", [local / "go-build"], group="Desarrollo"),
        CleanTarget("nuget", "Paquetes NuGet", "Se vuelven a descargar al compilar.",
                    [home / ".nuget" / "packages"], group="Desarrollo", selected=False),
    ]
    filtered: list[CleanTarget] = []
    seen: set[str] = set()
    for t in targets:
        if t.special:
            filtered.append(t)
            continue
        existing = []
        for p in t.paths:
            k = str(p).lower()
            try:
                ok = p.exists()
            except OSError:
                ok = False
            if k not in seen and ok:
                seen.add(k)
                existing.append(p)
        if existing:
            t.paths = existing
            filtered.append(t)
    return filtered


def measure_target(t: CleanTarget, stop_event: threading.Event | None = None) -> int:
    if t.special == "recycle":
        size = 0
        for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            bin_path = Path(f"{letter}:\\$Recycle.Bin")
            if bin_path.exists():
                size += _dir_size(bin_path, stop_event)
        return size
    size = 0
    for p in t.paths:
        if t.key == "thumbnails":
            for pattern in ("thumbcache_*.db", "iconcache_*.db"):
                for fp in p.glob(pattern):
                    try:
                        size += fp.stat().st_size
                    except OSError:
                        pass
        else:
            size += _dir_size(p, stop_event, TEMP_MIN_AGE if t.key in ("temp_user", "temp_win") else 0)
    return size


TEMP_MIN_AGE = 24 * 3600


def _skip_dir(name: str) -> bool:
    """Carpetas de programas en ejecución que viven en TEMP."""
    import sys

    low = name.lower()
    me = os.path.basename(getattr(sys, "_MEIPASS", "")).lower()
    return low.startswith("_mei") or (me and low == me)


def safe_delete_path(path: Path, min_age: int = 0) -> tuple[int, int]:
    freed = 0
    errors = 0
    if not path.exists():
        return 0, 0
    if path.is_file() or path.is_symlink():
        try:
            size = path.stat().st_size
            path.unlink(missing_ok=True)
            return size, 0
        except OSError:
            return 0, 1
    import time

    cutoff = time.time() - min_age
    for root, dirs, files in os.walk(path, topdown=False, onerror=lambda _: None):
        rel = os.path.relpath(root, path)
        if min_age and any(_skip_dir(part) for part in rel.split(os.sep)):
            continue
        for name in files:
            fp = Path(root) / name
            try:
                st = fp.stat()
                if min_age and max(st.st_mtime, st.st_ctime) > cutoff:
                    continue
                size = st.st_size
                fp.unlink(missing_ok=True)
                freed += size
            except OSError:
                errors += 1
        for name in dirs:
            if min_age and _skip_dir(name):
                continue
            dp = Path(root) / name
            try:
                dp.rmdir()  # solo si quedó vacía
            except OSError:
                pass
    return freed, errors


def empty_recycle_bin() -> tuple[int, int]:
    freed_estimate = 0
    for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        bin_path = Path(f"{letter}:\\$Recycle.Bin")
        if bin_path.exists():
            freed_estimate += _dir_size(bin_path)
    try:
        run_hidden(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Clear-RecycleBin -Force -ErrorAction SilentlyContinue",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return freed_estimate, 0
    except (OSError, subprocess.TimeoutExpired):
        return 0, 1


def clean_explorer_thumbs(paths: list[Path]) -> tuple[int, int]:
    freed = 0
    errors = 0
    for base in paths:
        if not base.exists():
            continue
        for pattern in ("thumbcache_*.db", "iconcache_*.db"):
            for fp in base.glob(pattern):
                try:
                    size = fp.stat().st_size
                    fp.unlink(missing_ok=True)
                    freed += size
                except OSError:
                    errors += 1
    return freed, errors


def clean_target(t: CleanTarget) -> tuple[int, int]:
    if t.special == "recycle":
        return empty_recycle_bin()
    if t.key == "thumbnails":
        return clean_explorer_thumbs(t.paths)
    freed = 0
    errors = 0
    for p in t.paths:
        f, e = safe_delete_path(p, TEMP_MIN_AGE if t.key in ("temp_user", "temp_win") else 0)
        freed += f
        errors += e
        if t.key in ("temp_user", "temp_win"):
            try:
                p.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
    return freed, errors


def preview_target(t: CleanTarget, limit: int = 40) -> dict:
    """Lista los archivos que se borrarían (mismas reglas que clean_target), sin tocar nada."""
    import time

    if t.special == "recycle":
        return {"count": None, "total": measure_target(t), "files": [], "note": "Contenido de la Papelera de todos los discos."}
    min_age = TEMP_MIN_AGE if t.key in ("temp_user", "temp_win") else 0
    cutoff = time.time() - min_age
    files: list[tuple[int, str, float]] = []
    count = total = 0
    for base in t.paths:
        if t.key == "thumbnails":
            cands = [(str(fp), fp.stat()) for pat in ("thumbcache_*.db", "iconcache_*.db") for fp in base.glob(pat)]
        else:
            cands = []
            for root, dirs, names in os.walk(base, onerror=lambda _: None):
                dirs[:] = [d for d in dirs if not (min_age and _skip_dir(d))]
                for n in names:
                    fp = os.path.join(root, n)
                    try:
                        cands.append((fp, os.stat(fp)))
                    except OSError:
                        pass
        for fp, st in cands:
            if min_age and max(st.st_mtime, st.st_ctime) > cutoff:
                continue
            count += 1
            total += st.st_size
            files.append((st.st_size, fp, st.st_mtime))
    files.sort(reverse=True)
    return {"count": count, "total": total, "files": [{"path": p, "size": s, "mtime": m} for s, p, m in files[:limit]],
            "note": "Solo archivos con más de 24 h; los que estén en uso se saltan." if min_age else ""}
