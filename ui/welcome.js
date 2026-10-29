"use strict";
/* Pantalla de bienvenida: qué puedes hacer con la app. Botones «Cerrar» y «No volver a mostrar». */

const WELCOME = [
  ["wrench", "Soluciones", "Te digo qué falla en tu PC, por qué y cómo arreglarlo paso a paso.", "soluciones"],
  ["rocket", "Optimizar en 1 clic", "Limpieza segura y diagnóstico completo desde el Panel.", "panel"],
  ["clean", "Limpieza", "Temporales, cachés de navegadores, GPU y apps. Ves qué se borra antes.", "limpieza"],
  ["disk", "Espacio", "Archivos grandes, sin usar y basura de proyectos de programación.", "espacio"],
  ["copy", "Duplicados", "Copias idénticas verificadas; van a la Papelera, recuperables.", "duplicados"],
  ["folder", "Organizador IA", "Ordena y renombra cualquier carpeta con vista previa y Deshacer.", "organizador"],
  ["shield", "Seguridad", "Microsoft Defender, extensiones sospechosas y cambios del malware.", "seguridad"],
  ["pulse", "Salud y Reparar", "Pantallas azules, apagados y reparaciones oficiales de Windows.", "reparar"],
  ["power", "Inicio y fondo", "Qué arranca con Windows y qué corre en segundo plano.", "inicio"],
];

function showWelcome(force) {
  try { if (!force && localStorage.getItem("nova-welcome") === "off") return; } catch {}
  if (document.querySelector(".welcome")) return;
  const name = typeof userName === "function" ? userName() : "";
  const w = modal(`<div class="welcome">
    <div class="wl-head"><div class="orb" style="width:46px;height:46px;border-radius:14px"></div>
      <div><h3 style="margin:0">Bienvenido${name ? ", " + esc(name) : ""} a Limpiador PC Nova</h3>
      <div class="muted">Tu PC más rápido, limpio y protegido. Esto es lo que puedes hacer:</div></div></div>
    <div class="wl-grid">${WELCOME.map(([i, t, d, p]) => `<button class="wl-item" data-wl="${p}"><span class="wl-ico">${ic(i)}</span><span><b>${t}</b><small>${d}</small></span></button>`).join("")}</div>
    <div class="wl-safe">${ic("lock")}<span><b>Seguro por diseño:</b> lo que borras va a la Papelera, lo esencial lleva candado, las reparaciones crean un punto de restauración y todo queda en el Historial.</span></div>
    <div class="wl-safe" style="margin-top:8px">🤖<span><b>Smally</b>, abajo a la derecha, responde tus dudas y te avisa de lo importante. Arrástralo donde quieras.</span></div>
    <div class="foot"><button class="btn ghost" data-wl-off>No volver a mostrar</button><button class="btn primary" data-wl-close>Cerrar y empezar</button></div>
  </div>`, true);
  w.addEventListener("click", (e) => {
    const off = e.target.closest("[data-wl-off]"), close = e.target.closest("[data-wl-close]"), item = e.target.closest("[data-wl]");
    if (off) { try { localStorage.setItem("nova-welcome", "off"); } catch {} toast("Puedes volver a verla desde «Guía rápida» en la barra lateral", "info"); }
    if (off || close || item || e.target === w) w.remove();
    if (item) go(item.dataset.wl);
  });
}
EXTRA_ACT.welcome = () => showWelcome(true);
// Se muestra al abrir, cuando ya conocemos tu nombre
(function wait(n = 0) { if (S.sys || n > 20) showWelcome(false); else setTimeout(() => wait(n + 1), 300); })();
