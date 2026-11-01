// Service worker mínimo (task 11): habilita a instalação do PWA.
// Nesta fase não cacheia agressivamente (o app depende da API em tempo real);
// estratégias de cache offline entram numa fase posterior.
self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", () => {
  // Passa direto para a rede (sem interceptar) nesta fase.
});
