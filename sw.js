/**
 * Wissens-SRS Service Worker v1
 * Cache-Strategie: Cache-First für App-Shell, Network-Only für API
 */
const CACHE = 'wissens-srs-v1';
const SHELL = ['/', '/index.html', '/manifest.json', '/sw.js'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k !== CACHE).map(k => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const { pathname } = new URL(e.request.url);
  // API immer frisch vom Netz
  if (pathname.startsWith('/api/')) {
    e.respondWith(fetch(e.request).catch(() =>
      new Response(JSON.stringify({ error: 'Offline' }), { status: 503, headers: { 'Content-Type': 'application/json' } })
    ));
    return;
  }
  // App-Shell & Assets: Cache-First
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request).then(res => {
      // CDN-Assets (Tailwind) nachladen für später
      if (res.ok && e.request.url.startsWith('https://')) {
        const clone = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
      }
      return res;
    }))
  );
});
