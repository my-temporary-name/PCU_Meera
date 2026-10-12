// The living orb: translucent ribbons of light that turn and breathe like a creature. Adapted from living_orbi.html (canvas 2D, no libraries).
// The colours follow who is speaking (pink for the doctor, violet and blue for the patient, a pink and violet blend when nobody speaks).
const TAU = Math.PI * 2;
const STOPS_AT = [0, 0.08, 0.15, 0.22, 0.32, 0.45, 0.55, 0.70, 0.85, 1];
const PAL = {
  idle: ['255,110,200', '255,170,150', '255,150,120', '190,110,255', '120,100,255', '255,150,220', '160,100,255', '100,120,255', '230,100,230', '255,110,200'],
  doctor: ['255,95,175', '255,170,140', '255,140,110', '235,85,205', '255,85,165', '255,170,220', '215,100,255', '255,100,160', '240,80,200', '255,95,175'],
  patient: ['130,100,255', '175,140,255', '120,110,255', '190,110,255', '80,100,255', '205,170,255', '100,90,255', '60,110,255', '150,90,255', '130,100,255'],
};
const GLOW = { idle: '200,110,255', doctor: '255,95,175', patient: '110,100,255' };
const STATES = {
  idle: { speed: 0.55, noise: 0.32, spread: 1.0, radius: 1.0, energy: 0.9, spin: 1.0 },
  listening: { speed: 0.8, noise: 0.5, spread: 1.15, radius: 0.97, energy: 1.05, spin: 1.1 },
  speaking: { speed: 1.05, noise: 0.85, spread: 1.3, radius: 1.03, energy: 1.2, spin: 1.3 },
};
const RINGS = [
  { rf: 1.00, sq: 0.82, a0: 1.15, y0: 0.35, z0: 0.2, fa: 0.31, fb: 0.23, fz: 0.11, s: 0.0, ph: 0.0, n: 22, roff: -0.10 },
  { rf: 0.97, sq: 0.70, a0: 0.55, y0: 1.05, z0: 1.9, fa: 0.27, fb: 0.34, fz: -0.09, s: 2.1, ph: 1.3, n: 22, roff: 0.25 },
  { rf: 1.03, sq: 0.90, a0: 1.45, y0: -0.70, z0: 3.4, fa: 0.22, fb: 0.29, fz: 0.08, s: 4.2, ph: 2.6, n: 20, roff: -0.30 },
  { rf: 0.92, sq: 0.62, a0: 0.20, y0: 0.60, z0: 4.7, fa: 0.35, fb: 0.19, fz: -0.13, s: 5.7, ph: 3.9, n: 18, roff: 0.12 },
];
const rgb = (s) => s.split(',').map(Number);
const mix = (a, b, k) => a.map((v, i) => v + (b[i] - v) * k);

const ORBS = new Set(); let raf = 0, last = 0;
const CALM = matchMedia('(prefers-reduced-motion: reduce)');

export function createOrb(canvas, { size = 120, small = false } = {}) {
  const ctx = canvas.getContext('2d'), DPR = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.round(size * DPR); canvas.height = Math.round(size * DPR); canvas.style.width = size + 'px'; canvas.style.height = size + 'px';
  const cx = size / 2, cy = size / 2, R = size * 0.3, segs = small ? 56 : 88, nScale = small ? 0.5 : 1;
  const P = { speed: 0.55, noise: 0.32, spread: 1, radius: 1, energy: 0.9, spin: 1 };
  const parts = Array.from({ length: small ? 8 : 24 }, () => ({ a: Math.random() * TAU, d: Math.sqrt(Math.random()) * 0.52, f: 0.2 + Math.random() * 0.5, p: Math.random() * 10, sz: 0.5 + Math.random() * 1.1, c: ['255,165,115', '255,140,190', '255,190,140', '175,190,255'][Math.floor(Math.random() * 4)] }));
  const o = { canvas, who: 'idle', talking: false, paused: false, level: 0, T: 0, SA: 0, amp: 0, px: 0, py: 0, pal: PAL.idle.map(rgb), glow: rgb(GLOW.idle), target: STATES.idle };
  const dark = () => document.documentElement.dataset.theme === 'dark';

  function draw() {
    const light = !dark();
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, canvas.width, canvas.height); ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    const T = o.T, SA = o.SA, amp = o.amp, E = P.energy, Reff = R * (P.radius + amp * 0.1 + Math.sin(T * 0.9) * 0.02), boost = light ? 2.1 : 0.8;
    // a frosted disc behind the ribbons, so the orb reads as an object over the page and nothing shows through it
    ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1;
    const dg = ctx.createRadialGradient(cx - Reff * 0.25, cy - Reff * 0.35, Reff * 0.1, cx, cy, Reff * 1.15);
    if (light) { dg.addColorStop(0, 'rgba(255,255,255,0.98)'); dg.addColorStop(0.7, 'rgba(246,236,255,0.96)'); dg.addColorStop(1, 'rgba(255,225,242,0.94)'); } else { dg.addColorStop(0, 'rgba(58,36,96,0.97)'); dg.addColorStop(0.7, 'rgba(30,18,56,0.97)'); dg.addColorStop(1, 'rgba(44,22,66,0.95)'); }
    ctx.fillStyle = dg; ctx.beginPath(); ctx.arc(cx, cy, Reff * 1.12, 0, TAU); ctx.fill();
    ctx.strokeStyle = light ? 'rgba(255,255,255,0.95)' : 'rgba(255,255,255,0.22)'; ctx.lineWidth = 1; ctx.stroke();
    ctx.globalCompositeOperation = light ? 'source-over' : 'lighter';
    const gl = o.glow.map(Math.round).join(',');
    // a soft pool of light under the ribbons
    const ig = ctx.createRadialGradient(cx, cy + Reff * 0.3, Reff * 0.05, cx, cy + Reff * 0.3, Reff * 1.05);
    ig.addColorStop(0, `rgba(${gl},${((light ? 0.2 : 0.3) * E + amp * 0.1).toFixed(3)})`); ig.addColorStop(1, `rgba(${gl},0)`);
    ctx.globalAlpha = 1; ctx.fillStyle = ig; ctx.beginPath(); ctx.arc(cx, cy + Reff * 0.15, Reff * 1.1, 0, TAU); ctx.fill();
    const stops = o.pal.map((c) => c.map(Math.round).join(','));
    for (const r of RINGS) {
      const noise = (P.noise + amp * 0.7) * (CALM.matches ? 0.5 : 1);
      const ax = r.a0 + 0.5 * Math.sin(T * r.fa + r.s) + o.py * 0.3, ay = r.y0 + 0.5 * Math.sin(T * r.fb + r.s * 1.3) + o.px * 0.3, az = r.z0 + SA * r.fz;
      const swirl = Math.max(0, Math.min(1, (P.spin - 1) / 1.4)), rot = r.roff + 0.15 * Math.sin(T * 0.2 + r.s) + swirl * SA * 0.6;
      let g; if (ctx.createConicGradient) g = ctx.createConicGradient(rot, cx, cy); else g = ctx.createLinearGradient(cx - R, cy - R, cx + R, cy + R);
      for (let i = 0; i < STOPS_AT.length; i++) g.addColorStop(STOPS_AT[i], `rgb(${stops[i]})`);
      ctx.strokeStyle = g;
      const n = Math.max(6, Math.round(r.n * nScale));
      for (let s = 0; s < n; s++) {
        const kk = (s / (n - 1)) * 2 - 1, edge = 1 - Math.abs(kk), axk = ax + kk * 0.05 * P.spread, ayk = ay + kk * 0.04 * P.spread;
        const cax = Math.cos(axk), sax = Math.sin(axk), cay = Math.cos(ayk), say = Math.sin(ayk), caz = Math.cos(az), saz = Math.sin(az);
        ctx.globalAlpha = Math.min(1, (0.10 + 0.20 * edge) * P.energy * boost * (small ? 1.5 : 1));
        ctx.lineWidth = (0.8 + edge * 0.7) * (small ? 0.75 : 1);
        ctx.beginPath();
        for (let i = 0; i <= segs; i++) {
          const t = (i / segs) * TAU, tp = t + r.ph + kk * 0.04;
          const wob = 1 + noise * (0.090 * Math.sin(2 * t + T * 0.7 + r.s + kk * 0.45) + 0.055 * Math.sin(3 * t - T * 0.9 + r.s * 1.7 - kk * 0.6) + 0.035 * Math.sin(5 * t + T * 1.1 + kk * 0.9));
          const rad = Reff * r.rf * wob * (1 + kk * 0.05 * P.spread), x = rad * Math.cos(tp), y = rad * Math.sin(tp) * r.sq, z = rad * 0.18 * Math.sin(2 * t + T * 0.5 + r.s + kk * 0.3);
          const y1 = y * cax - z * sax, z1 = y * sax + z * cax, x2 = x * cay + z1 * say, z2 = -x * say + z1 * cay, x3 = x2 * caz - y1 * saz, y3 = x2 * saz + y1 * caz, pers = 1 / (1 - z2 / (Reff * 4));
          if (i === 0) ctx.moveTo(cx + x3 * pers, cy + y3 * pers); else ctx.lineTo(cx + x3 * pers, cy + y3 * pers);
        }
        ctx.closePath(); ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;
    for (const p of parts) {
      const ang = p.a + SA * 0.03 * p.f + Math.sin(T * p.f + p.p) * 0.25, dist = p.d * (1 + 0.08 * Math.sin(T * 0.6 * p.f + p.p));
      const x = cx + Math.cos(ang) * dist * Reff + o.px * 4, y = cy + Math.sin(ang) * dist * Reff * 0.8 + Reff * 0.16, tw = Math.pow(0.5 + 0.5 * Math.sin(T * (1.2 + p.f * 2) + p.p * 3), 2), a = (0.25 + 0.75 * tw) * Math.min(1, P.energy);
      ctx.fillStyle = `rgba(${p.c},${(a * 0.16 * (light ? 2 : 1)).toFixed(3)})`; ctx.beginPath(); ctx.arc(x, y, p.sz * 3.2, 0, TAU); ctx.fill();
      ctx.fillStyle = light ? `rgba(255,120,170,${a.toFixed(3)})` : `rgba(255,225,200,${a.toFixed(3)})`; ctx.beginPath(); ctx.arc(x, y, p.sz, 0, TAU); ctx.fill();
    }
    ctx.globalCompositeOperation = 'source-over';
  }
  o.draw = draw;
  o.step = (dt, now) => {
    const k = 1 - Math.exp(-dt * 3), tgt = o.talking ? STATES.speaking : o.who === 'idle' ? STATES.idle : STATES.listening;
    for (const key in P) P[key] += (tgt[key] - P[key]) * k;
    const pk = 1 - Math.exp(-dt * 2.2), want = o.pal.map((c, i) => mix(c, rgb(PAL[o.who][i]), pk)); o.pal = want; o.glow = mix(o.glow, rgb(GLOW[o.who]), pk);
    if (!o.paused) { const sm = CALM.matches ? 0.5 : 1; o.T += dt * P.speed * sm; o.SA += dt * P.spin * sm; }
    const t = now / 1000, sim = o.talking ? (() => { let e = Math.sin(t * 6.3) * Math.sin(t * 2.1 + 1) * 0.5 + 0.5; e = Math.pow(e, 1.5); return 0.15 + 0.75 * e * (0.6 + 0.4 * Math.sin(t * 11.7)); })() : 0.04 + 0.03 * Math.sin(t * 0.8);
    o.amp += ((o.paused ? 0 : sim) - o.amp) * (1 - Math.exp(-dt * 12));
    o.px += (tilt.x - o.px) * (1 - Math.exp(-dt * 4)); o.py += (tilt.y - o.py) * (1 - Math.exp(-dt * 4));
    canvas.style.setProperty('--gl', o.glow.map(Math.round).join(','));
  };
  ORBS.add(o); start(); if (CALM.matches) { o.step(0.016, performance.now()); draw(); }
  return o;
}

const tilt = { x: 0, y: 0 };
addEventListener('pointermove', (e) => { tilt.x = (e.clientX / Math.max(1, innerWidth) - 0.5) * 2; tilt.y = (e.clientY / Math.max(1, innerHeight) - 0.5) * 2; }, { passive: true });
let acc = 0, parity = 0;
function loop(now) {
  const dt = Math.min(0.05, (now - last) / 1000); last = now; acc += dt;
  // idle or paused orbs only need about 30 frames a second; whoever is speaking gets the full rate
  let busy = false; for (const o of ORBS) if (o.talking && !o.paused) busy = true;
  if (!busy && (parity++ & 1)) { raf = requestAnimationFrame(loop); return; }
  for (const o of ORBS) { if (o.canvas.isConnected && o.canvas.offsetParent !== null) { o.step(acc, now); o.draw(); } }
  acc = 0; raf = requestAnimationFrame(loop);
}
function start() { if (CALM.matches || raf) return; last = performance.now(); raf = requestAnimationFrame(loop); }
document.addEventListener('visibilitychange', () => { if (document.hidden) { cancelAnimationFrame(raf); raf = 0; } else start(); });
// under reduced motion the orb is drawn again (not animated) whenever its state changes
export const redraw = (o) => { if (CALM.matches) { for (let i = 0; i < 40; i++) o.step(0.05, performance.now()); o.draw(); } };
