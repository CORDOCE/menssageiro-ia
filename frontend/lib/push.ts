// Inscrição de Web Push (spec 0023): pede permissão, assina no push service do browser e registra no
// backend. Degrada em browsers sem suporte (iOS sem PWA, etc.) — o fallback é o e-mail.

import { inscreverPush, obterChavePush } from "@/lib/api";

export type EstadoPush = "indisponivel" | "negado" | "sem-vapid" | "ok" | "erro";

// Converte a chave VAPID (base64url) para o Uint8Array que o pushManager espera.
function base64UrlParaBytes(base64: string): Uint8Array<ArrayBuffer> {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const b64 = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(b64);
  const bytes = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i = 0; i < raw.length; i += 1) bytes[i] = raw.charCodeAt(i);
  return bytes;
}

export function suportaPush(): boolean {
  return (
    typeof navigator !== "undefined" &&
    "serviceWorker" in navigator &&
    typeof window !== "undefined" &&
    "PushManager" in window &&
    "Notification" in window
  );
}

export async function ativarPush(): Promise<EstadoPush> {
  if (!suportaPush()) return "indisponivel";
  const permissao = await Notification.requestPermission();
  if (permissao !== "granted") return "negado";
  try {
    const { chave } = await obterChavePush();
    if (!chave) return "sem-vapid"; // backend sem VAPID configurado
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: base64UrlParaBytes(chave),
    });
    const json = sub.toJSON();
    if (!json.endpoint || !json.keys) return "erro";
    await inscreverPush({
      endpoint: json.endpoint,
      keys: { p256dh: json.keys.p256dh, auth: json.keys.auth },
    });
    return "ok";
  } catch {
    return "erro";
  }
}
