// Offline shell: rozhraní se načte i bez spojení, data se pak doplní.
const CACHE = 'hec-v1';
const SHELL = ['/', '/index.html', '/css/tokens.css', '/css/app.css',
  '/js/app.js', '/js/api.js', '/js/i18n.js', '/js/chart.js', '/js/flow.js',
  '/js/pages.js', '/js/icons.js', '/js/background.js', '/manifest.json', '/icon.svg'];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) return;
  // Data vždy ze sítě – zobrazovat stará měření jako aktuální by bylo zavádějící.
  if (url.pathname.startsWith('/api/')) return;
  event.respondWith(caches.match(event.request).then((cached) => cached || fetch(event.request)));
});
