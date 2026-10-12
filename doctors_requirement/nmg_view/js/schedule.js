// Today's schedule: the screen before the Doctor's view. A fictional hospital, a fictional senior endocrinologist and invented patients (apart from Meera).
// Only Meera's appointment opens. Slots are 20 minutes; empty slots show just their time. "Now" is fixed at 12:30 on the as-of date.
import { h, fmtDate } from './ui.js';

export const HOSPITAL = { name: 'Aarogya Institute of Medical Sciences', sub: 'Hospital Management Information System' };
export const DOCTOR = { name: 'Dr. Ananya Rao', init: 'AR', quals: 'MD, DM (Endocrinology)', role: 'Senior Consultant, Endocrinology and Diabetes', line: 'Outpatient clinic · Room 214 · Metabolic Health Unit' };
const NOW = '12:30';
const SEV = { red: 'High attention', amber: 'Increased attention', green: 'Lower concern' };
// time, name, age, sex, reason (4 to 5 words), severity, status for past slots (done | noshow), open = Meera
const APPTS = [
  ['09:00', 'Rajesh Menon', 58, 'Male', 'Diabetes follow-up, foot check', 'amber', 'done'],
  ['09:40', 'Sunita Patil', 46, 'Female', 'Thyroid dose review', 'green', 'done'],
  ['10:00', 'Arvind Kulkarni', 63, 'Male', 'HbA1c 9.1, new symptoms', 'red', 'done'],
  ['10:40', 'Farah Sheikh', 34, 'Female', 'PCOS, irregular cycles', 'amber', 'noshow'],
  ['11:00', 'Lakshmi Narayanan', 52, 'Female', 'High post-meal sugars', 'amber', 'done'],
  ['11:40', 'Mohan Das', 71, 'Male', 'Kidney function check', 'amber', 'done'],
  ['12:00', 'Imran Qureshi', 39, 'Male', 'Weight, new diabetes', 'green', 'noshow'],
  ['12:40', 'Meera Iyer', 43, 'Female', 'HbA1c up, sleep poor', 'red', 'next', true],
  ['13:20', 'Pooja Deshmukh', 29, 'Female', 'Gestational diabetes history', 'green', 'wait'],
  ['13:40', 'Kiran Reddy', 55, 'Male', 'LDL high, statin review', 'amber', 'wait'],
  ['14:20', 'Harish Bhat', 67, 'Male', 'Insulin dose adjustment', 'red', 'wait'],
  ['15:00', 'Neha Kapoor', 41, 'Female', 'Thyroid nodule follow-up', 'amber', 'wait'],
  ['15:20', 'Samuel Joseph', 60, 'Male', 'Routine diabetes review', 'green', 'wait'],
  ['16:00', 'Deepa Nair', 48, 'Female', 'Weight loss support', 'green', 'wait'],
];
const slots = () => { const out = []; for (let m = 9 * 60; m <= 16 * 60 + 40; m += 20) out.push(`${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`); return out; };
const ICON = {
  done: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.2 4.2L19 7"/></svg>',
  noshow: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="8.5"/><path d="M6.5 6.5l11 11"/></svg>',
};
const STATUS = { done: ['Completed', ICON.done], noshow: ['Did not attend', ICON.noshow], next: ['Up next', ''], wait: ['Scheduled', ''] };

export function scheduleBar(asOf) {
  const d = new Date(asOf + 'T00:00:00Z'), day = d.toLocaleDateString('en-GB', { weekday: 'long', timeZone: 'UTC' });
  return h('header', { class: 'topbar sbar' },
    h('div', { class: 'brand' }, h('span', { class: 'brand-mark', html: '<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>' }), h('span', { class: 'sb-h' }, h('b', {}, HOSPITAL.name), h('small', {}, HOSPITAL.sub))),
    h('span', { class: 'top-sp' }), h('span', { class: 'chip' }, `${day}, ${fmtDate(asOf)}`));
}

export function schedulePage(asOf, openMeera) {
  const booked = APPTS.length, done = APPTS.filter((a) => a[6] === 'done').length, ns = APPTS.filter((a) => a[6] === 'noshow').length, left = APPTS.filter((a) => a[6] === 'next' || a[6] === 'wait').length;
  const stat = (n, l) => h('div', { class: 'ds-stat' }, h('b', { class: 'num' }, String(n)), h('span', {}, l));
  const banner = h('section', { class: 'doc-banner', 'aria-label': 'Doctor' },
    h('div', { class: 'doc-av' }, h('img', { src: 'img/doctor.jpg', alt: DOCTOR.name })),
    h('div', { class: 'doc-id' }, h('h1', {}, DOCTOR.name), h('div', { class: 'doc-q' }, `${DOCTOR.quals} · ${DOCTOR.role}`), h('div', { class: 'doc-l' }, DOCTOR.line)),
    h('div', { class: 'doc-stats', role: 'group', 'aria-label': 'Today at a glance' }, stat(booked, 'booked'), stat(done, 'completed'), stat(ns, 'did not attend'), stat(left, 'to go')));

  const by = new Map(APPTS.map((a) => [a[0], a]));
  const rows = [];
  let nowPlaced = false;
  for (const t of slots()) {
    if (!nowPlaced && t > NOW) { rows.push(h('li', { class: 'tl-row tl-now', 'aria-label': `Now, ${NOW}` }, h('span', { class: 'tl-t' }, NOW), h('span', { class: 'tl-nl' }, h('i', {}), 'Now'))); nowPlaced = true; }
    const a = by.get(t);
    if (!a) { rows.push(h('li', { class: 'tl-row tl-empty' }, h('time', { class: 'tl-t', datetime: t }, t), h('span', { class: 'tl-gap', 'aria-label': 'Free slot' }))); continue; }
    const [, name, age, sex, why, sev, st, open] = a, [stText, stIcon] = STATUS[st];
    const inner = [
      h('div', { class: 'ap-main' },
        h('div', { class: 'ap-top' }, h('span', { class: 'ap-name' }, name), h('span', { class: 'ap-demo' }, `${age} · ${sex}`)),
        h('div', { class: 'ap-why' }, why)),
      h('div', { class: 'ap-side' },
        h('span', { class: `ap-sev ${sev}` }, h('i', {}), SEV[sev]),
        h('span', { class: `ap-st st-${st}` }, stIcon ? h('span', { class: 'ap-ic', html: stIcon }) : null, stText)),
      open ? h('span', { class: 'dc-go' }, 'Open ', h('span', { class: 'chev-r' }, '›')) : null,
    ];
    const card = open ? h('a', { class: `apt live ${st}`, href: '#/', 'aria-label': `${name}, ${age}, ${sex}. ${why}. ${SEV[sev]}. ${stText}. Open the Doctor's view`, onclick: (e) => { e.preventDefault(); openMeera(); } }, ...inner)
      : h('div', { class: `apt ${st}`, 'aria-label': `${name}, ${age}, ${sex}. ${why}. ${SEV[sev]}. ${stText}` }, ...inner);
    rows.push(h('li', { class: `tl-row tl-appt tl-${st}` }, h('time', { class: 'tl-t', datetime: t }, t), card));
  }
  const list = h('ol', { class: 'tl-list', 'aria-label': 'Appointments, in 20 minute slots' }, rows);
  const scroller = h('div', { class: 'tl', tabindex: '0', role: 'region', 'aria-label': "Today's timeline" }, list);
  // fade rows in and out as the list scrolls (IntersectionObserver rooted in the scroller; the edges also fade through a mask)
  requestAnimationFrame(() => {
    const live = list.querySelector('.apt.live'), now = list.querySelector('.tl-now');
    const calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (calm || !('IntersectionObserver' in window)) rows.forEach((r) => r.classList.add('in'));
    else { const io = new IntersectionObserver((es) => es.forEach((e) => e.target.classList.toggle('in', e.isIntersecting)), { root: scroller, rootMargin: '-6% 0px -6% 0px', threshold: 0.2 }); rows.forEach((r) => io.observe(r)); setTimeout(() => rows.forEach((r) => r.classList.add('in')), 2500); }
    // start with the now line near the top, so the finished visits sit above and Meera is in view
    const target = now || live; if (target) scroller.scrollTop = Math.max(0, target.offsetTop - scroller.clientHeight * 0.18);
  });
  return h('main', { class: 'sched-page' }, banner, h('div', { class: 'tl-wrap' }, h('div', { class: 'tl-legend' }, h('span', {}, h('i', { class: 'ap-sev red' }), 'High attention'), h('span', {}, h('i', { class: 'ap-sev amber' }), 'Increased attention'), h('span', {}, h('i', { class: 'ap-sev green' }), 'Lower concern')), scroller));
}
