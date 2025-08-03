// Define um nome e uma versão para o cache
const CACHE_NAME = 'buscador-concursos-v1';

// Lista de arquivos essenciais para o funcionamento offline
const FILES_TO_CACHE = [
  '/',
  '/index.html',
  '/dados/vagas.json',
  '/manifest.json',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
  'https://cdn.tailwindcss.com'
];

// Evento de Instalação: é acionado quando o service worker é instalado pela primeira vez.
self.addEventListener('install', (event) => {
  console.log('[Service Worker] Instalando...');
  // Espera até que o cache seja aberto e todos os arquivos essenciais sejam adicionados a ele.
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[Service Worker] Pré-cache de arquivos da aplicação');
      return cache.addAll(FILES_TO_CACHE);
    })
  );
  self.skipWaiting();
});

// Evento de Ativação: é acionado após a instalação, limpa caches antigos.
self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Ativando...');
  event.waitUntil(
    caches.keys().then((keyList) => {
      return Promise.all(keyList.map((key) => {
        // Se o nome do cache não for o atual, ele é deletado.
        if (key !== CACHE_NAME) {
          console.log('[Service Worker] Removendo cache antigo', key);
          return caches.delete(key);
        }
      }));
    })
  );
  self.clients.claim();
});

// Evento de Fetch: intercepta todas as requisições de rede da página.
self.addEventListener('fetch', (event) => {
  console.log('[Service Worker] Buscando:', event.request.url);
  // Responde à requisição servindo o arquivo do cache.
  // Se o arquivo não estiver no cache, ele tenta buscá-lo na rede.
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});
