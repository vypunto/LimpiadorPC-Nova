"use strict";
const KEY = new URLSearchParams(location.search).get("k") || "";
const $ = (s) => document.querySelector(s);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const nf = (n, d = 1) => Number(n).toLocaleString("es-ES", { maximumFractionDigits: d });
function fmt(b) { if (b == null) return "—"; const u = ["B", "KB", "MB", "GB", "TB"]; let i = 0; b = Number(b); while (b >= 1024 && i < 4) { b /= 1024; i++; } return nf(b, i ? 1 : 0) + " " + u[i]; }
const base = (p) => String(p).split(/[\\/]/).filter(Boolean).pop() || p;
const dir = (p) => String(p).replace(/[\\/][^\\/]*$/, "");
const date = (s) => s ? new Date(s * 1000).toLocaleDateString("es-ES") : "—";

const P = {
  home: "M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z",
  clean: "M12 3l1.8 4.7 4.7 1.8-4.7 1.8L12 16l-1.8-4.7-4.7-1.8 4.7-1.8z M19 15l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8z",
  disk: "M4 6a8 3 0 1 0 16 0a8 3 0 1 0-16 0 M4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6 M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3",
  copy: "M8 8h11a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z M4 16V5a1 1 0 0 1 1-1h11",
  shield: "M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6z M8.5 12l2.5 2.5 4.5-5",
  wrench: "M14.7 6.3a4 4 0 0 0-5.4 5.1L3 17.7V21h3.3l6.3-6.3a4 4 0 0 0 5.1-5.4l-2.6 2.6-2.4-.6-.6-2.4z",
  power: "M12 3v8 M6.3 6.3a8 8 0 1 0 11.4 0",
  apps: "M4 4h6v6H4z M14 4h6v6h-6z M4 14h6v6H4z M14 14h6v6h-6z",
  pulse: "M3 12h4l2-5 4 10 2-5h6",
  search: "M11 4a7 7 0 1 0 0 14a7 7 0 1 0 0-14 M20 20l-4-4",
  folder: "M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z",
  file: "M6 3h8l4 4v14H6z M14 3v4h4",
  trash: "M4 7h16 M9 7V4h6v3 M6 7l1 13h10l1-13",
  eye: "M14 4h6v6 M20 4l-9 9 M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5",
  lock: "M6 11h12v9H6z M8 11V8a4 4 0 0 1 8 0v3",
  alert: "M12 3l9.5 17h-19z M12 10v4 M12 17h.01",
  check: "M5 12l5 5 9-10",
  rocket: "M5 15c-1.5 1.5-2 5-2 5s3.5-.5 5-2 M9 18l-3-3 M14.5 4.5C17 3 21 3 21 3s0 4-1.5 6.5L13 16l-5-5z",
  cpu: "M7 7h10v10H7z M10 3v4 M14 3v4 M10 17v4 M14 17v4 M3 10h4 M3 14h4 M17 10h4 M17 14h4",
  layers: "M12 3l9 5-9 5-9-5z M3 13l9 5 9-5",
  refresh: "M20 11a8 8 0 0 0-14.3-4.9L4 8 M4 4v4h4 M4 13a8 8 0 0 0 14.3 4.9L20 16 M20 20v-4h-4",
  bag: "M5 8h14l-1 13H6z M9 8V6a3 3 0 0 1 6 0v2",
  window: "M3 5h18v14H3z M3 9h18",
  sound: "M4 10v4h4l5 4V6L8 10z M16 9a4 4 0 0 1 0 6 M19 6a8 8 0 0 1 0 12",
  printer: "M7 9V3h10v6 M5 17H3v-6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v6h-2 M7 14h10v7H7z",
  globe: "M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18 M3 12h18 M12 3c3 3.5 3 14.5 0 18 M12 3c-3 3.5-3 14.5 0 18",
  wifi: "M2 9a15 15 0 0 1 20 0 M5 12.5a10 10 0 0 1 14 0 M8.5 16a5 5 0 0 1 7 0 M12 19.5h.01",
  clock: "M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18 M12 7v5l3 2",
  compress: "M4 14h6v6 M20 10h-6V4 M14 10l7-7 M3 21l7-7",
  bolt: "M13 2L4 14h7l-1 8 9-12h-7z",
  leaf: "M5 19c0-9 6-14 15-14 0 9-5 15-14 15 M5 19l7-7",
  moon: "M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z",
  key: "M8 15a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M11 11h10 M17 11v3 M20 11v3",
  info: "M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18 M12 11v5 M12 8h.01",
  play: "M7 4l13 8-13 8z",
  x: "M6 6l12 12 M18 6L6 18",
  download: "M12 3v12 M7 10l5 5 5-5 M4 21h16",
};
P.grid = P.apps; P.chip = P.cpu; P.network = P.globe;
const ic = (n) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="${P[n] || P.wrench}"/></svg>`;

/* ---------------- API ---------------- */
async function api(path, body) {
  const opts = { method: body === undefined ? "GET" : "POST", headers: { "X-Nova-Key": KEY, "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) };
  let r;
  // Reintenta fallos de conexión puntuales (p. ej. en el arranque) antes de dar error
  for (let i = 0; ; i++) {
    try { r = await fetch(path, opts); break; }
    catch (e) {
      if (i >= 4) throw new Error("No se pudo conectar con el motor de la app. Ciérrala y vuelve a abrirla.");
      await new Promise((ok) => setTimeout(ok, 300 * (i + 1)));
    }
  }
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.error || "Error " + r.status);
  return d;
}
const S = { page: "panel", jobs: {}, cpuH: [], ramH: [], sel: {}, space: { tab: "large", minMb: 200, days: 365, drive: false }, dupes: { minMb: 1, drive: false }, prog: { q: "", f: "all" } };
const running = (slot) => S.jobs[slot]?.state === "running";
const res = (slot) => S.jobs[slot]?.result;

async function job(kind, params = {}, slot = kind) {
  let s;
  try { s = await api("/api/job", { kind, params }); } catch (e) { toast(e.message, "bad"); return null; }
  S.jobs[slot] = s; nav(); refresh(slot);
  return new Promise((done) => {
    const tick = async () => {
      try { s = await api("/api/job/" + s.id); } catch { return setTimeout(tick, 1500); }
      const prev = S.jobs[slot]; S.jobs[slot] = s;
      const changed = JSON.stringify(prev?.result)?.length !== JSON.stringify(s.result)?.length || prev?.state !== s.state;
      refresh(slot, changed);
      if (s.state === "running") setTimeout(tick, 600);
      else { nav(); if (s.state === "error") toast(s.error, "bad"); done(s); }
    };
    setTimeout(tick, 400);
  });
}
const cancel = (slot) => S.jobs[slot] && api(`/api/job/${S.jobs[slot].id}/cancel`, {});

function jobline(slot) {
  const j = S.jobs[slot];
  if (!j || j.state !== "running") return "";
  const ind = j.progress == null;
  return `<div class="jobline" data-job="${slot}"><div class="spinner"></div><span class="msg ellipsis">${esc(j.message || "Trabajando…")}</span><div class="progress ${ind ? "indet" : ""}"><i style="width:${(j.progress || 0) * 100}%"></i></div><button class="btn sm ghost" data-act="cancel" data-v="${slot}">Cancelar</button></div>`;
}

/* ---------------- UI helpers ---------------- */
function toast(msg, kind = "ok") {
  const el = document.createElement("div");
  el.className = "toast";
  el.innerHTML = `<span class="dot ${kind}"></span><span>${esc(msg)}</span>`;
  $("#toasts").appendChild(el);
  setTimeout(() => { el.classList.add("out"); setTimeout(() => el.remove(), 300); }, 4200);
}
function modal(html, wide) {
  const w = document.createElement("div");
  w.className = "modal-wrap";
  w.innerHTML = `<div class="modal ${wide ? "wide" : ""}">${html}</div>`;
  document.body.appendChild(w);
  return w;
}
function ask(title, body, ok = "Continuar", danger = false) {
  return new Promise((r) => {
    const w = modal(`<h3>${esc(title)}</h3><div class="body">${body}</div><div class="foot"><button class="btn ghost" data-r="0">Cancelar</button><button class="btn ${danger ? "danger" : "primary"}" data-r="1">${esc(ok)}</button></div>`);
    w.addEventListener("click", (e) => { const b = e.target.closest("[data-r]"); if (b || e.target === w) { w.remove(); r(b?.dataset.r === "1"); } });
  });
}
/* Ventana de consola para tareas con salida en directo */
async function consoleJob(title, kind, params) {
  const w = modal(`<div class="row"><h3 class="spacer">${esc(title)}</h3><span class="chip info" id="cj-state"><span class="spinner"></span> En curso</span></div>
    <div class="console mt" id="cj-log"></div><div class="foot"><button class="btn ghost" id="cj-cancel">Cancelar</button><button class="btn" id="cj-close">Cerrar</button></div>`, true);
  const slot = "console";
  w.querySelector("#cj-close").onclick = () => w.remove();
  w.querySelector("#cj-cancel").onclick = () => cancel(slot);
  const paint = () => {
    const j = S.jobs[slot]; if (!j) return;
    const log = w.querySelector("#cj-log");
    log.innerHTML = j.log.map((l) => l.startsWith("›") ? `<span class="cmd">${esc(l)}</span>` : esc(l)).join("\n") || esc(j.message);
    log.scrollTop = log.scrollHeight;
  };
  const iv = setInterval(paint, 500);
  const s = await job(kind, params, slot);
  clearInterval(iv); paint();
  const ok = s && s.state === "done" && !(s.result && s.result.code);
  const st = w.querySelector("#cj-state");
  st.className = "chip " + (ok ? "ok" : "warn");
  st.textContent = ok ? "Completado" : s?.state === "error" ? "Error" : "Terminado con avisos";
  w.querySelector("#cj-cancel").remove();
  if (s?.result?.reboot) toast("Reinicia el equipo para aplicar el cambio.", "warn");
  return s;
}

function spark(arr, max = 100, w = 300, h = 70, fill = "url(#sparkFill)", stroke = "#5ef2d6") {
  if (arr.length < 2) return "";
  const pts = arr.map((v, i) => [(i / (arr.length - 1)) * w, h - (v / max) * (h - 4) - 2]);
  const line = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join("");
  return `<path d="${line}L${w} ${h}L0 ${h}Z" fill="${fill}"/><path d="${line}" fill="none" stroke="${stroke}" stroke-width="1.6"/>`;
}
function ring(score, scanning) {
  const c = 2 * Math.PI * 100, off = c * (1 - (score ?? 0) / 100);
  return `<div class="ring ${scanning ? "scanning" : ""}"><svg viewBox="0 0 240 240"><circle class="ticks" cx="120" cy="120" r="114"/><circle class="track" cx="120" cy="120" r="100"/><circle class="val" cx="120" cy="120" r="100" stroke-dasharray="${c}" stroke-dashoffset="${off}"/></svg>
    <div class="center"><div class="num">${score ?? "··"}</div><div class="lbl">${scanning ? "Analizando" : "Salud"}</div></div></div>`;
}
const empty = (icon, t, s, btn = "") => `<div class="empty">${ic(icon)}<h4>${t}</h4><div>${s}</div>${btn ? `<div class="mt">${btn}</div>` : ""}</div>`;
const sevChip = { high: "bad", medium: "warn", low: "info", ok: "ok", bad: "bad", warn: "warn", info: "info" };
const sevTxt = { high: "Alto", medium: "Medio", low: "Bajo", ok: "Correcto", bad: "Crítico", warn: "Aviso", info: "Info" };
function selSet(k) { return (S.sel[k] ||= new Set()); }

/* ---------------- Páginas ---------------- */
const PAGES = [
  { id: "panel", t: "Panel", s: "Estado de tu equipo en tiempo real", i: "home", sec: "General", slots: ["health", "clean_scan", "sec_status", "optimize"] },
  { id: "limpieza", t: "Limpieza", s: "Basura del sistema, navegadores, apps y desarrollo", i: "clean", slots: ["clean_scan", "clean_run"] },
  { id: "espacio", t: "Espacio", s: "Archivos grandes, carpetas pesadas y archivos sin usar", i: "disk", slots: ["large", "folders", "unused", "devjunk", "organize_plan"] },
  { id: "duplicados", t: "Duplicados", s: "Copias idénticas verificadas byte a byte", i: "copy", slots: ["dupes"] },
  { id: "organizador", t: "Organizador IA", s: "Elige una carpeta y la IA te propone una estructura perfecta", i: "folder", slots: ["aiorg"] },
  { id: "seguridad", t: "Seguridad", s: "Microsoft Defender y auditoría de amenazas", i: "shield", sec: "Protección", slots: ["sec_status", "sec_audit"] },
  { id: "reparar", t: "Reparar", s: "Soluciona problemas de Windows con herramientas oficiales", i: "wrench", slots: [] },
  { id: "salud", t: "Salud", s: "Apagados inesperados, pantallas azules y hardware", i: "pulse", slots: ["health"] },
  { id: "inicio", t: "Inicio y fondo", s: "Lo que arranca con Windows y lo que se ejecuta en segundo plano", i: "power", sec: "Control", slots: ["bg"] },
  { id: "programas", t: "Programas", s: "Instalados, tamaño y cuáles no usas", i: "apps", slots: ["programs"] },
  { id: "buscar", t: "Buscar", s: "Encuentra archivos en tus carpetas", i: "search", slots: ["search"] },
];

function nav() {
  let html = "";
  for (const p of PAGES) {
    if (p.sec) html += `<div class="nav-label">${p.sec}</div>`;
    const busy = p.slots.some(running);
    let badge = "";
    if (p.id === "seguridad") { const n = (res("sec_audit")?.findings || []).filter((f) => f.severity === "high").length; if (n) badge = `<span class="badge">${n}</span>`; }
    html += `<a class="${S.page === p.id ? "on" : ""}" data-page="${p.id}">${ic(p.i)}<span>${p.t}</span>${busy ? '<span class="spin-dot"></span>' : badge}</a>`;
  }
  $("#nav").innerHTML = html;
  $("#sidefoot").innerHTML = (S.admin
    ? `<div class="row"><span class="dot ok"></span>Modo administrador</div>`
    : `<div class="row"><span class="dot warn"></span>Modo usuario</div><button class="btn sm" data-act="elevate">${ic("key")}Ejecutar como admin</button>`)
    + `<button class="btn sm ghost" data-act="hist">${ic("clock")}Historial</button>`
    + `<button class="btn sm ghost smally-show" data-act="smallyshow">🤖 Mostrar a Smally</button>`
    + `<button class="btn sm ghost" data-act="welcome">${ic("info")}Guía rápida</button>`
    + `<button class="btn sm ghost" data-act="support" title="Datos para pedir ayuda si algo falla">${ic("file")}Informe técnico</button>`
    + `<button class="btn sm ghost" data-act="shortcut" title="Crea accesos directos en el escritorio y el menú Inicio">${ic("rocket")}Acceso directo</button>`;
}

function go(id) {
  S.page = id;
  const p = PAGES.find((x) => x.id === id);
  $("#title").textContent = p.t; $("#subtitle").textContent = p.s;
  nav(); render(true);
  ENTER[id]?.();
}
function render(anim) {
  const v = $("#view"), a = document.activeElement, fid = a?.id, pos = a?.selectionStart;
  v.innerHTML = `<div class="${anim ? "page" : ""}">${VIEWS[S.page]()}</div>`;
  if (fid) { const el = document.getElementById(fid); if (el) { el.focus(); try { el.setSelectionRange(pos, pos); } catch {} } }
}
function refresh(slot, changed = true) {
  const p = PAGES.find((x) => x.id === S.page);
  if (!p.slots.includes(slot)) return;
  const el = document.querySelector(`[data-job="${slot}"]`);
  if (!changed && el && running(slot)) {
    const j = S.jobs[slot];
    el.querySelector(".msg").textContent = j.message || "Trabajando…";
    el.querySelector(".progress").classList.toggle("indet", j.progress == null);
    el.querySelector(".progress i").style.width = (j.progress || 0) * 100 + "%";
  } else render();
}

const ENTER = {
  limpieza: async () => { !S.jobs.clean_scan && job("clean_scan"); S.auto = await api("/api/autoclean").catch(() => null); render(); },
  seguridad: () => { !S.jobs.sec_status && job("sec_status"); !S.jobs.sec_audit && job("sec_audit"); },
  reparar: async () => { if (!S.fixes) { S.fixes = (await api("/api/fixes")).fixes; render(); } },
  inicio: () => loadStartup(),
  programas: () => !S.jobs.programs && job("programs"),
  salud: () => !S.jobs.health && job("health"),
};
async function loadStartup() { try { S.startup = (await api("/api/startup")).items; if (S.page === "inicio" || S.page === "panel") render(); } catch (e) { toast(e.message, "bad"); } }

function junkTotal() {
  const t = res("clean_scan")?.targets || [];
  return t.filter((x) => x.selected && !x.locked).reduce((a, x) => a + (x.size || 0), 0);
}

const VIEWS = {
  panel() {
    const h = res("health"), sec = res("sec_status")?.defender, m = S.metrics;
    const c = m?.disks?.find((d) => d.letter === "C:");
    const alerts = [];
    (h?.report?.checks || []).filter((x) => x.status === "bad" || x.status === "warn").forEach((x) => alerts.push([x.status, x.title, x.detail, "salud"]));
    (res("sec_audit")?.findings || []).filter((f) => f.severity === "high" || f.severity === "medium").forEach((f) => alerts.push([sevChip[f.severity], f.title, f.detail, "seguridad"]));
    if (sec && sec.available && !sec.RealTimeProtectionEnabled) alerts.unshift(["bad", "Protección en tiempo real desactivada", "Actívala en Seguridad de Windows.", "seguridad"]);
    const junk = junkTotal();
    if (junk > 1 << 30) alerts.unshift(["warn", `${fmt(junk)} de archivos basura`, "Puedes liberarlos de forma segura.", "limpieza"]);
    const st = S.startup?.filter((x) => x.enabled).length;
    const sys = S.sys || {};
    return `
    <div class="card glow hero">
      ${ring(h?.score, running("health"))}
      <div>
        <div class="eyebrow">${esc(sys.host || "Tu equipo")} · ${esc(sys.os || "Windows")}</div>
        <h2>${h ? (h.score >= 85 ? "Tu PC está en <span class='grad-text'>plena forma</span>" : h.score >= 60 ? "Tu PC puede <span class='grad-text'>ir más rápido</span>" : "Tu PC <span class='grad-text'>necesita atención</span>") : "Analizando tu equipo…"}</h2>
        <p class="lead">${esc(h?.report?.summary_es || "Leyendo eventos del sistema, discos, memoria y protección. Mientras tanto puedes explorar el resto de herramientas.")}</p>
        <div class="row wrap">
          <button class="btn primary lg" data-act="optimize" ${running("optimize") ? "disabled" : ""}>${ic("rocket")}Optimizar ahora</button>
          <button class="btn lg" data-page="limpieza">${ic("clean")}Ver limpieza</button>
        </div>
        <div class="stats">
          <div class="stat" data-page="limpieza"><div class="k">${ic("clean")}Basura</div><div class="v">${running("clean_scan") && !junk ? '<div class="skeleton" style="width:70%;height:22px"></div>' : fmt(junk)}</div></div>
          <div class="stat" data-page="seguridad"><div class="k">${ic("shield")}Protección</div><div class="v ${sec ? (sec.RealTimeProtectionEnabled ? "ok" : "bad") : ""}">${sec ? (sec.RealTimeProtectionEnabled ? "Activa" : "Desactivada") : "…"}</div></div>
          <div class="stat" data-page="inicio"><div class="k">${ic("power")}Al inicio</div><div class="v">${st ?? "…"} <small>apps</small></div></div>
          <div class="stat" data-page="espacio"><div class="k">${ic("disk")}Libre en C:</div><div class="v">${c ? fmt(c.free) : "…"} <small>${c ? nf((c.free / c.total) * 100, 0) + "%" : ""}</small></div></div>
        </div>
      </div>
    </div>
    ${alerts.length ? `<div class="section-title">Recomendaciones</div><div class="card"><div class="list">${alerts.slice(0, 6).map(([s, t, d, pg]) => `<div class="item"><span class="dot ${s}"></span><div class="main-col"><div class="t">${esc(t)}</div><div class="s ellipsis">${esc(d)}</div></div><button class="btn sm" data-page="${pg}">Revisar</button></div>`).join("")}</div></div>` : ""}
    <div class="section-title">En directo</div>
    <div class="g g3">
      <div class="card"><div class="eyebrow">Procesador</div><div class="metric-big">${m ? nf(m.cpu, 0) : "—"}<small>%</small></div><svg class="spark mt" viewBox="0 0 300 70" preserveAspectRatio="none" id="sp-cpu">${spark(S.cpuH)}</svg><div class="muted ellipsis" style="font-size:12px">${esc(sys.cpu || "")}</div></div>
      <div class="card"><div class="eyebrow">Memoria</div><div class="metric-big">${m ? nf(m.mem.load, 0) : "—"}<small>%</small></div><svg class="spark mt" viewBox="0 0 300 70" preserveAspectRatio="none" id="sp-ram">${spark(S.ramH, 100, 300, 70, "url(#sparkFill2)", "#a78bfa")}</svg><div class="muted" style="font-size:12px">${m ? fmt(m.mem.total - m.mem.available) + " de " + fmt(m.mem.total) : ""}</div></div>
      <div class="card"><div class="eyebrow">Discos</div>${(m?.disks || []).map((d) => { const u = 1 - d.free / d.total; return `<div class="disk"><div class="row"><b>${d.letter}</b><span class="spacer"></span><span class="mono muted">${fmt(d.free)} libres</span></div><div class="bar ${u > 0.92 ? "bad" : u > 0.85 ? "warn" : ""}"><i style="width:${u * 100}%"></i></div></div>`; }).join("")}</div>
    </div>
    <div class="g g2 mt">
      <div class="card"><h3>Equipo</h3><p class="sub">${esc(sys.maker || "")} ${esc(sys.machine || "")}</p><dl class="kv">
        <dt>Sistema</dt><dd>${esc(sys.os || "—")} · build ${esc(sys.build || "")}</dd><dt>CPU</dt><dd>${esc(sys.cpu || "—")} · ${esc(sys.cores || "")}C/${esc(sys.threads || "")}T</dd>
        <dt>Gráficos</dt><dd>${esc((sys.gpus || []).join(" · ") || "—")}</dd><dt>RAM</dt><dd>${m ? fmt(m.mem.total) : "—"}</dd>
        <dt>Encendido</dt><dd>${m ? `${Math.floor(m.uptime / 86400)} d ${Math.floor((m.uptime % 86400) / 3600)} h` : "—"}</dd><dt>Instalado</dt><dd>${esc(sys.installDate || "—")}</dd></dl></div>
      <div class="card"><div class="card-head"><div><h3>Procesos que más memoria usan</h3></div><button class="btn sm ghost" data-act="procs">${ic("refresh")}</button></div>
        <div class="list">${(S.procs || []).map((p) => `<div class="item" style="padding:7px 10px"><div class="main-col ellipsis">${esc(p.name)} ${p.count > 1 ? `<span class="dim">×${p.count}</span>` : ""}</div><span class="size">${fmt(p.mem)}</span></div>`).join("") || '<div class="skeleton"></div>'}</div></div>
    </div>`;
  },

  limpieza() {
    const r = res("clean_scan"), t = r?.targets || [];
    if (!r) return jobline("clean_scan") || empty("clean", "Analizando basura…", "");
    const sel = S.sel.clean ||= new Set(t.filter((x) => x.selected && !x.locked).map((x) => x.key));
    const total = t.filter((x) => sel.has(x.key)).reduce((a, x) => a + (x.size || 0), 0);
    const groups = [...new Set(t.map((x) => x.group))];
    const locked = t.some((x) => x.locked);
    return `${jobline("clean_scan")}${jobline("clean_run")}
    ${locked ? `<div class="banner">${ic("lock")}<div class="spacer"><div class="t">Algunas zonas del sistema necesitan permisos de administrador</div><div class="s">Windows Temp, Windows Update y Optimización de distribución.</div></div><button class="btn sm" data-act="elevate">Ejecutar como admin</button></div>` : ""}
    ${groups.map((g) => `<div class="section-title">${esc(g)}</div><div class="card"><div class="list">${t.filter((x) => x.group === g).map((x) => `
      <label class="item ${sel.has(x.key) ? "sel" : ""}"><input type="checkbox" class="chk" data-act="tclean" data-v="${x.key}" ${sel.has(x.key) ? "checked" : ""} ${x.locked ? "disabled" : ""}>
      <div class="main-col"><div class="t">${esc(x.title)}${TIPS["clean_" + x.key] ? tip("clean_" + x.key) : ""} ${x.locked ? `<span class="chip">${ic("lock")}Admin</span>` : ""}</div><div class="s ellipsis">${esc(x.description)}</div></div>
      <button class="btn sm ghost" data-act="cdet" data-v="${x.key}" title="Qué se borra exactamente">${ic("info")}Detalles</button>
      <span class="size">${x.size == null ? '<span class="spinner" style="display:inline-block"></span>' : fmt(x.size)}</span></label>`).join("")}</div></div>`).join("")}
    <div class="section-title">Automático</div>
    <div class="card"><div class="item"><label class="switch"><input type="checkbox" data-act="autoc" ${S.auto?.enabled ? "checked" : ""}><span></span></label>
      <div class="main-col"><div class="t">Limpieza automática semanal</div><div class="s">Limpia solo las categorías seguras marcadas por defecto, sin permisos de administrador. Queda anotado en el historial.</div></div>
      <select class="input" id="auto-day" data-act="autod">${Object.entries({ MON: "Lunes", TUE: "Martes", WED: "Miércoles", THU: "Jueves", FRI: "Viernes", SAT: "Sábado", SUN: "Domingo" }).map(([k, l]) => `<option value="${k}" ${(S.auto?.day || "SUN") === k ? "selected" : ""}>${l} 12:00</option>`).join("")}</select></div></div>
    <div class="actionbar"><div><div class="muted" style="font-size:12px">Seleccionado</div><div class="total grad-text">${fmt(total)}</div></div><span class="spacer"></span>
      <button class="btn ghost" data-act="rescan-clean">${ic("refresh")}Volver a analizar</button>
      <button class="btn primary" data-act="clean" ${!sel.size || running("clean_run") ? "disabled" : ""}>${ic("clean")}Limpiar ahora</button></div>`;
  },

  espacio() {
    const sp = S.space, tab = sp.tab, r = res(tab);
    const seg = `<div class="seg">${[["large", "Archivos grandes"], ["folders", "Carpetas"], ["unused", "Sin usar"], ["devjunk", "Desarrollo"], ["organize_plan", "Organizar Descargas"]].map(([k, l]) => `<button class="${tab === k ? "on" : ""}" data-act="stab" data-v="${k}">${l}</button>`).join("")}</div>`;
    if (tab === "devjunk" || tab === "organize_plan") return `<div class="toolbar">${seg}${tip(tab)}<span class="spacer"></span><button class="btn primary" data-act="sscan" ${running(tab) ? "disabled" : ""}>${ic("search")}Analizar</button></div>` + jobline(tab) + (tab === "devjunk" ? devView(r) : orgView(r));
    const opts = tab === "large" ? `<select class="input" id="opt-min" data-act="sopt">${[50, 100, 200, 500, 1000].map((v) => `<option value="${v}" ${sp.minMb == v ? "selected" : ""}>Más de ${v >= 1000 ? "1 GB" : v + " MB"}</option>`).join("")}</select>`
      : tab === "unused" ? `<select class="input" id="opt-days" data-act="sopt">${[90, 180, 365, 730].map((v) => `<option value="${v}" ${sp.days == v ? "selected" : ""}>Sin abrir en ${v >= 365 ? v / 365 + (v > 365 ? " años" : " año") : v + " días"}</option>`).join("")}</select>` : "";
    const bar = `<div class="toolbar">${seg}${opts}<label class="opt"><input type="checkbox" class="chk" id="opt-drive" data-act="sopt" ${sp.drive ? "checked" : ""}>Incluir Google Drive</label><span class="spacer"></span><button class="btn primary" data-act="sscan" ${running(tab) ? "disabled" : ""}>${ic("search")}Analizar</button></div>`;
    if (!r) return bar + (jobline(tab) || empty("disk", "Encuentra lo que ocupa espacio", "Analiza Descargas, Documentos, Escritorio, Vídeos, Imágenes y Música."));
    if (tab === "folders") {
      const f = r.folders || [], max = f[0]?.size || 1;
      return bar + jobline(tab) + `<div class="card"><div class="list">${f.map((x) => `<div class="item"><div class="ico">${ic("folder")}</div><div class="main-col"><div class="t ellipsis">${esc(base(x.path))}</div><div class="s ellipsis">${esc(x.path)} · ${nf(x.file_count, 0)} archivos</div><div class="bar thin mt" style="margin-top:6px"><i style="width:${(x.size / max) * 100}%"></i></div></div><span class="size">${fmt(x.size)}</span><button class="btn sm ghost icon-btn" data-act="reveal" data-v="${esc(x.path)}">${ic("eye")}</button></div>`).join("") || empty("folder", "Sin resultados", "")}</div></div>`;
    }
    return bar + jobline(tab) + fileList(tab, r.files || [], tab === "unused");
  },

  duplicados() {
    const d = S.dupes, r = res("dupes");
    const bar = `<div class="toolbar"><select class="input" id="dup-min" data-act="dopt">${[0, 1, 10, 100].map((v) => `<option value="${v}" ${d.minMb == v ? "selected" : ""}>${v ? "Más de " + v + " MB" : "Todos los tamaños"}</option>`).join("")}</select>
      <label class="opt"><input type="checkbox" class="chk" id="dup-drive" data-act="dopt" ${d.drive ? "checked" : ""}>Incluir Google Drive</label>${tip("drive")}<span class="spacer"></span>
      <button class="btn primary" data-act="dscan" ${running("dupes") ? "disabled" : ""}>${ic("copy")}Buscar duplicados</button></div>`;
    if (!r) return bar + (jobline("dupes") || empty("copy", "Libera espacio eliminando copias", "Se comparan tamaño, huella y contenido completo: solo verás archivos 100% idénticos."));
    const g = r.groups || [], sel = selSet("dupes");
    const wasted = g.reduce((a, x) => a + x.wasted, 0);
    const selSize = g.reduce((a, x) => a + x.paths.filter((p) => sel.has(p)).length * x.size, 0);
    return bar + jobline("dupes") + `
      <div class="g g3"><div class="card"><div class="eyebrow">Grupos</div><div class="metric-big">${g.length}</div></div><div class="card"><div class="eyebrow">Recuperable</div><div class="metric-big grad-text">${fmt(wasted)}</div></div>
      <div class="card"><div class="eyebrow">Selección rápida</div><button class="btn mt" data-act="dauto">${ic("check")}Marcar copias (conservar la más antigua)</button></div></div>
      <div class="mt">${g.slice(0, 200).map((x) => `<div class="dgroup"><div class="dh"><b class="mono">${fmt(x.size)}</b><span class="muted">× ${x.paths.length} copias</span><span class="spacer"></span><span class="chip warn">${fmt(x.wasted)} repetidos</span></div>
        ${x.paths.map((p, i) => `<label class="item ${sel.has(p) ? "sel" : ""}"><input type="checkbox" class="chk" data-act="tsel" data-k="dupes" data-v="${esc(p)}" ${sel.has(p) ? "checked" : ""}><div class="main-col"><div class="t ellipsis">${esc(base(p))} ${i === 0 ? '<span class="chip ok">Original sugerido</span>' : ""}</div><div class="s ellipsis">${esc(dir(p))} · ${date(x.mtimes[i])}</div></div><button class="btn sm ghost icon-btn" data-act="reveal" data-v="${esc(p)}">${ic("eye")}</button></label>`).join("")}</div>`).join("") || empty("check", "No hay duplicados", "¡Todo en orden!")}</div>
      ${sel.size ? `<div class="actionbar"><div><div class="muted" style="font-size:12px">${sel.size} archivos</div><div class="total grad-text">${fmt(selSize)}</div></div><span class="spacer"></span><button class="btn ghost" data-act="clrsel" data-v="dupes">Quitar selección</button><button class="btn danger" data-act="recycle" data-v="dupes">${ic("trash")}Enviar a la papelera</button></div>` : ""}`;
  },

  seguridad() {
    const s = res("sec_status"), d = s?.defender, f = res("sec_audit")?.findings || [];
    const high = f.filter((x) => x.severity === "high").length;
    const ok = d?.available && d.RealTimeProtectionEnabled && d.AntivirusEnabled && !high;
    const scanBusy = running("console");
    return `${jobline("sec_status")}${jobline("sec_audit")}
    <div class="card glow hero" style="grid-template-columns:200px 1fr">
      <div class="shield ${ok ? "" : "alert"}"><div class="halo"></div><svg viewBox="0 0 24 24" fill="none" stroke="${ok ? "#34d399" : d ? "#fb7185" : "#7f8b9d"}" stroke-width="1.1"><path d="${P.shield}"/></svg></div>
      <div><div class="eyebrow">Microsoft Defender</div><h2>${!d ? "Comprobando protección…" : ok ? "Estás <span class='grad-text'>protegido</span>" : "Hay puntos que <span class='grad-text'>revisar</span>"}</h2>
        <p class="lead">El análisis usa el motor y las firmas oficiales de Defender. La auditoría busca cambios típicos del malware: inicio, tareas programadas, hosts, proxy y firewall.</p>
        <div class="row wrap"><button class="btn primary" data-act="scan" data-v="quick" ${scanBusy ? "disabled" : ""}>${ic("play")}Análisis rápido</button><button class="btn" data-act="scan" data-v="full" ${scanBusy ? "disabled" : ""}>${ic("shield")}Análisis completo</button><button class="btn" data-act="sigupd" ${scanBusy ? "disabled" : ""}>${ic("refresh")}Actualizar firmas</button><button class="btn ghost" data-act="audit">${ic("search")}Repetir auditoría</button></div>
        ${d?.available ? `<div class="stats"><div class="stat"><div class="k">Tiempo real</div><div class="v ${d.RealTimeProtectionEnabled ? "ok" : "bad"}">${d.RealTimeProtectionEnabled ? "Activo" : "Apagado"}</div></div>
          <div class="stat"><div class="k">Firmas</div><div class="v ${d.AntivirusSignatureAge > 3 ? "warn" : ""}">${d.AntivirusSignatureAge === 0 ? "Hoy" : d.AntivirusSignatureAge + " días"}</div></div>
          <div class="stat"><div class="k">Último análisis</div><div class="v">${d.QuickScanAge == null ? "Nunca" : d.QuickScanAge === 0 ? "Hoy" : "hace " + d.QuickScanAge + " d"}</div></div>
          <div class="stat"><div class="k">Antimanipulación</div><div class="v ${d.IsTamperProtected ? "ok" : "warn"}">${d.IsTamperProtected ? "Sí" : "No"}</div></div></div>` : d ? `<div class="banner bad mt">${ic("alert")}<div>No se pudo leer Defender. Puede haber otro antivirus instalado.</div></div>` : ""}
      </div></div>
    <div class="section-title">Auditoría del sistema</div>
    <div class="card"><div class="list">${f.map((x) => `<div class="item"><span class="chip ${sevChip[x.severity]}">${sevTxt[x.severity]}</span><div class="main-col"><div class="t">${esc(x.title)} <span class="dim">· ${esc(x.area)}</span></div><div class="s">${esc(x.detail)}</div>${x.path ? `<div class="s mono ellipsis dim">${esc(x.path)}</div>` : ""}</div></div>`).join("") || (running("sec_audit") ? '<div class="skeleton"></div>' : empty("check", "Sin hallazgos", ""))}</div></div>
    <div class="section-title">Historial de amenazas</div>
    <div class="card">${(s?.threats || []).length ? `<table class="tbl"><tr><th style="width:40%">Amenaza</th><th>Gravedad</th><th>Estado</th><th>Fecha</th></tr>${s.threats.map((t) => `<tr><td class="ellipsis">${esc(t.name)}<div class="path ellipsis">${esc((t.resources || []).join(" · "))}</div></td><td>${esc(t.severity_es)}</td><td><span class="chip ${/Error|Detectada|Permitida/.test(t.status_es) ? "warn" : "ok"}">${esc(t.status_es)}</span></td><td class="mono">${esc(t.when)}</td></tr>`).join("")}</table>` : empty("shield", "Sin amenazas registradas", "Defender no ha detectado nada en este equipo.")}</div>`;
  },

  reparar() {
    if (!S.fixes) return '<div class="skeleton"></div>';
    const groups = [...new Set(S.fixes.map((f) => f.group))];
    return `${S.admin ? "" : `<div class="banner">${ic("key")}<div class="spacer"><div class="t">La mayoría de reparaciones necesitan permisos de administrador</div><div class="s">Reinicia la app con permisos elevados para desbloquearlas.</div></div><button class="btn sm primary" data-act="elevate">Ejecutar como admin</button></div>`}
    <div class="banner info">${ic("info")}<div><div class="t">Consejo</div><div class="s">Empieza creando un punto de restauración. Orden recomendado si Windows falla: SFC → DISM → SFC otra vez → CHKDSK.</div></div></div>
    ${groups.map((g) => `<div class="section-title">${esc(g)}</div><div class="g gauto">${S.fixes.filter((f) => f.group === g).map((f) => `
      <div class="card fix"><div class="row"><div class="ico">${ic(f.icon)}</div><h3 class="spacer">${esc(f.title)}${TIPS["fix_" + f.id] ? tip("fix_" + f.id) : ""}</h3></div><p>${esc(f.description)}</p>
      <div class="foot"><span class="chip">${ic("clock")}${esc(f.minutes)}</span>${f.admin ? `<span class="chip ${S.admin ? "acc" : ""}">${ic("key")}Admin</span>` : ""}${f.reboot ? '<span class="chip warn">Reinicio</span>' : ""}
      <button class="btn sm ${f.id === "restore_point" ? "primary" : ""}" data-act="fix" data-v="${f.id}" ${(f.admin && !S.admin) || running("console") ? "disabled" : ""}>${ic("play")}Ejecutar</button></div></div>`).join("")}</div>`).join("")}`;
  },

  salud() {
    const h = res("health");
    if (!h) return jobline("health") || empty("pulse", "Diagnosticando…", "");
    const r = h.report;
    return `${jobline("health")}<div class="card glow hero">${ring(h.score, running("health"))}<div><div class="eyebrow">${esc(h.label)}</div><h2>Diagnóstico de estabilidad</h2><p class="lead">${esc(r.summary_es)}</p>
      <div class="row wrap"><button class="btn primary" data-act="health">${ic("refresh")}Volver a diagnosticar</button><button class="btn" data-act="report">${ic("file")}Exportar informe</button></div>
      ${r.needs_admin ? `<div class="banner mt">${ic("lock")}<div>${esc(r.admin_hint)}</div></div>` : ""}</div></div>
    <div class="section-title">Comprobaciones</div>
    <div class="g g3">${r.checks.map((c) => `<div class="card"><div class="row"><span class="dot ${c.status}"></span><h3 class="spacer">${esc(c.title)}</h3><span class="chip ${sevChip[c.status]}">${sevTxt[c.status]}</span></div><p class="muted mono" style="font-size:12px;white-space:pre-wrap;margin:10px 0 0">${esc(c.detail)}</p></div>`).join("")}</div>
    <div class="section-title">Línea temporal (30 días)</div>
    <div class="card">${r.events.length ? `<div class="timeline">${r.events.slice(0, 40).map((e) => `<div class="tl ${["power", "unexpected_shutdown", "bugcheck", "whea"].includes(e.category) ? "bad" : "warn"}"><div class="when">${esc((e.time || "").replace("T", " "))} · ${esc(e.source)} #${e.event_id}</div><div class="t">${esc(e.probable_cause_es)}</div><div class="muted ellipsis" style="font-size:12px">${esc(e.message)}</div></div>`).join("")}</div>` : empty("check", "Sin caídas registradas", "No hay apagados inesperados ni pantallas azules recientes.")}</div>
    <div class="section-title">Mantener el PC joven</div><div class="card"><div class="list">${h.tips.map((t) => `<div class="item">${ic("check")}<div class="main-col">${esc(t)}</div></div>`).join("")}</div></div>`;
  },

  inicio() {
    const tab = S.bgTab || "start";
    const seg = `<div class="toolbar"><div class="seg">${[["start", "Al iniciar"], ["procs", "Abiertas ahora"], ["services", "Servicios"], ["tasks", "Tareas programadas"]].map(([k, l]) => `<button class="${tab === k ? "on" : ""}" data-act="bgtab" data-v="${k}">${l}</button>`).join("")}</div>${tip("bg_" + tab)}<span class="spacer"></span>${tab !== "start" ? `<button class="btn sm" data-act="bgload">${ic("refresh")}Actualizar</button>` : ""}</div>`;
    if (tab !== "start") return seg + bgView(tab);
    const it = S.startup;
    if (!it) return seg + '<div class="skeleton"></div>';
    const on = it.filter((x) => x.enabled).length;
    return seg + `<div class="banner info">${ic("info")}<div><div class="t">${on} de ${it.length} programas arrancan con Windows</div><div class="s">Desactivar es reversible: funciona igual que el Administrador de tareas y no borra nada. Los marcados con candado son esenciales y están protegidos.</div></div></div>
    <div class="card"><div class="list">${it.map((x, i) => `<div class="item">${x.essential ? `<span class="chip ok" style="width:40px;justify-content:center">${ic("lock")}</span>` : `<label class="switch"><input type="checkbox" data-act="stog" data-v="${i}" ${x.enabled ? "checked" : ""}><span></span></label>`}
      <div class="main-col"><div class="t">${esc(x.name)} ${x.suspicious && x.suspicious[0] !== "low" ? `<span class="chip ${sevChip[x.suspicious[0]]}">${ic("alert")}${esc(x.suspicious[1])}</span>` : ""}</div><div class="s mono ellipsis">${esc(x.command)}</div></div>
      <span class="chip">${esc(x.location)}</span><span class="chip ${x.impact === "alto" ? "warn" : x.impact === "medio" ? "info" : ""}">Impacto ${esc(x.impact)}</span></div>`).join("")}</div></div>`;
  },

  programas() {
    const r = res("programs");
    if (!r) return jobline("programs") || empty("apps", "Cargando programas…", "");
    const { q, f } = S.prog;
    let list = r.programs.filter((p) => !q || (p.name + " " + p.publisher).toLowerCase().includes(q.toLowerCase()));
    if (f === "unused") list = list.filter((p) => p.likely_unused);
    if (f === "big") list = [...list].sort((a, b) => (b.estimated_size_kb || 0) - (a.estimated_size_kb || 0)).slice(0, 40);
    const unused = r.programs.filter((p) => p.likely_unused).length;
    return `<div class="toolbar"><div class="search-big" style="flex:1;max-width:420px">${ic("search")}<input class="input" id="prog-q" data-act="pq" placeholder="Filtrar programas…" value="${esc(q)}" style="height:40px;font-size:14px"></div>
      <div class="seg">${[["all", "Todos " + r.programs.length], ["unused", "Sin uso " + unused], ["big", "Más grandes"]].map(([k, l]) => `<button class="${f === k ? "on" : ""}" data-act="pf" data-v="${k}">${l}</button>`).join("")}</div></div>
    <div class="card"><table class="tbl"><tr><th style="width:44%">Programa</th><th class="num">Tamaño</th><th class="num">Último uso</th><th style="width:140px"></th></tr>
    ${list.map((p) => `<tr><td><div class="ellipsis">${esc(p.name)} ${p.likely_unused ? '<span class="chip warn">Sin uso</span>' : ""}</div><div class="path ellipsis">${esc(p.publisher)} ${esc(p.version)}</div></td>
      <td class="num">${p.estimated_size_kb ? fmt(p.estimated_size_kb * 1024) : "—"}</td><td class="num">${p.days_since_touch != null ? "hace " + p.days_since_touch + " d" : "—"}</td>
      <td style="text-align:right">${p.can_uninstall ? `<button class="btn sm danger" data-act="uninst" data-v="${esc(p.name)}">${ic("trash")}Desinstalar</button>` : ""}</td></tr>`).join("")}</table></div>`;
  },

  buscar() {
    const r = res("search");
    return `<div class="search-big">${ic("search")}<input class="input" id="sq" placeholder="Escribe un nombre y pulsa Intro…" value="${esc(S.sq || "")}"></div><div class="mt">${jobline("search")}</div>
    ${r ? fileList("search", (r.hits || []).map((h) => ({ path: h.path, size: h.size, folder: h.kind === "folder" }))) : ""}`;
  },
};

function fileList(key, files, showDays) {
  const sel = selSet(key);
  const selSize = files.filter((f) => sel.has(f.path)).reduce((a, f) => a + f.size, 0);
  if (!files.length) return empty("check", "Nada por aquí", "No se encontraron archivos con estos filtros.");
  return `<div class="card"><div class="list">${files.map((f) => `<label class="item ${sel.has(f.path) ? "sel" : ""}">${f.folder ? `<div class="ico">${ic("folder")}</div>` : `<input type="checkbox" class="chk" data-act="tsel" data-k="${key}" data-v="${esc(f.path)}" ${sel.has(f.path) ? "checked" : ""}>`}
    <div class="main-col"><div class="t ellipsis">${esc(base(f.path))} ${f.category ? `<span class="chip">${esc(f.category)}</span>` : ""}</div><div class="s ellipsis">${esc(dir(f.path))}${showDays ? ` · sin usar ${f.days} días` : f.mtime ? " · " + date(f.mtime) : ""}</div></div>
    <span class="size">${f.folder ? "" : fmt(f.size)}</span><button class="btn sm ghost icon-btn" data-act="reveal" data-v="${esc(f.path)}" title="Mostrar en el Explorador">${ic("eye")}</button></label>`).join("")}</div></div>
  ${sel.size ? `<div class="actionbar"><div><div class="muted" style="font-size:12px">${sel.size} archivos</div><div class="total grad-text">${fmt(selSize)}</div></div><span class="spacer"></span><button class="btn ghost" data-act="clrsel" data-v="${key}">Quitar selección</button><button class="btn danger" data-act="recycle" data-v="${key}">${ic("trash")}Enviar a la papelera</button></div>` : ""}`;
}

/* ---------------- Acciones ---------------- */
async function optimize() {
  const auto = (res("clean_scan")?.targets || []).filter((x) => x.selected && !x.locked && x.key !== "recycle");
  const ok = await askDetailed("Optimizar ahora", (auto.length ? cleanSummary(auto) : "<p>Limpieza de temporales y cachés seguras.</p>")
    + `<p class="mt">Después: <b>vaciar la caché DNS</b> (las webs se resuelven de nuevo) y <b>diagnóstico de salud</b> (solo lectura).</p>`, "Optimizar");
  if (!ok) return;
  const w = modal(`<div class="boost"><div class="orbit" id="ob"><i></i><i></i><i></i><b></b></div><div class="big grad-text" id="ob-n">0 B</div><div class="muted" id="ob-m">Preparando…</div><div class="progress mt"><i id="ob-p" style="width:0"></i></div><div class="console mt" id="ob-log" style="height:140px;text-align:left"></div><div class="foot"><button class="btn" id="ob-close" disabled>Cerrar</button></div></div>`);
  const iv = setInterval(() => { const j = S.jobs.optimize; if (!j) return; w.querySelector("#ob-m").textContent = j.message; w.querySelector("#ob-p").style.width = (j.progress || 0) * 100 + "%"; w.querySelector("#ob-log").textContent = j.log.join("\n"); if (j.result?.freed != null) w.querySelector("#ob-n").textContent = fmt(j.result.freed); }, 400);
  const s = await job("optimize");
  clearInterval(iv);
  w.querySelector("#ob").classList.add("done");
  w.querySelector("#ob-close").disabled = false;
  w.querySelector("#ob-close").onclick = () => w.remove();
  if (s?.state === "done") {
    w.querySelector("#ob-n").textContent = fmt(s.result.freed);
    w.querySelector("#ob-m").textContent = `liberados · salud ${s.result.score}/100 (${s.result.label})`;
    w.querySelector("#ob-log").textContent = s.log.join("\n");
    job("health"); job("clean_scan"); delete S.sel.clean;
  } else if (s) {
    w.querySelector("#ob-n").textContent = fmt(s.result?.freed || 0);
    w.querySelector("#ob-m").innerHTML = `<span class="warn">Se detuvo antes de terminar: ${esc(s.error || s.state)}</span> · lo liberado hasta ahí se mantiene`;
    w.querySelector("#ob-log").textContent = s.log.join("\n");
  }
}

async function recycle(key) {
  const paths = [...selSet(key)];
  const sizes = {};
  const rr0 = res(key);
  (rr0?.files || rr0?.hits || []).forEach((f) => (sizes[f.path] = f.size));
  (rr0?.groups || []).forEach((g) => g.paths.forEach((p) => (sizes[p] = g.size)));
  if (!(await askDetailed(`Enviar ${paths.length} archivos a la Papelera`, filesSummary(paths, sizes), "Enviar a la papelera", true))) return;
  const r = await api("/api/files/recycle", { paths }).catch((e) => toast(e.message, "bad"));
  if (!r) return;
  const gone = new Set(r.recycled.map((x) => x.path));
  toast(`${r.recycled.length} archivos a la papelera · ${fmt(r.freed)}` + (r.failed.length ? ` · ${r.failed.length} no se pudieron mover` : ""), r.failed.length ? "warn" : "ok");
  selSet(key).clear();
  const slot = key === "dupes" ? "dupes" : key;
  const rr = res(slot);
  if (rr?.files) rr.files = rr.files.filter((f) => !gone.has(f.path));
  if (rr?.hits) rr.hits = rr.hits.filter((f) => !gone.has(f.path));
  if (rr?.groups) rr.groups = rr.groups.map((g) => { const keep = g.paths.map((p, i) => [p, g.mtimes[i]]).filter(([p]) => !gone.has(p)); return { ...g, paths: keep.map((x) => x[0]), mtimes: keep.map((x) => x[1]), wasted: g.size * Math.max(0, keep.length - 1) }; }).filter((g) => g.paths.length > 1);
  render();
}

const ACT = {
  optimize,
  cancel: (v) => cancel(v),
  procs: async () => { S.procs = (await api("/api/processes")).processes; render(); },
  elevate: async () => {
    if (!(await ask("Ejecutar como administrador", "Windows pedirá confirmación y la app se abrirá de nuevo con permisos elevados. Esta ventana se cerrará.", "Reiniciar como admin"))) return;
    const r = await api("/api/elevate", {}).catch(() => null);
    if (r?.ok) { toast("Abriendo con permisos de administrador…"); setTimeout(() => window.close(), 1200); } else toast("No se concedieron permisos.", "warn");
  },
  tclean: (v) => { const s = S.sel.clean; s.has(v) ? s.delete(v) : s.add(v); render(); },
  "rescan-clean": () => { delete S.sel.clean; job("clean_scan"); },
  clean: async () => {
    const keys = [...S.sel.clean];
    const t = res("clean_scan").targets.filter((x) => S.sel.clean.has(x.key));
    const risky = t.filter((x) => RISKY_CLEAN.has(x.key));
    if (!(await askDetailed(`Limpiar ${fmt(t.reduce((a, x) => a + (x.size || 0), 0))}`, cleanSummary(t), "Limpiar ahora", risky.length > 0,
      risky.length ? `Entiendo que ${risky.map((x) => x.title).join(", ")} no se puede recuperar` : ""))) return;
    const s = await job("clean_run", { keys });
    if (s?.state === "done") { toast(`¡Listo! ${fmt(s.result.freed)} liberados`); delete S.sel.clean; job("clean_scan"); }
  },
  stab: (v) => { S.space.tab = v; render(); if ((v === "devjunk" || v === "organize_plan") && !S.jobs[v]) ACT.sscan(); },
  sopt: () => { const sp = S.space; sp.minMb = +($("#opt-min")?.value || sp.minMb); sp.days = +($("#opt-days")?.value || sp.days); sp.drive = $("#opt-drive").checked; },
  sscan: () => { const sp = S.space; selSet(sp.tab).clear(); if (sp.tab === "devjunk" || sp.tab === "organize_plan") return job(sp.tab); job(sp.tab, { min_mb: sp.tab === "unused" ? 10 : sp.minMb, days: sp.days, include_drive: sp.drive }); },
  dopt: () => { S.dupes.minMb = +$("#dup-min").value; S.dupes.drive = $("#dup-drive").checked; },
  dscan: () => { selSet("dupes").clear(); job("dupes", { min_mb: S.dupes.minMb, include_drive: S.dupes.drive }); },
  dauto: () => { const s = selSet("dupes"); s.clear(); res("dupes").groups.forEach((g) => g.paths.slice(1).forEach((p) => s.add(p))); render(); },
  tsel: (v, el) => { const s = selSet(el.dataset.k); s.has(v) ? s.delete(v) : s.add(v); render(); },
  clrsel: (v) => { selSet(v).clear(); render(); },
  recycle,
  reveal: (v) => api("/api/files/reveal", { path: v }),
  scan: (v) => consoleJob(v === "full" ? "Análisis completo de Defender" : "Análisis rápido de Defender", "sec_scan", { type: v }).then(() => job("sec_status")),
  sigupd: () => consoleJob("Actualizar firmas de Defender", "sec_update", {}).then(() => job("sec_status")),
  audit: () => job("sec_audit"),
  fix: async (v) => {
    const f = S.fixes.find((x) => x.id === v);
    const tw = TIPS["fix_" + v], warn = tw && tw[0] !== "info";
    if (!(await askDetailed(f.title, fixSummary(f) + (warn ? `<div class="banner mt">${ic("alert")}<div><div class="t">${esc(tw[1])}</div><div class="s">${esc(tw[2])}</div></div></div>` : ""),
      "Ejecutar", warn, warn ? "Entiendo las consecuencias" : ""))) return;
    consoleJob(f.title, "fix", { id: v });
  },
  health: () => job("health"),
  report: async () => { const r = await api("/api/report", {}).catch((e) => toast(e.message, "bad")); if (r?.ok) toast("Informe guardado en Descargas"); },
  stog: async (v, el) => {
    const it = S.startup[+v];
    const r = await api("/api/startup/toggle", { name: it.name, hive: it.hive, approved: it.approved, enabled: el.checked }).catch((e) => ({ ok: false, message: e.message }));
    toast(r.message, r.ok ? "ok" : "warn");
    if (r.ok) it.enabled = el.checked; else el.checked = !el.checked;
  },
  pf: (v) => { S.prog.f = v; render(); },
  autoc: async (_v, el) => {
    const r = await api("/api/autoclean", { enabled: el.checked, day: $("#auto-day").value }).catch((e) => ({ ok: false, message: e.message }));
    toast(r.message, r.ok ? "ok" : "warn");
    S.auto = await api("/api/autoclean").catch(() => null); render();
  },
  autod: () => { if (S.auto?.enabled) ACT.autoc(null, { checked: true }); },
  shortcut: async () => {
    if (!(await ask("Crear acceso directo", "Se creará «Limpiador PC Nova» en tu <b>escritorio</b> y en el <b>menú Inicio</b>, apuntando a la ubicación actual de la app. Si después la mueves de carpeta, vuelve a pulsar este botón.", "Crear"))) return;
    const r = await api("/api/shortcuts", {}).catch((e) => ({ ok: false, message: e.message }));
    toast(r.message, r.ok ? "ok" : "warn");
  },
  hist: async () => {
    const r = await api("/api/history");
    const w = modal(`<h3>Historial</h3><div class="console mt">${esc(r.lines.join("\n") || "Todavía no hay acciones registradas.")}</div><div class="foot"><button class="btn" data-r>Cerrar</button></div>`, true);
    w.addEventListener("click", (e) => { if (e.target.closest("[data-r]") || e.target === w) w.remove(); });
  },
  uninst: async (v) => {
    if (!(await ask("Desinstalar", `Se abrirá el desinstalador oficial de <b>${esc(v)}</b>. Sigue sus pasos para completarlo.`, "Abrir desinstalador", true))) return;
    const r = await api("/api/programs/uninstall", { name: v }); toast(r.message, r.ok ? "ok" : "warn");
  },
};

document.addEventListener("click", (e) => {
  const pg = e.target.closest("[data-page]");
  if (pg && !e.target.closest("[data-act]")) return go(pg.dataset.page);
  const a = e.target.closest("[data-act]");
  if (!a || a.tagName === "SELECT" || a.id === "prog-q") return;
  if (a.tagName === "INPUT" && !["tclean", "tsel", "stog", "sopt", "dopt", "autoc", "svc", "task", "orgskip", "orgren", "soldone"].includes(a.dataset.act)) return;
  if (a.tagName === "BUTTON") e.preventDefault();
  if (a.closest("label") && a.tagName !== "INPUT") e.preventDefault();
  (ACT[a.dataset.act] || EXTRA_ACT[a.dataset.act])?.(a.dataset.v, a);
});
document.addEventListener("change", (e) => { const a = e.target.closest("select[data-act]"); if (a) ACT[a.dataset.act]?.(a.value, a); });
document.addEventListener("input", (e) => { if (e.target.id === "prog-q") { S.prog.q = e.target.value; render(); } });
document.addEventListener("keydown", (e) => {
  if (e.target.id === "sq" && e.key === "Enter" && e.target.value.trim()) { S.sq = e.target.value.trim(); selSet("search").clear(); job("search", { query: S.sq }); }
});
addEventListener("pagehide", () => navigator.sendBeacon("/api/bye"));

/* ---------------- Arranque ---------------- */
async function poll() {
  try {
    const m = await api("/api/metrics");
    S.metrics = m;
    S.cpuH.push(m.cpu); S.ramH.push(m.mem.load);
    if (S.cpuH.length > 60) { S.cpuH.shift(); S.ramH.shift(); }
    $("#live-cpu").textContent = nf(m.cpu, 0) + "%"; $("#live-ram").textContent = m.mem.load + "%";
    $("#mini-cpu").innerHTML = spark(S.cpuH.slice(-20), 100, 56, 18);
    $("#mini-ram").innerHTML = spark(S.ramH.slice(-20), 100, 56, 18, "url(#sparkFill2)", "#a78bfa");
    if (S.page === "panel") {
      const c = $("#sp-cpu"), r = $("#sp-ram");
      if (c) { c.innerHTML = spark(S.cpuH); r.innerHTML = spark(S.ramH, 100, 300, 70, "url(#sparkFill2)", "#a78bfa"); c.previousElementSibling.innerHTML = nf(m.cpu, 0) + "<small>%</small>"; r.previousElementSibling.innerHTML = m.mem.load + "<small>%</small>"; }
    }
  } catch {}
  setTimeout(poll, 1500);
}

(async function init() {
  go("panel");
  poll();
  try { const o = await api("/api/overview"); S.admin = o.admin; S.sys = o.system; nav(); if (S.page === "panel") render(); } catch (e) { toast("No se pudo conectar con el motor: " + e.message, "bad"); }
  ACT.procs();
  loadStartup();
  job("health"); job("clean_scan"); job("sec_status"); job("sec_audit");
})();
