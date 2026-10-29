"use strict";
/* Smally conversacional: chat con IA (si hay clave) o con base de conocimiento local, y sonido de robot. */

const CHAT = { open: false, msgs: [], busy: false, ai: null };

/* ---------- Sonido de robot (sintetizado, sin archivos) ---------- */
let audioCtx;
function robotSound() {
  try {
    audioCtx ||= new (window.AudioContext || window.webkitAudioContext)();
    const t0 = audioCtx.currentTime, out = audioCtx.createGain();
    out.gain.value = 0.12; out.connect(audioCtx.destination);
    [[520, 0], [780, 0.09], [640, 0.18], [980, 0.27]].forEach(([f, t]) => {
      const o = audioCtx.createOscillator(), g = audioCtx.createGain();
      o.type = "square"; o.frequency.setValueAtTime(f, t0 + t);
      o.frequency.exponentialRampToValueAtTime(f * (Math.random() > 0.5 ? 1.5 : 0.7), t0 + t + 0.08);
      g.gain.setValueAtTime(0.0001, t0 + t); g.gain.exponentialRampToValueAtTime(1, t0 + t + 0.01); g.gain.exponentialRampToValueAtTime(0.0001, t0 + t + 0.085);
      o.connect(g); g.connect(out); o.start(t0 + t); o.stop(t0 + t + 0.09);
    });
  } catch {}
}

/* ---------- Base de conocimiento local (sin Internet) ---------- */
const KB = [
  [/(c[oó]mo est[aá]|salud|estado).*(pc|equipo|ordenador)|^(salud|estado)/i, () => stateAnswer(), ["salud", "panel"]],
  [/reinici|apaga|pantallazo|pantalla azul|bsod|cuelg|se va/i, () => crashAnswer(), ["soluciones", "salud"]],
  [/lento|rápid|rapid|acelerar|rendimiento|optimiz|va mal/i, () => "Para que vaya más rápido:\n• Pulsa **Optimizar ahora** en el Panel (seguro).\n• En **Inicio y fondo** desactiva lo que no necesites al encender.\n• Cierra apps pesadas en «Abiertas ahora».\n• Si el disco está casi lleno, libera espacio.\n• Si estás enchufado, prueba el plan **Alto rendimiento** en Reparar.\nOlvídate de «limpiadores de registro» o «aceleradores de RAM»: no funcionan.", ["panel", "inicio"]],
  [/espacio|lleno|liberar|gigas|\bgb\b|ocupa/i, () => `Para liberar espacio, de menos a más impacto:\n1. **Limpieza**: temporales y cachés (${fmt(junkTotal())} detectados ahora).\n2. **Espacio → Desarrollo**: node_modules y entornos olvidados.\n3. **Espacio → Archivos grandes** y **Sin usar**.\n4. **Duplicados**.\n5. **Reparar → CompactOS** (2-6 GB, reversible) y desactivar la hibernación.`, ["limpieza", "espacio"]],
  [/borrar.*(seguro|riesgo)|es seguro|puedo borrar|qué se borra|que se borra/i, () => "Todo lo marcado por defecto en Limpieza es seguro: se regenera solo. Pulsa **Detalles** en cada categoría para ver qué se borra, qué no se toca y la lista real de archivos. Lo que llega a la Papelera (duplicados, archivos grandes) se puede recuperar. Solo **vaciar la Papelera** es definitivo.", ["limpieza"]],
  [/virus|malware|troyano|hacke|seguridad|defender|antivirus/i, () => secAnswer(), ["seguridad"]],
  [/extensi[oó]n|navegador|chrome|edge|hola vpn|cup[oó]n/i, () => "En **Seguridad** reviso las extensiones de Chrome, Edge y Brave. Las de VPN gratis y de cupones/cashback suelen leer todo lo que navegas: quita las que no uses desde el propio navegador (chrome://extensions).", ["seguridad"]],
  [/inicio|arranque|arranca|encender|startup|segundo plano|servicio/i, () => "En **Inicio y fondo** tienes cuatro pestañas: lo que arranca con Windows, las apps abiertas, los servicios y las tareas programadas. Desactivar es reversible y lo esencial (audio, drivers, red, seguridad) lleva candado: no puedes romper nada.", ["inicio"]],
  [/duplicad|copias|repetid/i, () => "En **Duplicados** comparo el contenido completo de cada archivo, así que solo verás copias 100 % idénticas. Marco la más antigua como original y las demás van a la Papelera.", ["duplicados"]],
  [/organiz|ordenar|carpeta|renombr/i, () => "El **Organizador IA** propone carpetas y nombres limpios para la carpeta que elijas, con vista «Así quedará». Solo mueve, nunca borra, no toca proyectos de código y se deshace con un clic.", ["organizador"]],
  [/sfc|dism|chkdsk|reparar|arreglar|archivos del sistema|corrupt/i, () => "Si Windows falla, el orden recomendado en **Reparar** es: punto de restauración → SFC → DISM → SFC otra vez → CHKDSK. Necesitan permisos de administrador y antes de las delicadas creo un punto de restauración automático.", ["reparar"]],
  [/internet|wifi|red|dns|conexi/i, () => "Problemas de Internet, de menos a más: **Vaciar caché DNS** → **Renovar IP** → **Sincronizar la hora** → como último recurso **Restablecer pila de red** (puede afectar a VPN). Todo en Reparar → Red e Internet.", ["reparar"]],
  [/sonido|audio|altavo/i, () => "Prueba **Reparar → Reiniciar servicios de audio** (necesita admin). Si sigue sin sonido, busca drivers en **Buscar actualizaciones y drivers**.", ["reparar"]],
  [/impresora|imprim/i, () => "**Reparar → Desatascar la impresora** vacía la cola y reinicia el servicio. Ojo: se pierden los trabajos pendientes.", ["reparar"]],
  [/programa|desinstal|aplicaci/i, () => "En **Programas** ves lo instalado, su tamaño y cuáles llevan más de 6 meses sin usarse. «Desinstalar» abre el desinstalador oficial de cada programa.", ["programas"]],
  [/admin|permis/i, () => "Algunas funciones (Windows Temp, SFC, DISM, servicios…) necesitan permisos elevados. Pulsa **Ejecutar como admin** en la barra lateral: Windows pedirá confirmación.", []],
  [/autom[aá]tic|programar|semanal/i, () => "En **Limpieza → Automático** puedes activar una limpieza semanal. Solo limpia lo seguro y no necesita permisos de administrador.", ["limpieza"]],
  [/modo (noche|d[ií]a|oscuro|claro)|tema/i, () => "Cambia entre modo día y noche con el botón ☀/☾ arriba a la derecha.", []],
  [/historial|qu[eé] (has|se ha) (hecho|borrado)/i, () => "Todo lo que se limpia, borra o cambia queda en el **Historial** (botón en la barra lateral).", []],
  [/registro|regedit/i, () => "No limpio el registro a propósito: los «limpiadores de registro» apenas ganan rendimiento y pueden romper Windows.", []],
  [/hola|buenas|hey|qu[ié]n eres/i, () => "¡Hola! Soy Smally 🤖 Conozco todas las herramientas de la app y el estado de tu PC. Pregúntame lo que quieras: por qué va lento, qué borrar, si tienes virus…", []],
];

function stateAnswer() {
  const h = res("health"), c = S.metrics?.disks?.find((d) => d.letter === "C:");
  const recs = smallyRecs();
  return `${h ? `Salud: **${h.score}/100 (${h.label})**.` : "Todavía estoy diagnosticando la salud."}${c ? ` En C: te quedan ${fmt(c.free)}.` : ""}${S.metrics ? ` La RAM va al ${S.metrics.mem.load}%.` : ""}\n` +
    (recs.length ? "Lo que yo haría:\n" + recs.slice(0, 5).map((r) => "• " + r[1]).join("\n") : "¡Todo en orden!");
}
function crashAnswer() {
  if (!res("health")) return "Estoy leyendo los registros de Windows para ver por qué se apaga o reinicia. Pregúntame en unos segundos o abre **Soluciones**.";
  const ev = (res("health")?.report?.events || []).filter((e) => ["power", "unexpected_shutdown", "bugcheck", "whea"].includes(e.category));
  return (ev.length ? `He visto **${ev.length} caídas** en 30 días (la última: ${esc((ev[0].time || "").replace("T", " "))}, ${esc(ev[0].source)}).\n` : "No veo caídas registradas recientemente.\n") +
    ((res("diagnosis")?.problems || []).find((p) => p.id === "crashes")
      ? ((p) => `Mi diagnóstico: **${p.title}**.\n\nCómo arreglarlo:\n${p.steps.slice(0, 6).map((s, i) => `${i + 1}. ${s.text}`).join("\n")}\n\nEn **Soluciones** cada paso tiene su botón.`)(res("diagnosis").problems.find((p) => p.id === "crashes"))
      : "Qué revisar:\n• Drivers de gráficos y chipset (Reparar → Buscar actualizaciones y drivers).\n• Test de memoria RAM (Reparar).\n• Temperaturas y polvo en ventiladores.\n• SFC y DISM si hay archivos dañados.");
}
function secAnswer() {
  const d = res("sec_status")?.defender, f = (res("sec_audit")?.findings || []).filter((x) => x.severity === "high" || x.severity === "medium");
  return `${d ? `Defender: protección en tiempo real **${d.RealTimeProtectionEnabled ? "activa" : "APAGADA"}**, firmas de hace ${d.AntivirusSignatureAge} días.` : "Estoy comprobando Defender."}\n` +
    (f.length ? `La auditoría marca ${f.length} punto(s), por ejemplo: ${f.slice(0, 3).map((x) => "«" + x.title + "»").join(", ")}.\n` : "La auditoría no encuentra nada preocupante.\n") +
    "Si sospechas algo, lanza un **Análisis rápido** (o completo) en Seguridad.";
}
function localAnswer(q) {
  const hit = KB.find(([rx]) => rx.test(q));
  if (hit) return { text: hit[1](), pages: hit[2] };
  return { text: "No estoy seguro de entenderte 🤔 Puedo ayudarte con: salud y caídas, velocidad, liberar espacio, virus y extensiones, programas de inicio, reparaciones de Windows, duplicados y organizar carpetas." + (CHAT.ai ? "" : "\n\nSi conectas tu clave de Anthropic (en Organizador IA) responderé cualquier pregunta con IA."), pages: [] };
}

/* ---------- Interfaz del chat ---------- */
const PAGE_NAMES = Object.fromEntries(PAGES.map((p) => [p.id, p.t]));
function mdLite(t) {
  return esc(t).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/\n/g, "<br>");
}
function renderChat() {
  const b = document.getElementById("smally-bubble");
  if (!CHAT.open) { b.innerHTML = ""; return; }
  const chips = ["¿Cómo está mi PC?", "¿Por qué se reinicia?", "¿Qué puedo borrar sin riesgo?", "¿Tengo virus?", "¿Cómo lo hago más rápido?"];
  b.innerHTML = `<div class="bubble chat"><div class="name"><span class="grad-text">Smally</span><span class="chip ${CHAT.ai ? "acc" : ""}" style="height:19px">${CHAT.ai ? "IA · Claude" : "Modo local"}</span><span class="close" data-sm="x">${ic("x")}</span></div>
    <div class="chat-log" id="chat-log">${CHAT.msgs.map((m) => `<div class="msg ${m.role}">${m.role === "assistant" ? mdLite(m.content) : esc(m.content)}
      ${m.pages?.length ? `<div class="row wrap" style="margin-top:8px">${m.pages.map((p) => `<button class="btn sm" data-page="${p}">Ir a ${esc(PAGE_NAMES[p] || p)}</button>`).join("")}</div>` : ""}</div>`).join("")}
      ${CHAT.busy ? '<div class="msg assistant"><span class="typing"><i></i><i></i><i></i></span></div>' : ""}</div>
    ${CHAT.msgs.length < 3 ? `<div class="chips">${chips.map((c) => `<button class="chip" data-ask="${esc(c)}">${esc(c)}</button>`).join("")}</div>` : ""}
    <form class="chat-in" id="chat-form"><input class="input" id="chat-q" placeholder="Pregúntame lo que quieras…" autocomplete="off"><button class="btn primary icon-btn" style="width:38px;height:38px">${ic("play")}</button></form>
    ${CHAT.ai === false ? '<div class="muted" style="font-size:11px;margin-top:6px">Con tu clave de Anthropic (Organizador IA) respondo cualquier pregunta usando el estado real de tu PC.</div>' : ""}</div>`;
  b.querySelector(".close svg").style.width = "14px";
  const log = b.querySelector("#chat-log"); log.scrollTop = log.scrollHeight;
  const q = b.querySelector("#chat-q"); q.focus();
}
async function askSmally(q) {
  q = q.trim(); if (!q || CHAT.busy) return;
  CHAT.msgs.push({ role: "user", content: q });
  CHAT.busy = true; renderChat();
  let answer = null;
  if (CHAT.ai) {
    const r = await api("/api/smally/chat", { messages: CHAT.msgs.map(({ role, content }) => ({ role, content })) }).catch(() => null);
    if (r?.ok) {
      const pages = [...r.text.matchAll(/\[\[ir:([a-z]+)\]\]/g)].map((m) => m[1]).filter((p) => PAGE_NAMES[p]);
      answer = { text: r.text.replace(/\s*\[\[ir:[a-z]+\]\]/g, "").trim(), pages: [...new Set(pages)] };
    } else if (r?.text && !r.offline) answer = { text: r.text, pages: [] };
  }
  answer ||= localAnswer(q);
  CHAT.busy = false;
  CHAT.msgs.push({ role: "assistant", content: answer.text, pages: answer.pages });
  robotSound(); talk(); renderChat();
}
function talk() { const bot = document.getElementById("smally-bot"); bot.classList.remove("talk"); void bot.getBBox(); bot.classList.add("talk"); }

async function toggleChat() {
  robotSound(); talk();
  CHAT.open = !CHAT.open;
  if (CHAT.open && CHAT.ai === null) CHAT.ai = !!(await api("/api/aiorg/config").catch(() => ({}))).has_key;
  if (CHAT.open && !CHAT.msgs.length) {
    const recs = smallyRecs();
    CHAT.msgs.push({ role: "assistant", content: "¡Hola! Soy Smally 🤖 Pregúntame lo que quieras sobre tu PC o la app." + (recs.length ? "\n\nAhora mismo yo haría esto:\n" + recs.slice(0, 4).map((r) => "• " + r[1]).join("\n") : ""), pages: [...new Set(recs.slice(0, 3).map((r) => r[2]))] });
  }
  clearTimeout(bubbleTimer);
  renderChat();
}

// Sustituye el panel de recomendaciones por el chat
document.getElementById("smally-bot").onclick = toggleChat;
smallyPanel = toggleChat;
const _say = smallySay;
smallySay = (html, sticky) => { if (!CHAT.open) _say(html, sticky); };
document.addEventListener("submit", (e) => { if (e.target.id === "chat-form") { e.preventDefault(); const q = document.getElementById("chat-q"); askSmally(q.value); q.value = ""; } });
document.addEventListener("click", (e) => {
  const c = e.target.closest("[data-ask]"); if (c) askSmally(c.dataset.ask);
  if (e.target.closest("#smally-bubble [data-sm='x']")) { CHAT.open = false; renderChat(); }
});
// Cuando se conecta/quita la clave en el organizador, Smally lo sabe
const _orgEnter = ENTER.organizador;
ENTER.organizador = async () => { await _orgEnter(); CHAT.ai = !!S.orgCfg?.has_key; };
