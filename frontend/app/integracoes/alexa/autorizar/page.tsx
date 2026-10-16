"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/use-auth-store";

export default function AutorizarAlexaPage() {
  return (
    <Suspense fallback={<main className="mx-auto min-h-screen max-w-2xl p-6 sm:p-10">Carregando autorização…</main>}>
      <AutorizarAlexaConteudo />
    </Suspense>
  );
}

function AutorizarAlexaConteudo() {
  const searchParams = useSearchParams();
  const context = searchParams.get("context");
  const isAuthenticated = useAuthStore(state => state.isAuthenticated);
  const [authHydrated, setAuthHydrated] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const returnTo = `/integracoes/alexa/autorizar?context=${encodeURIComponent(context ?? "")}`;

  useEffect(() => {
    if (useAuthStore.persist.hasHydrated()) setAuthHydrated(true);
    return useAuthStore.persist.onFinishHydration(() => setAuthHydrated(true));
  }, []);

  const decide = async (approve: boolean) => {
    if (!context || busy) return;
    setBusy(true);
    setError(null);
    try {
      const { data } = await api.post<{ redirect_url: string }>("/integrations/alexa/oauth/consent", {
        context_id: context,
        approve,
      });
      window.location.assign(data.redirect_url);
    } catch {
      setError("Não foi possível concluir o vínculo. Volte ao aplicativo Alexa e tente novamente.");
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto min-h-screen max-w-2xl p-6 sm:p-10">
      <section className="mt-10 rounded-2xl border bg-card p-6 sm:p-8">
        <p className="text-sm font-medium uppercase tracking-widest text-primary">Fornada · Modo cozinha</p>
        <h1 className="mt-3 text-3xl font-bold">Vincular conta à Alexa</h1>
        <p className="mt-4 text-lg leading-relaxed text-muted-foreground">
          A skill poderá buscar receitas da sua conta e enviar a receita escolhida para uma estação de cozinha que você selecionar. Ela não altera receitas nem dados de produção.
        </p>
        {!context && <p role="alert" className="mt-5 rounded-xl border border-amber-300 bg-amber-50 p-4 text-amber-950">Pedido de autorização inválido. Inicie o vínculo pelo aplicativo Alexa.</p>}
        {error && <p role="alert" className="mt-5 rounded-xl border border-red-300 bg-red-50 p-4 text-red-900">{error}</p>}
        {!authHydrated && context && <p role="status" className="mt-7 rounded-xl bg-muted p-4">Verificando sua sessão Fornada…</p>}
        {authHydrated && !isAuthenticated && context && <div className="mt-7 rounded-xl bg-muted p-4">
          <p className="text-base">Entre na conta Fornada que contém suas receitas para revisar este acesso.</p>
          <Link href={`/login?next=${encodeURIComponent(returnTo)}`} className="mt-4 inline-flex min-h-12 items-center rounded-xl bg-primary px-5 font-semibold text-primary-foreground">Entrar na conta Fornada</Link>
        </div>}
        {authHydrated && isAuthenticated && <div className="mt-7 flex flex-col gap-3 sm:flex-row">
          <button type="button" disabled={!context || busy} onClick={() => void decide(true)} className="min-h-14 flex-1 rounded-xl bg-primary px-6 text-lg font-semibold text-primary-foreground disabled:opacity-50">
            {busy ? "Conectando…" : "Permitir acesso"}
          </button>
          <button type="button" disabled={!context || busy} onClick={() => void decide(false)} className="min-h-14 rounded-xl border px-6 text-lg font-semibold disabled:opacity-50">
            Não permitir
          </button>
        </div>}
      </section>
    </main>
  );
}
