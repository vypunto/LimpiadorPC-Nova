from __future__ import annotations

import hashlib
import os
import shutil
import threading
from pathlib import Path


SKIP_DIR_NAMES = {
    "$recycle.bin",
    "system volume information",
    "windows",
    "winsxs",
    "program files",
    "program files (x86)",
    "programdata",
    "appdata",
    "node_modules",
    ".git",
    ".cache",
    "__pycache__",
    "msocache",
    "recovery",
}


def format_size(num: float) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(max(0, num))
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def user_home() -> Path:
    return Path(os.path.expanduser("~"))


def downloads_dir() -> Path:
    return known_folder("Downloads")


def get_drives() -> list[tuple[str, int, int]]:
    drives: list[tuple[str, int, int]] = []
    for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        root = f"{letter}:\\"
        if not os.path.exists(root):
            continue
        try:
            usage = shutil.disk_usage(root)
            drives.append((f"{letter}:", usage.free, usage.total))
        except OSError:
            continue
    return drives


def should_skip_dir(name: str, aggressive: bool = False) -> bool:
    lower = name.lower()
    if lower in SKIP_DIR_NAMES:
        return True
    if aggressive and lower.startswith("."):
        return True
    return False


def iter_files(
    roots: list[Path],
    *,
    min_size: int = 0,
    extensions: set[str] | None = None,
    stop_event: threading.Event | None = None,
    skip_system: bool = True,
    progress_cb=None,
):
    """Yield (path, size) for files under roots."""
    seen: set[str] = set()
    count = 0
    for root in roots:
        if stop_event and stop_event.is_set():
            return
        if not root.exists():
            continue
        root_s = str(root)
        for dirpath, dirnames, filenames in os.walk(root_s, topdown=True, onerror=lambda _: None):
            if stop_event and stop_event.is_set():
                return
            # prune
            keep = []
            for d in dirnames:
                full = os.path.join(dirpath, d)
                try:
                    if os.path.islink(full):
                        continue
                except OSError:
                    continue
                if skip_system and should_skip_dir(d):
                    # Still allow walking user folders named oddly; skip known system
                    # but do not skip if root itself is under those (e.g. scanning AppData intentionally)
                    if Path(root_s).name.lower() not in {d.lower()} and d.lower() in SKIP_DIR_NAMES:
                        continue
                keep.append(d)
            dirnames[:] = keep

            for name in filenames:
                if stop_event and stop_event.is_set():
                    return
                fp = os.path.join(dirpath, name)
                try:
                    if os.path.islink(fp):
                        continue
                    st = os.stat(fp)
                except OSError:
                    continue
                if st.st_size < min_size:
                    continue
                if extensions is not None:
                    ext = os.path.splitext(name)[1].lower()
                    if ext not in extensions:
                        continue
                key = fp.lower()
                if key in seen:
                    continue
                seen.add(key)
                count += 1
                if progress_cb and count % 250 == 0:
                    progress_cb(count, fp)
                yield Path(fp), st.st_size


def quick_file_fingerprint(path: Path, size: int, chunk: int = 65536) -> str:
    """Fast fingerprint: size + hash of head/tail chunks."""
    h = hashlib.md5()
    h.update(str(size).encode())
    try:
        with path.open("rb") as f:
            head = f.read(chunk)
            h.update(head)
            if size > chunk * 2:
                f.seek(max(0, size - chunk))
                h.update(f.read(chunk))
            elif size > chunk:
                h.update(f.read())
    except OSError:
        return f"err-{size}-{path.name}"
    return h.hexdigest()


def full_md5(path: Path, chunk: int = 1024 * 1024, stop_event: threading.Event | None = None) -> str | None:
    h = hashlib.md5()
    try:
        with path.open("rb") as f:
            while True:
                if stop_event and stop_event.is_set():
                    return None
                data = f.read(chunk)
                if not data:
                    break
                h.update(data)
    except OSError:
        return None
    return h.hexdigest()


def open_in_explorer(path: Path) -> None:
    try:
        if path.is_dir():
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess_select(path)
    except OSError:
        pass


def subprocess_select(path: Path) -> None:
    import subprocess

    subprocess.run(["explorer", "/select,", str(path)], check=False)


# --- Procesos, permisos y borrado seguro -------------------------------------

import ctypes
import subprocess
import sys

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def run_hidden(*args, **kwargs):
    """subprocess.run sin abrir ventanas de consola (la app corre con pythonw)."""
    kwargs.setdefault("creationflags", NO_WINDOW)
    if "input" not in kwargs:
        kwargs.setdefault("stdin", subprocess.DEVNULL)
    return subprocess.run(*args, **kwargs)


def oem_encoding() -> str:
    try:
        return f"cp{ctypes.windll.kernel32.GetOEMCP()}"
    except Exception:  # noqa: BLE001
        return "cp850"


def decode_console(data: bytes) -> str:
    """sfc/DISM/chkdsk escriben en OEM y a veces en UTF-16 con bytes nulos."""
    if not data:
        return ""
    if data.count(b"\x00") > len(data) // 4:
        try:
            return data.decode("utf-16-le", errors="replace")
        except UnicodeDecodeError:
            data = data.replace(b"\x00", b"")
    return data.replace(b"\x00", b"").decode(oem_encoding(), errors="replace")


def run_ps(script: str, timeout: int = 60) -> tuple[int, str, str]:
    """Ejecuta PowerShell y devuelve (código, stdout, stderr)."""
    wrapped = "[Console]::OutputEncoding=[Text.Encoding]::UTF8;$ProgressPreference='SilentlyContinue';" + script
    try:
        proc = run_hidden(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", wrapped],
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return -1, "", str(exc)
    out = proc.stdout.decode("utf-8", errors="replace")
    err = proc.stderr.decode("utf-8", errors="replace")
    return proc.returncode, out, err


def run_ps_json(script: str, timeout: int = 60):
    import json

    code, out, _err = run_ps(script + " | ConvertTo-Json -Depth 4 -Compress", timeout=timeout)
    out = out.strip()
    if not out:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:  # noqa: BLE001
        return False


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_command(*args: str) -> tuple[str, str]:
    """(ejecutable, argumentos) para volver a lanzar esta app, en .exe o con Python."""
    extra = " ".join(args)
    if is_frozen():
        return sys.executable, extra
    exe = Path(sys.executable)
    if exe.with_name("pythonw.exe").exists():
        exe = exe.with_name("pythonw.exe")
    script = Path(__file__).resolve().parents[1] / "limpiador.py"
    return str(exe), f'"{script}" {extra}'.strip()


def relaunch_as_admin(script: Path) -> bool:
    if is_frozen():
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, None, None, 1)
        return rc > 32
    exe = Path(sys.executable)
    pyw = exe.with_name("pythonw.exe")
    if pyw.exists():
        exe = pyw
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", str(exe), f'"{script}"', str(script.parent), 1)
    return rc > 32


class _SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("wFunc", ctypes.c_uint),
        ("pFrom", ctypes.c_wchar_p),
        ("pTo", ctypes.c_wchar_p),
        ("fFlags", ctypes.c_ushort),
        ("fAnyOperationsAborted", ctypes.c_int),
        ("hNameMappings", ctypes.c_void_p),
        ("lpszProgressTitle", ctypes.c_wchar_p),
    ]


_FO_DELETE = 3
_FOF_SILENT = 0x0004
_FOF_NOCONFIRMATION = 0x0010
_FOF_ALLOWUNDO = 0x0040
_FOF_NOERRORUI = 0x0400
_FOF_WANTNUKEWARNING = 0x4000


def has_recycle_bin(path: Path) -> bool:
    """Solo discos fijos tienen Papelera; en USB o red Windows borraría para siempre."""
    drive = str(path.resolve())[:3]
    return ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(drive)) == 3  # DRIVE_FIXED


def send_to_recycle(path: Path) -> bool:
    """Mueve a la Papelera (recuperable). Nunca borra de forma permanente."""
    if not path.exists() or not has_recycle_bin(path):
        return False
    op = _SHFILEOPSTRUCTW()
    op.wFunc = _FO_DELETE
    op.pFrom = str(path.resolve()) + "\0\0"
    op.fFlags = _FOF_ALLOWUNDO | _FOF_NOCONFIRMATION | _FOF_SILENT | _FOF_NOERRORUI | _FOF_WANTNUKEWARNING
    rc = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    return rc == 0 and not op.fAnyOperationsAborted and not path.exists()


PROTECTED_ROOTS = [
    Path(os.environ.get("SystemRoot", r"C:\Windows")),
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
    Path(os.environ.get("ProgramData", r"C:\ProgramData")),
]


def is_protected(path: Path) -> bool:
    try:
        rp = path.resolve()
    except OSError:
        return True
    if rp.parent == rp:  # raíz de disco
        return True
    if rp == user_home().resolve():
        return True
    for root in PROTECTED_ROOTS:
        try:
            rp.relative_to(root.resolve())
            return True
        except (ValueError, OSError):
            continue
    return False


# --- Carpetas y unidades reales de este PC ---------------------------------

# Nombres internos de Windows de las carpetas de usuario (pueden estar en OneDrive u otro disco)
KNOWN_FOLDERS = {
    "Desktop": "Desktop",
    "Documents": "Personal",
    "Downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
    "Pictures": "My Pictures",
    "Videos": "My Video",
    "Music": "My Music",
}


def known_folder(name: str) -> Path:
    """Ruta real de Escritorio, Documentos, Descargas… aunque estén movidas a OneDrive o a otro disco."""
    import winreg

    reg = KNOWN_FOLDERS.get(name, name)
    for sub in (r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub) as key:
                val, _ = winreg.QueryValueEx(key, reg)
            p = Path(os.path.expandvars(str(val)))
            if p.exists():
                return p
        except OSError:
            continue
    return user_home() / name


def volume_label(root: str) -> str:
    buf = ctypes.create_unicode_buffer(261)
    ok = ctypes.windll.kernel32.GetVolumeInformationW(ctypes.c_wchar_p(root), buf, 261, None, None, None, None, 0)
    return buf.value if ok else ""


def google_drive_letters() -> list[str]:
    """Unidades montadas por Google Drive para escritorio (se reconocen por su etiqueta, no por la letra)."""
    out = []
    for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
        root = f"{letter}:\\"
        if os.path.exists(root) and "google drive" in volume_label(root).lower():
            out.append(f"{letter}:")
    return out
