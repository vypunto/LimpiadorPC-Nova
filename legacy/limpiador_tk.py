#!/usr/bin/env python3
"""Limpiador PC Pro — mantenimiento, espacio y diagnóstico de caídas (Windows)."""

from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from core import __app_name__, __version__
from core.cleaner import CleanTarget, build_targets, clean_target, measure_target
from core.drive import default_scan_roots, get_drive_info
from core.duplicates import find_duplicates, flag_drive_local_pairs
from core.folders import top_folders
from core.health import build_health_report, maintenance_suggestions
from core.large_files import find_large_files
from core.programs import list_installed_programs
from core.report import export_html, export_txt, health_score
from core.search import search_files
from core.startup import disable_startup_hkcu, list_startup_run_entries
from core.utils import format_size, get_drives, open_in_explorer, user_home


class LimpiadorPro(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{__app_name__} {__version__}")
        self.geometry("980x700")
        self.minsize(860, 600)
        self.configure(bg="#0b1220")

        self.stop_event = threading.Event()
        self.busy = False
        self.health_report = None
        self.clean_targets: list[CleanTarget] = []
        self.clean_vars: dict[str, tk.BooleanVar] = {}

        self._style()
        self._build()
        self.after(150, self.refresh_header)
        self.after(400, self.run_health_scan)

    # --- style / chrome ---
    def _style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        bg, card, text, muted, accent = "#0b1220", "#152033", "#e8eef8", "#8fa3bf", "#2dd4bf"
        style.configure("TFrame", background=bg)
        style.configure("Card.TFrame", background=card)
        style.configure("TNotebook", background=bg, borderwidth=0)
        style.configure("TNotebook.Tab", background="#1a2740", foreground=text, padding=(14, 8))
        style.map("TNotebook.Tab", background=[("selected", card)], foreground=[("selected", accent)])
        style.configure("Title.TLabel", background=bg, foreground=text, font=("Segoe UI Semibold", 18))
        style.configure("Sub.TLabel", background=bg, foreground=muted, font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=card, foreground=text, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=card, foreground=muted, font=("Segoe UI", 9))
        style.configure("Score.TLabel", background=card, foreground=accent, font=("Segoe UI Semibold", 28))
        style.configure("Alert.TLabel", background=card, foreground="#fbbf24", font=("Segoe UI", 10))
        style.configure("Bad.TLabel", background=card, foreground="#f87171", font=("Segoe UI", 10))
        style.configure("Accent.TButton", font=("Segoe UI Semibold", 10), padding=(12, 7))
        style.configure("TCheckbutton", background=card, foreground=text)
        style.map("TCheckbutton", background=[("active", card)])

    def _build(self) -> None:
        head = ttk.Frame(self)
        head.pack(fill="x", padx=16, pady=(12, 4))
        ttk.Label(head, text=__app_name__, style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            head,
            text="Limpieza segura · espacio · Drive · arranque · diagnóstico de apagados — sin telemetría ni upsell.",
            style="Sub.TLabel",
        ).pack(anchor="w")
        self.header_drives = ttk.Label(head, text="Discos…", style="Sub.TLabel")
        self.header_drives.pack(anchor="w", pady=(4, 0))

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=16, pady=4)
        ttk.Button(bar, text="Plan 1-clic (seguro)", style="Accent.TButton", command=self.one_click_plan).pack(
            side="left"
        )
        ttk.Button(bar, text="Diagnosticar caídas", command=self.run_health_scan).pack(side="left", padx=6)
        ttk.Button(bar, text="Exportar informe", command=self.export_report).pack(side="left")
        self.status = tk.StringVar(value="Listo.")
        ttk.Label(bar, textvariable=self.status, style="Sub.TLabel").pack(side="right")

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=16, pady=(4, 12))

        self.tab_dash = ttk.Frame(self.nb)
        self.tab_health = ttk.Frame(self.nb)
        self.tab_clean = ttk.Frame(self.nb)
        self.tab_space = ttk.Frame(self.nb)
        self.tab_dupes = ttk.Frame(self.nb)
        self.tab_progs = ttk.Frame(self.nb)
        self.tab_start = ttk.Frame(self.nb)
        self.tab_search = ttk.Frame(self.nb)

        self.nb.add(self.tab_dash, text="  Dashboard  ")
        self.nb.add(self.tab_health, text="  Salud / Caídas  ")
        self.nb.add(self.tab_clean, text="  Limpieza  ")
        self.nb.add(self.tab_space, text="  Espacio  ")
        self.nb.add(self.tab_dupes, text="  Duplicados / Drive  ")
        self.nb.add(self.tab_progs, text="  Programas  ")
        self.nb.add(self.tab_start, text="  Inicio  ")
        self.nb.add(self.tab_search, text="  Buscar  ")

        self._build_dash()
        self._build_health()
        self._build_clean()
        self._build_space()
        self._build_dupes()
        self._build_progs()
        self._build_start()
        self._build_search()

    def refresh_header(self) -> None:
        parts = []
        for letter, free, total in get_drives():
            pct = free / total * 100 if total else 0
            mark = " ⚠" if pct < 10 else ""
            parts.append(f"{letter} {format_size(free)} libres ({pct:.0f}%){mark}")
        self.header_drives.configure(text="  ·  ".join(parts))

    def set_busy(self, busy: bool, msg: str | None = None) -> None:
        self.busy = busy
        if msg:
            self.status.set(msg)

    # ---------- Dashboard ----------
    def _build_dash(self) -> None:
        card = ttk.Frame(self.tab_dash, style="Card.TFrame")
        card.pack(fill="x", padx=8, pady=8)
        self.score_lbl = ttk.Label(card, text="—", style="Score.TLabel")
        self.score_lbl.pack(anchor="w", padx=16, pady=(14, 0))
        self.score_sub = ttk.Label(card, text="Analiza Salud / Caídas para obtener puntuación.", style="Muted.TLabel")
        self.score_sub.pack(anchor="w", padx=16, pady=(0, 8))
        self.dash_summary = ttk.Label(card, text="", style="Card.TLabel", wraplength=900)
        self.dash_summary.pack(anchor="w", padx=16, pady=(0, 8))
        self.dash_alerts = tk.Text(card, height=8, bg="#0f1a2c", fg="#e8eef8", relief="flat", wrap="word")
        self.dash_alerts.pack(fill="x", padx=16, pady=(0, 14))

        tips = ttk.Frame(self.tab_dash, style="Card.TFrame")
        tips.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        ttk.Label(tips, text="Mantén el PC joven — checklist", style="Card.TLabel").pack(anchor="w", padx=16, pady=(12, 4))
        self.tips_box = tk.Text(tips, bg="#0f1a2c", fg="#cbd5e1", relief="flat", wrap="word")
        self.tips_box.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        for t in maintenance_suggestions():
            self.tips_box.insert("end", f"• {t}\n")
        self.tips_box.configure(state="disabled")

    def update_dashboard(self) -> None:
        if not self.health_report:
            return
        score, label = health_score(self.health_report)
        self.score_lbl.configure(text=f"{score}/100")
        self.score_sub.configure(text=f"Estado general: {label}")
        self.dash_summary.configure(text=self.health_report.summary_es)
        self.dash_alerts.configure(state="normal")
        self.dash_alerts.delete("1.0", "end")
        alerts = []
        for c in self.health_report.checks:
            if c.status in ("bad", "warn"):
                alerts.append(f"⚠ [{c.status}] {c.title}: {c.detail}")
        crashy = [
            e
            for e in self.health_report.events
            if e.category in ("power", "unexpected_shutdown", "bugcheck", "whea")
        ]
        for e in crashy[:8]:
            when = e.time.strftime("%Y-%m-%d %H:%M") if e.time else "?"
            alerts.append(f"💥 {when} — {e.source} #{e.event_id}: {e.probable_cause_es}")
        if self.health_report.needs_admin:
            alerts.append(f"🔐 {self.health_report.admin_hint}")
        if not alerts:
            alerts.append("Sin alertas graves en esta pasada.")
        self.dash_alerts.insert("end", "\n".join(alerts))
        self.dash_alerts.configure(state="disabled")

    # ---------- Salud / Caídas ----------
    def _build_health(self) -> None:
        top = ttk.Frame(self.tab_health)
        top.pack(fill="x", padx=8, pady=8)
        ttk.Button(top, text="Analizar caídas y salud", style="Accent.TButton", command=self.run_health_scan).pack(
            side="left"
        )
        ttk.Label(
            top,
            text="Kernel-Power 41 · 6008 · BugCheck · WHEA · minidumps · discos · RAM · Update",
            style="Sub.TLabel",
        ).pack(side="left", padx=10)

        self.health_summary = ttk.Label(self.tab_health, text="", style="Sub.TLabel", wraplength=920)
        self.health_summary.pack(anchor="w", padx=12)

        paned = ttk.Panedwindow(self.tab_health, orient="vertical")
        paned.pack(fill="both", expand=True, padx=8, pady=8)

        checks_f = ttk.Frame(paned, style="Card.TFrame")
        events_f = ttk.Frame(paned, style="Card.TFrame")
        paned.add(checks_f, weight=1)
        paned.add(events_f, weight=2)

        ttk.Label(checks_f, text="Comprobaciones", style="Card.TLabel").pack(anchor="w", padx=10, pady=6)
        cols = ("estado", "area", "detalle")
        self.checks_tree = ttk.Treeview(checks_f, columns=cols, show="headings", height=7)
        for c, t, w in (("estado", "Estado", 70), ("area", "Área", 160), ("detalle", "Detalle", 620)):
            self.checks_tree.heading(c, text=t)
            self.checks_tree.column(c, width=w, anchor="w")
        self.checks_tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        ttk.Label(events_f, text="Timeline de caídas / eventos (solo datos reales del registro)", style="Card.TLabel").pack(
            anchor="w", padx=10, pady=6
        )
        cols2 = ("fecha", "nivel", "origen", "tipo", "causa")
        self.events_tree = ttk.Treeview(events_f, columns=cols2, show="headings", height=12)
        for c, t, w in (
            ("fecha", "Fecha", 130),
            ("nivel", "Nivel", 70),
            ("origen", "Origen / ID", 220),
            ("tipo", "Tipo", 120),
            ("causa", "Causa probable", 400),
        ):
            self.events_tree.heading(c, text=t)
            self.events_tree.column(c, width=w, anchor="w")
        self.events_tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.events_tree.bind("<<TreeviewSelect>>", self._on_event_select)
        self.event_detail = tk.Text(events_f, height=4, bg="#0f1a2c", fg="#e8eef8", relief="flat", wrap="word")
        self.event_detail.pack(fill="x", padx=8, pady=(0, 8))

    def run_health_scan(self) -> None:
        if self.busy:
            return
        self.set_busy(True, "Diagnosticando caídas y salud…")
        self.nb.select(self.tab_health)

        def work() -> None:
            report = build_health_report(days=45)
            self.health_report = report
            self.after(0, self._fill_health)

        threading.Thread(target=work, daemon=True).start()

    def _fill_health(self) -> None:
        report = self.health_report
        self.refresh_header()
        if not report:
            self.set_busy(False, "Sin informe.")
            return
        self.health_summary.configure(text=report.summary_es)
        for i in self.checks_tree.get_children():
            self.checks_tree.delete(i)
        for c in report.checks:
            self.checks_tree.insert("", "end", values=(c.status, c.title, c.detail))
        for i in self.events_tree.get_children():
            self.events_tree.delete(i)
        self._event_rows = report.events
        for e in report.events:
            when = e.time.strftime("%Y-%m-%d %H:%M") if e.time else "?"
            self.events_tree.insert(
                "",
                "end",
                values=(when, e.level, f"{e.source} #{e.event_id}", e.category, e.probable_cause_es),
            )
        self.update_dashboard()
        self.set_busy(False, "Diagnóstico listo.")
        if report.needs_admin:
            messagebox.showwarning(
                "Permisos",
                "Algunos registros no se leyeron por permisos.\n\n" + report.admin_hint,
            )

    def _on_event_select(self, _evt=None) -> None:
        sel = self.events_tree.selection()
        if not sel or not getattr(self, "_event_rows", None):
            return
        idx = self.events_tree.index(sel[0])
        if idx >= len(self._event_rows):
            return
        e = self._event_rows[idx]
        self.event_detail.delete("1.0", "end")
        self.event_detail.insert(
            "end",
            f"{e.probable_cause_es}\n\n{e.message}",
        )

    def export_report(self) -> None:
        if not self.health_report:
            messagebox.showinfo("Informe", "Primero ejecuta el diagnóstico de Salud / Caídas.")
            return
        try:
            t = export_txt(self.health_report)
            h = export_html(self.health_report)
            messagebox.showinfo("Informe", f"Guardado en Descargas:\n{t.name}\n{h.name}")
            open_in_explorer(h)
        except OSError as exc:
            messagebox.showerror("Informe", str(exc))

    # ---------- Limpieza ----------
    def _build_clean(self) -> None:
        bar = ttk.Frame(self.tab_clean)
        bar.pack(fill="x", padx=8, pady=8)
        ttk.Button(bar, text="Analizar basura", command=self.scan_clean).pack(side="left")
        ttk.Button(bar, text="Limpiar selección", style="Accent.TButton", command=self.do_clean).pack(
            side="left", padx=6
        )
        self.clean_total = tk.StringVar(value="Seleccionable: 0 B")
        ttk.Label(bar, textvariable=self.clean_total, style="Sub.TLabel").pack(side="right")
        self.clean_list = ttk.Frame(self.tab_clean, style="Card.TFrame")
        self.clean_list.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def scan_clean(self) -> None:
        if self.busy:
            return
        self.set_busy(True, "Analizando basura…")
        for w in self.clean_list.winfo_children():
            w.destroy()
        ttk.Label(self.clean_list, text="Escaneando…", style="Card.TLabel").pack(padx=12, pady=12)

        def work() -> None:
            targets = build_targets()
            for t in targets:
                t.size = measure_target(t)
            targets = [t for t in targets if t.size > 0 or t.special == "recycle"]
            targets.sort(key=lambda x: x.size, reverse=True)
            self.clean_targets = targets
            self.after(0, self._render_clean)

        threading.Thread(target=work, daemon=True).start()

    def _render_clean(self) -> None:
        for w in self.clean_list.winfo_children():
            w.destroy()
        self.clean_vars.clear()
        for t in self.clean_targets:
            row = ttk.Frame(self.clean_list, style="Card.TFrame")
            row.pack(fill="x", padx=8, pady=4)
            var = tk.BooleanVar(value=t.selected and t.size > 0)
            self.clean_vars[t.key] = var
            ttk.Checkbutton(row, variable=var, command=self._upd_clean_total).pack(side="left", padx=6)
            box = ttk.Frame(row, style="Card.TFrame")
            box.pack(side="left", fill="x", expand=True)
            ttk.Label(box, text=t.title, style="Card.TLabel").pack(anchor="w")
            ttk.Label(box, text=t.description, style="Muted.TLabel").pack(anchor="w")
            ttk.Label(row, text=format_size(t.size), style="Card.TLabel").pack(side="right", padx=10)
        self._upd_clean_total()
        self.set_busy(False, "Análisis de limpieza listo.")

    def _upd_clean_total(self) -> None:
        total = sum(t.size for t in self.clean_targets if self.clean_vars.get(t.key) and self.clean_vars[t.key].get())
        self.clean_total.set(f"Seleccionable: {format_size(total)}")

    def do_clean(self) -> None:
        selected = [t for t in self.clean_targets if self.clean_vars.get(t.key) and self.clean_vars[t.key].get()]
        if not selected:
            messagebox.showinfo("Limpieza", "Nada seleccionado.")
            return
        total = sum(t.size for t in selected)
        if not messagebox.askyesno("Confirmar", f"Eliminar aprox. {format_size(total)} de basura segura?"):
            return
        self.set_busy(True, "Limpiando…")

        def work() -> None:
            freed = err = 0
            for t in selected:
                f, e = clean_target(t)
                freed += f
                err += e
            def done() -> None:
                self.refresh_header()
                self.set_busy(False, f"Liberados ~{format_size(freed)}.")
                messagebox.showinfo("Limpieza", f"Listo. ~{format_size(freed)} liberados." + (f"\nErrores: {err}" if err else ""))
                self.scan_clean()
            self.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    # ---------- Espacio ----------
    def _build_space(self) -> None:
        bar = ttk.Frame(self.tab_space)
        bar.pack(fill="x", padx=8, pady=8)
        ttk.Label(bar, text="Mín. MB:", style="Sub.TLabel").pack(side="left")
        self.min_mb = tk.StringVar(value="200")
        ttk.Entry(bar, textvariable=self.min_mb, width=8).pack(side="left", padx=4)
        ttk.Button(bar, text="Archivos grandes", style="Accent.TButton", command=self.scan_large).pack(side="left", padx=6)
        ttk.Button(bar, text="Carpetas que más ocupan", command=self.scan_folders).pack(side="left")
        cols = ("tam", "ruta")
        self.space_tree = ttk.Treeview(self.tab_space, columns=cols, show="headings")
        self.space_tree.heading("tam", text="Tamaño")
        self.space_tree.heading("ruta", text="Ruta")
        self.space_tree.column("tam", width=100)
        self.space_tree.column("ruta", width=760)
        self.space_tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.space_tree.bind("<Double-1>", lambda e: self._open_tree_path(self.space_tree))

    def scan_large(self) -> None:
        if self.busy:
            return
        try:
            mb = max(50, int(self.min_mb.get()))
        except ValueError:
            mb = 200
        self.set_busy(True, "Buscando archivos grandes…")

        def work() -> None:
            roots = default_scan_roots(include_drive=True)
            # also user profile lightly
            home = user_home()
            if home not in roots:
                roots.append(home)
            files = find_large_files(roots, min_bytes=mb * 1024 * 1024, limit=120)
            self.after(0, lambda: self._fill_space([(f.size, str(f.path)) for f in files], "Archivos grandes listos."))

        threading.Thread(target=work, daemon=True).start()

    def scan_folders(self) -> None:
        if self.busy:
            return
        self.set_busy(True, "Midiendo carpetas…")

        def work() -> None:
            roots = default_scan_roots(include_drive=True)
            folders = top_folders(roots, depth=2, limit=50)
            self.after(
                0,
                lambda: self._fill_space(
                    [(f.size, f"{f.path}  ({f.file_count} archivos)") for f in folders],
                    "Carpetas listas.",
                ),
            )

        threading.Thread(target=work, daemon=True).start()

    def _fill_space(self, rows: list[tuple[int, str]], msg: str) -> None:
        for i in self.space_tree.get_children():
            self.space_tree.delete(i)
        for size, path in rows:
            self.space_tree.insert("", "end", values=(format_size(size), path))
        self.set_busy(False, msg)

    def _open_tree_path(self, tree: ttk.Treeview) -> None:
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0], "values")
        if len(vals) < 2:
            return
        raw = str(vals[1]).split("  (")[0]
        p = Path(raw)
        if p.exists():
            open_in_explorer(p)

    # ---------- Duplicados / Drive ----------
    def _build_dupes(self) -> None:
        info = ttk.Frame(self.tab_dupes, style="Card.TFrame")
        info.pack(fill="x", padx=8, pady=8)
        self.drive_info_lbl = ttk.Label(info, text="Pulsa Analizar Drive…", style="Card.TLabel", wraplength=900)
        self.drive_info_lbl.pack(anchor="w", padx=12, pady=10)
        bar = ttk.Frame(self.tab_dupes)
        bar.pack(fill="x", padx=8)
        ttk.Button(bar, text="Config Drive", command=self.show_drive).pack(side="left")
        ttk.Button(bar, text="Buscar duplicados", style="Accent.TButton", command=self.scan_dupes).pack(
            side="left", padx=6
        )
        cols = ("ahorro", "tam", "archivos")
        self.dupe_tree = ttk.Treeview(self.tab_dupes, columns=cols, show="headings")
        for c, t, w in (("ahorro", "Ahorro", 90), ("tam", "Tamaño", 90), ("archivos", "Copias (rutas)", 700)):
            self.dupe_tree.heading(c, text=t)
            self.dupe_tree.column(c, width=w)
        self.dupe_tree.pack(fill="both", expand=True, padx=8, pady=8)

    def show_drive(self) -> None:
        info = get_drive_info()
        text = "\n".join(info.notes)
        if info.roots:
            text += "\n\nRaíces: " + ", ".join(str(r) for r in info.roots)
        self.drive_info_lbl.configure(text=text)

    def scan_dupes(self) -> None:
        if self.busy:
            return
        self.show_drive()
        self.set_busy(True, "Buscando duplicados (puede tardar)…")

        def work() -> None:
            roots = default_scan_roots(include_drive=True)
            groups = flag_drive_local_pairs(find_duplicates(roots, min_bytes=1024 * 1024))
            self.after(0, lambda: self._fill_dupes(groups))

        threading.Thread(target=work, daemon=True).start()

    def _fill_dupes(self, groups) -> None:
        for i in self.dupe_tree.get_children():
            self.dupe_tree.delete(i)
        for g in groups[:80]:
            paths = "  ||  ".join(str(p) for p in g.paths[:4])
            if len(g.paths) > 4:
                paths += f"  (+{len(g.paths)-4})"
            tag = ""
            has_g = any(str(p).lower().startswith("g:") for p in g.paths)
            has_l = any(not str(p).lower().startswith("g:") for p in g.paths)
            if has_g and has_l:
                paths = "[LOCAL+DRIVE] " + paths
            self.dupe_tree.insert("", "end", values=(format_size(g.wasted), format_size(g.size), paths))
        self.set_busy(False, f"{len(groups)} grupos de duplicados.")

    # ---------- Programas ----------
    def _build_progs(self) -> None:
        bar = ttk.Frame(self.tab_progs)
        bar.pack(fill="x", padx=8, pady=8)
        ttk.Button(bar, text="Listar programas", style="Accent.TButton", command=self.scan_progs).pack(side="left")
        ttk.Label(bar, text="Heurística: sin tocar el ejecutable ~180+ días = posible sin uso.", style="Sub.TLabel").pack(
            side="left", padx=8
        )
        cols = ("nombre", "dias", "tam", "editor")
        self.prog_tree = ttk.Treeview(self.tab_progs, columns=cols, show="headings")
        for c, t, w in (
            ("nombre", "Programa", 280),
            ("dias", "Días sin tocarse", 120),
            ("tam", "Tamaño est.", 100),
            ("editor", "Editor", 220),
        ):
            self.prog_tree.heading(c, text=t)
            self.prog_tree.column(c, width=w)
        self.prog_tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def scan_progs(self) -> None:
        if self.busy:
            return
        self.set_busy(True, "Leyendo programas instalados…")

        def work() -> None:
            progs = list_installed_programs(180)
            self.after(0, lambda: self._fill_progs(progs))

        threading.Thread(target=work, daemon=True).start()

    def _fill_progs(self, progs) -> None:
        for i in self.prog_tree.get_children():
            self.prog_tree.delete(i)
        for p in progs:
            days = str(p.days_since_touch) if p.days_since_touch is not None else "?"
            if p.likely_unused:
                days = f"{days} ★"
            size = format_size((p.estimated_size_kb or 0) * 1024) if p.estimated_size_kb else "—"
            self.prog_tree.insert("", "end", values=(p.name, days, size, p.publisher))
        unused = sum(1 for p in progs if p.likely_unused)
        self.set_busy(False, f"{len(progs)} programas ({unused} posiblemente sin uso).")

    # ---------- Inicio ----------
    def _build_start(self) -> None:
        bar = ttk.Frame(self.tab_start)
        bar.pack(fill="x", padx=8, pady=8)
        ttk.Button(bar, text="Analizar inicio", style="Accent.TButton", command=self.scan_startup).pack(side="left")
        ttk.Button(bar, text="Deshabilitar seleccionado (HKCU)", command=self.disable_selected_startup).pack(
            side="left", padx=6
        )
        ttk.Label(bar, text="Solo deshabilita entradas de usuario (seguro).", style="Sub.TLabel").pack(side="left")
        cols = ("impacto", "estado", "nombre", "ubicacion", "comando")
        self.start_tree = ttk.Treeview(self.tab_start, columns=cols, show="headings")
        for c, t, w in (
            ("impacto", "Impacto", 70),
            ("estado", "Estado", 90),
            ("nombre", "Nombre", 160),
            ("ubicacion", "Ubicación", 140),
            ("comando", "Comando", 420),
        ):
            self.start_tree.heading(c, text=t)
            self.start_tree.column(c, width=w)
        self.start_tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._startup_items = []

    def scan_startup(self) -> None:
        items = list_startup_run_entries()
        self._startup_items = items
        for i in self.start_tree.get_children():
            self.start_tree.delete(i)
        for it in items:
            self.start_tree.insert(
                "",
                "end",
                values=(it.impact, "Activo" if it.enabled else "Deshabilitado", it.name, it.location, it.command[:180]),
            )
        self.status.set(f"{len(items)} entradas de inicio.")

    def disable_selected_startup(self) -> None:
        sel = self.start_tree.selection()
        if not sel:
            return
        idx = self.start_tree.index(sel[0])
        if idx >= len(self._startup_items):
            return
        it = self._startup_items[idx]
        if it.hive != "HKCU":
            messagebox.showinfo(
                "Inicio",
                "Esta entrada es del sistema (HKLM). Deshabilítala desde Administrador de tareas → Inicio o Autoruns.",
            )
            return
        if not messagebox.askyesno("Confirmar", f"¿Quitar del inicio de usuario?\n{it.name}"):
            return
        ok, msg = disable_startup_hkcu(it.name)
        messagebox.showinfo("Inicio", msg)
        if ok:
            self.scan_startup()

    # ---------- Buscar ----------
    def _build_search(self) -> None:
        bar = ttk.Frame(self.tab_search)
        bar.pack(fill="x", padx=8, pady=8)
        self.search_q = tk.StringVar()
        ttk.Entry(bar, textvariable=self.search_q).pack(side="left", fill="x", expand=True)
        ttk.Button(bar, text="Buscar", style="Accent.TButton", command=self.do_search).pack(side="left", padx=6)
        cols = ("tipo", "tam", "ruta")
        self.search_tree = ttk.Treeview(self.tab_search, columns=cols, show="headings")
        for c, t, w in (("tipo", "Tipo", 70), ("tam", "Tamaño", 90), ("ruta", "Ruta", 720)):
            self.search_tree.heading(c, text=t)
            self.search_tree.column(c, width=w)
        self.search_tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.search_tree.bind("<Double-1>", lambda e: self._open_tree_path(self.search_tree))

    def do_search(self) -> None:
        q = self.search_q.get().strip()
        if not q:
            return
        if self.busy:
            return
        self.set_busy(True, f"Buscando “{q}”…")

        def work() -> None:
            roots = default_scan_roots(include_drive=True)
            roots.append(user_home())
            hits = search_files(q, roots, limit=200)
            self.after(0, lambda: self._fill_search(hits))

        threading.Thread(target=work, daemon=True).start()

    def _fill_search(self, hits) -> None:
        for i in self.search_tree.get_children():
            self.search_tree.delete(i)
        for h in hits:
            self.search_tree.insert("", "end", values=(h.kind, format_size(h.size), str(h.path)))
        self.set_busy(False, f"{len(hits)} resultados.")

    # ---------- Plan 1-clic ----------
    def one_click_plan(self) -> None:
        if self.busy:
            return
        if not messagebox.askyesno(
            "Plan 1-clic",
            "Ejecutará de forma SEGURA:\n"
            "1) Diagnóstico de caídas/salud\n"
            "2) Limpieza de basura seleccionable (temporales, papelera, cachés)\n"
            "3) Resumen en Dashboard\n\n"
            "No toca Documentos/fotos ni el registro de forma agresiva.\n¿Continuar?",
        ):
            return
        self.set_busy(True, "Plan 1-clic en marcha…")

        def work() -> None:
            report = build_health_report(days=45)
            self.health_report = report
            targets = build_targets()
            for t in targets:
                t.size = measure_target(t)
            # Auto-select safe defaults with size
            safe_keys = {"temp_user", "temp_win", "recycle", "thumbnails", "crashdumps", "npm", "pip"}
            selected = [t for t in targets if t.key in safe_keys and (t.size > 0 or t.special == "recycle")]
            freed = err = 0
            for t in selected:
                f, e = clean_target(t)
                freed += f
                err += e

            def done() -> None:
                self._fill_health()
                self.refresh_header()
                self.set_busy(False, f"Plan listo. Liberados ~{format_size(freed)}.")
                score, label = health_score(report)
                messagebox.showinfo(
                    "Plan 1-clic",
                    f"Salud: {score}/100 ({label})\n"
                    f"Liberados ~{format_size(freed)}\n\n{report.summary_es[:400]}",
                )
                self.nb.select(self.tab_dash)

            self.after(0, done)

        threading.Thread(target=work, daemon=True).start()


def main() -> None:
    app = LimpiadorPro()
    app.mainloop()


if __name__ == "__main__":
    main()
