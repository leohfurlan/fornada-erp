"use client";

import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { useAuthStore } from "@/stores/use-auth-store";
import { ADIAMENTO_MS, emitirPwa, identidadeAtual, lerLocal, modoApp, salvarLocal, type InstallPrompt, type PwaSession } from "@/lib/pwa";

interface PwaContextValue {
  available: boolean; open: boolean; error: string; busy: boolean;
  dismiss(): void; install(origin: "automatico" | "menu"): void;
}
const PwaContext = createContext<PwaContextValue | null>(null);
export function usePwaInstall(): PwaContextValue | null { return useContext(PwaContext); }

export function PwaProvider({ children }: { children: ReactNode }) {
  const { usuario, isAuthenticated } = useAuthStore();
  const [hydrated, setHydrated] = useState(false);
  const [available, setAvailable] = useState(false);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const prompt = useRef<InstallPrompt | null>(null);
  const session = useRef<PwaSession | null>(null);
  const offered = useRef(false);
  const active = useRef(false);
  const previousIdentity = useRef<string | null>(null);
  const installationOwner = useRef<PwaSession | null>(null);

  useEffect(() => {
    const off = useAuthStore.persist.onFinishHydration(() => setHydrated(true));
    setHydrated(useAuthStore.persist.hasHydrated());
    return off;
  }, []);

  useEffect(() => {
    const receive = (event: Event) => {
      event.preventDefault();
      prompt.current = event as InstallPrompt;
      setAvailable(!modoApp());
    };
    const installed = () => {
      const current = session.current;
      if (active.current && current && (!installationOwner.current || installationOwner.current === current) && identidadeAtual() === current.identity) emitirPwa(current, "instalacao_sinalizada", "navegador");
      installationOwner.current = null;
      prompt.current = null; setAvailable(false); setOpen(false);
    };
    const media = [window.matchMedia("(display-mode: standalone)"), window.matchMedia("(display-mode: fullscreen)")];
    const modeChanged = () => {
      if (modoApp()) {
        setAvailable(false); setOpen(false);
        const current = session.current;
        if (current && active.current && !appRecorded.current) {
          appRecorded.current = true; emitirPwa(current, "acesso_app", "abertura_app");
        }
      } else setAvailable(Boolean(prompt.current));
    };
    window.addEventListener("beforeinstallprompt", receive);
    window.addEventListener("appinstalled", installed);
    media.forEach((item) => item.addEventListener("change", modeChanged));
    return () => {
      window.removeEventListener("beforeinstallprompt", receive);
      window.removeEventListener("appinstalled", installed);
      media.forEach((item) => item.removeEventListener("change", modeChanged));
    };
  }, []);

  const appRecorded = useRef(false);
  useEffect(() => {
    const identity = hydrated && isAuthenticated && usuario ? identidadeAtual() : null;
    active.current = Boolean(identity);
    if (!identity) {
      session.current?.controller.abort();
      if (previousIdentity.current) { prompt.current = null; setAvailable(false); }
      previousIdentity.current = null; session.current = null; offered.current = false;
      appRecorded.current = false; setOpen(false); setBusy(false); setError("");
      return;
    }
    if (previousIdentity.current !== identity) {
      session.current?.controller.abort();
      if (previousIdentity.current) { prompt.current = null; setAvailable(false); }
      previousIdentity.current = identity;
      const browserId = lerLocal("fornada-pwa-browser") || crypto.randomUUID();
      salvarLocal("fornada-pwa-browser", browserId);
      session.current = { identity, browserId, sessionId: crypto.randomUUID(), controller: new AbortController() };
      offered.current = false; appRecorded.current = false;
      setOpen(false); setError(""); setBusy(false);
    }
    const current = session.current;
    if (!current) return;
    if (modoApp()) {
      setOpen(false);
      if (!appRecorded.current) { appRecorded.current = true; emitirPwa(current, "acesso_app", "abertura_app"); }
      return;
    }
    const until = Number(lerLocal(`fornada-pwa-adiar:${identity}`));
    if (available && prompt.current && !offered.current && !(until > Date.now())) {
      offered.current = true; setOpen(true); emitirPwa(current, "convite_exibido", "automatico");
    }
  }, [hydrated, isAuthenticated, usuario, available]);

  function dismiss() {
    setOpen(false);
    const current = session.current;
    if (current) {
      salvarLocal(`fornada-pwa-adiar:${current.identity}`, String(Date.now() + ADIAMENTO_MS));
      offered.current = true; emitirPwa(current, "adiado", "automatico");
    }
  }
  function install(origin: "automatico" | "menu") {
    const event = prompt.current;
    const current = session.current;
    if (!event || !current || identidadeAtual() !== current.identity || modoApp()) return;
    prompt.current = null; setAvailable(false); setBusy(true); setError(""); setOpen(false);
    installationOwner.current = current;
    // A chamada ocorre no gesto, antes de qualquer await ou envio HTTP.
    let result: Promise<{ outcome: "accepted" | "dismissed" }>;
    try { result = event.prompt(); }
    catch { result = Promise.reject(new Error("prompt")); }
    emitirPwa(current, "instalar_clicado", origin);
    void result.then(() => event.userChoice).then(({ outcome }) => {
      if (identidadeAtual() !== current.identity || session.current !== current) return;
      emitirPwa(current, outcome === "accepted" ? "confirmacao_aceita" : "confirmacao_recusada", origin);
    }).catch(() => {
      if (session.current === current) setError("Não foi possível abrir a instalação. Tente novamente pelo menu.");
    }).finally(() => { if (session.current === current) setBusy(false); });
  }
  return <PwaContext.Provider value={{ available: active.current && available && !busy, open, error, busy, dismiss, install }}>{children}</PwaContext.Provider>;
}
