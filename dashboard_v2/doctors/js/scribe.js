// A note-taking assistant, UI only: a living orb at the bottom right that opens a notepad-style panel. The conversation is SCRIPTED (nothing is recorded or recognised);
// it shows how a real one would look: the orb changes colour with whoever is speaking, and each line is written down word by word as it is "spoken".
import { h } from './ui.js';
import { createOrb, redraw } from './orb.js';

// [who, text]: the first HISTORY lines are shown as already taken down, the rest arrive live and then loop
const SCRIPT = [
  ['D', 'Good morning Meera, come in. How have you been since the June visit?'],
  ['P', 'Good morning doctor. Honestly, a bit tired. The last few weeks have been very busy.'],
  ['D', 'Busy with work or at home?'],
  ['P', 'Both. Quarter-close at work, and then Ganesh Chaturthi at home with all the hosting.'],
  ['D', 'I see. Let us look at your numbers together. Your HbA1c today is 7.4, up from 7.2 in June.'],
  ['P', 'Oh. I thought it might be higher, to be honest.'],
  ['D', 'It is a small rise, but it is above your goal of under 7. Your sensor average has also crept up over the last two weeks.'],
  ['P', 'Yes, I stopped my morning walks on the 7th. Three in a row missed by the 10th.'],
  ['D', 'Thank you for telling me. How has your sleep been?'],
  ['P', 'Not great. Maybe five hours a night this past week.'],
  ['D', 'That can push glucose up as well. And the medicines, are you managing every dose?'],
  ['P', 'Mostly. The evening ones I sometimes forget when I am still at my desk.'],
  ['D', 'That is very common. Metformin was taken on about eighty-six percent of days, amlodipine a little less.'],
  ['P', 'I will set a reminder on my phone.'],
  ['D', 'Good idea. Now the plan. Last time we agreed to give lifestyle changes three more months.'],
  ['P', 'Yes, and I did not manage that well with everything going on.'],
  ['D', 'Understood. We could add a second medicine, or give it a few more weeks once the festival pressure eases. What would you prefer?'],
  ['P', 'I would like to try the walks again first, if that is alright.'],
  ['D', 'That is reasonable. We will recheck your HbA1c on the seventeenth of December and decide then.'],
  ['P', 'Okay. Should I be worried about my cholesterol?'],
  ['D', 'Your LDL is 126 and your goal is under 70. You are not on a cholesterol medicine yet, so we should talk about that at the next visit.'],
  ['P', 'Alright. And my blood pressure?'],
  ['D', 'In clinic it was 138 over 90, but your home average is about 125 over 82. Let us keep measuring at home.'],
  ['P', 'I will keep the log going.'],
  ['D', 'Your thyroid result is fine, the TSH is 3.0, so the levothyroxine stays the same.'],
  ['P', 'That is a relief.'],
  ['D', 'One more thing, your weight is 72 kilos, about four above your goal. Small steps are enough for now.'],
  ['P', 'I will start with the walking and see how it goes.'],
  ['D', 'Any new symptoms? Chest tightness, swelling, anything unusual?'],
  ['P', 'No, nothing new. Just the tiredness.'],
  ['D', 'Good. We will also repeat your kidney and liver tests with the next blood work.'],
  ['P', 'Will do. When should I come back?'],
  ['D', 'In three months. Sooner if the walks or the sleep do not settle, just call the clinic.'],
  ['P', 'Thank you, doctor. I feel better having a plan.'],
  ['D', 'You are doing fine, Meera. Take care.'],
];
const HISTORY = 14, AGO = [228, 214, 205, 190, 176, 160, 148, 129, 113, 99, 82, 62, 41, 22]; // seconds before opening, for the lines already taken down
const WHO = { D: 'Doctor', P: 'Patient' };
const clock = (t) => new Date(t).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
const CALM = matchMedia('(prefers-reduced-motion: reduce)');

export function initScribe() {
  if (document.querySelector('.scribe-root')) return;
  // the living orb (js/orb.js), in the top right corner after the patient's name; the panel opens below it
  const bigCanvas = h('canvas', { class: 'orb-c', 'aria-hidden': 'true' });
  const orbs = [createOrb(bigCanvas, { size: 68 })];
  const log = h('div', { class: 'sc-log', role: 'log', 'aria-live': 'off', 'aria-label': 'Conversation so far' });
  const stat = h('div', { class: 'sc-stat' }, h('span', { class: 'sc-dot' }), h('span', { class: 'sc-stat-t' }, 'Listening'));
  const who = h('div', { class: 'sc-who', 'aria-hidden': 'true' }, h('span', { 'data-w': 'D' }, 'Doctor'), h('span', { 'data-w': 'P' }, 'Patient'));
  const eq = h('span', { class: 'sc-eq', 'aria-hidden': 'true' }, h('i'), h('i'), h('i'), h('i'), h('i'));
  const pauseBtn = h('button', { type: 'button', class: 'sc-btn', 'aria-label': 'Pause note taking', title: 'Pause', html: '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true"><rect x="6" y="5" width="4" height="14" rx="1.2"/><rect x="14" y="5" width="4" height="14" rx="1.2"/></svg>' });
  const closeBtn = h('button', { type: 'button', class: 'sc-btn', 'aria-label': 'Close notes', title: 'Close', html: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>' });
  const panel = h('section', { class: 'sc-panel', id: 'scribe-panel', role: 'complementary', 'aria-label': 'Visit notes', hidden: true },
    h('header', { class: 'sc-head' }, h('div', { class: 'sc-title' }, h('div', { class: 'sc-name' }, 'Visit notes'), stat), h('div', { class: 'sc-actions' }, pauseBtn, closeBtn)),
    who, log,
    h('footer', { class: 'sc-foot' }, eq));
  const orbBtn = h('button', { type: 'button', class: 'scribe-orb', 'aria-label': 'Open visit notes', 'aria-expanded': 'false', 'aria-controls': 'scribe-panel', 'data-nt': '1' }, bigCanvas);
  const root = h('div', { class: 'scribe-root', 'data-speaker': 'idle' }, panel, orbBtn);
  document.body.append(root);

  let idx = 0, paused = false, open = false, timer = 0, speaking = null, lvlT = 0;
  const setSpeaker = (w) => { speaking = w; root.dataset.speaker = w ? (w === 'D' ? 'doctor' : 'patient') : 'idle'; orbs.forEach((o) => { o.who = root.dataset.speaker; o.talking = !!w && !paused; redraw(o); }); root.classList.toggle('speaking', !!w); who.querySelectorAll('span').forEach((s) => s.classList.toggle('on', s.dataset.w === w));
    stat.querySelector('.sc-stat-t').textContent = paused ? 'Paused' : w ? `${WHO[w]} speaking` : 'Listening'; };
  const level = () => { clearTimeout(lvlT); const tick = () => { if (!speaking || paused) { root.style.setProperty('--lvl', '0'); return; } root.style.setProperty('--lvl', (0.25 + Math.random() * 0.75).toFixed(2)); lvlT = setTimeout(tick, 110 + Math.random() * 90); }; tick(); };
  const stick = () => { log.scrollTop = log.scrollHeight; };
  const bubble = (w, text, time, typing) => {
    const t = h('span', { class: 'sc-t' }, typing ? '' : text), el = h('div', { class: `sc-msg ${w === 'D' ? 'doc' : 'pat'}${typing ? ' live' : ''}` }, h('div', { class: 'sc-meta' }, h('span', { class: 'sc-who-l' }, WHO[w]), h('time', {}, clock(time))), h('p', {}, t));
    log.append(el); while (log.children.length > 80) log.firstChild.remove(); stick(); return [el, t];
  };
  const now = Date.now();
  for (let i = 0; i < HISTORY; i++) bubble(SCRIPT[i][0], SCRIPT[i][1], now - AGO[i] * 1000, false);
  idx = HISTORY;

  const speak = () => {
    if (paused) return;
    const [w, text] = SCRIPT[idx]; idx = idx + 1 >= SCRIPT.length ? HISTORY : idx + 1;
    const words = text.split(' '), [el, t] = bubble(w, '', Date.now(), true); setSpeaker(w); level();
    let i = 0;
    const step = () => {
      if (paused) return;
      if (CALM.matches) { t.textContent = text; i = words.length; } else { i += 1; t.textContent = words.slice(0, i).join(' '); }
      stick();
      if (i < words.length) timer = setTimeout(step, 150 + Math.random() * 110 + (words[i - 1].length > 7 ? 60 : 0));
      else { el.classList.remove('live'); setSpeaker(null); level(); timer = setTimeout(speak, CALM.matches ? 2600 : 1100 + Math.random() * 700); }
    };
    timer = setTimeout(step, CALM.matches ? 0 : 280);
  };
  const run = () => { clearTimeout(timer); timer = setTimeout(speak, 900); };
  const toggle = (v) => { open = v; panel.hidden = !v; root.classList.toggle('open', v); orbBtn.setAttribute('aria-expanded', String(v)); orbBtn.setAttribute('aria-label', v ? 'Close visit notes' : 'Open visit notes'); if (v) { requestAnimationFrame(stick); } };
  orbBtn.addEventListener('click', () => toggle(!open));
  closeBtn.addEventListener('click', () => { toggle(false); orbBtn.focus(); });
  pauseBtn.addEventListener('click', () => {
    paused = !paused; pauseBtn.setAttribute('aria-label', paused ? 'Resume note taking' : 'Pause note taking'); pauseBtn.title = paused ? 'Resume' : 'Pause';
    pauseBtn.innerHTML = paused ? '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true"><path d="M7 5l12 7-12 7z"/></svg>' : '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true"><rect x="6" y="5" width="4" height="14" rx="1.2"/><rect x="14" y="5" width="4" height="14" rx="1.2"/></svg>';
    root.classList.toggle('paused', paused); orbs.forEach((o) => { o.paused = paused; });
    if (paused) { clearTimeout(timer); const live = log.querySelector('.sc-msg.live'); if (live) live.classList.remove('live'); setSpeaker(null); } else { setSpeaker(null); run(); }
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && open && !document.querySelector('.modal-back')) { toggle(false); orbBtn.focus(); } });
  document.addEventListener('visibilitychange', () => { if (document.hidden) { clearTimeout(timer); clearTimeout(lvlT); } else if (!paused) { setSpeaker(null); run(); } });
  // the orb lives in a gutter of its own at the right of the page, just below the top bar (the page leaves 76px free there), so it never overlaps the bar or the patient panels.
  // On narrow screens there is no gutter, so it sits at the bottom right above the theme switch.
  const place = () => {
    const bar = document.querySelector('.topbar'), body = document.querySelector('.dv-body'); if (!bar || !body) return;
    if (innerWidth <= 900) { root.style.top = 'auto'; root.style.bottom = '70px'; root.style.right = '18px'; root.classList.add('low'); return; }
    root.classList.remove('low'); root.style.bottom = 'auto'; const r = bar.getBoundingClientRect(), br = body.getBoundingClientRect();
    root.style.top = `${Math.round(r.bottom + 14)}px`; root.style.right = `${Math.round(document.documentElement.clientWidth - br.right + 15)}px`;
  };
  place(); addEventListener('scroll', place, { passive: true }); addEventListener('resize', place); addEventListener('dv-bar', place); addEventListener('hashchange', () => requestAnimationFrame(place));
  const rootEl = document.getElementById('root'); if (rootEl) new MutationObserver(() => requestAnimationFrame(place)).observe(rootEl, { childList: true });
  run();
}
