"use client";

import { useEffect } from "react";

// Registra o service worker (PWA instalável). Falhas são silenciosas — não bloqueiam o app.
export function RegistrarSW(): null {
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => undefined);
    }
  }, []);
  return null;
}
