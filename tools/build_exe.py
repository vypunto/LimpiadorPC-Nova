"""Genera el icono y compila LimpiadorPC-Nova.exe con PyInstaller.

Uso:  py -3 tools/build_exe.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ICON = ROOT / "tools" / "nova.ico"


def make_icon() -> None:
    from PIL import Image, ImageDraw

    s = 256
    grad = Image.new("RGBA", (s, s))
    px = grad.load()
    stops = [(0.0, (94, 242, 214)), (0.55, (106, 168, 255)), (1.0, (167, 139, 250))]
    for y in range(s):
        for x in range(s):
            t = (x + y) / (2 * (s - 1))
            for (a, ca), (b, cb) in zip(stops, stops[1:]):
                if a <= t <= b:
                    k = (t - a) / (b - a)
                    px[x, y] = tuple(int(ca[i] + (cb[i] - ca[i]) * k) for i in range(3)) + (255,)
                    break

    def rounded(box, r):
        m = Image.new("L", (s, s), 0)
        ImageDraw.Draw(m).rounded_rectangle(box, r, fill=255)
        return m

    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    img.paste(grad, (0, 0), rounded((0, 0, s - 1, s - 1), 72))
    img.paste(Image.new("RGBA", (s, s), (5, 7, 11, 255)), (0, 0), rounded((56, 56, 200, 200), 40))
    img.paste(grad, (0, 0), rounded((96, 96, 160, 160), 16))
    img.save(ICON, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


def main() -> None:
    make_icon()
    sep = ";"
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", "LimpiadorPC-Nova", "--icon", str(ICON),
        "--add-data", f"{ROOT / 'ui'}{sep}ui", "--collect-submodules", "anthropic",
        "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build"), "--specpath", str(ROOT / "build"),
        str(ROOT / "limpiador.py"),
    ], check=True, cwd=ROOT)
    print("\nListo:", ROOT / "dist" / "LimpiadorPC-Nova.exe")


if __name__ == "__main__":
    main()
