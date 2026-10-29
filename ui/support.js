"use strict";
/* Errores de la interfaz al registro y botón «Informe técnico» para pedir ayuda. */

let sentErrors = 0;
function reportClientError(where, message, stack) {
  if (sentErrors++ > 30) return;  // evita inundar el registro si algo falla en bucle
  fetch("/api/clientlog", { method: "POST", headers: { "X-Nova-Key": KEY, "Content-Type": "application/json" },
    body: JSON.stringify({ where, message: String(message), stack: String(stack || "") }) }).catch(() => {});
}
addEventListener("error", (e) => reportClientError(`${S.page} · ${e.filename?.split("/").pop()}:${e.lineno}`, e.message, e.error?.stack));
addEventListener("unhandledrejection", (e) => reportClientError(S.page, e.reason?.message || e.reason, e.reason?.stack));
// Los avisos de error que ve el usuario también quedan registrados
const _toast = toast;
toast = (msg, kind = "ok") => { if (kind === "bad") reportClientError(`aviso en ${S.page}`, msg); _toast(msg, kind); };

const clientInfo = () => ({ ua: navigator.userAgent.replace(/.*(Chrome|Edg)\/(\d+).*/, "$1 $2"), screen: `${innerWidth}x${innerHeight}@${devicePixelRatio}`, theme: document.documentElement.dataset.theme });

// Se registra cuando ya han cargado todos los scripts (este se carga antes para capturar errores desde el inicio)
addEventListener("DOMContentLoaded", () => { EXTRA_ACT.support = openSupport; });
async function openSupport() {
  const r = await api("/api/support", { client: clientInfo() }).catch((e) => ({ text: "No se pudo generar: " + e.message }));
  const w = modal(`<h3>Informe técnico</h3>
    <div class="muted" style="font-size:12.5px">Si algo falla, copia este informe y envíalo a quien te ayude. No incluye tus archivos ni tu clave; tu nombre de usuario aparece como &lt;usuario&gt;.</div>
    <div class="console mt" style="height:320px">${esc(r.text)}</div>
    <div class="foot"><button class="btn ghost" data-r>Cerrar</button><button class="btn" data-save>${ic("file")}Guardar en Descargas</button><button class="btn primary" data-copy>${ic("copy")}Copiar</button></div>`, true);
  w.addEventListener("click", async (e) => {
    if (e.target.closest("[data-copy]")) {
      try { await navigator.clipboard.writeText(r.text); toast("Informe copiado: pégalo en WhatsApp o en un correo"); }
      catch { toast("No se pudo copiar; usa «Guardar en Descargas»", "warn"); }
    } else if (e.target.closest("[data-save]")) {
      const s = await api("/api/support/save", { client: clientInfo() }).catch(() => null);
      if (s?.ok) toast("Guardado en Descargas");
    } else if (e.target.closest("[data-r]") || e.target === w) w.remove();
  });
}
