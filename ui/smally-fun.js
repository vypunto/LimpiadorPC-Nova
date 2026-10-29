"use strict";
/* Smally divertido: se arrastra, se oculta, sigue el ratón con la mirada y cambia de humor según tu PC. */

const box = document.getElementById("smally"), bot = document.getElementById("smally-bot");
const FUN = { mood: "", partyUntil: 0, lastActive: Date.now(), dragged: false, pokes: [], asleep: false };
const store = (k, v) => { try { v === undefined ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch {} };
const load = (k) => { try { return localStorage.getItem(k); } catch { return null; } };

/* ---------- Frases ---------- */
const QUIPS = {
  drag: ["¡Wiiii! 🎢", "¡Que me mareo! 😵‍💫", "¡Allá vamos! 🚀", "Llévame a un sitio con vistas 🏝️"],
  dizzy: ["Uff… todo me da vueltas 😵‍💫", "¿Dónde estoy? ¿Quién soy? 🌀", "Avisa la próxima vez, que me mareo 🤢", "Vale… ya paro de girar… creo 😵"],
  drop: ["Aquí se está bien 😎", "Buen sitio, sí señor 👌", "Me quedo aquí vigilando 👀", "Perfecto, desde aquí lo controlo todo 🛰️"],
  poke: ["¡Eh, que tengo cosquillas! 😆", "¡Para, para! 🤭", "Mis circuitos no aguantan tanto cariño 🤖💕", "Vale, vale, ya estoy despierto ⚡"],
  wake: ["¡Ah! Estaba descansando los circuitos 😅", "Zzz… ¡uy! ¿Me necesitabas? 🙃", "Vuelvo al servicio, capitán 🫡"],
  party: ["¡Toma ya! PC más limpio que una patena ✨", "¡Misión cumplida! 🎉", "¡Así me gusta! Tu PC te lo agradece 🥳"],
  hidden: "Me escondo un ratito. Vuelve a llamarme desde la barra lateral 👋",
};
const pick = (a) => a[Math.floor(Math.random() * a.length)];
function quip(text, ms = 3200) {
  if (CHAT.open) return;
  _say(`<div>${esc(text)}</div>`);
  clearTimeout(bubbleTimer);
  bubbleTimer = setTimeout(() => { if (!CHAT.open) document.getElementById("smally-bubble").innerHTML = ""; }, ms);
}
function act(name, ms = 1400) {
  box.classList.remove("a-" + name); void box.offsetWidth; box.classList.add("a-" + name);
  setTimeout(() => box.classList.remove("a-" + name), ms);
}
function confetti(chars = ["✨", "🎉", "⭐", "💫", "🧹"]) {
  const fx = document.getElementById("smally-fx");
  for (let i = 0; i < 12; i++) {
    const s = document.createElement("span");
    s.textContent = pick(chars);
    s.style.setProperty("--dx", `${(Math.random() - 0.5) * 160}px`);
    s.style.setProperty("--dy", `${-40 - Math.random() * 110}px`);
    s.style.setProperty("--r", `${(Math.random() - 0.5) * 360}deg`);
    fx.appendChild(s);
    setTimeout(() => s.remove(), 1200);
  }
}

/* ---------- Humor según el estado real ---------- */
const WORK = new Set(["clean_run", "optimize", "fix", "sec_scan", "sec_update", "console", "devjunk", "dupes", "aiorg"]);
function computeMood() {
  if (Object.entries(S.jobs).some(([k, j]) => WORK.has(k) && j.state === "running")) return "busy";
  if (CHAT.busy) return "thinking";
  if (Date.now() < FUN.partyUntil) return "party";
  if (Date.now() - FUN.lastActive > 120000 && !CHAT.open) return "sleepy";
  const probs = res("diagnosis")?.problems || [];
  if (probs.some((p) => p.severity === "bad")) return "alarm";
  if (probs.some((p) => p.severity === "warn") || (res("sec_audit")?.findings || []).some((f) => f.severity === "high")) return "worried";
  return "happy";
}
// Humor de la app → expresión del Smally original
const MOOD_FACE = { happy: "neutral", alarm: "worried", worried: "empathetic", busy: "focused", thinking: "thinking", sleepy: "sleepy", party: "excited" };
// Cuando está tranquilo, de vez en cuando cambia de gesto para parecer vivo
const IDLE_FACES = ["relaxed", "curious", "attentive", "amused", "playful", "happy", "guino", "ilusionado"];
function applyMood() {
  if (box.classList.contains("dizzy")) { SFACE.set("perplejo"); return; }
  const m = computeMood();
  if (m === FUN.mood) return;
  if (FUN.mood === "sleepy" && m !== "sleepy") { act("squash", 400); SFACE.flash("surprised", 700); quip(pick(QUIPS.wake)); }
  box.classList.remove("m-" + FUN.mood);
  box.classList.add("m-" + m);
  SFACE.set(MOOD_FACE[m] || "neutral");
  FUN.mood = m;
}
setInterval(() => {
  if (FUN.mood === "happy" && !CHAT.open && !box.classList.contains("dizzy") && Math.random() < 0.6) SFACE.flash(pick(IDLE_FACES), 2200 + Math.random() * 1800);
}, 9000);
setInterval(applyMood, 800);
["mousemove", "keydown", "pointerdown", "wheel"].forEach((ev) => addEventListener(ev, () => (FUN.lastActive = Date.now()), { passive: true }));

// Fiesta cuando termina bien una limpieza u optimización
const _job = job;
job = async (kind, params, slot) => {
  const s = await _job(kind, params, slot);
  if (s?.state === "done" && ["clean_run", "optimize"].includes(kind)) {
    FUN.partyUntil = Date.now() + 4500; applyMood(); confetti();
    setTimeout(() => quip(pick(QUIPS.party), 4000), 300);
  }
  return s;
};

/* ---------- Ojos que siguen al ratón ---------- */
addEventListener("mousemove", (e) => {
  if (FUN.mood === "sleepy" || FUN.mood === "thinking" || box.classList.contains("dizzy")) return;
  const r = bot.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  const dx = e.clientX - cx, dy = e.clientY - cy, d = Math.hypot(dx, dy) || 1, k = Math.min(1, d / 300);
  SFACE.look((dx / d) * 14 * k, (dy / d) * 9 * k);
}, { passive: true });

/* ---------- Arrastrar y colocar ---------- */
function boxXY() {  // posición del robot (no del bocadillo)
  const r = bot.getBoundingClientRect();
  return [r.left, r.top];
}
// El contenedor se coloca por la esquina del robot: ajustamos por el desplazamiento del bocadillo
// Se ancla por la esquina donde está el robot, así no se mueve cuando aparece o desaparece el bocadillo
function moveBotTo(x, y) {
  const w = bot.getBoundingClientRect().width || 96;
  x = Math.max(8, Math.min(innerWidth - w - 8, x));
  y = Math.max(8, Math.min(innerHeight - w - 8, y));
  const left = x + w / 2 < innerWidth / 2, top = y < innerHeight * 0.45;
  box.classList.toggle("left", left);
  box.classList.toggle("top", top);
  const L = left ? x : null, R = left ? null : innerWidth - x - w, T = top ? y : null, B = top ? null : innerHeight - y - w;
  const set = (l, r, t, b) => Object.assign(box.style, {
    left: l == null ? "auto" : l + "px", right: r == null ? "auto" : r + "px",
    top: t == null ? "auto" : t + "px", bottom: b == null ? "auto" : b + "px",
  });
  set(L, R, T, B);
  // Corrige el margen interno del contenedor para que el robot quede justo donde se soltó
  const rb = bot.getBoundingClientRect(), dx = x - rb.left, dy = y - rb.top;
  set(L == null ? null : L + dx, R == null ? null : R - dx, T == null ? null : T + dy, B == null ? null : B - dy);
}
let drag = null;
bot.addEventListener("pointerdown", (e) => {
  if (e.button !== 0) return;
  const [x, y] = boxXY();
  drag = { sx: e.clientX, sy: e.clientY, x, y, moved: false };
  bot.setPointerCapture(e.pointerId);
});
bot.addEventListener("pointermove", (e) => {
  if (!drag) return;
  const dx = e.clientX - drag.sx, dy = e.clientY - drag.sy;
  if (!drag.moved && Math.hypot(dx, dy) < 6) return;
  if (!drag.moved) {
    // Al cogerlo se cierran el bocadillo y el chat: solo se arrastra el robot
    drag.moved = true; box.classList.add("dragging", "dizzy"); SFACE.dizzy(true); SFACE.set("perplejo");
    clearTimeout(FUN.dizzyT);
    clearTimeout(bubbleTimer);
    if (CHAT.open) { CHAT.open = false; if (typeof shush === "function") shush(); }
    document.getElementById("smally-bubble").innerHTML = "";
    const [bx, by] = boxXY(); drag.x = bx; drag.y = by;  // la posición puede cambiar al quitar el bocadillo
  }
  moveBotTo(drag.x + dx, drag.y + dy);
});
bot.addEventListener("pointerup", () => {
  if (!drag) return;
  FUN.dragged = drag.moved;
  if (drag.moved) {
    box.classList.remove("dragging");
    const [x, y] = boxXY();
    store("nova-smally-pos", JSON.stringify({ x: x / innerWidth, y: y / innerHeight }));
    act("squash", 400);
    // Sigue mareado un momento después de soltarlo
    FUN.dizzyT = setTimeout(() => { box.classList.remove("dizzy"); SFACE.dizzy(false); FUN.mood = ""; applyMood(); SFACE.flash("aliviado", 1600); }, 2200);
    setTimeout(() => quip(pick(QUIPS.dizzy)), 200);
  }
  drag = null;
});
// Clic (sin arrastre) abre el chat; muchos toques seguidos le hacen cosquillas
bot.onclick = () => {
  if (FUN.dragged) { FUN.dragged = false; return; }
  const now = Date.now();
  FUN.pokes = FUN.pokes.filter((t) => now - t < 3000).concat(now);
  act("squash", 400); SFACE.flash(CHAT.open ? "happy" : "surprised", 600);
  if (FUN.pokes.length >= 4) { FUN.pokes = []; act("spin", 800); SFACE.flash("amused", 2200); robotSound(); if (CHAT.open) toggleChat(); setTimeout(() => quip(pick(QUIPS.poke)), 100); return; }
  toggleChat();
};
function restorePos() {
  const p = JSON.parse(load("nova-smally-pos") || "null");
  if (p) moveBotTo(p.x * innerWidth, p.y * innerHeight);
}
addEventListener("resize", () => { if (load("nova-smally-pos")) restorePos(); });
setTimeout(restorePos, 50);

/* ---------- Ocultar / mostrar ---------- */
function setHidden(h) {
  document.body.classList.toggle("smally-hidden", h);
  store("nova-smally-hidden", h ? "1" : undefined);
  if (h) { CHAT.open = false; renderChat(); }
}
document.getElementById("smally-x").addEventListener("click", (e) => {
  e.stopPropagation();
  quip(QUIPS.hidden, 1600);
  setTimeout(() => setHidden(true), 1200);
});
EXTRA_ACT.smallyshow = () => { setHidden(false); act("wave"); quip(`¡He vuelto${hi()}! 👋`); };
if (load("nova-smally-hidden") === "1") setHidden(true);

/* ---------- Animaciones espontáneas ---------- */
new MutationObserver(() => {
  if (!CHAT.open && document.getElementById("smally-bubble").innerHTML) { act("wave"); SFACE.flash("happy", 1500); SFACE.talk(1200); }
}).observe(document.getElementById("smally-bubble"), { childList: true });
setInterval(() => {
  if (document.body.classList.contains("smally-hidden") || CHAT.open || drag || FUN.mood !== "happy") return;
  const r = Math.random();
  if (r < 0.3) { SFACE.look(r < 0.15 ? -14 : 14, -3); SFACE.flash("curious", 1600); } else if (r < 0.5) act("wave"); else if (r < 0.6) act("squash", 400);
}, 14000);
applyMood();
