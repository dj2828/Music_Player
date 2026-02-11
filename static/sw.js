const CACHE_NAME = 'offline-cache-v1';
const URLS_TO_CACHE = ['./', './static/style.css', 'https://fonts.googleapis.com/css2?family=Montserrat:wght@900&display=swap'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE_NAME).then(c => c.addAll(URLS_TO_CACHE))
  );
  self.skipWaiting(); // attiva subito il nuovo SW
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
});