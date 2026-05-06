const CACHE_NAME = "offline-cache-v1";
const URLS_TO_CACHE = ["./", "./static/style.css"];

self.addEventListener("install", e => {
    e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(URLS_TO_CACHE)));
    self.skipWaiting(); // attiva subito il nuovo SW
});

self.addEventListener("activate", e => {
    e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))));
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
