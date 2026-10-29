"use strict";
/* Bienvenida tipo app: carrusel de 5 pantallas con puntos, flechas del teclado y arrastre.
   «Saltar», «Empezar» y «No volver a mostrar». */

const SLIDES = [
  { art: "smally", title: (n) => `Hola${n ? ", " + n : ""}`, text: "Soy Smally. Voy a ayudarte a tener tu PC rápido, limpio y protegido." },
  { art: "wrench", title: () => "Sé qué le pasa a tu PC", text: "Detecto la causa de cuelgues, pantallazos y lentitud, y te guío para arreglarlo paso a paso.", go: "soluciones" },
  { art: "clean", title: () => "Libera espacio sin riesgo", text: "Basura, duplicados y archivos olvidados. Antes de borrar ves exactamente qué se va.", go: "limpieza" },
  { art: "shield", title: () => "Protegido y reparado", text: "Defender, extensiones sospechosas y reparaciones oficiales de Windows. Lo esencial lleva candado.", go: "seguridad" },
  { art: "spark", title: () => "Todo a un toque", text: "Pulsa Ctrl + K para ir a cualquier sitio, o pregúntame lo que quieras haciendo clic en mí." },
];

function slideArt(a) {
  if (a === "smally") return `<canvas class="ob-face" width="411" height="297"></canvas>`;
  const icon = { wrench: "wrench", clean: "clean", shield: "shield", spark: "search" }[a];
  return `<div class="ob-orb"><div class="ob-ring"></div><div class="ob-ring r2"></div><span>${ic(icon)}</span></div>`;
}

function showWelcome(force) {
  try { if (!force && localStorage.getItem("nova-welcome") === "off") return; } catch {}
  if (document.querySelector(".ob")) return;
  const name = typeof userName === "function" ? userName() : "";
  const w = document.createElement("div");
  w.className = "modal-wrap ob-wrap";
  w.innerHTML = `<div class="ob">
    <button class="ob-skip" data-ob="skip">Saltar</button>
    <div class="ob-track">${SLIDES.map((s, i) => `<section class="ob-slide" data-i="${i}">
      <div class="ob-art">${slideArt(s.art)}</div>
      <h2>${esc(s.title(name))}</h2><p>${esc(s.text)}</p>
      ${s.go ? `<button class="ob-link" data-ob-go="${s.go}">Verlo ahora →</button>` : ""}
    </section>`).join("")}</div>
    <div class="ob-foot">
      <label class="ob-never"><input type="checkbox" class="chk" id="ob-never">No volver a mostrar</label>
      <div class="ob-dots">${SLIDES.map((_, i) => `<button data-ob-dot="${i}" aria-label="Pantalla ${i + 1}"></button>`).join("")}</div>
      <div class="ob-nav"><button class="btn ghost" data-ob="prev">Atrás</button><button class="btn primary" data-ob="next">Siguiente</button></div>
    </div></div>`;
  document.body.appendChild(w);

  let i = 0;
  const track = w.querySelector(".ob-track"), next = w.querySelector('[data-ob="next"]'), prev = w.querySelector('[data-ob="prev"]');
  const goTo = (n) => {
    i = Math.max(0, Math.min(SLIDES.length - 1, n));
    track.style.transform = `translateX(${-i * 100}%)`;
    w.querySelectorAll(".ob-slide").forEach((s, k) => s.classList.toggle("on", k === i));
    w.querySelectorAll("[data-ob-dot]").forEach((d, k) => d.classList.toggle("on", k === i));
    prev.style.visibility = i ? "visible" : "hidden";
    next.textContent = i === SLIDES.length - 1 ? "Empezar" : "Siguiente";
  };
  const close = (page) => {
    try { if (w.querySelector("#ob-never").checked) localStorage.setItem("nova-welcome", "off"); } catch {}
    w.classList.add("out");
    setTimeout(() => w.remove(), 250);
    removeEventListener("keydown", onKey);
    if (page) go(page);
  };
  const onKey = (e) => {
    if (e.key === "ArrowRight") goTo(i + 1);
    else if (e.key === "ArrowLeft") goTo(i - 1);
    else if (e.key === "Escape") close();
    else if (e.key === "Enter") i === SLIDES.length - 1 ? close() : goTo(i + 1);
  };
  addEventListener("keydown", onKey);
  w.addEventListener("click", (e) => {
    const b = e.target.closest("[data-ob],[data-ob-dot],[data-ob-go]");
    if (!b) return;
    if (b.dataset.obDot != null) goTo(+b.dataset.obDot);
    else if (b.dataset.obGo) close(b.dataset.obGo);
    else if (b.dataset.ob === "next") i === SLIDES.length - 1 ? close() : goTo(i + 1);
    else if (b.dataset.ob === "prev") goTo(i - 1);
    else if (b.dataset.ob === "skip") close();
  });
  // Arrastrar / deslizar para cambiar de pantalla
  let sx = null;
  track.addEventListener("pointerdown", (e) => { if (!e.target.closest("button")) { sx = e.clientX; track.style.transition = "none"; } });
  addEventListener("pointermove", (e) => { if (sx != null) track.style.transform = `translateX(calc(${-i * 100}% + ${e.clientX - sx}px))`; });
  addEventListener("pointerup", (e) => {
    if (sx == null) return;
    const dx = e.clientX - sx; sx = null; track.style.transition = "";
    goTo(dx < -60 ? i + 1 : dx > 60 ? i - 1 : i);
  });
  goTo(0);

  // La primera pantalla muestra la cara real de Smally, en grande y en directo
  const big = w.querySelector(".ob-face"), src = document.getElementById("smally-face");
  if (big && src) {
    const bctx = big.getContext("2d");
    (function mirror() {
      if (!big.isConnected) return;
      bctx.clearRect(0, 0, big.width, big.height);
      bctx.drawImage(src, 0, 0, big.width, big.height);
      requestAnimationFrame(mirror);
    })();
    SFACE.flash("happy", 2500);
  }
}
EXTRA_ACT.welcome = () => showWelcome(true);
// Se muestra al abrir, cuando ya conocemos tu nombre
(function wait(n = 0) { if (S.sys || n > 20) showWelcome(false); else setTimeout(() => wait(n + 1), 300); })();
