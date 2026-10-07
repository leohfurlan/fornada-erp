"use client";

import { useEffect, useState } from "react";
import { clearSupportSession, getSupportSession, type SessaoSuporte } from "@/lib/admin-session";
import { encerrarSuporte } from "@/hooks/use-admin";
import { useAuthStore } from "@/stores/use-auth-store";

export function SupportBanner() {
  const [session, setSession] = useState<SessaoSuporte | null>(null);
  const [expired, setExpired] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { usuario } = useAuthStore();
  useEffect(() => {
    const value = getSupportSession();
    if (!value || value.operador_id !== usuario?.id) return;
    setSession(value);
    const tick = () => setExpired(Date.parse(value.expires_at) <= Date.now());
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [usuario?.id]);

  if (!session) return null;
  async function sair() {
    if (!session || busy) return;
    setBusy(true);
    try {
      await encerrarSuporte(session.id);
      clearSupportSession();
      window.location.assign("/admin");
    } catch {
      setError("Não foi possível encerrar. Tente novamente.");
      setBusy(false);
    }
  }
  return <aside className="border-b bg-amber-50 px-4 py-3 text-amber-950" aria-label="Acesso administrativo">
    <div className="mx-auto max-w-5xl flex flex-wrap items-center gap-3">
      <p className="flex-1 min-w-0 break-words"><strong>{expired ? "Suporte expirado" : "Modo de suporte"}</strong>: {session.conta.negocio} · {session.conta.email}. Ações realizadas por {usuario?.nome}.</p>
      <button disabled={busy} className="rounded border border-amber-800 px-3 py-2" onClick={sair}>{busy ? "Encerrando..." : "Voltar à administração"}</button>
      {error && <p role="alert">{error}</p>}
    </div>
  </aside>;
}
