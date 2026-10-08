async function api(url, options = {}) {
  const config = { credentials: 'include', ...options };
  if (options.body && !(options.body instanceof FormData)) {
    config.headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  }
  let response;
  try {
    response = await fetch(url, config);
  } catch (_) {
    throw new Error('Cannot connect to the application server. Keep run_windows.bat open and try again.');
  }
  let data = {};
  try { data = await response.json(); } catch (_) {}
  if (!response.ok) {
    const error = new Error(data.detail || `Request failed (${response.status}).`);
    error.status = response.status;
    throw error;
  }
  return data;
}

function byId(id) { return document.getElementById(id); }

function toast(message, type = '') {
  const old = document.querySelector('.toast');
  if (old) old.remove();
  const el = document.createElement('div');
  el.className = `toast ${type}`.trim();
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3800);
}

function escapeHtml(value = '') {
  return String(value).replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
}

function formatDate(value) {
  if (!value) return '—';
  return new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

function clampPercent(value) {
  const number = Number(value) || 0;
  return Math.max(0, Math.min(100, number));
}

async function logout() {
  await api('/api/logout', { method: 'POST' });
  location.href = '/';
}
