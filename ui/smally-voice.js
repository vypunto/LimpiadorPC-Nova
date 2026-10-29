"use strict";
/* Smally te llama por tu nombre y saca bocadillos escritos con consejos de vez en cuando (sin voz). */

const TIPSCFG = { on: true, shown: new Set(), timer: null };
try { TIPSCFG.on = localStorage.getItem("nova-tips") !== "0"; } catch {}

function userName() {
  const first = String(S.sys?.fullName || "").trim().split(/\s+/)[0];
  const u = first || String(S.sys?.user || "").trim();
  return u ? u.charAt(0).toUpperCase() + u.slice(1) : "";
}
const hi = () => (userName() ? `, ${userName()}` : "");

/* ---------- Voz (sintetizador de Windows: gratis y sin Internet). Apagada por defecto ---------- */
let voiceOn = false;
try { voiceOn = localStorage.getItem("nova-voice") === "1"; } catch {}
let esVoice = null;
function pickVoice() {
  const vs = speechSynthesis.getVoices();
  esVoice = vs.find((v) => /^es[-_]ES/i.test(v.lang) && /natural|online/i.test(v.name)) || vs.find((v) => /^es[-_]ES/i.test(v.lang)) || vs.find((v) => /^es/i.test(v.lang)) || null;
}
const hasVoice = "speechSynthesis" in window;
if (hasVoice) { pickVoice(); speechSynthesis.onvoiceschanged = pickVoice; }
function speak(text) {
  if (!voiceOn || !hasVoice) return;
  const clean = String(text).replace(/\*\*/g, "").replace(/[•👉✅⚠🤖🎉🤔👋✨💡]/gu, "").replace(/https?:\S+/g, "")
    .replace(/\n+/g, ". ").replace(/\s{2,}/g, " ").trim();
  if (!clean) return;
  speechSynthesis.cancel();
  // En frases cortas suena más natural y no se corta en textos largos
  (clean.match(/[^.!?]+[.!?]*/g) || [clean]).slice(0, 10).forEach((p) => {
    const u = new SpeechSynthesisUtterance(p.trim());
    u.lang = "es-ES"; if (esVoice) u.voice = esVoice;
    u.rate = 1.05; u.pitch = 1.3;
    u.onstart = talk;
    speechSynthesis.speak(u);
  });
}
const shush = () => hasVoice && speechSynthesis.cancel();

/* ---------- Saludo con nombre en el chat ---------- */
const _toggle = toggleChat;
toggleChat = async () => {
  const first = !CHAT.msgs.length;
  await _toggle();
  if (first && CHAT.msgs[0]) {
    CHAT.msgs[0].content = CHAT.msgs[0].content.replace("¡Hola! Soy Smally", `¡Hola${hi()}! Soy Smally`);
    renderChat();
  }
  if (!CHAT.open) shush();
};
// Solo se leen en voz alta las respuestas del chat (nunca los bocadillos automáticos)
const _ask = askSmally;
askSmally = async (q) => {
  await _ask(q);
  const m = CHAT.msgs.at(-1);
  if (m?.role === "assistant") { SFACE.flash("speaking", Math.min(5000, 900 + m.content.length * 25)); SFACE.talk(Math.min(5000, 900 + m.content.length * 25)); }
  if (m?.role === "assistant") speak(m.content);
};
// Botones de voz y de consejos en la cabecera del chat
const _render = renderChat;
renderChat = () => {
  _render();
  const name = document.querySelector("#smally-bubble .bubble.chat .name");
  if (!name) return;
  const mk = (id, text, title) => {
    const b = document.createElement("button");
    b.className = "btn sm ghost"; b.id = id; b.title = title; b.textContent = text;
    b.style.cssText = "height:24px;padding:0 7px;font-size:11.5px";
    name.insertBefore(b, name.querySelector(".close"));
  };
  if (hasVoice) mk("sm-voice", voiceOn ? "🔊" : "🔇", voiceOn ? "Silenciar a Smally" : "Que Smally lea sus respuestas en voz alta");
  mk("sm-tips", TIPSCFG.on ? "💡 Consejos: sí" : "💤 Consejos: no", "Consejos automáticos");
  mk("sm-hide", "Ocultar", "Esconder a Smally (vuelve desde la barra lateral)");
};
document.addEventListener("click", (e) => {
  if (e.target.id === "sm-hide") { setHidden(true); toast("Smally se ha escondido. Vuelve con «Mostrar a Smally» en la barra lateral", "info"); }
});
document.addEventListener("click", (e) => {
  if (e.target.id === "sm-voice") {
    voiceOn = !voiceOn;
    try { localStorage.setItem("nova-voice", voiceOn ? "1" : "0"); } catch {}
    if (voiceOn) speak(`Vale${hi()}, ahora leeré mis respuestas en voz alta.`); else shush();
    toast(voiceOn ? (esVoice ? `Voz activada (${esVoice.name})` : "Voz activada (no encuentro una voz en español; usaré la predeterminada)") : "Smally en silencio", "info");
    renderChat();
  }
  if (e.target.id === "sm-tips") {
    TIPSCFG.on = !TIPSCFG.on;
    try { localStorage.setItem("nova-tips", TIPSCFG.on ? "1" : "0"); } catch {}
    toast(TIPSCFG.on ? "Smally te dará consejos de vez en cuando" : "Consejos automáticos desactivados", "info");
    renderChat();
  }
  if (e.target.closest("#smally-bubble [data-sm='x']")) shush();
});

/* ---------- Bocadillos con consejos ---------- */
const EXTRA_TIPS = [
  ["info", "reinicia el portátil al menos una vez por semana: apagar con el inicio rápido no limpia la memoria del todo.", null],
  ["info", "actualiza los drivers desde la web del fabricante cada pocos meses; evitan cuelgues y pantallazos.", "soluciones"],
  ["info", "una limpieza automática semanal mantiene el PC ligero sin que tengas que acordarte.", "limpieza"],
  ["info", "revisa de vez en cuando las extensiones del navegador: las que no usas solo gastan memoria.", "seguridad"],
  ["info", "si el portátil se calienta, límpiale los ventiladores y no lo uses sobre la cama o el sofá.", null],
  ["info", "cuantos menos programas arranquen con Windows, antes estará listo al encender.", "inicio"],
];
function nextTip() {
  const pool = smallyRecs().map((r) => [r[0], r[1], r[2]]).concat(EXTRA_TIPS);
  let fresh = pool.filter((t) => !TIPSCFG.shown.has(t[1]));
  if (!fresh.length) { TIPSCFG.shown.clear(); fresh = pool; }
  const order = { bad: 0, warn: 1, info: 2 };  // primero lo importante
  return fresh.sort((a, b) => (order[a[0]] ?? 3) - (order[b[0]] ?? 3))[0];
}
function showTip() {
  if (!TIPSCFG.on || CHAT.open || document.body.classList.contains("smally-hidden") || document.hidden || document.querySelector(".modal-wrap")) return;
  const t = nextTip();
  if (!t) return;
  TIPSCFG.shown.add(t[1]);
  const name = userName();
  const text = (name ? `${name}, ` : "") + t[1].charAt(0).toLowerCase() + t[1].slice(1);
  _say(`<div class="rec"><span class="dot ${t[0]}"></span><div>${esc(text)}${t[2] ? `<br><button class="btn sm" data-page="${t[2]}">Ir</button>` : ""}</div></div>`);
  talk();
}
function scheduleTips() {
  clearTimeout(TIPSCFG.timer);
  // Primer consejo a los 90 s; después cada 4-7 minutos
  TIPSCFG.timer = setTimeout(function loop() { showTip(); TIPSCFG.timer = setTimeout(loop, (240 + Math.random() * 180) * 1000); }, 90000);
}

// Saludo inicial con tu nombre en cuanto se conoce
(function waitName(n = 0) {
  if (S.sys || n > 40) {
    const name = userName();
    _say(`<div>¡Hola${name ? ", <b>" + esc(name) + "</b>" : ""}! 👋 Soy Smally. Tócame cuando quieras y te explico cualquier cosa de tu PC.</div>`);
    scheduleTips();
  } else setTimeout(() => waitName(n + 1), 500);
})();
document.addEventListener("input", (e) => { if (e.target.id === "chat-q") SFACE.flash("listening", 1500); });
