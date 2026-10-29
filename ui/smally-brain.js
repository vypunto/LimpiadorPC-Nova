"use strict";
/* Cerebro local de Smally: entiende preguntas libres sin Internet.
   - Normaliza (minúsculas, sin tildes), corrige erratas (distancia de edición) y reduce palabras a su raíz.
   - Busca en un corpus construido con todo lo que sabe la app (temas, reparaciones, limpieza, avisos,
     diagnóstico real del PC y secciones) y puntúa por coincidencia ponderada (TF-IDF simplificado).
   - Recuerda el tema anterior para preguntas de seguimiento ("¿y eso cómo se hace?"). */

const STOP = new Set("el la los las un una unos unas de del al a en y o u que se me mi mis tu tus su sus es son esta este esto eso esa lo le les con por para como pero mas muy ya hay tengo tiene puedo puede quiero hacer hago sobre cual cuales donde cuando porque por que yo te nos ha he han si no sin le ver algo todo nada esta estan estoy ser".split(" "));
// Sinónimos → término canónico (amplía lo que entiende)
const SYN = {
  ordenador: "pc", computadora: "pc", equipo: "pc", portatil: "pc", laptop: "pc", maquina: "pc",
  lento: "lentitud", lenta: "lentitud", tarda: "lentitud", ralentiza: "lentitud", rapido: "lentitud", rapida: "lentitud", acelerar: "lentitud", rendimiento: "lentitud", optimizar: "lentitud", va: "lentitud",
  reinicia: "caida", reinicio: "caida", reinicios: "caida", apaga: "caida", apagones: "caida", apagado: "caida", pantallazo: "caida", pantallazos: "caida", bsod: "caida", azul: "caida", cuelga: "caida", congela: "caida", bloquea: "caida", crash: "caida", error: "caida",
  espacio: "espacio", lleno: "espacio", llena: "espacio", liberar: "espacio", gigas: "espacio", gb: "espacio", ocupa: "espacio", disco: "espacio", almacenamiento: "espacio", capacidad: "espacio",
  borrar: "limpiar", eliminar: "limpiar", limpieza: "limpiar", basura: "limpiar", temporales: "limpiar", cache: "limpiar", quitar: "limpiar",
  virus: "seguridad", malware: "seguridad", troyano: "seguridad", hackeado: "seguridad", hacker: "seguridad", antivirus: "seguridad", defender: "seguridad", amenaza: "seguridad", espia: "seguridad", spyware: "seguridad",
  arranque: "inicio", arranca: "inicio", encender: "inicio", enciende: "inicio", startup: "inicio", fondo: "inicio", servicio: "inicio", servicios: "inicio", segundo: "inicio",
  copias: "duplicados", repetidos: "duplicados", duplicado: "duplicados", iguales: "duplicados",
  ordenar: "organizar", carpetas: "organizar", carpeta: "organizar", renombrar: "organizar", desordenado: "organizar",
  driver: "drivers", controlador: "drivers", controladores: "drivers", grafica: "drivers", graficos: "drivers", amd: "drivers", nvidia: "drivers", radeon: "drivers",
  wifi: "red", internet: "red", conexion: "red", navegar: "red", dns: "red", ip: "red",
  memoria: "ram", ram: "ram",
  programa: "programas", aplicacion: "programas", aplicaciones: "programas", apps: "programas", desinstalar: "programas", instalado: "programas",
  arreglar: "reparar", solucionar: "reparar", reparacion: "reparar", fix: "reparar", solucion: "reparar", soluciones: "reparar", falla: "reparar", roto: "reparar",
  sonido: "audio", altavoz: "audio", altavoces: "audio", impresora: "imprimir",
  peligroso: "riesgo", seguro: "riesgo", riesgo: "riesgo", romper: "riesgo", peligro: "riesgo",
};
const FOLLOW = /^(y |pero |entonces |vale |ok |eso|esto|lo |la |como lo|cómo lo|como se|cómo se|donde|dónde|por que|por qué|y si|mas |más |que mas|qué más|explica|detalla|siguiente|despues|después)/i;

const norm = (t) => String(t).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9ñ\s]/g, " ");
function stem(w) {
  for (const suf of ["amente", "aciones", "acion", "mente", "ando", "iendo", "ados", "idas", "idos", "ado", "ido", "ada", "ida", "ar", "er", "ir", "es", "s"]) {
    if (w.length > suf.length + 3 && w.endsWith(suf)) return w.slice(0, -suf.length);
  }
  return w;
}
function tokens(text) {
  return norm(text).split(/\s+/).filter((w) => w.length > 1 && !STOP.has(w)).flatMap((w) => (SYN[w] ? [SYN[w], stem(w)] : [stem(w)]));
}
function lev(a, b) {
  if (Math.abs(a.length - b.length) > 2) return 9;
  const d = Array.from({ length: a.length + 1 }, (_, i) => [i]);
  for (let j = 1; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++) for (let j = 1; j <= b.length; j++)
    d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
  return d[a.length][b.length];
}

/* ---------- Corpus: todo lo que sabe la app ---------- */
function buildCorpus() {
  const docs = [];
  const add = (keys, answer, pages = [], boost = 1) => docs.push({ toks: tokens(keys), answer, pages, boost });
  // Temas principales (respuestas dinámicas con datos reales)
  add("salud estado pc como esta resumen general diagnostico problemas que le pasa", () => stateAnswer(), ["soluciones", "panel"], 1.4);
  add("caida reinicia apaga pantallazo azul bsod cuelga causa por que se reinicia", () => crashAnswer(), ["soluciones", "salud"], 1.5);
  add("lentitud lento rapido rendimiento optimizar acelerar mejorar va mal tarda", () => KB[2][1](), ["panel", "inicio"], 1.3);
  add("espacio liberar lleno disco gigas ocupa almacenamiento", () => KB[3][1](), ["limpieza", "espacio"], 1.3);
  add("limpiar borrar riesgo seguro que se borra puedo borrar basura temporales", () => KB[4][1](), ["limpieza"], 1.2);
  add("seguridad virus malware antivirus defender amenaza hackeado", () => secAnswer(), ["seguridad"], 1.3);
  add("extension navegador chrome edge cupones vpn hola", () => KB[6][1](), ["seguridad"]);
  add("inicio arranque encender segundo plano servicios tareas programadas quitar quito desactivar programas al iniciar", () => KB[7][1](), ["inicio"], 1.4);
  add("duplicados copias repetidos iguales", () => KB[8][1](), ["duplicados"]);
  add("organizar carpetas ordenar renombrar descargas desordenado", () => KB[9][1](), ["organizador"]);
  add("reparar windows sfc dism chkdsk archivos sistema dañados corruptos falla", () => KB[10][1](), ["reparar"]);
  add("red internet wifi conexion dns ip navegar no carga", () => KB[11][1](), ["reparar"]);
  add("audio sonido altavoz no suena", () => KB[12][1](), ["reparar"]);
  add("imprimir impresora cola atascada", () => KB[13][1](), ["reparar"]);
  add("programas desinstalar aplicaciones instalados sin uso", () => KB[14][1](), ["programas"]);
  add("admin administrador permisos elevar", () => KB[15][1](), []);
  add("automatico programar semanal limpieza automatica", () => KB[16][1](), ["limpieza"]);
  add("modo noche dia oscuro claro tema", () => KB[17][1](), []);
  add("historial que has hecho que se ha borrado registro acciones", () => KB[18][1](), []);
  add("registro regedit limpiador registro", () => KB[19][1](), []);
  add("ram memoria llena consume consumo uso usando gasta cuanta", () => ramAnswer(), ["inicio"], 1.4);
  add("drivers controlador grafica actualizar amd nvidia radeon", () => driverAnswer(), ["soluciones", "reparar"], 1.3);
  add("riesgo romper peligroso seguro puede romper pc app", () => "No puedes romper el PC con la app: lo que se borra va a la Papelera (salvo vaciar la Papelera, que te avisa), las reparaciones delicadas crean antes un punto de restauración, lo esencial (audio, drivers, red, seguridad) lleva candado y todo queda en el Historial. Las opciones con **!** explican su riesgo al pasar el ratón.", []);
  add("hola buenas quien eres que haces ayuda que sabes", () => KB[20][1](), [], 0.8);
  add("smally clave api anthropic ia inteligencia conectar", () => "Sin clave respondo con lo que sé de la app y tu PC. Con tu clave de Anthropic (en **Organizador IA**) puedo responder cualquier pregunta con IA usando los datos reales de tu equipo.", ["organizador"]);
  add("informe exportar html reporte", () => "En **Salud** o **Soluciones** pulsa «Informe»: se guarda un HTML en Descargas con el diagnóstico, las soluciones y la línea temporal de caídas.", ["salud"]);
  add("punto restauracion volver atras deshacer cambios", () => "**Reparar → Crear punto de restauración** guarda el estado de Windows. Además se crea solo antes de SFC, DISM, restablecer red o Windows Update. Para volver: busca «Crear un punto de restauración» en Windows → Restaurar sistema.", ["reparar"]);
  // Secciones
  PAGES.forEach((p) => add(`${p.t} ${p.s} seccion pagina`, () => `**${p.t}**: ${p.s}.`, [p.id], 0.7));
  // Reparaciones del catálogo
  (S.fixes || []).forEach((f) => add(`${f.title} ${f.description} ${f.group}`, () => `**${f.title}** (Reparar → ${f.group}): ${f.description}\n${f.admin ? "Necesita permisos de administrador. " : ""}${f.revert ? "Deshacer: " + f.revert : ""}`, ["reparar"], 1.1));
  // Categorías de limpieza
  Object.entries(CLEAN_INFO).forEach(([k, i]) => {
    const t = res("clean_scan")?.targets?.find((x) => x.key === k);
    add(`${t?.title || k} ${t?.title || k} ${i[0]} ${i[1]} limpiar borrar riesgo peligroso seguro`, () => `**${t?.title || k}**${t?.size != null ? ` (${fmt(t.size)})` : ""}\n• Qué es: ${i[0]}\n• Qué se borra: ${i[1]}\n• Qué NO se toca: ${i[2]}\n• Consecuencia: ${i[3]}\n${RISKY_CLEAN.has(k) ? "⚠ Tiene alguna pega: léela antes de marcarlo." : "✅ Es seguro limpiarlo."}`, ["limpieza"], 1.3);
  });
  // Avisos de riesgo (tooltips)
  Object.entries(TIPS).forEach(([, t]) => add(`${t[1]} ${t[2]}`, () => `**${t[1]}**: ${t[2]}`, [], 0.6));
  // Diagnóstico real del PC
  (res("diagnosis")?.problems || []).forEach((p) => add(`${p.title} ${p.summary || ""} problema solucion arreglar pasos`,
    () => `**${p.title}**\n${p.why}\n\nPasos:\n${p.steps.map((s, i) => `${i + 1}. ${s.text}`).join("\n")}`, ["soluciones"], 1.1));
  // Hallazgos de seguridad
  (res("sec_audit")?.findings || []).filter((f) => f.severity !== "ok").forEach((f) => add(`${f.title} ${f.area} ${f.detail}`, () => `**${f.title}** (${f.area}): ${f.detail}`, ["seguridad"]));
  // Programas de inicio
  (S.startup || []).forEach((s) => add(`${s.name} inicio arranque`, () => `**${s.name}** ${s.enabled ? "arranca" : "no arranca"} con Windows (impacto ${s.impact}). ${s.essential ? "Es esencial y está protegido." : "Puedes desactivarlo en Inicio y fondo; es reversible."}`, ["inicio"], 0.9));
  // IDF
  const df = {};
  docs.forEach((d) => new Set(d.toks).forEach((t) => (df[t] = (df[t] || 0) + 1)));
  const n = docs.length;
  docs.forEach((d) => (d.vocab = new Set(d.toks)));
  return { docs, idf: (t) => Math.log(1 + n / (df[t] || 0.5)), vocab: Object.keys(df) };
}

function ramAnswer() {
  const m = S.metrics?.mem;
  const top = (S.procs || []).slice(0, 4).map((p) => `${p.name} (${fmt(p.mem)})`).join(", ");
  return `${m ? `La RAM va al **${m.load}%** (libre ${fmt(m.available)} de ${fmt(m.total)}).` : ""}${top ? `\nLo que más consume: ${top}.` : ""}\nPara bajarla: cierra apps en **Inicio y fondo → Abiertas ahora**, quita del arranque lo que no uses y, en Chrome, activa Ahorro de memoria.`;
}
function driverAnswer() {
  const p = (res("diagnosis")?.problems || []).find((x) => x.id === "crashes");
  const ev = (p?.evidence || []).filter((e) => e.startsWith("Driver instalado"));
  return (p ? `Mi diagnóstico: **${p.title}**.\n` : "") + (ev.length ? ev.join("\n") + "\n" : "") +
    "Para actualizar drivers: web de soporte de tu fabricante (lo más compatible) o la del fabricante de la gráfica, y Windows Update → Actualizaciones opcionales. En **Soluciones** tienes los enlaces exactos.";
}

let BRAIN = null, lastTopic = null;
function smartAnswer(q) {
  BRAIN = buildCorpus(); // se reconstruye para usar siempre los datos más recientes
  let qt = tokens(q);
  // Corrige erratas contra el vocabulario conocido
  if (/^\s*(hola|buenas|hey|buenos dias|buenos días|buenas tardes|buenas noches|que tal|qué tal)\b[\s!?.¿¡]*\w{0,12}[\s!?.]*$/i.test(q)) {
    return { text: KB[20][1](), pages: [] };
  }
  qt = qt.map((w) => {
    if (BRAIN.vocab.includes(w) || w.length < 5) return w;
    let best = w, bd = w.length >= 8 ? 2 : 1;
    for (const v of BRAIN.vocab) { const d = lev(w, v); if (d <= bd) { bd = d; best = v; } }
    return best;
  });
  const rank = (toks) => {
    let best = null, score = 0;
    for (const d of BRAIN.docs) {
      let s = 0;
      for (const t of new Set(toks)) if (d.vocab.has(t)) s += BRAIN.idf(t);
      s *= d.boost / Math.pow(Math.max(4, d.vocab.size), 0.25);  // los textos largos no deben ganar por volumen
      if (s > score) { score = s; best = d; }
    }
    return [best, score];
  };
  // 1) La pregunta por sí sola; 2) si es un seguimiento o no queda clara, con el tema anterior
  let [best, score] = rank(qt);
  const follow = lastTopic && (FOLLOW.test(q.trim()) || score < 1.2);
  if (follow) {
    const [b2, s2] = rank(qt.concat(lastTopic.toks.slice(0, 10)));
    if (FOLLOW.test(q.trim()) || s2 > score * 1.5) [best, score] = [b2, s2];
  }
  if (!best || score < 0.6) return null;
  const key = best.toks.join(" ");
  if (follow && lastTopic.key === key) {
    // Seguimiento del mismo tema: va al grano y lleva a la acción
    return { text: best.answer() + "\n\n👉 Pulsa el botón de abajo para hacerlo directamente.", pages: best.pages };
  }
  lastTopic = { toks: best.toks, key };
  return { text: best.answer(), pages: best.pages };
}

// Sustituye la respuesta local básica
const _basicLocal = localAnswer;
localAnswer = (q) => smartAnswer(q) || _basicLocal(q);
// Precarga el catálogo de reparaciones para poder responder sobre ellas
api("/api/fixes").then((r) => { S.fixes ||= r.fixes; }).catch(() => {});
