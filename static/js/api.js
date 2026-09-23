import {t} from './i18n.js';
let csrf;
export function clearPrivateState() {
  for (const key of Object.keys(sessionStorage)) if (key.startsWith('trendbox-checkout-')) sessionStorage.removeItem(key);
}
export async function api(path, options = {}) {
  const method = options.method || 'GET';
  if (method !== 'GET' && !csrf) csrf = (await fetch('/api/v1/auth/csrf/').then(r => r.json())).csrfToken;
  const headers = {...options.headers};
  if (method !== 'GET') headers['X-CSRFToken'] = csrf;
  let body = options.body;
  if (body && !(body instanceof FormData)) { headers['Content-Type'] = 'application/json'; body = JSON.stringify(body); }
  if (/^https?:/.test(path)) { const url=new URL(path); if(url.origin!==location.origin)throw new Error('Invalid API origin'); path=url.pathname+url.search; }
  const response = await fetch(path.startsWith('/') ? path : '/api/v1/' + path, {...options, body, headers, credentials: 'same-origin', cache: 'no-store'});
  const data = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) {
    if (data.code === 'csrf_failed') csrf = null;
    if (data.code === 'not_authenticated' && !location.pathname.includes('login')) {
      clearPrivateState();
      document.querySelector('main')?.replaceChildren();
      location.assign((location.pathname.startsWith('/admin/') ? '/admin/login/' : '/login/') + '?next=' + encodeURIComponent(location.pathname));
    }
    const error = new Error(data.message || t('error')); error.data = data; error.status = response.status; throw error;
  }
  if (path.includes('login') || path.includes('register')) csrf = null;
  if (path.includes('logout')) clearPrivateState();
  return data;
}
export function showError(element, error) {
  element.replaceChildren();
  const title = document.createElement('p'); title.textContent = error.data?.message || t('error'); element.append(title);
  if (error.data?.field_errors) for (const [field, messages] of Object.entries(error.data.field_errors)) {
    const flatten = value => typeof value === 'object' && value !== null ? Object.values(value).map(flatten).join(' ') : String(value);
    const p = document.createElement('p'); p.textContent = `${t(field)}: ${flatten(messages)}`; element.append(p);
  }
  element.hidden = false;
}
export function toast(message) { const node = document.getElementById('toast'); node.textContent = message; node.hidden = false; setTimeout(() => node.hidden = true, 3500); }
