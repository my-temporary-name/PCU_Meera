// Runs js/rules.js on data/nmg.json and prints the result as JSON (used by tests/test_nmg.py).
import { readFileSync } from 'node:fs';
import { evaluate } from '../js/rules.js';
const data = JSON.parse(readFileSync(new URL('../data/nmg.json', import.meta.url), 'utf8'));
const r = evaluate(data);
const slim = (d) => ({ id: d.id, signal: d.signal, rules: d.rules, also: d.also, headline: d.headline, met: d.trace.filter((t) => t.met).map((t) => t.rule + ': ' + t.value) });
console.log(JSON.stringify({ domains: r.domains.map(slim), state: r.state.rule + ' ' + r.state.name, followup: r.followup.map((x) => ({ rule: x.rule, label: x.label, next: x.next, text: x.text, note: x.note })), notices: r.notices.map((n) => n.title) }, null, 1));
