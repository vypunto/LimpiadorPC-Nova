"use strict";
/* Organizador de carpetas con IA: elegir carpeta → plan → revisar → aplicar (reversible). */

S.org = { folder: "", mode: "local", instr: "", rename: true, view: "tree", skip: new Set(), open: new Set(), openTree: new Set() };
TIPS.aiorg = ["info", "Solo mueve, nunca borra", "Los archivos se mueven dentro de la carpeta elegida. Los proyectos de código, carpetas ocultas y archivos de la última hora no se tocan. Puedes deshacerlo todo con un clic."];
TIPS.aiorg_privacy = ["warn", "Qué se envía a la IA", "Solo nombres de archivo, tamaños y fechas, a la API de Anthropic con tu clave. Nunca el contenido de los archivos. Si prefieres no enviar nada, usa 'Reglas locales'."];
GREET.organizador = "Elige una carpeta y te propongo un orden. Nada se mueve hasta que revises el plan y pulses 'Organizar', y siempre se puede deshacer.";

VIEWS.organizador = function () {
  const o = S.org, cfg = S.orgCfg || {}, r = res("aiorg");
  const needKey = o.mode === "ai" && !cfg.has_key;
  let html = `${jobline("aiorg")}<div class="card glow"><div class="card-head"><div><h3>¿Qué carpeta quieres ordenar?${tip("aiorg")}</h3><p class="sub">Por ejemplo Descargas, Escritorio o una carpeta de fotos.</p></div></div>
    <div class="row wrap"><input class="input" id="org-folder" placeholder="C:\\Users\\…\\Downloads" value="${esc(o.folder)}" style="flex:1;min-width:280px">
      <button class="btn" data-act="orgpick">${ic("folder")}Elegir carpeta</button></div>
    <div class="row wrap mt"><div class="seg">${[["ai", "✨ Con IA (Claude)"], ["local", "Reglas locales (sin Internet)"]].map(([k, l]) => `<button class="${o.mode === k ? "on" : ""}" data-act="orgmode" data-v="${k}">${l}</button>`).join("")}</div>
      ${o.mode === "ai" ? tip("aiorg_privacy") : `<label class="opt"><input type="checkbox" class="chk" data-act="orgren" ${o.rename ? "checked" : ""}>Proponer nombres limpios</label>${tip("orgren")}`}<span class="spacer"></span>
      <button class="btn primary" data-act="orgplan" ${running("aiorg") || needKey ? "disabled" : ""}>${ic("bolt")}Generar plan</button></div>
    ${o.mode === "ai" ? `<input class="input mt" id="org-instr" style="width:100%" placeholder="Opcional: indicaciones, p. ej. «separa por clientes» o «fotos por viaje y año»" value="${esc(o.instr)}">` : ""}
    ${needKey ? `<div class="banner info mt">${ic("key")}<div class="spacer"><div class="t">Conecta tu clave de API de Anthropic</div><div class="s">Créala en console.anthropic.com → API Keys. Se guarda solo en este PC. Coste orientativo: ~0,10 $ por cada 250 archivos.</div>
      <div class="row mt"><input class="input" type="password" id="org-key" placeholder="sk-ant-…" style="flex:1"><button class="btn sm primary" data-act="orgkey">Guardar</button></div></div></div>` : ""}
    ${o.mode === "ai" && cfg.has_key ? `<div class="muted mt" style="font-size:12px">Modelo ${esc(cfg.model)} · clave configurada · <a data-act="orgkeydel" style="cursor:pointer;text-decoration:underline">quitar clave</a></div>` : ""}
  </div>`;
  if (!r) return html + `<div class="mt">${empty("folder", "Así funciona", "1. Eliges carpeta · 2. Se genera un plan · 3. Lo revisas y desmarcas lo que no quieras · 4. Organizas · 5. Si no te gusta, Deshacer.")}</div><div class="row mt"><span class="spacer"></span><button class="btn ghost" data-act="orgundo2">${ic("refresh")}Deshacer la última organización</button></div>`;
  const plan = r.plan || [];
  const groups = {};
  plan.forEach((p) => (groups[p.target] ||= []).push(p));
  const keys = Object.keys(groups).sort((a, b) => groups[b].length - groups[a].length);
  const active = plan.filter((p) => !o.skip.has(p.target));
  html += `<div class="g g4 mt"><div class="card"><div class="eyebrow">Analizados</div><div class="metric-big">${nf(r.scanned, 0)}</div></div>
    <div class="card"><div class="eyebrow">Se moverán</div><div class="metric-big grad-text">${nf(active.length, 0)}</div></div>
    <div class="card"><div class="eyebrow">Se renombrarán</div><div class="metric-big">${nf(active.filter((p) => p.renamed).length, 0)}</div></div>
    <div class="card"><div class="eyebrow">Se quedan igual</div><div class="metric-big">${nf(r.scanned - plan.length, 0)}</div></div></div>
    ${r.capped ? `<div class="banner mt">${ic("alert")}<div>Se analizaron los primeros 2.000 archivos. Organiza y vuelve a generar el plan para el resto.</div></div>` : ""}
    ${r.kept?.length ? `<div class="banner info mt">${ic("lock")}<div><div class="t">${r.kept.length} carpetas protegidas no se tocan</div><div class="s">${esc(r.kept.slice(0, 8).join(" · "))}${r.kept.length > 8 ? " …" : ""} (proyectos de código, ocultas o de apps)</div></div></div>` : ""}
    <div class="toolbar mt2"><div class="seg">${[["tree", "Así quedará"], ["groups", "Por carpetas (elegir)"]].map(([k, l]) => `<button class="${o.view === k ? "on" : ""}" data-act="orgview" data-v="${k}">${l}</button>`).join("")}</div>
      <span class="muted" style="font-size:12.5px">${o.view === "tree" ? "Vista previa del resultado final. Nada se ha movido todavía." : "Desmarca las carpetas que no quieras crear."}</span></div>
    ${o.view === "tree" ? orgTree(r.folder, active) : keys.map((k) => { const g = groups[k], on = !o.skip.has(k), open = o.open.has(k);
      return `<div class="dgroup"><div class="dh"><input type="checkbox" class="chk" data-act="orgskip" data-v="${esc(k)}" ${on ? "checked" : ""}>
        <span class="ok">${ic("folder")}</span><b class="ellipsis" style="flex:1">${esc(k)}</b><span class="muted">${g.length} archivos · ${fmt(g.reduce((a, p) => a + p.size, 0))}</span>
        <button class="btn sm ghost" data-act="orgopen" data-v="${esc(k)}">${open ? "Ocultar" : "Ver archivos"}</button></div>
        ${open ? `<div class="list">${g.slice(0, 60).map((p) => `<div class="item" style="padding:7px 16px"><div class="main-col"><div class="ellipsis">${esc(p.new_name || base(p.rel))}</div><div class="s ellipsis">${p.renamed ? `antes: ${esc(base(p.rel))} · ` : ""}${esc(dir(p.rel) || "(raíz)")} → ${esc(k)}</div></div><span class="size">${fmt(p.size)}</span></div>`).join("")}${g.length > 60 ? `<div class="muted" style="padding:8px 16px">…y ${g.length - 60} más</div>` : ""}</div>` : ""}</div>`; }).join("") || empty("check", "Ya está ordenada", "No hay nada que mover.")}
    ${active.length ? `<div class="actionbar"><div><div class="muted" style="font-size:12px">${esc(r.folder)}</div><div class="total grad-text">${nf(active.length, 0)} archivos</div></div><span class="spacer"></span>
      <button class="btn ghost" data-act="orgundo2">${ic("refresh")}Deshacer la última</button><button class="btn primary" data-act="orgapply2">${ic("folder")}Organizar ahora</button></div>` : ""}`;
  return html;
};

ENTER.organizador = async () => { S.orgCfg = await api("/api/aiorg/config").catch(() => ({})); render(); };

const _syncOrg = () => { const f = $("#org-folder"), i = $("#org-instr"); if (f) S.org.folder = f.value; if (i) S.org.instr = i.value; };
Object.assign(EXTRA_ACT, {
  orgpick: async () => { toast("Se ha abierto el selector de carpetas (puede quedar detrás de esta ventana)", "info"); const r = await api("/api/aiorg/pick", {}); if (r.folder) { S.org.folder = r.folder; render(); } },
  orgmode: (v) => { _syncOrg(); S.org.mode = v; render(); },
  orgkey: async () => { const r = await api("/api/aiorg/key", { key: $("#org-key").value }); toast(r.message, r.ok ? "ok" : "warn"); ENTER.organizador(); },
  orgkeydel: async () => { await api("/api/aiorg/key", { key: "" }); toast("Clave eliminada de este equipo"); ENTER.organizador(); },
  orgplan: () => { _syncOrg(); if (!S.org.folder.trim()) return toast("Elige primero una carpeta", "warn"); S.org.skip.clear(); S.org.open.clear(); S.org.openTree.clear(); job("aiorg", { folder: S.org.folder, mode: S.org.mode, instructions: S.org.instr, rename: S.org.rename }); },
  orgren: () => { S.org.rename = !S.org.rename; if (res("aiorg")) EXTRA_ACT.orgplan(); else render(); },
  orgview: (v) => { S.org.view = v; render(); },
  orgtree: (v) => { const s = S.org.openTree; s.has(v) ? s.delete(v) : s.add(v); render(); },
  orgskip: (v) => { const s = S.org.skip; s.has(v) ? s.delete(v) : s.add(v); render(); },
  orgopen: (v) => { const s = S.org.open; s.has(v) ? s.delete(v) : s.add(v); render(); },
  orgapply2: async () => {
    const r = res("aiorg"), act = r.plan.filter((p) => !S.org.skip.has(p.target));
    const n = new Set(act.map((p) => p.target)).size;
    if (!(await askDetailed("Organizar carpeta", `<p>Se moverán <b>${nf(act.length, 0)} archivos</b> (${nf(act.filter((p) => p.renamed).length, 0)} con nombre nuevo) a <b>${n} carpetas</b> dentro de <span class="mono">${esc(r.folder)}</span>.</p>
      <div class="infoblock"><div class="rec"><span class="ok" style="flex:none">${ic("lock")}</span><div><b>Nada se borra</b><div class="muted">Solo se mueven. Si ya existe un archivo con el mismo nombre, se añade (1), (2)…</div></div></div>
      <div class="rec"><span class="ok" style="flex:none">${ic("refresh")}</span><div><b>Reversible</b><div class="muted">«Deshacer la última» devuelve cada archivo a su sitio y elimina las carpetas vacías creadas.</div></div></div>
      <div class="rec"><span class="warn" style="flex:none">${ic("alert")}</span><div><b>Ten en cuenta</b><div class="muted">Los accesos directos o programas que apunten a la ruta antigua de un archivo dejarán de encontrarlo hasta que deshagas.</div></div></div></div>`,
      "Organizar ahora", false, "He revisado el plan"))) return;
    const out = await api("/api/aiorg/apply", { skip: [...S.org.skip] }).catch((e) => toast(e.message, "bad"));
    if (!out) return;
    toast(`${nf(out.moved, 0)} archivos organizados` + (out.failed ? ` · ${out.failed} omitidos` : ""));
    delete S.jobs.aiorg; render();
  },
  orgundo2: async () => {
    if (!(await ask("Deshacer", "Los archivos de la última organización volverán a su ubicación original.", "Deshacer"))) return;
    const r = await api("/api/aiorg/undo", {}); toast(r.message, r.restored ? "ok" : "info"); delete S.jobs.aiorg; render();
  },
});
document.addEventListener("input", (e) => { if (e.target.id === "org-folder" || e.target.id === "org-instr") _syncOrg(); });

TIPS.orgren = ["info", "Nombres ordenables y sin ruido", "Pone la fecha delante cuando viene en el nombre (o en fotos de cámara y capturas), quita guiones bajos, 'Copia de', 'at', 'UTC'… Conserva (1), (2). Si dos archivos acabarían igual, se numeran. Al deshacer vuelven sus nombres originales."];

/* Árbol con la estructura final */
function orgTree(root, plan) {
  const tree = { dirs: {}, files: [] };
  plan.forEach((p) => {
    let node = tree;
    p.dst.split(/[\\/]/).slice(0, -1).forEach((seg) => (node = node.dirs[seg] ||= { dirs: {}, files: [] }));
    node.files.push(p);
  });
  const count = (n) => n.files.length + Object.values(n.dirs).reduce((a, d) => a + count(d), 0);
  const size = (n) => n.files.reduce((a, p) => a + p.size, 0) + Object.values(n.dirs).reduce((a, d) => a + size(d), 0);
  const draw = (node, path, depth) => Object.keys(node.dirs).sort((a, b) => a.localeCompare(b, "es", { numeric: true })).map((name) => {
    const d = node.dirs[name], key = path + "/" + name, open = depth === 0 || S.org.openTree.has(key);
    const files = [...d.files].sort((a, b) => a.new_name.localeCompare(b.new_name, "es", { numeric: true }));
    return `<li><div class="tnode" data-act="orgtree" data-v="${esc(key)}"><span class="tw">${open ? "▾" : "▸"}</span><span class="ok">${ic("folder")}</span><b>${esc(name)}</b><span class="muted">${nf(count(d), 0)} · ${fmt(size(d))}</span></div>
      ${open ? `<ul>${draw(d, key, depth + 1)}${files.slice(0, 40).map((p) => `<li class="tfile"><span class="dim">${ic("file")}</span><div class="main-col"><div class="ellipsis">${esc(p.new_name)}</div>${p.renamed ? `<div class="s ellipsis">antes: ${esc(base(p.rel))}</div>` : ""}</div><span class="size">${fmt(p.size)}</span></li>`).join("")}
        ${files.length > 40 ? `<li class="tfile muted">…y ${nf(files.length - 40, 0)} archivos más</li>` : ""}</ul>` : ""}</li>`;
  }).join("");
  return `<div class="card"><div class="tnode"><span class="ok">${ic("folder")}</span><b>${esc(base(root))}</b><span class="muted">${nf(plan.length, 0)} archivos organizados</span></div><ul class="tree">${draw(tree, "", 0)}</ul></div>`;
}
