// Service worker: la app abre rápido y sin cobertura muestra la última versión.
// Los datos (Supabase) nunca se guardan en caché.
const CACHE = 'sanjose-v34';
const SHELL = [
  './', './index.html', './config.js', './manifest.webmanifest',
  './icon-192.png', './icon-512.png', './apple-touch-icon.png',
  'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/dist/umd/supabase.js'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.hostname.endsWith('supabase.co') || url.hostname.endsWith('supabase.in')) return;
  // Vídeos y audio (Dropbox, etc.): nunca pasar por el service worker.
  // Safari en iPhone no reproduce vídeos cuyas peticiones con "Range" atraviesan el service worker.
  if (req.headers.has('range') || req.destination === 'video' || req.destination === 'audio') return;
  const cdn = ['cdn.jsdelivr.net', 'fonts.googleapis.com', 'fonts.gstatic.com'];
  if (url.origin !== self.location.origin && !cdn.includes(url.hostname)) return;

  if (url.origin === self.location.origin) {
    // Primero la red (para recibir actualizaciones); si no hay, la caché.
    // "no-cache": pregunta siempre al servidor si hay versión nueva (evita ver la app antigua).
    e.respondWith(
      fetch(req, { cache: 'no-cache' }).then(res => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {});
        }
        return res;
      }).catch(async () => {
        const cached = await caches.match(req);
        if (cached) return cached;
        if (req.mode === 'navigate') return (await caches.match('./index.html')) || Response.error();
        return Response.error();
      })
    );
  } else {
    // Librerías y fuentes: primero la caché.
    e.respondWith(caches.match(req).then(r => r || fetch(req).then(res => {
      if (res.ok || res.type === 'opaque') {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {});
      }
      return res;
    })));
  }
});
