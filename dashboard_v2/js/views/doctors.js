// The doctor's view lives in doctors_requirement/nmg_view and is shown here in a frame, so this dashboard holds none of its code.
import { h } from '../ui.js';

export function render(root, args) {
  const theme = document.documentElement.dataset.theme || 'light';
  const sub = args.length ? `#/${args.map(encodeURIComponent).join('/')}` : '';
  root.append(h('iframe', { class: 'doctors-frame', src: `doctors/index.html?embed=1&theme=${theme}${sub}`, title: "Doctor's view" }));
  return [['Doctor\'s view']];
}
