// Offline shell: rozhraní se načte i bez spojení, data se pak doplní.
//
// Záměrně network-first, ne cache-first: tohle je aktivně vyvíjený produkt,
// který se aktualizuje přes `git pull` + restart. Cache-first by po každé
// úpravě JS/CSS ukazovalo starý kód donekonečna, dokud by si někdo ručně
// nevymazal cache prohlížeče – cache je zde jen záloha pro výpadek sítě,
// ne primární zdroj.
const CACHE = 'hec-v15';
const SHELL = ['/', '/index.html', '/css/tokens.css', '/css/app.css',
  '/js/app.js', '/js/api.js', '/js/i18n.js', '/js/chart.js', '/js/flow.js',
  '/js/pages.js', '/js/advisor.js', '/js/icons.js', '/js/background.js', '/manifest.json', '/icon.svg'];

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

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE).then((cache) => cache.put(event.request, copy));
        return response;
      })
      .catch(() => caches.match(event.request)),
  );
});
