"use strict";
/* Diagnóstico → soluciones guiadas paso a paso, con botones que ejecutan cada paso. */

PAGES.splice(1, 0, { id: "soluciones", t: "Soluciones", s: "Problemas detectados en tu PC y cómo arreglarlos paso a paso", i: "wrench", slots: ["diagnosis", "health"] });
const STEP_BTN = { fix: "Ejecutar", url: "Abrir web", settings: "Abrir ajustes", tool: "Abrir", page: "Ir" };
const doneKey = (pid, i) => `nova-done-${pid}-${i}`;
const isDone = (pid, i) => { try { return localStorage.getItem(doneKey(pid, i)) === "1"; } catch { return false; } };

function solutionsList(limit) {
  const d = res("diagnosis");
  if (!d) return jobline("diagnosis") || '<div class="skeleton"></div>';
  const probs = d.problems || [];
  if (!probs.length) return empty("check", "No he encontrado problemas", "Tu equipo no muestra caídas, falta de espacio ni avisos importantes.");
  return probs.slice(0, limit || 99).map((p, pi) => {
    const done = p.steps.filter((_, i) => isDone(p.id, i)).length;
    const open = S.solOpen ? S.solOpen.has(p.id) : pi === 0;
    return `<div class="card sol ${p.severity} mt"><div class="row" data-act="solopen" data-v="${esc(p.id)}" style="cursor:pointer">
        <span class="dot ${p.severity}"></span><h3 class="spacer" style="margin:0">${esc(p.title)}</h3>
        <span class="chip ${done === p.steps.length ? "ok" : ""}">${done}/${p.steps.length} pasos</span><span class="muted">${open ? "▾" : "▸"}</span></div>
      ${open ? `<p style="margin:12px 0 6px">${esc(p.why)}</p>
        <details class="evid"><summary>Pruebas que he encontrado</summary><ul>${p.evidence.map((e) => `<li>${esc(e)}</li>`).join("")}</ul></details>
        <div class="steps">${p.steps.map((s, i) => { const a = s.action, ok = isDone(p.id, i);
          return `<div class="step ${ok ? "done" : ""}"><label class="stepn"><input type="checkbox" class="chk" data-act="soldone" data-v="${esc(p.id)}|${i}" ${ok ? "checked" : ""}><b>${i + 1}</b></label>
            <div class="main-col">${esc(s.text)}</div>
            ${a ? `<button class="btn sm ${i === p.steps.findIndex((_, j) => !isDone(p.id, j)) ? "primary" : ""}" data-act="solstep" data-v="${pi}|${i}">${ic(a.type === "url" ? "eye" : a.type === "fix" ? "play" : "folder")}${STEP_BTN[a.type]}</button>` : ""}</div>`; }).join("")}</div>
        <div class="muted" style="font-size:12px;margin-top:10px">Marca cada paso al terminarlo. Después de arreglarlo, pulsa «Volver a diagnosticar» para comprobar que no hay caídas nuevas.</div>` : ""}</div>`;
  }).join("");
}

VIEWS.soluciones = () => `${jobline("diagnosis")}
  <div class="banner info">${ic("info")}<div class="spacer"><div class="t">Te digo qué falla, por qué y cómo arreglarlo</div><div class="s">Analizo el Visor de eventos, los drivers instalados, la memoria y los discos. Los pasos con botón los puedes hacer desde aquí.</div></div>
    <button class="btn sm" data-act="soldiag" ${running("diagnosis") ? "disabled" : ""}>${ic("refresh")}Volver a diagnosticar</button><button class="btn sm ghost" data-act="report">${ic("file")}Informe</button></div>
  ${solutionsList()}`;
ENTER.soluciones = () => { if (!S.jobs.diagnosis) job("diagnosis"); };

// En Salud y en el Panel, el problema principal arriba
const _salud = VIEWS.salud;
VIEWS.salud = () => (res("diagnosis")?.problems?.length ? `<div class="section-title" style="margin-top:0">Cómo solucionarlo</div>${solutionsList(1)}<div class="row mt"><span class="spacer"></span><button class="btn sm" data-page="soluciones">Ver todas las soluciones</button></div><div class="section-title">Detalle técnico</div>` : "") + _salud();
const _panel = VIEWS.panel;
VIEWS.panel = () => {
  const p = res("diagnosis")?.problems?.[0];
  return (p && p.severity === "bad" ? `<div class="banner bad">${ic("alert")}<div class="spacer"><div class="t">He encontrado la causa: ${esc(p.title.toLowerCase())}</div><div class="s">${esc(p.summary || p.why.slice(0, 120))}</div></div><button class="btn primary" data-page="soluciones">${ic("wrench")}Ver cómo arreglarlo</button></div>` : "") + _panel();
};
const _salEnter = ENTER.salud;
ENTER.salud = () => { _salEnter?.(); if (!S.jobs.diagnosis) job("diagnosis"); };

Object.assign(EXTRA_ACT, {
  soldiag: () => job("diagnosis", { refresh: true }),
  solopen: (v) => { S.solOpen ||= new Set([res("diagnosis").problems[0]?.id]); S.solOpen.has(v) ? S.solOpen.delete(v) : S.solOpen.add(v); render(); },
  soldone: (v, el) => { const [pid, i] = v.split("|"); try { el.checked ? localStorage.setItem(doneKey(pid, i), "1") : localStorage.removeItem(doneKey(pid, i)); } catch {} render(); },
  solstep: async (v) => {
    const [pi, i] = v.split("|").map(Number), p = res("diagnosis").problems[pi], s = p.steps[i], a = s.action;
    if (a.type === "page") return go(a.id);
    if (a.type === "fix") {
      if (!S.fixes) S.fixes = (await api("/api/fixes")).fixes;
      const f = S.fixes.find((x) => x.id === a.id);
      if (f?.admin && !S.admin) return toast("Este paso necesita permisos: pulsa «Ejecutar como admin» en la barra lateral.", "warn");
      return ACT.fix(a.id);
    }
    const r = await api("/api/open", a).catch((e) => ({ ok: false, message: e.message }));
    toast(r.ok ? (a.type === "url" ? "Abierto en tu navegador" : "Abierto") : r.message, r.ok ? "ok" : "warn");
  },
});
["panel", "salud"].forEach((id) => PAGES.find((p) => p.id === id).slots.push("diagnosis"));
// Diagnóstico en segundo plano al abrir la app, cuando termine la salud
setTimeout(() => { if (!S.jobs.diagnosis) job("diagnosis"); }, 6000);
nav(); // que «Soluciones» aparezca en el menú desde el primer momento
