// Pipeline overview: the 8 components as a flow, what goes in and what comes out, with real counts.
import { S, n1 } from '../store.js';
import { h, card } from '../ui.js';
import { mount, palette, base } from '../charts.js';

const HEADLINE = {
  threshold: ['readings checked', 'readings checked'], linker: ['pairings', 'pairings'], baseline: null, state: ['alerts', 'alerts'], rulebook: ['packets', 'packets'],
  evidence: ['alert records', 'alert evidence records'], findings: ['versions', 'versions'], pi: ['relationships', 'long-term notes'],
};
const SHORT_IN = { threshold: 'raw readings', linker: 'high / low glucose + context', baseline: 'her readings by day', state: 'latest reading vs her usual', rulebook: 'one alert', evidence: 'a packet + her history', findings: 'alerts + evidence + context', pi: 'every version, weekly' };
const SHORT_OUT = { threshold: 'a status per reading', linker: 'what happened nearby', baseline: 'day / week / month gists', state: 'alerts', rulebook: 'a checklist of factors', evidence: 'a label per factor', findings: 'cases, versions, text', pi: 'weekly and long-term notes' };

const ACCENT = ['#7cc8bb', '#8fd1a8', '#f2cf8a', '#f0a3b2', '#b6acec', '#9db9ee', '#7cc8bb', '#b6acec'];


const SVGNS = 'http://www.w3.org/2000/svg';
const sv = (tag, attrs = {}, ...kids) => { const e = document.createElementNS(SVGNS, tag); Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v)); kids.flat().forEach((c) => c != null && e.append(c.nodeType ? c : document.createTextNode(c))); return e; };

function flowDiagram(P, st, total) {
  const W = 128, H = 94, X = [24, 338, 652, 966], Y1 = 62, Y2 = 318;
  // snake layout: 1 2 3 4 on the first row, 5 6 7 8 on the second row running back
  const POS = [[X[0], Y1], [X[1], Y1], [X[2], Y1], [X[3], Y1], [X[3], Y2], [X[2], Y2], [X[1], Y2], [X[0], Y2]];
  const IDS = ['threshold', 'linker', 'baseline', 'state', 'rulebook', 'evidence', 'findings', 'pi'];
  const NAME = ['Plausibility and Threshold', 'Linker and Store', 'Baseline Engine', 'State Engine', 'Rulebook Lookup', 'Evidence Engine', 'Findings Engine', 'PI'];
  const baselineN = Object.entries(st.find((x) => x.id === 'baseline').counts).reduce((a, [, v]) => a + v, 0);
  const NUM = [[n1(total('threshold', 'readings checked'), 0), 'readings checked'], [n1(total('linker', 'pairings'), 0), 'pairings'], [n1(baselineN, 0), 'windows'], [n1(total('state', 'alerts'), 0), 'alerts'], [n1(total('rulebook', 'packets'), 0), 'packets'],
    [n1(total('evidence', 'alert records'), 0), 'alert evidence records'], [n1(total('findings', 'versions'), 0), 'versions'], [n1(total('pi', 'relationships'), 0), 'long-term notes']];
  const ALSO = ['', 'writes the store', 'reads: the store', 'also reads: store readings', 'reads: alerts only', 'also reads: store history, alerts', 'also reads: alerts, diary, gists, PI notes', 'also reads: Evidence daily labels'];
  const R = (i) => ({ l: [POS[i][0], POS[i][1] + H / 2], r: [POS[i][0] + W, POS[i][1] + H / 2], t: (dx = 0) => [POS[i][0] + W / 2 + dx, POS[i][1]], b: (dx = 0) => [POS[i][0] + W / 2 + dx, POS[i][1] + H] });
  const bz = (a, b, c, d, t) => (1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t ** 2 * c + t ** 3 * d;
  const cub = (p0, c1, c2, p1, t = 0.5) => ({ d: `M${p0} C${c1} ${c2} ${p1}`, lab: [bz(p0[0], c1[0], c2[0], p1[0], t), bz(p0[1], c1[1], c2[1], p1[1], t)] });
  const line = (p0, p1) => ({ d: `M${p0} L${p1}`, lab: [(p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2] });
  const below = (p0, p1, depth) => cub(p0, [p0[0], p0[1] + depth], [p1[0], p1[1] + depth], p1);
  const dia = (p0, p1, y0, y1, t) => cub(p0, [p0[0], y0], [p1[0], y1], p1, t);
  const E = [
    { id: 'm12', kind: 'main', ...line(R(0).r, R(1).l), label: '44,469 status rows', desc: 'The status rows go to the linker. The high or low glucose ones (14,697) are paired with what happened nearby, and every row is written to the store.' },
    { id: 'm23', kind: 'main', ...line(R(1).r, R(2).l), label: 'readings + context', desc: 'The Baseline Engine reads the store: 44,469 status rows and 45,952 context events. It does not read the pairings or any alert, and builds 710 day, week and month windows.' },
    { id: 'm34', kind: 'main', ...line(R(2).r, R(3).l), label: 'her usual', desc: 'The State Engine reads her usual (the median and spread of each measure, as of each day) from the Baseline windows.' },
    { id: 'm45', kind: 'main', ...line(R(3).b(), R(4).t()), label: '287 alerts', desc: 'The 287 alerts (hand-offs) go to the Rulebook Lookup, one packet each. Alerts never go back to the Baseline Engine.' },
    { id: 'm56', kind: 'main', ...line(R(4).l, R(5).r), label: '287 packets', desc: 'Each packet is a checklist of factors to test for one alert.' },
    { id: 'm67', kind: 'main', ...line(R(5).l, R(6).r), label: '287 evidence records', desc: 'The Evidence Engine tests each listed factor on her own history and writes one evidence record per alert, with a label for each factor.' },
    { id: 'm78', kind: 'main', ...line(R(6).l, R(7).r), label: '284 versions', desc: 'Every Findings version goes into PI\'s open week as an entry.' },
    { id: 's24', kind: 'store', ...cub(R(1).t(-30), [R(1).t(-30)[0], 4], [R(3).t(-30)[0], 4], R(3).t(-30)), label: 'newest readings at every tick', desc: 'The State Engine also reads the newest readings from the store at every 15-minute tick, to compare them with her usual.' },
    { id: 's26', kind: 'store', ...dia(R(1).b(30), R(5).t(-30), 235, 215, 0.2), label: 'her whole history', desc: 'The Evidence Engine reads her whole history from the store to test each factor.' },
    { id: 's37', kind: 'gist', ...dia(R(2).b(-30), R(6).t(30), 235, 215, 0.2), label: 'gists as context', desc: 'The Findings Engine reads yesterday\'s day gist, the week and the latest month gist as light context. Only the day headline can reach the text, and only if that day was notable.' },
    { id: 's57', kind: 'packet', ...below(R(4).b(-25), R(6).b(40), 105), label: 'which alerts count', desc: 'The Findings Engine uses each packet\'s status: 279 alerts have an ok packet and make versions; 8 deferred ones do not.' },
    { id: 's68', kind: 'label', ...below(R(5).b(-15), R(7).b(40), 72), label: 'daily labels by date', desc: 'PI reads the Evidence Engine\'s daily labels by date to build its weekly labels for each relationship.' },
    { id: 'loop', kind: 'loop', ...below(R(7).b(15), R(6).b(-15), 40), label: 'earlier notes read back', desc: 'The only loop. PI\'s long-term notes are read back by the Findings Engine, as of that moment, to add "this has come up before" wording. A PI status never changes a wording class, a mode or a group.' }];
  const svg = sv('svg', { class: 'fd-svg', viewBox: '0 0 1130 560', role: 'img', 'aria-label': 'How data flows between the eight components' },
    sv('defs', {}, ...['main', 'store', 'gist', 'packet', 'label', 'loop'].map((k) => sv('marker', { id: `fd-arrow-${k}`, viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 9, markerHeight: 9, markerUnits: 'userSpaceOnUse', orient: 'auto-start-reverse' }, sv('path', { d: 'M0,0 L10,5 L0,10 z', class: `fd-head ${k}` })))));
  const desc = h('div', { class: 'fd-desc' }, h('b', {}, 'Hover a line'), ' to see what flows along it, or click a box to open its page.');
  const edgeEls = [];
  E.forEach((e) => {
    const g = sv('g', { class: `fd-edge ${e.kind}`, 'data-id': e.id }, sv('path', { d: e.d, class: 'fd-line', 'marker-end': `url(#fd-arrow-${e.kind})` }), sv('path', { d: e.d, class: 'fd-hit' }));
    const w = e.label.length * 5 + 12;
    const pill = sv('g', { class: 'fd-pill' }, sv('rect', { x: e.lab[0] - w / 2, y: e.lab[1] - 8, width: w, height: 16, rx: 8 }), sv('text', { x: e.lab[0], y: e.lab[1] + 3, 'text-anchor': 'middle' }, e.label));
    g.append(pill);
    g.addEventListener('mouseenter', () => { svg.classList.add('dim'); g.classList.add('on'); desc.replaceChildren(h('b', {}, `${e.label}: `), e.desc); });
    g.addEventListener('mouseleave', () => { svg.classList.remove('dim'); g.classList.remove('on'); desc.replaceChildren(h('b', {}, 'Hover a line'), ' to see what flows along it, or click a box to open its page.'); });
    edgeEls.push(g);
  });
  edgeEls.forEach((g) => svg.append(g));
  IDS.forEach((id, i) => {
    const fo = sv('foreignObject', { x: POS[i][0], y: POS[i][1], width: W, height: H });
    const accent = ACCENT[i % ACCENT.length];
    fo.append(h('a', { class: 'fd-node', href: `#/stage/${id}`, style: `--accent: ${accent}` },
      h('div', { class: 'fd-top' }, h('span', { class: 'fd-badge' }, i + 1), h('b', {}, NAME[i])), h('div', { class: 'fd-num num' }, NUM[i][0]), h('div', { class: 'fd-cap' }, NUM[i][1]), ALSO[i] ? h('div', { class: 'fd-also' }, ALSO[i]) : h('span', {})));
    svg.append(fo);
  });
  const key = h('div', { class: 'fd-key' }, [['main', 'main chain: one component\'s output is the next one\'s input'], ['store', 'read-only side input from the store'], ['gist', 'Baseline gists used as context'], ['packet', 'packet status'], ['label', 'Evidence daily labels'], ['loop', 'the one loop: PI notes read back by Findings']]
    .map(([k, t]) => h('span', { class: `fd-k ${k}` }, h('i', {}), t)));
  return card('How data flows between the eight components', 'Arrows show what is read from what. Nothing flows backwards except the one loop between PI and the Findings Engine.',
    h('div', { class: 'stack', style: { gap: '12px' } }, key, h('div', { class: 'fd-wrap' }, svg), desc,
      h('div', { class: 'flow-note' }, 'What never flows back: an alert never feeds the Baseline Engine, the pairings are not used downstream, and a PI status never changes what the Findings Engine may say.')));
}

export function render(root) {
  const P = S.pipeline;
  const st = P.stages;
  const total = (id, k) => st.find((s) => s.id === id).counts[k];
  const featured = S.cases.find((c) => c.date === '2025-11-18') || S.cases[0];

  root.append(h('section', { class: 'hero' },
    h('h1', {}, 'From a reading to her context'),
    h('p', {}, `Eight components, each reading what the one before it wrote. ${n1(total('threshold', 'readings checked'), 0)} readings became ${total('state', 'alerts')} alerts, ${total('findings', 'cases')} cases and ${total('findings', 'versions')} written versions. `
      + 'Every box below shows what goes in, what comes out, and the id that links it to the next — so any piece of context can be traced back to the readings behind it.'),
    h('div', { class: 'row' },
      h('a', { class: 'btn solid', href: `#/case/${encodeURIComponent(featured.id)}` }, 'Follow a case from start to finish →'),
      h('a', { class: 'btn', href: '#/cases' }, 'Browse all cases'),
      h('a', { class: 'btn', href: '#/pi' }, 'PI long-term notes'))));

  const flow = h('div', { class: 'flow' });
  st.forEach((s) => {
    const hl = HEADLINE[s.id];
    let big, small;
    if (s.id === 'baseline') {
      const n = Object.entries(s.counts).reduce((a, [, v]) => a + v, 0);
      big = n1(n, 0); small = 'windows (day, week, month)';
    } else if (s.id === 'threshold') { big = n1(s.counts['readings checked'], 0); small = `readings checked · ${s.counts.rejected} rejected`; }
    else if (s.id === 'findings') { big = s.counts.versions; small = `versions in ${s.counts.cases} cases`; }
    else if (s.id === 'pi') { big = s.counts.relationships; small = `long-term notes · ${s.counts['memory versions']} versions`; }
    else { big = n1(s.counts[hl[0]], 0); small = hl[1]; }
    flow.append(h('a', { class: 'node', href: `#/stage/${s.id}`, style: `--accent: ${ACCENT[(s.n - 1) % ACCENT.length]}` },
      h('div', { class: 'node-top' }, h('span', { class: 'nbadge' }, s.n), h('span', { class: 'node-go' }, 'Open →')),
      h('div', { class: 'sname' }, s.name),
      h('div', { class: 'io' },
        h('div', { class: 'io-row' }, h('span', { class: 'tag in' }, 'IN'), h('span', { class: 'io-text' }, SHORT_IN[s.id])),
        h('div', { class: 'io-row' }, h('span', { class: 'tag out' }, 'OUT'), h('span', { class: 'io-text' }, SHORT_OUT[s.id]))),
      h('div', { class: 'big-wrap' }, h('div', { class: 'big num' }, big), h('div', { class: 'big-sub' }, small))));
  });
  root.append(card('The eight components', 'Click one to see its input, its output, real examples and where it hands over to the next', flow));

  // how data flows between the eight components
  root.append(flowDiagram(P, st, total));

  // versions
  const v = P.versions;
  root.append(card('Versions in this run', 'Everything written is stamped with the version of the method that wrote it',
    h('div', { class: 'tile-grid' },
      [['Findings method', v.findings.method_version], ['Prompt', v.findings.prompt_version], ['Checks', v.findings.checks_version], ['Phrase book', v.findings.phrasebook_version], ['Evidence library', v.findings.library_version], ['Rulebook', v.rulebook], ['Evidence method', v.evidence]]
        .map(([k, x]) => h('div', { class: 'stat' }, h('span', { class: 'k' }, k), h('span', { class: 'v mono' }, x))))));
  return [['Pipeline']];
}
