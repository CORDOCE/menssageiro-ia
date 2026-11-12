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

// Web Push (spec 0023): o backend envia {titulo, corpo, url} nos alertas §12. Sem PII no corpo.
self.addEventListener("push", (event) => {
  let dados = { titulo: "Mensageiro", corpo: "Novo alerta.", url: "/" };
  try {
    if (event.data) dados = { ...dados, ...event.data.json() };
  } catch {
    // payload não-JSON: usa o default
  }
  event.waitUntil(
    self.registration.showNotification(dados.titulo, {
      body: dados.corpo,
      data: { url: dados.url },
      tag: "mensageiro-alerta",
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clientes) => {
      const aberto = clientes.find((c) => "focus" in c);
      return aberto ? aberto.focus() : self.clients.openWindow(url);
    }),
  );
});
