const CACHE_NAME = "offline-cache-v1-2";
const URLS_TO_CACHE = ["./", "./static/style.css"];

self.addEventListener("install", e => {
    e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(URLS_TO_CACHE)));
    self.skipWaiting(); // attiva subito il nuovo SW
});

self.addEventListener("activate", e => {
    e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))));
});

const IMAGE_CACHE = "image-cache-v1";
self.addEventListener("fetch", e => {
    const req = e.request;
    // Cache-first solo per le immagini
    if (req.destination === "image") {
        e.respondWith(
            caches.open(IMAGE_CACHE).then(async cache => {
                const cached = await cache.match(req);
                if (cached) return cached;

                try {
                    const networkResponse = await fetch(req);
                    if (networkResponse.ok) {
                        cache.put(req, networkResponse.clone());
                    }
                    return networkResponse;
                } catch (err) {
                    // fallback opzionale: return cache.match('./static/placeholder.png');
                    throw err;
                }
            })
        );
        return;
    }
});


// Aggiunta della gestione a runtime (opzionale ma consigliata per le risorse esterne)
// self.addEventListener("fetch", e => {
//     e.respondWith(
//         caches.match(e.request).then(response => {
//             // Se la risorsa è nella cache, restituiscila
//             if (response) {
//                 return response;
//             }

//             // Altrimenti, scaricala dalla rete
//             return fetch(e.request).then(networkResponse => {
//                 // Non cachiamo le risorse esterne (es. kit.fontawesome.com o fonts.googleapis.com)
//                 // per evitare errori CORS, a meno che non si tratti di una strategia avanzata.
//                 return networkResponse;
//             });
//         }),
//     );
// });
