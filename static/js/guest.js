import {api, showError} from './api.js';
const form = document.querySelector('[data-auth]');
form?.addEventListener('submit', async event => {
  event.preventDefault(); const button = form.querySelector('[type=submit]'); button.disabled = true;
  const error = form.querySelector('[role=alert]'); error.hidden = true;
  const data = Object.fromEntries(new FormData(form)); delete data.csrfmiddlewaretoken;
  if (form.dataset.auth !== 'register') data.next = new URLSearchParams(location.search).get('next') || '';
  try { const result = await api('auth/' + form.dataset.auth + '/', {method: 'POST', body: data}); location.assign(result.redirect); }
  catch (exc) { showError(error, exc); } finally { button.disabled = false; }
});
document.querySelector('[data-show-password]')?.addEventListener('change', event => {
  form.querySelectorAll('[autocomplete*=password]').forEach(input => input.type = event.target.checked ? 'text' : 'password');
});
