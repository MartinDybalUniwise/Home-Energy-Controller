// Vstupní bod rozhraní: přihlášení, jazyk, směrování, obnova dat.

import { api } from './api.js';
import { applyScene } from './background.js';
import { applyTranslations, preferredLanguage, setLanguage, t, time } from './i18n.js';
import { pages } from './pages.js?v=11';

const REFRESH_MS = 10000;
// Gesto swipe zůstává jen mezi třemi hlavními stránkami (kap. 13 zadání);
// Stav, Data a Nastavení jsou dostupné výhradně přes menu.
const PRIMARY_ORDER = ['overview', 'prediction', 'flow', 'history', 'finance'];
const ALL_PAGES = ['overview', 'prediction', 'flow', 'history', 'finance', 'finance/manual', 'status', 'logs', 'settings'];

const state = {
  page: 'overview',
  motion: localStorage.getItem('hec_motion') || 'full',
  theme: localStorage.getItem('hec_theme') || 'auto',
  timer: null,
};

const view = document.getElementById('view');
let pageCleanup = null;

function applyPreferences({ animations, theme } = {}) {
  if (animations) { state.motion = animations; localStorage.setItem('hec_motion', animations); }
  if (theme) { state.theme = theme; localStorage.setItem('hec_theme', theme); }
  document.documentElement.dataset.theme = state.theme;
  document.body.dataset.motion = state.motion;
}

function pageFromHash() {
  const name = (location.hash.replace('#/', '') || 'overview').split('?')[0];
  return ALL_PAGES.includes(name) ? name : 'overview';
}

async function render({ showLoading = true } = {}) {
  if (pageCleanup) { pageCleanup(); pageCleanup = null; }

  state.page = pageFromHash();
  document.querySelectorAll('nav a').forEach((link) => {
    if (link.dataset.page === state.page) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  });

  // Na navigaci (nový obsah zatím neexistuje) se "Načítám…" hodí. Na
  // periodickou obnovu téže stránky ne – vymazání celé stránky na jeden
  // řádek a zpět každých pár sekund by bylo jen matoucí probliknutí.
  if (showLoading) view.innerHTML = `<p class="loading">${t('app.loading')}</p>`;
  try {
    // Stránky Stav a Data se samy obnovují a vrací úklidovou funkci pro
    // zastavení časovače při odchodu jinam – ostatní stránky nic nevrací.
    const cleanup = await pages[state.page](view, { api, state, motion: state.motion, onUiChange: applyPreferences });
    if (typeof cleanup === 'function') pageCleanup = cleanup;
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
    if (status.ui?.brand_accent) {
      document.documentElement.style.setProperty('--brand-accent', status.ui.brand_accent);
    }
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
    const index = PRIMARY_ORDER.indexOf(state.page);
    if (index === -1) return;
    const next = PRIMARY_ORDER[index + (deltaX < 0 ? 1 : -1)];
    if (next) location.hash = `#/${next}`;
  }, { passive: true });
}

async function start() {
  await setLanguage(preferredLanguage(), api);
  applyTranslations(document);
  await refreshStatus();
  await render();
  clearInterval(state.timer);

  // Pokud by se jedno kolo někdy zdrželo (pomalá síť, uspaná záložka), další
  // tik se přeskočí, místo aby se požadavky hromadily a stránka se postupně
  // "zpomalovala" nabalováním nedokončených volání.
  let refreshing = false;
  state.timer = setInterval(async () => {
    if (refreshing) return;
    refreshing = true;
    try {
      await refreshStatus();
      if (state.page === 'overview') await render({ showLoading: false });
    } finally {
      refreshing = false;
    }
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
  document.getElementById('more-toggle').addEventListener('click', (event) => {
    const utility = document.getElementById('utility-nav');
    const expanded = utility.hasAttribute('hidden');
    utility.toggleAttribute('hidden', !expanded);
    event.currentTarget.setAttribute('aria-expanded', String(expanded));
  });
  document.querySelectorAll('#utility-nav a').forEach((link) => link.addEventListener('click', () => {
    document.getElementById('utility-nav').hidden = true;
    document.getElementById('more-toggle').setAttribute('aria-expanded', 'false');
  }));

  const session = await api.session().catch(() => ({ required: false, authorised: true }));
  if (session.required && !session.authorised) return askForPassword();
  await start();

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  }
}

init();
