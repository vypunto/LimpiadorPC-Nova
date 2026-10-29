"use strict";
/* Detalles "pro": luz que sigue al ratón, números animados y paleta de comandos (Ctrl+K). */

/* ---------- Luz que sigue al ratón en tarjetas y botones ---------- */
document.addEventListener("pointermove", (e) => {
  const el = e.target.closest(".card, .stat, .wl-item, .fix, .step");
  if (!el) return;
  const r = el.getBoundingClientRect();
  el.style.setProperty("--mx", `${e.clientX - r.left}px`);
  el.style.setProperty("--my", `${e.clientY - r.top}px`);
}, { passive: true });

/* ---------- Números que cuentan hasta su valor cuando cambian ---------- */
const NUMCACHE = new Map();
const parseNum = (t) => { const m = String(t).match(/^\s*([\d.]+(?:,\d+)?)/); return m ? parseFloat(m[1].replace(/\./g, "").replace(",", ".")) : null; };
function animateNumbers() {
  document.querySelectorAll("#view .metric-big, #view .stat .v, #view .ring .num").forEach((el, i) => {
    const node = [...el.childNodes].find((n) => n.nodeType === 3 && n.textContent.trim());
    if (!node) return;
    const val = parseNum(node.textContent);
    if (val == null) return;
    const key = `${S.page}:${i}`, prev = NUMCACHE.get(key);
    NUMCACHE.set(key, val);
    if (prev == null || prev === val) return;
    const original = node.textContent, decimals = (original.match(/,(\d+)/) || [, ""])[1].length, rest = original.replace(/^\s*[\d.,]+/, "");
    const t0 = performance.now(), dur = 700;
    const step = (t) => {
      if (!node.isConnected) return;
      const k = Math.min(1, (t - t0) / dur), ease = 1 - Math.pow(1 - k, 3);
      node.textContent = (prev + (val - prev) * ease).toLocaleString("es-ES", { minimumFractionDigits: decimals, maximumFractionDigits: decimals }) + rest;
      if (k < 1) requestAnimationFrame(step); else node.textContent = original;
    };
    requestAnimationFrame(step);
  });
}
new MutationObserver(animateNumbers).observe(document.getElementById("view"), { childList: true });

/* ---------- Paleta de comandos (Ctrl+K) ---------- */
function commands() {
  const list = PAGES.map((p) => ({ icon: p.i, title: `Ir a ${p.t}`, sub: p.s, run: () => go(p.id) }));
  list.push(
    { icon: "rocket", title: "Optimizar ahora", sub: "Limpieza segura + diagnóstico", run: () => ACT.optimize() },
    { icon: "clean", title: "Analizar basura", sub: "Limpieza", run: () => { go("limpieza"); job("clean_scan"); } },
    { icon: "copy", title: "Buscar duplicados", sub: "Duplicados", run: () => { go("duplicados"); EXTRA_ACT.dscan ? EXTRA_ACT.dscan() : ACT.dscan(); } },
    { icon: "shield", title: "Análisis rápido de Defender", sub: "Seguridad", run: () => { go("seguridad"); ACT.scan("quick"); } },
    { icon: "file", title: "Exportar informe", sub: "HTML con diagnóstico y soluciones", run: () => ACT.report() },
    { icon: "moon", title: "Cambiar modo día / noche", sub: "Tema", run: () => setTheme(document.documentElement.dataset.theme === "light" ? "dark" : "light") },
    { icon: "info", title: "Guía rápida", sub: "Pantalla de bienvenida", run: () => EXTRA_ACT.welcome() },
    { icon: "clock", title: "Historial", sub: "Lo que se ha limpiado o cambiado", run: () => ACT.hist() },
    { icon: "key", title: "Ejecutar como administrador", sub: "Desbloquea todas las reparaciones", run: () => ACT.elevate() },
    { icon: "pulse", title: "Hablar con Smally", sub: "Abre el chat", run: () => { if (document.body.classList.contains("smally-hidden")) EXTRA_ACT.smallyshow(); if (!CHAT.open) toggleChat(); } },
    document.body.classList.contains("smally-hidden")
      ? { icon: "eye", title: "Mostrar a Smally", sub: "Vuelve a aparecer", run: () => EXTRA_ACT.smallyshow() }
      : { icon: "x", title: "Ocultar a Smally", sub: "Se esconde hasta que lo vuelvas a llamar", run: () => setHidden(true) },
  );
  (S.fixes || []).forEach((f) => list.push({ icon: f.icon, title: f.title, sub: `Reparar · ${f.group}${f.admin ? " · admin" : ""}`, run: () => { go("reparar"); ACT.fix(f.id); } }));
  return list;
}
const nrm = (t) => String(t).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
function openPalette() {
  if (document.querySelector(".palette")) return;
  if (!S.fixes) api("/api/fixes").then((r) => (S.fixes = r.fixes)).catch(() => {});
  const w = document.createElement("div");
  w.className = "modal-wrap palette-wrap";
  w.innerHTML = `<div class="palette"><div class="pal-in">${ic("search")}<input id="pal-q" placeholder="Escribe una sección o acción… (p. ej. «duplicados», «sfc», «modo día»)" autocomplete="off"><kbd>Esc</kbd></div><div class="pal-list" id="pal-list"></div></div>`;
  document.body.appendChild(w);
  let sel = 0, items = [];
  const draw = () => {
    const q = nrm(w.querySelector("#pal-q").value).split(/\s+/).filter(Boolean);
    items = commands().filter((c) => q.every((t) => nrm(c.title + " " + c.sub).includes(t))).slice(0, 9);
    sel = Math.min(sel, Math.max(0, items.length - 1));
    w.querySelector("#pal-list").innerHTML = items.map((c, i) => `<div class="pal-item ${i === sel ? "on" : ""}" data-i="${i}"><span class="wl-ico">${ic(c.icon)}</span><div class="main-col"><b>${esc(c.title)}</b><small>${esc(c.sub)}</small></div>${i === sel ? "<kbd>↵</kbd>" : ""}</div>`).join("")
      || `<div class="muted" style="padding:18px">Nada coincide. Prueba con otra palabra.</div>`;
  };
  const run = (i) => { const c = items[i]; w.remove(); c?.run(); };
  w.addEventListener("click", (e) => { const it = e.target.closest(".pal-item"); if (it) run(+it.dataset.i); else if (e.target === w) w.remove(); });
  w.addEventListener("mousemove", (e) => { const it = e.target.closest(".pal-item"); if (it && +it.dataset.i !== sel) { sel = +it.dataset.i; draw(); } });
  const q = w.querySelector("#pal-q");
  q.addEventListener("input", () => { sel = 0; draw(); });
  q.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { sel = Math.min(items.length - 1, sel + 1); draw(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { sel = Math.max(0, sel - 1); draw(); e.preventDefault(); }
    else if (e.key === "Enter") run(sel);
    else if (e.key === "Escape") w.remove();
  });
  draw(); q.focus();
}
addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); openPalette(); }
});
// Acceso visible en la barra superior
(() => {
  const live = document.querySelector(".top .live");
  const b = document.createElement("button");
  b.className = "btn pal-btn"; b.title = "Buscar secciones y acciones (Ctrl+K)";
  b.innerHTML = `${ic("search")}<span>Buscar acción</span><kbd>Ctrl K</kbd>`;
  b.onclick = openPalette;
  live.prepend(b);
})();
