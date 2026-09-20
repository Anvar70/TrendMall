import {api, toast} from './api.js';
import {t} from './i18n.js';
import {poll} from './components/ui.js';
const notificationPrefix = document.body.dataset.section === 'admin_panel' ? 'admin/' : '';
async function updateUnread() {
  const data = await api(notificationPrefix + 'notifications/unread-count/');
  document.getElementById('unread-count').textContent = data.count || '';
}
updateUnread().catch(() => {});
poll(updateUnread, 12000);
document.querySelector('[data-logout]')?.addEventListener('click', async () => {
  try { await api('auth/logout/', {method: 'POST'}); location.assign('/'); } catch { toast(t('error')); }
});
const menu = document.querySelector('[data-menu]');
menu?.addEventListener('click', () => { const open = document.body.classList.toggle('nav-open'); menu.setAttribute('aria-expanded', open); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') { document.body.classList.remove('nav-open'); menu?.setAttribute('aria-expanded', 'false'); } });
