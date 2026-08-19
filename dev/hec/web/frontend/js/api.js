// Komunikace s lokálním API. Žádné externí volání – systém musí fungovat offline.

async function request(path, options = {}) {
  const response = await fetch(path, {
    credentials: 'same-origin',
    headers: { 'Accept': 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}) },
    ...options,
  });
  if (response.status === 401) {
    const error = new Error('unauthorised');
    error.unauthorised = true;
    throw error;
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(payload.error || `HTTP ${response.status}`);
    error.payload = payload;
    throw error;
  }
  return payload;
}

export const api = {
  session: () => request('/api/session'),
  login: (password) => request('/api/login', { method: 'POST', body: JSON.stringify({ password }) }),
  current: () => request('/api/current'),
  status: () => request('/api/status'),
  weather: () => request('/api/weather'),
  prices: () => request('/api/prices'),
  prediction: () => request('/api/prediction'),
  summaries: (days = 30) => request(`/api/summaries?days=${days}`),
  appliances: (days = 7) => request(`/api/appliances?days=${days}`),
  phases: (days = 7) => request(`/api/phases?days=${days}`),
  heatpump: () => request('/api/heatpump'),
  metrics: (days = 30) => request(`/api/metrics?days=${days}`),
  decisions: (days = 7) => request(`/api/decisions?days=${days}`),
  sources: () => request('/api/sources'),
  history: (params) => request('/api/history?' + new URLSearchParams(params)),
  config: () => request('/api/config'),
  configSchema: () => request('/api/config/schema'),
  saveConfig: (config) => request('/api/config', { method: 'PUT', body: JSON.stringify({ config }) }),
  translations: (lang) => request(`/api/i18n/${lang}`),
};
