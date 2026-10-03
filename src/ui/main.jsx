import { render } from 'preact';
import { App } from './app.jsx';
import { getPref } from './prefs.js';

const rootEl = document.getElementById('root');
document.documentElement.setAttribute('dir', 'rtl');
document.documentElement.setAttribute('lang', 'ar');
{
  const t = getPref('theme');
  if (t === 'dark' || t === 'light') document.documentElement.setAttribute('data-theme', t);
}
if (rootEl) {
  rootEl.setAttribute('dir', 'rtl');
  rootEl.setAttribute('lang', 'ar');
  rootEl.textContent = '';
  render(<App />, rootEl);
}
