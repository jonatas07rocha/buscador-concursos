// ATENÇÃO: CACHE_NAME foi incrementado para forçar a atualização do cache.
const CACHE_NAME = 'painel-de-vagas-cache-v2'; // Alterado de v1 para v2
const urlsToCache = [
  '/',
  '/painel_de_vagas.html',
  '/manifest.json',
  '/service-worker.js',
  'https://cdn.tailwindcss.com',
  'https://unpkg.com/lucide@latest',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
  'https://unpkg.com/tone@14.7.77/build/Tone.js',
  'https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500;700&display=swap',
  'https://fonts.gstatic.com',
  '/dados/brazil.geojson',
  '/dados/municipios_brasileiros.json',
  '/icons/icon-180x180.png', // Adicionado
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        if (response) {
          return response;
        }
        return fetch(event.request);
      })
  );
});

self.addEventListener('activate', (event) => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

