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
    h('div', { class: 'brand' },
      h('div', { class: 'brand-mark' }, h('svg', { viewBox: '0 0 32 32', width: 20, height: 20, html: '<path d="M4 17h6l3-8 5 15 3-7h7" fill="none" stroke="white" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>' })),
      h('div', {}, h('div', { class: 'brand-name' }, 'Clinical Timeline + Pipeline'), h('div', { class: 'brand-sub' }, 'Patient record and pipeline trace'))),
    nav,
    h('div', { class: 'side-foot' }, h('b', {}, p.name), h('div', { class: 'muted' }, `${p.age} y · ${p.sex} · ${fmtDate(S.first, { year: true })} → ${fmtDate(S.last, { year: true })}`)));
}

function setTopbar(crumbs) {
  const bar = document.getElementById('topbar');
  const trail = h('div', { class: 'crumbs' });
  crumbs.forEach(([label, href], i) => {
    if (i) trail.append(h('span', { class: 'sep' }, '/'));
    trail.append(i === crumbs.length - 1 || !href ? h('span', { class: 'here' }, label) : h('a', { href }, label));
  });
  const dark = document.documentElement.dataset.theme === 'dark';
  bar.replaceChildren(trail, h('div', { class: 'actions' },
    h('button', { class: 'btn icon', title: 'Toggle theme', onclick: toggleTheme }, icon(dark ? 'sun' : 'moon')),
    h('button', { class: 'btn', title: 'Print this view', onclick: () => window.print() }, icon('print'), 'Print')));
}

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
