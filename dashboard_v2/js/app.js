// App shell: sidebar, topbar, hash router.
import { S, loadAll, mondayOf, fmtDate } from './store.js';
import { h, icon } from './ui.js';
import { disposeAll } from './charts.js';

const VIEWS = {
  year: () => import('./views/overview.js'),
  month: () => import('./views/month.js'),
  week: () => import('./views/week.js'),
  labs: () => import('./views/labs.js'),
  sources: () => import('./views/sources.js'),
  pipeline: () => import('./views/pipeline.js'),
  stage: () => import('./views/stage.js'),
  cases: () => import('./views/cases.js'),
  case: () => import('./views/case.js'),
  pi: () => import('./views/pi.js'),
  quality: () => import('./views/quality.js'),
  baselines: () => import('./views/baselines.js'),
  doctors: () => import('./views/doctors.js'),
};
const NAV_SECTION = { year: 'year', month: 'month', week: 'week', labs: 'labs', sources: 'sources', pipeline: 'pipeline', stage: 'pipeline', cases: 'cases', case: 'cases', pi: 'pi', quality: 'quality', baselines: 'baselines', doctors: 'doctors' };

function parse() {
  const parts = (location.hash.replace(/^#\/?/, '') || 'year').split('/').map(decodeURIComponent);
  return { name: VIEWS[parts[0]] ? parts[0] : 'year', args: parts.slice(1) };
}

function buildSidebar() {
  const lastMonth = S.months[S.months.length - 1];
  const items = [
    ['Patient timeline', [['year', '#/year', 'year', 'Full year'], ['month', `#/month/${lastMonth}`, 'month', 'Months'], ['week', `#/week/${mondayOf(S.last)}`, 'week', 'Weeks'], ['labs', '#/labs', 'lab', 'Labs & body']]],
    ['Pipeline', [['pipeline', '#/pipeline', 'flow', 'Overview'], ['baselines', '#/baselines', 'base', 'Her baseline'], ['cases', '#/cases', 'case', 'Cases & alerts'], ['pi', '#/pi', 'pi', 'PI notes']]],
    ['Clinical', [['doctors', '#/doctors', 'lab', "Doctor's view"]]],
    ['Reference', [['sources', '#/sources', 'data', 'Data sources & glossary']]],
  ];
  const nav = h('nav', { class: 'nav' });
  items.forEach(([label, links]) => {
    nav.append(h('div', { class: 'nav-label' }, label));
    links.forEach(([key, href, ic, text]) => nav.append(h('a', { href, 'data-key': key }, icon(ic), text)));
  });
  const p = S.meta.patient;
  const side = document.getElementById('sidebar');
  side.replaceChildren(
    h('button', { class: 'side-close', type: 'button', title: 'Hide the sidebar', 'aria-label': 'Hide the sidebar', onclick: () => setSide(false), html: SIDE_ICON }),
    h('div', { class: 'brand' },
      h('div', { class: 'brand-mark' }, h('svg', { viewBox: '0 0 32 32', width: 20, height: 20, html: '<path d="M4 17h6l3-8 5 15 3-7h7" fill="none" stroke="white" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>' })),
      h('div', {}, h('div', { class: 'brand-name' }, 'Clinical Timeline + Pipeline'), h('div', { class: 'brand-sub' }, 'Patient record and pipeline trace'))),
    nav,
    h('div', { class: 'side-foot' }, h('b', {}, p.name), h('div', { class: 'muted' }, `${p.age} y · ${p.sex} · ${fmtDate(S.first, { year: true })} → ${fmtDate(S.last, { year: true })}`)));
}

// the sidebar can be hidden (a grey button in its corner) and brought back (a grey button in the top bar); the choice is remembered
const SIDE_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="3"/><path d="M9 4v16"/></svg>';
function setSide(open) {
  const app = document.querySelector('.app'); if (!app) return;
  app.classList.toggle('side-closed', !open);
  try { localStorage.setItem('sideClosed', open ? '0' : '1'); } catch (e) { /* ignore */ }
}
try { if (localStorage.getItem('sideClosed') === '1') document.querySelector('.app').classList.add('side-closed'); } catch (e) { /* ignore */ }

function setTopbar(crumbs) {
  const bar = document.getElementById('topbar');
  const trail = h('div', { class: 'crumbs' });
  crumbs.forEach(([label, href], i) => {
    if (i) trail.append(h('span', { class: 'sep' }, '/'));
    trail.append(i === crumbs.length - 1 || !href ? h('span', { class: 'here' }, label) : h('a', { href }, label));
  });
  const dark = document.documentElement.dataset.theme === 'dark';
  trail.prepend(h('button', { class: 'side-open', type: 'button', title: 'Show the sidebar', 'aria-label': 'Show the sidebar', onclick: () => setSide(true), html: SIDE_ICON }));
  bar.replaceChildren(trail, h('div', { class: 'actions' },
    h('button', { class: 'btn icon', title: 'Toggle theme', onclick: toggleTheme }, icon(dark ? 'sun' : 'moon')),
    h('button', { class: 'btn', title: 'Print this view', onclick: () => window.print() }, icon('print'), 'Print')));
}

// the Doctor's view (in its frame) asks the shell to switch theme; the frame has already switched itself, so nothing is reloaded
window.addEventListener('message', (e) => {
  if (e.origin !== location.origin || !e.data || e.data.type !== 'dv-theme' || !/^(light|dark)$/.test(e.data.theme)) return;
  document.documentElement.dataset.theme = e.data.theme;
  try { localStorage.setItem('theme', e.data.theme); } catch (err) { /* ignore */ }
  const b = document.querySelector('.actions .btn.icon'); if (b) b.replaceChildren(icon(e.data.theme === 'dark' ? 'sun' : 'moon'));
});
// when the shell's top bar is hidden (Doctor's view) and the sidebar is closed, a small grey button brings the sidebar back
document.body.append(h('button', { class: 'side-open-float', type: 'button', title: 'Show the sidebar', 'aria-label': 'Show the sidebar', onclick: () => setSide(true), html: SIDE_ICON }));

function toggleTheme() {
  const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem('theme', next); } catch (e) { /* ignore */ }
  route();
}

let token = 0;
async function route() {
  const my = ++token;
  const { name, args } = parse();
  const root = document.getElementById('content');
  disposeAll();
  document.querySelectorAll('.nav a').forEach((a) => a.classList.toggle('active', a.dataset.key === NAV_SECTION[name]));
  try {
    const mod = await VIEWS[name]();
    if (my !== token) return;
    const page = h('div', { class: 'stack' });
    root.replaceChildren(page);
    const crumbs = (await mod.render(page, args)) || [['Full year']];
    if (my !== token) return;
    setTopbar(crumbs);
    document.querySelector('.app').classList.toggle('bare', name === 'doctors'); // the Doctor's view carries its own controls, so the shell's top bar is hidden there
    window.scrollTo(0, 0);
  } catch (err) {
    console.error(err);
    root.replaceChildren(h('div', { class: 'card' }, h('h2', {}, 'Something went wrong'), h('pre', { class: 'mono' }, String(err && err.stack || err))));
  }
}

(async function boot() {
  try {
    await loadAll();
  } catch (err) {
    document.getElementById('content').replaceChildren(h('div', { class: 'card' }, h('h2', {}, 'Data not found'), h('p', {}, String(err.message))));
    return;
  }
  buildSidebar();
  window.addEventListener('hashchange', route);
  route();
})();
