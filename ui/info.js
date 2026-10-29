"use strict";
/* Capas de información: qué se borra, qué se conserva, consecuencias y vista previa. */

// [qué es, qué se borra, qué NO se toca, consecuencia]
const CLEAN_INFO = {
  temp_user: ["Archivos que los programas crean para trabajar y olvidan borrar.", "Archivos de tu carpeta TEMP con más de 24 horas.", "Archivos recientes, los que estén en uso y las carpetas de apps abiertas.", "Ninguna. Si un programa necesitara alguno, lo vuelve a crear."],
  temp_win: ["Temporales del propio Windows y de instaladores.", "Archivos de C:\\Windows\\Temp con más de 24 horas.", "Archivos recientes y en uso.", "Ninguna."],
  recycle: ["Lo que tú ya enviaste a la Papelera.", "TODO el contenido de la Papelera, de forma definitiva.", "Nada: no hay vuelta atrás.", "No podrás recuperar nada de lo que había en la Papelera."],
  thumbnails: ["Miniaturas de fotos y vídeos que muestra el Explorador.", "Archivos thumbcache e iconcache.", "Tus fotos y vídeos originales.", "Las carpetas con muchas fotos tardarán un poco en mostrar miniaturas la primera vez."],
  wer: ["Informes de fallos de programas que Windows envía a Microsoft.", "Informes ya enviados o en cola.", "Los volcados de memoria (van aparte).", "Ninguna."],
  crashdumps: ["Copias de la memoria guardadas cuando un programa o Windows se cuelga.", "Volcados .dmp de CrashDumps y Minidump.", "Todo lo demás.", "Pierdes la información para investigar pantallas azules pasadas."],
  wu_download: ["Instaladores de actualizaciones que Windows ya aplicó.", "Contenido de SoftwareDistribution\\Download.", "Las actualizaciones instaladas.", "Ninguna, salvo que haya una actualización instalándose ahora mismo."],
  delivery: ["Caché para compartir actualizaciones con otros PCs de tu red.", "La caché de Optimización de distribución.", "Las actualizaciones instaladas.", "Ninguna."],
  recent: ["La lista de 'Archivos recientes' del Explorador y Office.", "Solo los accesos directos de esa lista.", "Los archivos reales.", "La lista de recientes aparecerá vacía."],
  chrome: ["Copias de webs que Chrome guarda para cargarlas más rápido.", "Cache, Code Cache, GPUCache y cachés gráficas de todos tus perfiles.", "Contraseñas, historial, marcadores, cookies y sesiones abiertas.", "Las webs cargarán algo más lento la primera vez."],
  edge: ["Copias de webs que Edge guarda para cargarlas más rápido.", "Cachés de todos los perfiles.", "Contraseñas, historial, marcadores y cookies.", "Las webs cargarán algo más lento la primera vez."],
  brave: ["Caché del navegador Brave.", "Cachés de todos los perfiles.", "Contraseñas, historial, marcadores y cookies.", "Carga algo más lenta la primera vez."],
  opera: ["Caché del navegador Opera.", "Carpeta Cache.", "Contraseñas, historial y marcadores.", "Carga algo más lenta la primera vez."],
  firefox: ["Caché de Firefox.", "Carpeta cache2 de cada perfil.", "Contraseñas, historial, marcadores y cookies.", "Carga algo más lenta la primera vez."],
  shader: ["Sombreadores que DirectX compila para los juegos.", "La caché D3DSCache.", "Los juegos y sus partidas guardadas.", "El primer arranque de cada juego puede ir a tirones unos segundos."],
  nvidia: ["Sombreadores compilados por el driver NVIDIA.", "DXCache y GLCache.", "El driver y su configuración.", "Primer arranque de juegos algo más lento."],
  amd: ["Sombreadores compilados por el driver AMD.", "DxCache, GLCache, VkCache.", "El driver y su configuración.", "Primer arranque de juegos algo más lento."],
  discord: ["Imágenes y código que Discord guarda.", "Cache, Code Cache y GPUCache.", "Tu cuenta, mensajes y ajustes.", "Ninguna (Discord debe estar cerrado)."],
  spotify: ["Canciones que Spotify guarda al escucharlas.", "La caché de reproducción.", "Las canciones descargadas para escuchar sin conexión.", "Las canciones se volverán a descargar al escucharlas (gasta datos)."],
  steam: ["El navegador interno de la tienda Steam.", "La carpeta htmlcache.", "Los juegos, partidas y tu cuenta.", "Ninguna."],
  npm: ["Paquetes que npm descargó para tus proyectos.", "La caché global de npm.", "Los node_modules de tus proyectos.", "npm volverá a descargar paquetes la próxima vez (más lento una vez)."],
  pip: ["Paquetes que pip descargó.", "La caché de pip.", "Los paquetes ya instalados.", "pip volverá a descargar al instalar algo."],
  yarn: ["Paquetes que Yarn descargó.", "La caché de Yarn.", "Los proyectos.", "Yarn volverá a descargar."],
  gobuild: ["Compilaciones intermedias de Go.", "La caché go-build.", "Tu código.", "La siguiente compilación tarda más."],
  nuget: ["Paquetes .NET descargados.", "La carpeta .nuget\\packages.", "Tus proyectos.", "La siguiente compilación .NET descargará los paquetes de nuevo."],
};
const RISKY_CLEAN = new Set(["recycle", "crashdumps", "spotify", "nuget"]);

function infoBlock(k) {
  const i = CLEAN_INFO[k];
  if (!i) return "";
  const row = (icon, cls, label, txt) => `<div class="rec"><span class="${cls}" style="flex:none">${ic(icon)}</span><div><b>${label}</b><div class="muted">${esc(txt)}</div></div></div>`;
  return `<div class="infoblock">${row("info", "info", "Qué es", i[0])}${row("trash", "bad", "Qué se borra", i[1])}${row("lock", "ok", "Qué NO se toca", i[2])}${row("alert", RISKY_CLEAN.has(k) ? "warn" : "muted", "Consecuencia", i[3])}</div>`;
}

async function cleanDetails(key) {
  const t = res("clean_scan").targets.find((x) => x.key === key);
  const w = modal(`<h3>${esc(t.title)}</h3>${infoBlock(key)}<div class="section-title" style="margin-top:18px">Archivos que se borrarían</div><div id="pv" class="console" style="height:220px">Leyendo archivos…</div>
    <div class="muted" style="font-size:12px;margin-top:8px">Rutas: ${t.paths.map(esc).join(" · ") || "Papelera"}</div><div class="foot"><button class="btn" data-r>Cerrar</button></div>`, true);
  w.addEventListener("click", (e) => { if (e.target.closest("[data-r]") || e.target === w) w.remove(); });
  const p = await api("/api/clean/preview", { key }).catch((e) => ({ files: [], note: e.message }));
  w.querySelector("#pv").textContent = (p.count != null ? `${nf(p.count, 0)} archivos · ${fmt(p.total)}${p.note ? " · " + p.note : ""}\nLos ${p.files.length} más grandes:\n\n` : (p.note || "") + "\n")
    + p.files.map((f) => `${fmt(f.size).padStart(10)}  ${f.path}`).join("\n");
}

/* Confirmación con detalle y casilla "Entiendo" cuando hay riesgos */
function askDetailed(title, html, ok, danger, ackText) {
  return new Promise((r) => {
    const w = modal(`<h3>${esc(title)}</h3><div class="body">${html}</div>
      ${ackText ? `<label class="opt mt" style="color:var(--text)"><input type="checkbox" class="chk" id="ack">${esc(ackText)}</label>` : ""}
      <div class="foot"><button class="btn ghost" data-r="0">Cancelar</button><button class="btn ${danger ? "danger" : "primary"}" data-r="1" ${ackText ? "disabled" : ""}>${esc(ok)}</button></div>`, true);
    const go1 = w.querySelector('[data-r="1"]');
    w.querySelector("#ack")?.addEventListener("change", (e) => (go1.disabled = !e.target.checked));
    w.addEventListener("click", (e) => { const b = e.target.closest("[data-r]"); if (b && !b.disabled) { w.remove(); r(b.dataset.r === "1"); } });
  });
}

function cleanSummary(targets) {
  const rows = targets.map((t) => {
    const i = CLEAN_INFO[t.key], risky = RISKY_CLEAN.has(t.key);
    return `<tr><td>${risky ? '<span class="dot warn"></span> ' : ""}<b>${esc(t.title)}</b><div class="path">${esc(i ? i[1] : t.description)}</div>${i ? `<div class="path ${risky ? "warn" : ""}">↳ ${esc(i[3])}</div>` : ""}</td><td class="num">${fmt(t.size)}</td></tr>`;
  }).join("");
  return `<table class="tbl"><tr><th>Se limpiará</th><th class="num" style="width:110px">Tamaño</th></tr>${rows}</table>
    <div class="banner info mt">${ic("lock")}<div><div class="t">Nunca se tocan</div><div class="s">Documentos, fotos, vídeos, descargas, programas instalados, contraseñas, historial ni marcadores. En TEMP se saltan los archivos en uso y los de las últimas 24 h.</div></div></div>`;
}

function filesSummary(paths, sizes) {
  return `<table class="tbl"><tr><th>Archivo</th><th class="num" style="width:100px">Tamaño</th></tr>${paths.slice(0, 25).map((p) => `<tr><td><div class="ellipsis">${esc(base(p))}</div><div class="path ellipsis">${esc(dir(p))}</div></td><td class="num">${sizes[p] != null ? fmt(sizes[p]) : ""}</td></tr>`).join("")}</table>
    ${paths.length > 25 ? `<div class="muted mt">…y ${paths.length - 25} más.</div>` : ""}
    <div class="banner info mt">${ic("refresh")}<div><div class="t">Recuperable</div><div class="s">Van a la Papelera de reciclaje: puedes restaurarlos desde allí (clic derecho → Restaurar). No la vacíes hasta comprobar que no los necesitas.</div></div></div>`;
}

function fixSummary(f) {
  return `<p>${esc(f.description)}</p><div class="infoblock">
    <div class="rec"><span class="info" style="flex:none">${ic("play")}</span><div><b>Comandos exactos que se ejecutarán</b><div class="mono muted" style="font-size:12px;white-space:pre-wrap">${f.commands.map(esc).join("\n")}</div></div></div>
    <div class="rec"><span class="ok" style="flex:none">${ic("refresh")}</span><div><b>Cómo deshacerlo</b><div class="muted">${esc(f.revert || "—")}</div></div></div>
    <div class="rec"><span class="muted" style="flex:none">${ic("clock")}</span><div><b>Duración</b><div class="muted">${esc(f.minutes)}${f.reboot ? " · necesitará reiniciar" : ""}</div></div></div>
    ${f.restore_first ? `<div class="rec"><span class="ok" style="flex:none">${ic("shield")}</span><div><b>Red de seguridad</b><div class="muted">Antes se crea un punto de restauración automáticamente.</div></div></div>` : ""}</div>`;
}
