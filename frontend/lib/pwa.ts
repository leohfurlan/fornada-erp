import { api } from "@/lib/api";
import { getSupportSession } from "@/lib/admin-session";
import { useAuthStore } from "@/stores/use-auth-store";

export const pwaTipos = ["convite_exibido", "adiado", "instalar_clicado", "confirmacao_aceita", "confirmacao_recusada", "instalacao_sinalizada", "acesso_app"] as const;
export type PwaTipo = typeof pwaTipos[number];
export type PwaOrigem = "automatico" | "menu" | "navegador" | "abertura_app";
export const ADIAMENTO_MS = 7 * 24 * 60 * 60 * 1000;
export interface InstallPrompt extends Event {
  prompt(): Promise<{ outcome: "accepted" | "dismissed" }>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}
export function lerLocal(key: string): string | null {
  try { return localStorage.getItem(key); } catch { return null; }
}
export function salvarLocal(key: string, value: string): void {
  try { localStorage.setItem(key, value); } catch { /* Sessão em memória continua utilizável. */ }
}
export function modoApp(): boolean {
  return window.matchMedia("(display-mode: standalone)").matches || window.matchMedia("(display-mode: fullscreen)").matches;
}
export interface PwaSession { identity: string; sessionId: string; browserId: string; controller: AbortController }
export function identidadeAtual(): string | null {
  const state = useAuthStore.getState();
  return state.isAuthenticated && state.usuario && !getSupportSession()
    ? `${state.usuario.tenant_id}:${state.usuario.id}` : null;
}
export function emitirPwa(session: PwaSession, tipo: PwaTipo, origem: PwaOrigem): void {
  const payload = { event_id: crypto.randomUUID(), browser_id: session.browserId, session_id: session.sessionId, tipo, origem };
  const enviar = async () => {
    if (identidadeAtual() !== session.identity || session.controller.signal.aborted) return;
    try { await api.post("/pwa/eventos", payload, { signal: session.controller.signal }); }
    catch (error) {
      const status = (error as { response?: { status?: number } }).response?.status;
      if ((!status || status >= 500) && identidadeAtual() === session.identity && !session.controller.signal.aborted) {
        try { await api.post("/pwa/eventos", payload, { signal: session.controller.signal }); } catch { /* Melhor esforço. */ }
      }
    }
  };
  void enviar();
}
