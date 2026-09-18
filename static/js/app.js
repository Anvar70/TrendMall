import {api, toast} from './api.js';
import {t} from './i18n.js';
document.querySelector('[data-logout]')?.addEventListener('click', async () => {
  try { await api('auth/logout/', {method: 'POST'}); location.assign('/'); } catch { toast(t('error')); }
});
const menu = document.querySelector('[data-menu]');
menu?.addEventListener('click', () => { const open = document.body.classList.toggle('nav-open'); menu.setAttribute('aria-expanded', open); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') { document.body.classList.remove('nav-open'); menu?.setAttribute('aria-expanded', 'false'); } });
