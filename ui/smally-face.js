"use strict";
/* Cara de Smally: rasgos, expresiones, colores y dibujo copiados del Smally original
   (smalletters/SMALLY/app.js): ojos orgánicos con halo en 4 pasadas, boca de grosor
   variable con formas cápsula/onda/chevrón, paleta emocional y transiciones suaves.
   Se dibuja en un canvas de 411×297 (el mismo sistema de coordenadas que el original). */

const SFACE = (() => {
  const E = (lx, ly, lw, lh, lr, lsy, ltf, lbr, rx, ry, rw, rh, rr, rsy, rtf, rbr, m, extraL = {}, extraR = {}) => ({
    leftEye: { x: lx, y: ly, width: lw, height: lh, rotation: lr, scaleY: lsy, scaleX: 1, topFlat: ltf, botRound: lbr, ...extraL },
    rightEye: { x: rx, y: ry, width: rw, height: rh, rotation: rr, scaleY: rsy, scaleX: 1, topFlat: rtf, botRound: rbr, ...extraR },
    mouth: { x: 0, y: 88, tilt: 0, asym: 0, open: 0, taper: 1, ...m },
  });
  // Mismos valores que el original (neutral, happy, …, guino)
  const EXPR = {
    neutral: E(-52, -4, 76, 122, 0, 1, .30, .70, 52, -4, 76, 122, 0, 1, .30, .70, { y: 89, w: 58, t: 13, curve: 7.5 }),
    happy: E(-52, -3, 76, 118, 0, .82, .62, .60, 52, -3, 76, 118, 0, .82, .62, .60, { w: 62, t: 12, curve: 17, taper: .82 }),
    enthusiastic: E(-53, -4, 80, 132, 0, 1.02, .26, .76, 53, -4, 80, 132, 0, 1.02, .26, .76, { y: 90, w: 70, t: 12, curve: 23, taper: .78 }),
    curious: E(-53, -7, 80, 128, -3, 1, .26, .74, 53, -4, 70, 112, 3, .96, .34, .70, { y: 86, w: 34, t: 12, curve: 4, tilt: -5, asym: .12, taper: .90 }),
    surprised: E(-53, -4, 80, 140, 0, 1.08, .22, .80, 53, -4, 80, 140, 0, 1.08, .22, .80, { y: 101, w: 12, t: 14, curve: 0, open: 13, shape: "capsule" }),
    confused: E(-53, -4, 76, 120, -5, 1, .36, .68, 53, -3, 72, 116, 6, .97, .42, .64, { w: 36, t: 11, curve: -2, tilt: 7, asym: -.15, taper: .85 }),
    focused: E(-52, -2, 78, 116, -7, .72, .55, .45, 52, -2, 78, 116, 7, .72, .55, .45, { y: 86, w: 30, t: 11, curve: 1, taper: .95 }),
    proud: E(-52, -6, 74, 112, -2, .94, .34, .68, 52, -6, 74, 112, 2, .94, .34, .68, { w: 56, t: 12, curve: 13, taper: .88 }),
    empathetic: E(-52, -4, 76, 114, -1, .90, .44, .72, 52, -4, 76, 114, 1, .90, .44, .72, { w: 44, t: 12, curve: 9, taper: .88 }),
    attentive: E(-52, -2, 74, 124, -1, 1, .28, .72, 52, -2, 74, 124, 1, 1, .28, .72, { y: 85, w: 46, t: 12, curve: 1.5, taper: .95 }),
    playful: E(-53, -4, 78, 112, -6, .86, .58, .56, 53, -5, 74, 118, 4, .92, .40, .66, { w: 56, t: 12, curve: 17, tilt: -4, asym: .30, taper: .80 }),
    tired: E(-52, -3, 76, 122, 0, .46, .80, .50, 52, -3, 76, 122, 0, .46, .80, .50, { w: 38, t: 10, curve: -1, taper: .92 }),
    sleepy: E(-52, -3, 76, 122, 0, .24, .88, .42, 52, -3, 76, 122, 0, .24, .88, .42, { w: 30, t: 9, curve: 0, taper: .90 }),
    worried: E(-53, -6, 74, 118, -4, 1, .32, .66, 53, -6, 74, 118, 4, 1, .32, .66, { y: 89, w: 40, t: 11, curve: -13, taper: .85 }, { scaleX: .95 }, { scaleX: .95 }),
    relaxed: E(-52, -4, 74, 110, 0, .86, .52, .66, 52, -4, 74, 110, 0, .86, .52, .66, { w: 58, t: 12, curve: 8, taper: .90 }),
    amused: E(-53, -4, 78, 114, -3, .80, .66, .54, 53, -4, 74, 116, 2, .84, .58, .58, { w: 52, t: 12, curve: 14, tilt: 5, asym: -.26, taper: .82 }),
    listening: E(-52, -4, 76, 126, -1, 1, .28, .74, 52, -4, 76, 126, 1, 1, .28, .74, { w: 36, t: 13, curve: 2, taper: .95 }),
    thinking: E(-53, -12, 76, 114, -5, .92, .34, .68, 53, -12, 74, 114, 7, .92, .34, .68, { w: 18, t: 14, curve: 0, shape: "capsule" }),
    speaking: E(-52, -4, 76, 122, 0, 1, .32, .70, 52, -4, 76, 122, 0, 1, .32, .70, { w: 42, t: 16, curve: 0, open: 2, shape: "capsule" }),
    excited: E(-54, -2, 84, 138, 0, 1.06, .22, .80, 54, -2, 84, 138, 0, 1.06, .22, .80, { y: 90, w: 74, t: 12, curve: 26, taper: .75 }, { scaleX: 1.04 }, { scaleX: 1.04 }),
    aliviado: E(-52, -4, 75, 119, 0, .62, .66, .60, 52, -4, 75, 119, 0, .62, .66, .60, { w: 56, t: 12, curve: 15, taper: .86 }),
    abrumado: E(-52, -4, 75, 118, -2, .58, .70, .55, 52, -4, 73, 116, 3, .72, .60, .60, { w: 38, t: 11, curve: -11, tilt: 2, asym: -.08, taper: .86 }),
    nervioso: E(-52, -4, 75, 118, -3, .70, .40, .62, 52, -4, 74, 120, 3, .85, .34, .68, { w: 40, t: 11, curve: -4, tilt: 3, asym: -.10, taper: .88 }),
    ilusionado: E(-53, -4, 80, 130, -2, 1, .26, .76, 53, -4, 76, 122, 2, .98, .30, .74, { w: 44, t: 12, curve: 16, asym: .06, taper: .86 }),
    perplejo: E(-52, -4, 76, 120, -6, 1, .36, .68, 52, -4, 72, 116, 7, .97, .42, .64, { y: 89, w: 40, t: 9, curve: 0, shape: "wave", waves: 2, amp: 5 }),
    radiante: E(-52, -6, 74, 50, 0, 1, .5, .5, 52, -6, 74, 50, 0, 1, .5, .5, { w: 66, t: 12, curve: 20, taper: .80 }, { shape: "crescent" }, { shape: "crescent" }),
    estoico: E(-52, -4, 76, 114, -6, .70, .55, .45, 52, -4, 76, 114, 6, .70, .55, .45, { w: 44, t: 11, curve: 6, shape: "chevron" }),
    guino: E(-52, -4, 74, 16, 0, 1, .5, .5, 52, -4, 76, 122, 0, 1, .30, .70, { w: 52, t: 12, curve: 14, tilt: 3, asym: .15, taper: .82 }, { shape: "sliver" }),
  };
  // Paleta emocional del original; las expresiones nuevas toman el color de su familia
  const COLORS = {
    neutral: ["#B2F7FF", .34, 1], happy: ["#FFD64D", .46, 1.1], enthusiastic: ["#FF8A3D", .56, 1.16], curious: ["#A4FF4F", .44, 1.08],
    surprised: ["#3DD6FF", .50, 1.12], confused: ["#B388FF", .38, 1.02], focused: ["#3B82F6", .40, 1.04], proud: ["#FF5EC7", .46, 1.1],
    empathetic: ["#FF8FB1", .38, 1.04], attentive: ["#33E6B8", .44, 1.08], playful: ["#FF5EF0", .54, 1.14], tired: ["#8CA3FF", .26, .92],
    sleepy: ["#6366F1", .20, .84], worried: ["#FF6B6B", .36, 1], relaxed: ["#4ADE80", .32, .98], amused: ["#FFC94D", .46, 1.1],
    listening: ["#60A5FA", .42, 1.06], thinking: ["#A855F7", .38, 1.02], speaking: ["#22D3EE", .46, 1.08], excited: ["#FF4D4D", .58, 1.18],
  };
  const FAMILY = { aliviado: "relaxed", abrumado: "worried", nervioso: "worried", ilusionado: "happy", perplejo: "confused", radiante: "happy", estoico: "focused", guino: "playful" };
  const colorOf = (n) => COLORS[n] || COLORS[FAMILY[n]] || COLORS.neutral;
  const hex = (h) => ({ r: parseInt(h.slice(1, 3), 16), g: parseInt(h.slice(3, 5), 16), b: parseInt(h.slice(5, 7), 16) });

  const canvas = document.getElementById("smally-face");
  const ctx = canvas.getContext("2d");
  const W = 411, H = 297, SCALE = 0.5;  // se dibuja a media resolución: nítido a este tamaño y ligero
  canvas.width = W * SCALE; canvas.height = H * SCALE;

  const clone = (o) => JSON.parse(JSON.stringify(o));
  const st = {
    base: "neutral", flash: null, flashUntil: 0,
    face: clone(EXPR.neutral), col: hex(COLORS.neutral[0]), glow: .34, bright: 1,
    look: { x: 0, y: 0 }, gaze: { x: 0, y: 0 }, blink: 0, nextBlink: performance.now() + 2500, talkUntil: 0, jitter: 0,
  };
  const target = () => (st.flash && performance.now() < st.flashUntil ? st.flash : st.base);
  const lerp = (a, b, k) => a + (b - a) * k;
  function tween(cur, tgt, k) {
    for (const key of Object.keys(tgt)) {
      if (typeof tgt[key] === "number") cur[key] = lerp(typeof cur[key] === "number" ? cur[key] : tgt[key], tgt[key], k);
      else cur[key] = tgt[key];  // formas (shape) cambian directamente
    }
    for (const key of Object.keys(cur)) if (!(key in tgt) && typeof cur[key] !== "number") delete cur[key];
  }

  /* ---------- Geometría del original ---------- */
  function organicEye(hw, hh, topFlat, botRound) {
    const midY = -hh * 0.27, topSpan = hh + midY, botSpan = hh - midY, botW = hw * (0.66 + botRound * 0.24);
    const cpTopW = hw * (0.58 + topFlat * 0.42), cpTopH = topSpan * (0.42 + topFlat * 0.30), cpBotY = midY + botSpan * 0.38;
    const p = new Path2D();
    p.moveTo(0, -hh);
    p.bezierCurveTo(cpTopW, -hh, hw, midY - cpTopH, hw, midY);
    p.bezierCurveTo(hw * 0.92, cpBotY, botW * 0.98, hh, 0, hh);
    p.bezierCurveTo(-botW * 0.98, hh, -hw * 0.92, cpBotY, -hw, midY);
    p.bezierCurveTo(-hw, midY - cpTopH, -cpTopW, -hh, 0, -hh);
    p.closePath();
    return p;
  }
  function capsule(w, h) {
    const rx = Math.max(w, 3) / 2, ry = Math.max(h, 3) / 2, p = new Path2D();
    p.roundRect(-rx, -ry, rx * 2, ry * 2, Math.min(rx, ry));
    return p;
  }
  function strokeAlong(pts) {
    const p = new Path2D(), N = pts.length - 1, s = pts[0], e = pts[N];
    p.moveTo(s.x - s.nx * s.h, s.y - s.ny * s.h);
    for (let i = 1; i <= N; i++) p.lineTo(pts[i].x - pts[i].nx * pts[i].h, pts[i].y - pts[i].ny * pts[i].h);
    p.arc(e.x, e.y, e.h, Math.atan2(-e.ny, -e.nx), Math.atan2(e.ny, e.nx), false);
    for (let i = N; i >= 0; i--) p.lineTo(pts[i].x + pts[i].nx * pts[i].h, pts[i].y + pts[i].ny * pts[i].h);
    p.arc(s.x, s.y, s.h, Math.atan2(s.ny, s.nx), Math.atan2(-s.ny, -s.nx), false);
    p.closePath();
    return p;
  }
  function mouthCurve(w, t, curve, asym, open, taper) {
    const hw = w / 2, N = 22, px = [-hw, -hw * 0.42 + asym * hw, hw * 0.42 + asym * hw, hw], py = [0, curve * 1.18, curve * 1.18, 0];
    const bez = (a, b, c, d, u) => { const m = 1 - u; return m * m * m * a + 3 * m * m * u * b + 3 * m * u * u * c + u * u * u * d; };
    const dbez = (a, b, c, d, u) => { const m = 1 - u; return 3 * m * m * (b - a) + 6 * m * u * (c - b) + 3 * u * u * (d - c); };
    const pts = [];
    for (let i = 0; i <= N; i++) {
      const u = i / N; let dx = dbez(...px, u), dy = dbez(...py, u); const L = Math.hypot(dx, dy) || 1; dx /= L; dy /= L;
      const bulge = Math.sin(Math.PI * u), taperF = taper + (1 - taper) * Math.pow(bulge, 0.6);
      pts.push({ x: bez(...px, u), y: bez(...py, u), nx: -dy, ny: dx, h: t * 0.5 * taperF + open * bulge });
    }
    return strokeAlong(pts);
  }
  function mouthWave(w, t, waves, amp) {
    const hw = w / 2, N = 28, pts = [];
    for (let i = 0; i <= N; i++) {
      const u = i / N, slope = amp * waves * Math.PI * 2 * Math.cos(u * waves * Math.PI * 2), L = Math.hypot(1, slope) || 1;
      pts.push({ x: -hw + u * w, y: amp * Math.sin(u * waves * Math.PI * 2), nx: -slope / L, ny: 1 / L, h: t * 0.5 * (0.55 + 0.45 * Math.sin(Math.PI * u)) });
    }
    return strokeAlong(pts);
  }
  function mouthChevron(w, t, depth) {
    const hw = w / 2, N = 24, pts = [];
    const bez = (a, b, c, u) => { const m = 1 - u; return m * m * a + 2 * m * u * b + u * u * c; };
    const dbez = (a, b, c, u) => 2 * (1 - u) * (b - a) + 2 * u * (c - b);
    for (let i = 0; i <= N; i++) {
      const u = i / N; let dx = dbez(-hw, 0, hw, u), dy = dbez(0, depth, 0, u); const L = Math.hypot(dx, dy) || 1; dx /= L; dy /= L;
      pts.push({ x: bez(-hw, 0, hw, u), y: bez(0, depth, 0, u), nx: -dy, ny: dx, h: t * 0.5 * (0.6 + 0.4 * Math.sin(Math.PI * u)) });
    }
    return strokeAlong(pts);
  }

  /* ---------- Dibujo con el halo de 4 pasadas del original ---------- */
  function drawEye(eye, col, gi, br) {
    ctx.save();
    ctx.translate(eye.x, eye.y);
    ctx.rotate(eye.rotation * Math.PI / 180);
    ctx.scale(eye.scaleX || 1, Math.max(0.04, eye.scaleY * (1 - st.blink)));
    const hw = eye.width / 2, hh = eye.height / 2;
    const path = eye.shape === "crescent" ? mouthCurve(hw * 2, Math.max(hh * 0.55, 4), -hh * 1.05, 0, 0, 1)
      : eye.shape === "sliver" ? capsule(hw * 2, Math.max(hh * 0.16, 3))
      : organicEye(hw, hh, eye.topFlat ?? 0.5, eye.botRound ?? 0.7);
    for (const [blur, a, fa] of [[80, Math.min(.55, gi * 1.8), Math.min(.55, gi * 1.8)], [40, Math.min(.7, gi * 2.4), Math.min(.75, gi * 2.5)], [14, Math.min(.8, gi * 2.8), .92], [0, 0, .97]]) {
      ctx.shadowColor = `rgba(${col},${a})`; ctx.shadowBlur = blur * SCALE; ctx.fillStyle = `rgba(${col},${fa})`; ctx.fill(path);
    }
    ctx.shadowBlur = 0;
    const hl = ctx.createRadialGradient(-hw * 0.12, -hh * 0.34, 0, -hw * 0.12, -hh * 0.34, hh * 0.8);
    hl.addColorStop(0, `rgba(255,253,247,${0.17 * br})`); hl.addColorStop(0.45, `rgba(255,253,247,${0.06 * br})`); hl.addColorStop(1, "rgba(255,253,247,0)");
    ctx.fillStyle = hl; ctx.fill(path);
    ctx.restore();
  }
  function drawMouth(m, col, gi) {
    ctx.save();
    ctx.translate(m.x + st.gaze.x * 0.35, m.y + st.gaze.y * 0.25);
    ctx.rotate((m.tilt || 0) * Math.PI / 180);
    const talking = performance.now() < st.talkUntil;
    const open = Math.max(m.open || 0, 0) + (talking ? 3 + 3 * Math.abs(Math.sin(performance.now() / 85)) : 0);
    const path = (m.shape === "capsule" || talking) ? capsule(m.w + m.t, m.t + open * 2)
      : m.shape === "wave" ? mouthWave(Math.max(m.w, 4), Math.max(m.t, 4), m.waves ?? 2, m.amp ?? 6)
      : m.shape === "chevron" ? mouthChevron(Math.max(m.w, 4), Math.max(m.t, 4), m.curve)
      : mouthCurve(Math.max(m.w, 4), Math.max(m.t, 4), m.curve, m.asym || 0, open, m.taper ?? 1);
    ctx.shadowColor = `rgba(${col},${Math.min(.65, gi * 2.2)})`; ctx.shadowBlur = 28 * SCALE; ctx.fillStyle = `rgba(${col},.93)`; ctx.fill(path);
    ctx.restore();
  }

  let last = 0;
  function frame(now) {
    requestAnimationFrame(frame);
    if (now - last < 33 || document.hidden) return;  // ~30 fps: fluido y sin gastar CPU
    last = now;
    const name = target(), tgt = EXPR[name] || EXPR.neutral, [h, g, b] = colorOf(name), c = hex(h);
    tween(st.face.leftEye, tgt.leftEye, .2); tween(st.face.rightEye, tgt.rightEye, .2); tween(st.face.mouth, tgt.mouth, .2);
    st.col = { r: lerp(st.col.r, c.r, .12), g: lerp(st.col.g, c.g, .12), b: lerp(st.col.b, c.b, .12) };
    st.glow = lerp(st.glow, g, .12); st.bright = lerp(st.bright, b, .12);
    // Parpadeo natural (no cuando duerme o guiña)
    if (now > st.nextBlink && !["sleepy", "guino", "radiante"].includes(name)) { st.blinkStart = now; st.nextBlink = now + 2600 + Math.random() * 3800; }
    const bt = st.blinkStart ? (now - st.blinkStart) / 150 : 2;
    st.blink = bt < 1 ? Math.sin(bt * Math.PI) * 0.92 : 0;
    // Mirada (y temblor si está mareado)
    const jx = st.jitter ? Math.sin(now / 60) * 7 * st.jitter : 0, jy = st.jitter ? Math.cos(now / 75) * 5 * st.jitter : 0;
    st.gaze.x = lerp(st.gaze.x, st.look.x + jx, .25); st.gaze.y = lerp(st.gaze.y, st.look.y + jy, .25);

    const br = st.bright, col = `${Math.min(255, st.col.r * br) | 0},${Math.min(255, st.col.g * br) | 0},${Math.min(255, st.col.b * br) | 0}`;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = "#000"; ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.setTransform(SCALE, 0, 0, SCALE, (W / 2) * SCALE, (H / 2) * SCALE);
    // Brillo ambiental
    const amb = ctx.createRadialGradient(0, 0, 0, 0, 0, 180);
    amb.addColorStop(0, `rgba(${col},${st.glow * 0.04})`); amb.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = amb; ctx.fillRect(-206, -150, 412, 300);
    const L = { ...st.face.leftEye, x: st.face.leftEye.x + st.gaze.x, y: st.face.leftEye.y + st.gaze.y };
    const R = { ...st.face.rightEye, x: st.face.rightEye.x + st.gaze.x, y: st.face.rightEye.y + st.gaze.y };
    drawEye(L, col, st.glow, br); drawEye(R, col, st.glow, br); drawMouth(st.face.mouth, col, st.glow);
    // El color de la antena y los detalles sigue a la emoción
    document.getElementById("smally").style.setProperty("--face", `rgb(${col})`);
  }
  requestAnimationFrame(frame);

  return {
    names: Object.keys(EXPR),
    set(name) { if (EXPR[name]) st.base = name; },                         // expresión de fondo (humor)
    flash(name, ms = 1200) { if (EXPR[name]) { st.flash = name; st.flashUntil = performance.now() + ms; } },  // reacción breve
    look(x, y) { st.look.x = Math.max(-14, Math.min(14, x)); st.look.y = Math.max(-9, Math.min(9, y)); },
    talk(ms = 1800) { st.talkUntil = performance.now() + ms; },
    dizzy(on) { st.jitter = on ? 1 : 0; },
    blink() { st.blinkStart = performance.now(); },
    get current() { return target(); },
  };
})();
