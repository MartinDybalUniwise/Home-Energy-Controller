// Vstupní bod rozhraní: přihlášení, jazyk, směrování, obnova dat.

import { api } from './api.js';
import { applyScene } from './background.js';
import { applyTranslations, preferredLanguage, setLanguage, t, time } from './i18n.js';
import { pages } from './pages.js';

const REFRESH_MS = 10000;
const ORDER = ['overview', 'history', 'prediction', 'settings'];

const state = {
  page: 'overview',
  motion: localStorage.getItem('hec_motion') || 'full',
  theme: localStorage.getItem('hec_theme') || 'auto',
  timer: null,
};

const view = document.getElementById('view');

function applyPreferences({ animations, theme } = {}) {
  if (animations) { state.motion = animations; localStorage.setItem('hec_motion', animations); }
  if (theme) { state.theme = theme; localStorage.setItem('hec_theme', theme); }
  document.documentElement.dataset.theme = state.theme;
  document.body.dataset.motion = state.motion;
}

function pageFromHash() {
  const name = (location.hash.replace('#/', '') || 'overview').split('?')[0];
  return ORDER.includes(name) ? name : 'overview';
}

async function render() {
  state.page = pageFromHash();
  document.querySelectorAll('.nav a').forEach((link) => {
    if (link.dataset.page === state.page) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  });

  view.innerHTML = `<p class="loading">${t('app.loading')}</p>`;
  try {
    await pages[state.page](view, { api, state, motion: state.motion, onUiChange: applyPreferences });
  } catch (error) {
    if (error.unauthorised) return askForPassword();
    view.innerHTML = `<p class="notice error">${t('error.load_failed')}</p>`;
    console.error(error);
  }
}

async function refreshStatus() {
  try {
    const [status, weather] = await Promise.all([api.status(), api.weather().catch(() => ({}))]);
    applyScene(weather, state.motion);
    document.getElementById('site-name').textContent = status.site_name || t('app.name');
    document.getElementById('clock').textContent = time(new Date());

    const pill = document.getElementById('status-pill');
    const stale = status.stale_sources || [];
    const safeMode = status.controller?.safe_mode && status.controller?.enabled;
    if (stale.length || safeMode) {
      pill.hidden = false;
      pill.dataset.level = stale.length ? 'critical' : 'warning';
      pill.textContent = stale.length ? `${t('status.stale')}: ${stale.join(', ')}` : t('status.safe_mode');
    } else {
      pill.hidden = false;
      pill.dataset.level = 'ok';
      pill.textContent = t('status.ok');
    }
  } catch (error) {
    if (error.unauthorised) askForPassword();
  }
}

function askForPassword() {
  const dialog = document.getElementById('login');
  const form = document.getElementById('login-form');
  const error = document.getElementById('login-error');
  if (!dialog.open) dialog.showModal();
  form.onsubmit = async (event) => {
    event.preventDefault();
    try {
      await api.login(document.getElementById('login-password').value);
      dialog.close();
      error.hidden = true;
      await start();
    } catch {
      error.hidden = false;
    }
  };
}

function enableSwipe() {
  let startX = 0;
  let startY = 0;
  document.addEventListener('touchstart', (event) => {
    startX = event.touches[0].clientX;
    startY = event.touches[0].clientY;
  }, { passive: true });
  document.addEventListener('touchend', (event) => {
    const deltaX = event.changedTouches[0].clientX - startX;
    const deltaY = event.changedTouches[0].clientY - startY;
    // Gesto je zkratka, ne jediná cesta – menu funguje vždy.
    if (Math.abs(deltaX) < 70 || Math.abs(deltaY) > 50) return;
    const index = ORDER.indexOf(state.page);
    const next = ORDER[index + (deltaX < 0 ? 1 : -1)];
    if (next) location.hash = `#/${next}`;
  }, { passive: true });
}

async function start() {
  await setLanguage(preferredLanguage(), api);
  applyTranslations(document);
  await refreshStatus();
  await render();
  clearInterval(state.timer);
  state.timer = setInterval(() => {
    refreshStatus();
    if (state.page === 'overview') render();
  }, REFRESH_MS);
}

async function init() {
  applyPreferences();
  enableSwipe();
  window.addEventListener('hashchange', render);
  document.getElementById('menu-toggle').addEventListener('click', (event) => {
    const nav = document.getElementById('nav');
    const expanded = nav.hasAttribute('hidden');
    nav.toggleAttribute('hidden', !expanded);
    event.currentTarget.setAttribute('aria-expanded', String(expanded));
  });

  const session = await api.session().catch(() => ({ required: false, authorised: true }));
  if (session.required && !session.authorised) return askForPassword();
  await start();

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  }
}

init();
