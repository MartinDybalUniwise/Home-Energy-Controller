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
  current: (params = {}, options = {}) => request('/api/current?' + new URLSearchParams(params), options),
  status: (options = {}) => request('/api/status', options),
  weather: (options = {}) => request('/api/weather', options),
  prices: (options = {}) => request('/api/prices', options),
  prediction: (options = {}) => request('/api/prediction', options),
  summaries: (days = 30) => request(`/api/summaries?days=${days}`),
  appliances: (days = 7) => request(`/api/appliances?days=${days}`),
  phases: (days = 7) => request(`/api/phases?days=${days}`),
  heatpump: () => request('/api/heatpump'),
  metrics: (days = 30) => request(`/api/metrics?days=${days}`),
  decisions: (days = 7, options = {}) => request(`/api/decisions?days=${days}`, options),
  financeDashboard: (params = {}) => request('/api/finance?' + new URLSearchParams(params)),
  financeManual: (params = {}) => request('/api/finance/manual?' + new URLSearchParams(params)),
  sources: () => request('/api/sources'),
  history: (params) => request('/api/history?' + new URLSearchParams(params)),
  logDays: (source) => request(`/api/logs/days?source=${encodeURIComponent(source)}`),
  logs: (source, params = {}, options = {}) => request('/api/logs?' + new URLSearchParams({ source, ...params }), options),
  config: (options = {}) => request('/api/config', options),
  configSchema: () => request('/api/config/schema'),
  verifyConfig: (target) => request(`/api/config/verify?target=${encodeURIComponent(target)}`),
  goodweAuthorization: () => request('/api/goodwe/authorization'),
  verifyGoodweAuthorization: () => request('/api/goodwe/authorization/verify', { method: 'POST', body: JSON.stringify({}) }),
  approveGoodweAuthorization: () => request('/api/goodwe/authorization/approve', { method: 'POST', body: JSON.stringify({ approved_by: 'config-ui' }) }),
  saveConfig: (config) => request('/api/config', { method: 'PUT', body: JSON.stringify({ config }) }),
  translations: (lang) => request(`/api/i18n/${lang}`),
};
