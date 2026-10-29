"use strict";
/* Tooltips de riesgo, Smally, tema día/noche y vistas de segundo plano, desarrollo y organizar. */

// [nivel, título, explicación]  nivel: info | warn | bad
const TIPS = {
  clean_recycle: ["bad", "Borrado definitivo", "Vacía la Papelera para siempre. Si acabas de enviar duplicados o archivos ahí, ya no podrás recuperarlos."],
  clean_crashdumps: ["warn", "Guárdalos si investigas caídas", "Los volcados explican las pantallas azules. Tu equipo tiene caídas recientes: exporta el informe de Salud antes de borrarlos."],
  clean_wu_download: ["info", "Seguro salvo durante una actualización", "Son instaladores ya aplicados. No lo limpies mientras Windows Update esté instalando algo."],
  clean_delivery: ["info", "Seguro", "Caché para compartir actualizaciones con otros PCs. Windows la regenera si hace falta."],
  clean_recent: ["info", "Solo accesos directos", "Vacía la lista de 'Recientes'. Tus archivos no se tocan."],
  clean_nuget: ["info", "Se vuelven a descargar", "Si programas en .NET, la siguiente compilación tardará más porque descargará los paquetes otra vez."],
  clean_spotify: ["info", "Se vuelve a descargar", "Las canciones en caché se volverán a bajar al escucharlas. Las descargadas para escuchar sin conexión no se tocan."],
  clean_temp_user: ["info", "Seguro", "Archivos temporales. Si alguno está en uso, se salta automáticamente. Cierra instaladores abiertos antes."],
  clean_chrome: ["info", "No borra contraseñas ni historial", "Solo la caché. Las webs tardarán un poco más la primera vez que las abras."],
  fix_net_reset: ["warn", "Puede afectar a VPN y redes guardadas", "Restablece Winsock y TCP/IP. Algunas VPN o configuraciones de IP fija tendrán que volver a configurarse. Úsalo solo si no hay Internet."],
  fix_hibernate_off: ["warn", "Pierdes hibernación e inicio rápido", "Libera varios GB, pero el portátil no podrá hibernar. Reversible con powercfg /hibernate on."],
  fix_wu_reset: ["info", "Seguro y reversible", "Renombra carpetas de Windows Update a .bak; Windows las recrea. Se crea un punto de restauración antes."],
  fix_component_cleanup: ["info", "Seguro", "Tras esto no podrás desinstalar actualizaciones antiguas de Windows (las recientes sí)."],
  fix_compactos: ["info", "Seguro y reversible", "Comprime Windows de forma transparente. En equipos muy lentos puede notarse un poco al abrir apps. Se revierte con compact /compactos:never."],
  fix_spooler: ["warn", "Cancela impresiones pendientes", "Los documentos en cola de impresión se pierden y habrá que volver a mandarlos."],
  fix_power_high: ["info", "Más consumo", "Más rendimiento, pero la batería dura menos y el portátil se calienta más."],
  fix_memtest: ["info", "Reinicia el equipo", "Windows se reinicia y comprueba la RAM antes de arrancar (unos 15 min)."],
  fix_ip_renew: ["info", "Corte breve", "Te quedas sin Internet unos segundos."],
  bg_start: ["info", "Qué es seguro desactivar", "Actualizadores, launchers de juegos, chat y nube no hacen falta al arrancar: se abren cuando los uses. Lo esencial (audio, drivers, seguridad) está bloqueado."],
  bg_procs: ["warn", "Guarda antes de cerrar", "Cerrar una app pierde lo que no hayas guardado en ella. No rompe Windows: los procesos del sistema no se muestran ni se pueden cerrar."],
  bg_services: ["warn", "Solo 'Manual', nunca 'Deshabilitado'", "Manual significa que arranca cuando algo lo necesita. Los servicios de hardware, red y seguridad están bloqueados para que no puedas romper nada."],
  bg_tasks: ["info", "Suelen ser actualizadores", "Las tareas de terceros suelen comprobar actualizaciones. Desactívalas solo si no las reconoces o no usas ese programa."],
  devjunk: ["warn", "El proyecto dejará de funcionar hasta reinstalar", "node_modules y entornos virtuales se regeneran con npm install o pip install. Van a la Papelera, así que puedes recuperarlos."],
  organize_plan: ["info", "Reversible con un clic", "Mueve los archivos sueltos de Descargas a subcarpetas por tipo. No toca carpetas ni descargas en curso, y puedes deshacerlo."],
  drive: ["warn", "Puede descargar tus archivos", "Para comparar contenido, Google Drive descargará los archivos que solo están en la nube. Gasta datos y espacio temporalmente."],
};
const tipLevelTxt = { info: "Info", warn: "Precaución", bad: "Peligro" };
function tip(key) {
  const t = TIPS[key];
  return t ? `<span class="tip ${t[0]}" data-tip="${key}">${t[0] === "info" ? "?" : "!"}</span>` : "";
}

/* ---------- Tooltip flotante ---------- */
document.addEventListener("mouseover", (e) => {
  const el = e.target.closest("[data-tip]"), box = document.getElementById("tipbox");
  if (!el) return box.classList.remove("on");
  const [lv, t, d] = TIPS[el.dataset.tip];
  box.innerHTML = `<b class="${lv}">${tipLevelTxt[lv]} · ${esc(t)}</b>${esc(d)}<small>Clic para que Smally te lo explique</small>`;
  const r = el.getBoundingClientRect();
  box.style.left = Math.min(innerWidth - 320, Math.max(10, r.left - 140)) + "px";
  box.style.top = (r.bottom + 10 + 140 > innerHeight ? r.top - 10 - box.offsetHeight : r.bottom + 10) + "px";
  box.classList.add("on");
});
document.addEventListener("click", (e) => {
  const el = e.target.closest("[data-tip]");
  if (!el) return;
  e.preventDefault(); e.stopPropagation();
  const [lv, t, d] = TIPS[el.dataset.tip];
  smallySay(`<div class="rec"><span class="dot ${lv}"></span><div><b>${esc(t)}</b><div class="muted">${esc(d)}</div></div></div>`);
}, true);

/* ---------- Tema ---------- */
function setTheme(t) {
  document.documentElement.dataset.theme = t;
  try { localStorage.setItem("nova-theme", t); } catch {}
  document.getElementById("theme-btn").innerHTML = ic(t === "light" ? "moon" : "sun");
}
P.sun = "M12 3v2 M12 19v2 M4.2 4.2l1.4 1.4 M18.4 18.4l1.4 1.4 M3 12h2 M19 12h2 M4.2 19.8l1.4-1.4 M18.4 5.6l1.4-1.4 M12 8a4 4 0 1 0 0 8a4 4 0 1 0 0-8";
(function () {
  let t = "dark";
  try { t = localStorage.getItem("nova-theme") || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark"); } catch {}
  setTheme(t);
  document.getElementById("theme-btn").onclick = () => setTheme(document.documentElement.dataset.theme === "light" ? "dark" : "light");
})();

/* ---------- Smally ---------- */
const GREET = {
  panel: "¡Hola! Soy Smally 👋 Pulsa en mí cuando quieras y te digo qué mejorar. Los iconos ? y ! te avisan de riesgos.",
  limpieza: "Todo lo marcado es seguro. Lo que lleva ! tiene alguna pega: pasa el ratón por encima antes de marcarlo.",
  espacio: "Truco: la pestaña Desarrollo encuentra carpetas node_modules y entornos de Python olvidados. ¡Suelen ocupar GB!",
  duplicados: "Marco siempre la copia más antigua como original. Lo que borres va a la Papelera, tranquilo.",
  seguridad: "Si ves una extensión que no reconoces, quítala desde el propio navegador. Las de cupones y VPN gratis son las más sospechosas.",
  reparar: "Antes de las reparaciones delicadas creo un punto de restauración automático. Si algo va raro, puedes volver atrás.",
  salud: "Si hay muchas pantallas azules, actualiza drivers de gráficos y chipset y pasa el diagnóstico de memoria.",
  inicio: "Menos programas al inicio = arranque más rápido. Lo esencial lleva candado y no se puede tocar.",
  programas: "Los marcados 'Sin uso' llevan más de 6 meses sin abrirse. Si no los necesitas, desinstálalos.",
  buscar: "Escribe parte del nombre y pulsa Intro.",
};
const seen = new Set();
let bubbleTimer;
function smallySay(html, sticky) {
  const b = document.getElementById("smally-bubble"), bot = document.getElementById("smally-bot");
  b.innerHTML = `<div class="bubble"><div class="name"><span class="grad-text">Smally</span><span class="close" data-sm="x">${ic("x")}</span></div>${html}</div>`;
  b.querySelector(".close svg").style.width = "14px";
  bot.classList.remove("talk"); void bot.getBBox(); bot.classList.add("talk");
  clearTimeout(bubbleTimer);
  if (!sticky) bubbleTimer = setTimeout(() => (b.innerHTML = ""), 12000);
}
function smallyRecs() {
  const r = [];
  const junk = junkTotal(), h = res("health"), f = res("sec_audit")?.findings || [], c = S.metrics?.disks?.find((d) => d.letter === "C:");
  if (junk > 500 * 2 ** 20) r.push(["warn", `Tienes ${fmt(junk)} de basura que puedo limpiar sin riesgo.`, "limpieza"]);
  if (c && c.free / c.total < 0.15) r.push(["bad", `Solo queda ${fmt(c.free)} libre en C:. Mira archivos grandes, desarrollo y CompactOS.`, "espacio"]);
  const ext = f.filter((x) => x.area === "Navegador" && (x.severity === "high" || x.severity === "medium"));
  if (ext.length) r.push(["warn", `Hay ${ext.length} extensión(es) del navegador de riesgo, por ejemplo «${ext[0].title}».`, "seguridad"]);
  const other = f.filter((x) => x.area !== "Navegador" && x.severity === "high");
  if (other.length) r.push(["bad", `La auditoría encontró ${other.length} punto(s) de riesgo alto.`, "seguridad"]);
  const crashes = (h?.report?.events || []).filter((e) => ["power", "unexpected_shutdown", "bugcheck", "whea"].includes(e.category)).length;
  if (crashes) r.push(["bad", `${crashes} caídas o pantallas azules en 30 días. Actualiza drivers (Reparar → Buscar actualizaciones) y pasa el test de memoria.`, "salud"]);
  const heavy = (S.startup || []).filter((x) => x.enabled && x.impact === "alto" && !x.essential).length;
  if (heavy) r.push(["info", `${heavy} programa(s) pesados arrancan con Windows. Desactiva los que no uses al encender.`, "inicio"]);
  if (S.metrics?.mem?.load > 85) r.push(["warn", "La memoria está casi llena. Cierra apps en Inicio y fondo → Abiertas ahora.", "inicio"]);
  if (!S.auto?.enabled) r.push(["info", "Activa la limpieza automática semanal y olvídate de mantener el PC.", "limpieza"]);
  return r;
}
function smallyPanel() {
  const recs = smallyRecs();
  smallySay(recs.length
    ? `<div class="muted" style="margin-bottom:4px">Esto es lo que yo haría:</div>` + recs.map(([lv, t, pg]) => `<div class="rec"><span class="dot ${lv}"></span><div>${esc(t)}<br><button class="btn sm" data-page="${pg}">Ir</button></div></div>`).join("")
    : "¡Todo en orden! Tu PC está limpio y protegido. 🎉", true);
}
function smallyInit() {
  document.getElementById("smally-bot").onclick = smallyPanel;
  document.getElementById("smally-bubble").addEventListener("click", (e) => {
    if (e.target.closest("[data-sm='x']")) document.getElementById("smally-bubble").innerHTML = "";
  });
  api("/api/autoclean").then((a) => (S.auto = a)).catch(() => {});
  smallySay(GREET.panel);
  seen.add("panel");
  const _go = go;
  go = (id) => { _go(id); if (!seen.has(id) && GREET[id]) { seen.add(id); smallySay(GREET[id]); } };
}

/* ---------- Vistas nuevas ---------- */
function bgView(tab) {
  const r = res("bg");
  if (!r || S.bgLoaded !== tab) return jobline("bg") || '<div class="skeleton"></div>';
  const items = r.items || [];
  if (tab === "procs") {
    const startNames = new Set((S.startup || []).filter((x) => x.enabled).map((x) => x.name.toLowerCase()));
    return `<div class="card"><table class="tbl"><tr><th style="width:42%">Aplicación</th><th class="num">Memoria</th><th class="num">CPU (s)</th><th>Tipo</th><th style="width:110px"></th></tr>${items.map((p) => `
      <tr><td><div class="ellipsis">${esc(p.desc || p.name)} ${p.count > 1 ? `<span class="dim">×${p.count}</span>` : ""}</div><div class="path ellipsis">${esc(p.company)} · ${esc(p.path)}</div></td>
      <td class="num">${fmt(p.mem)}</td><td class="num">${p.cpu ?? "—"}</td>
      <td>${p.window ? '<span class="chip info">Con ventana</span>' : '<span class="chip warn">Segundo plano</span>'} ${[...startNames].some((n) => n.includes(p.name.toLowerCase())) ? '<span class="chip">Al iniciar</span>' : ""}</td>
      <td style="text-align:right">${p.protected ? `<span class="chip ok">${ic("lock")}</span>` : `<button class="btn sm danger" data-act="kill" data-v="${esc(p.name)}">Cerrar</button>`}</td></tr>`).join("")}</table></div>`;
  }
  if (tab === "services") return `<div class="card"><div class="list">${items.map((s) => `<div class="item">
      ${s.essential ? `<span class="chip ok" style="width:40px;justify-content:center" title="Esencial: protegido">${ic("lock")}</span>` : `<label class="switch" title="Automático / Manual"><input type="checkbox" data-act="svc" data-v="${esc(s.name)}" ${s.mode === "Auto" ? "checked" : ""} ${s.mode === "Disabled" ? "disabled" : ""}><span></span></label>`}
      <div class="main-col"><div class="t ellipsis">${esc(s.display)}</div><div class="s ellipsis">${esc(s.desc || s.path)}</div></div>
      <span class="chip ${s.state === "Running" ? "acc" : ""}">${s.state === "Running" ? "En marcha" : "Parado"}</span><span class="chip">${{ Auto: "Automático", Manual: "Manual", Disabled: "Deshabilitado" }[s.mode] || esc(s.mode)}</span></div>`).join("")}</div></div>`;
  return `<div class="card"><div class="list">${items.map((t) => `<div class="item">
      ${t.essential ? `<span class="chip ok" style="width:40px;justify-content:center">${ic("lock")}</span>` : `<label class="switch"><input type="checkbox" data-act="task" data-v="${esc(t.path)}|${esc(t.name)}" ${t.state !== "Disabled" ? "checked" : ""}><span></span></label>`}
      <div class="main-col"><div class="t ellipsis">${esc(t.name)} <span class="dim">${esc(t.path)}</span></div><div class="s mono ellipsis">${esc(t.cmd)}</div></div></div>`).join("") || empty("check", "Sin tareas de terceros", "")}</div></div>`;
}
function devView(r) {
  if (!r) return running("devjunk") ? "" : empty("cpu", "Basura de proyectos", "Busca node_modules, entornos virtuales y cachés de compilación en tus carpetas.");
  const items = r.items || [], sel = selSet("devjunk");
  const total = items.reduce((a, x) => a + x.size, 0), selSize = items.filter((x) => sel.has(x.path)).reduce((a, x) => a + x.size, 0);
  return `<div class="g g3"><div class="card"><div class="eyebrow">Carpetas</div><div class="metric-big">${items.length}</div></div><div class="card"><div class="eyebrow">Recuperable</div><div class="metric-big grad-text">${fmt(total)}</div></div>
    <div class="card"><div class="eyebrow">Selección rápida</div><button class="btn mt" data-act="devold">${ic("clock")}Marcar proyectos sin tocar en 3 meses</button></div></div>
    <div class="card mt"><div class="list">${items.map((x) => `<label class="item ${sel.has(x.path) ? "sel" : ""}"><input type="checkbox" class="chk" data-act="tsel" data-k="devjunk" data-v="${esc(x.path)}" ${sel.has(x.path) ? "checked" : ""}>
      <div class="main-col"><div class="t ellipsis">${esc(x.project)} <span class="chip">${esc(x.kind)}</span></div><div class="s ellipsis">${esc(x.path)} · modificado ${date(x.mtime)}</div></div>
      <span class="size">${fmt(x.size)}</span><button class="btn sm ghost icon-btn" data-act="reveal" data-v="${esc(x.path)}">${ic("eye")}</button></label>`).join("") || empty("check", "Nada que limpiar", "")}</div></div>
    ${sel.size ? `<div class="actionbar"><div><div class="muted" style="font-size:12px">${sel.size} carpetas</div><div class="total grad-text">${fmt(selSize)}</div></div><span class="spacer"></span><button class="btn ghost" data-act="clrsel" data-v="devjunk">Quitar selección</button><button class="btn danger" data-act="devdel">${ic("trash")}Enviar a la papelera</button></div>` : ""}`;
}
function orgView(r) {
  if (!r) return running("organize_plan") ? "" : empty("folder", "Ordena tus Descargas", "");
  const plan = r.plan || [], cats = {};
  plan.forEach((p) => { (cats[p.category] ||= { n: 0, size: 0 }); cats[p.category].n++; cats[p.category].size += p.size; });
  return `<div class="banner info">${ic("info")}<div class="spacer"><div class="t">${plan.length} archivos sueltos se moverán a subcarpetas dentro de Descargas</div><div class="s">Nada se borra. Las descargas de la última hora y las carpetas no se tocan.</div></div><button class="btn ghost" data-act="orgundo">${ic("refresh")}Deshacer la última</button></div>
    <div class="g g4">${Object.entries(cats).map(([c, v]) => `<div class="card"><div class="eyebrow">${esc(c)}</div><div class="metric-big">${v.n}</div><div class="muted mono">${fmt(v.size)}</div></div>`).join("")}</div>
    ${plan.length ? `<div class="actionbar"><div><div class="muted" style="font-size:12px">Descargas/&lt;Tipo&gt;/</div><div class="total grad-text">${plan.length} archivos</div></div><span class="spacer"></span><button class="btn primary" data-act="orgapply">${ic("folder")}Organizar ahora</button></div>` : empty("check", "Descargas ya está ordenada", "")}`;
}

const EXTRA_ACT = {
  cdet: (v) => cleanDetails(v),
  bgtab: (v) => { S.bgTab = v; render(); if (v !== "start" && S.bgLoaded !== v) EXTRA_ACT.bgload(); },
  bgload: async () => { const t = S.bgTab; S.bgLoaded = null; await job("bg", { what: t }); S.bgLoaded = t; render(); },
  kill: async (v) => {
    if (!(await ask("Cerrar " + v, "Se cerrará la aplicación. <b>Lo que no hayas guardado en ella se perderá.</b> Windows no se ve afectado.", "Cerrar aplicación", true))) return;
    const r = await api("/api/proc/kill", { name: v }); toast(r.message, r.ok ? "ok" : "warn"); if (r.ok) EXTRA_ACT.bgload();
  },
  svc: async (v, el) => {
    const r = await api("/api/service/set", { name: v, mode: el.checked ? "Automatic" : "Manual" }).catch((e) => ({ ok: false, message: e.message }));
    toast(r.message, r.ok ? "ok" : "warn"); if (!r.ok) el.checked = !el.checked;
  },
  task: async (v, el) => {
    const [path, name] = v.split("|");
    const r = await api("/api/task/set", { path, name, enabled: el.checked }).catch((e) => ({ ok: false, message: e.message }));
    toast(r.message, r.ok ? "ok" : "warn"); if (!r.ok) el.checked = !el.checked;
  },
  devold: () => { const s = selSet("devjunk"), lim = Date.now() / 1000 - 90 * 86400; s.clear(); res("devjunk").items.forEach((x) => x.mtime < lim && s.add(x.path)); render(); },
  devdel: async () => {
    const items = res("devjunk").items.filter((x) => selSet("devjunk").has(x.path));
    const sizes = Object.fromEntries(items.map((x) => [x.path, x.size]));
    if (!(await askDetailed(`Enviar ${items.length} carpetas a la Papelera`, filesSummary(items.map((x) => x.path), sizes)
      + `<div class="banner mt">${ic("alert")}<div><div class="t">Esos proyectos dejarán de funcionar hasta reinstalar</div><div class="s">Ejecuta npm install o pip install -r requirements.txt en cada uno cuando vuelvas a usarlo.</div></div></div>`,
      "Enviar a la papelera", true, "Entiendo que tendré que reinstalar las dependencias"))) return;
    toast("Moviendo a la papelera… puede tardar con carpetas grandes", "info");
    const r = await api("/api/files/recycle", { paths: items.map((x) => x.path), sizes }).catch((e) => toast(e.message, "bad"));
    if (!r) return;
    const gone = new Set(r.recycled.map((x) => x.path));
    res("devjunk").items = res("devjunk").items.filter((x) => !gone.has(x.path)); selSet("devjunk").clear();
    toast(`${fmt(r.freed)} liberados` + (r.failed.length ? ` · ${r.failed.length} no se pudieron mover` : ""), r.failed.length ? "warn" : "ok"); render();
  },
  orgapply: async () => {
    if (!(await ask("Organizar Descargas", "Los archivos sueltos se moverán a subcarpetas por tipo (Instaladores, Documentos, Imágenes…). Nada se borra y puedes deshacerlo.", "Organizar"))) return;
    const r = await api("/api/organize/apply", {}); toast(`${r.moved} archivos organizados` + (r.failed ? ` · ${r.failed} omitidos` : "")); job("organize_plan");
  },
  orgundo: async () => { const r = await api("/api/organize/undo", {}); toast(r.message, r.restored ? "ok" : "info"); job("organize_plan"); },
};

smallyInit();
