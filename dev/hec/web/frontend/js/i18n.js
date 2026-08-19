// Překlady a formátování. V šablonách nikdy nestojí hotový text, jen klíč.

const state = { lang: 'cs', catalog: {}, available: ['cs', 'en'] };

const LOCALE = { cs: 'cs-CZ', en: 'en-GB' };

export function lookup(key) {
  return key.split('.').reduce((node, part) => (node && typeof node === 'object' ? node[part] : undefined), state.catalog);
}

export function t(key, params) {
  const text = lookup(key);
  if (typeof text !== 'string') return key;
  if (!params) return text;
  return text.replace(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g, (match, name) => (name in params ? params[name] : match));
}

export async function setLanguage(lang, api) {
  const payload = await api.translations(lang);
  state.lang = payload.lang;
  state.catalog = payload.catalog;
  state.available = payload.available;
  document.documentElement.lang = payload.lang;
  localStorage.setItem('hec_lang', payload.lang);
  applyTranslations(document);
  return payload;
}

export function currentLanguage() { return state.lang; }
export function availableLanguages() { return state.available; }
export function preferredLanguage(fallback = 'cs') {
  return localStorage.getItem('hec_lang') || (navigator.language || '').slice(0, 2) || fallback;
}

export function applyTranslations(root) {
  root.querySelectorAll('[data-i18n]').forEach((element) => {
    element.textContent = t(element.dataset.i18n);
  });
  root.querySelectorAll('[data-i18n-label]').forEach((element) => {
    element.setAttribute('aria-label', t(element.dataset.i18nLabel));
  });
}

// --- formátování ----------------------------------------------------------
const locale = () => LOCALE[state.lang] || state.lang;

export function num(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '–';
  return new Intl.NumberFormat(locale(), { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(Number(value));
}

export function power(watts, digits = 2) {
  if (watts === null || watts === undefined || Number.isNaN(Number(watts))) return { value: '–', unit: t('unit.kw') };
  const absolute = Math.abs(Number(watts));
  if (absolute < 1000) return { value: num(watts, 0), unit: t('unit.w') };
  return { value: num(Number(watts) / 1000, digits), unit: t('unit.kw') };
}

export function time(value, options = { hour: '2-digit', minute: '2-digit' }) {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return '–';
  return new Intl.DateTimeFormat(locale(), options).format(date);
}

export function dateTime(value) {
  return time(value, { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

export function weekday(value) {
  return time(value, { weekday: 'long' });
}

export function duration(minutes) {
  const total = Math.round(Number(minutes) || 0);
  const hours = Math.floor(total / 60);
  return hours ? `${hours} ${t('unit.hours')} ${total % 60} min` : `${total} min`;
}
