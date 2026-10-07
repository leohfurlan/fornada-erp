"use client";

import { useRef, useState } from "react";
import { AxiosError } from "axios";
import * as Dialog from "@radix-ui/react-dialog";
import { useAuthStore } from "@/stores/use-auth-store";
import { iniciarSuporte, useContasAdmin } from "@/hooks/use-admin";
import { setSupportSession } from "@/lib/admin-session";
import type { ContaAdmin } from "@/lib/admin-session";

export default function AdminPage() {
  const { usuario } = useAuthStore();
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);
  const [conta, setConta] = useState<ContaAdmin | null>(null);
  const [motivo, setMotivo] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const motivoRef = useRef<HTMLTextAreaElement>(null);
  const acessoRef = useRef<HTMLButtonElement | null>(null);
  const { data, isLoading, isError } = useContasAdmin(q, offset, Boolean(usuario?.is_superuser));

  if (!usuario?.is_superuser) return <p>Acesso exclusivo da administração.</p>;

  async function acessar() {
    if (!conta || !usuario || busy) return;
    setBusy(true);
    setError("");
    try {
      const session = await iniciarSuporte(conta.id, motivo.trim());
      setSupportSession({ ...session, operador_id: usuario.id });
      // Recarrega toda a aplicação para descartar consultas e formulários da conta anterior.
      window.location.assign("/");
    } catch (err) {
      setError(err instanceof AxiosError ? err.response?.data?.detail ?? "Não foi possível abrir a conta." : "Não foi possível abrir a conta.");
      setBusy(false);
    }
  }

  return <div className="space-y-5">
    <div><h1 className="text-2xl font-bold">Administração</h1><p className="text-muted-foreground">Acesse uma conta para prestar suporte. As ações serão atribuídas a você.</p></div>
    <label className="block">Buscar nome, e-mail ou negócio
      <input className="mt-1 w-full rounded border p-3" value={q} onChange={(e) => { setQ(e.target.value); setOffset(0); }} />
    </label>
    {isLoading && <p>Carregando contas...</p>}
    {isError && <p role="alert">Não foi possível carregar as contas. Atualize a página.</p>}
    {data?.length === 0 && <p>Nenhuma conta encontrada.</p>}
    <div className="space-y-3">{data?.map((item) => <article key={item.id} className="rounded-lg border p-4 space-y-2">
      <h2 className="font-semibold break-words">{item.negocio}</h2>
      <p className="break-words">{item.nome} · {item.email}</p>
      <p className="text-sm text-muted-foreground">{item.is_superuser ? "Administrador da plataforma" : item.ativo ? "Conta ativa" : "Conta desativada"}</p>
      {!item.is_superuser && item.ativo && <button className="rounded bg-primary px-4 py-2 text-primary-foreground" onClick={(event) => { acessoRef.current = event.currentTarget; setConta(item); setMotivo(""); setError(""); }}>Acessar conta</button>}
    </article>)}</div>
    <div className="flex gap-4">
      <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 50))}>Anterior</button>
      <button disabled={!data || data.length < 50} onClick={() => setOffset(offset + 50)}>Próxima</button>
    </div>
    <Dialog.Root open={conta !== null} onOpenChange={(open) => { if (!open && !busy) setConta(null); }}>
      {conta && <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40" />
        <Dialog.Content
          className="fixed left-1/2 top-4 z-50 max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 overflow-y-auto rounded-xl border bg-background p-5 shadow-xl sm:top-8 sm:p-6"
          aria-busy={busy}
          onOpenAutoFocus={(event) => { event.preventDefault(); motivoRef.current?.focus(); }}
          onCloseAutoFocus={(event) => { event.preventDefault(); acessoRef.current?.focus(); }}
          onEscapeKeyDown={(event) => { if (busy) event.preventDefault(); }}
          onInteractOutside={(event) => { if (busy) event.preventDefault(); }}
        >
          <div className="space-y-4">
            <Dialog.Title className="text-lg font-semibold break-words">Acessar {conta.negocio}</Dialog.Title>
            <Dialog.Description className="text-sm text-muted-foreground break-words">
              {conta.email}. Você poderá consultar e alterar dados desta conta durante 15 minutos.
            </Dialog.Description>
            <label className="block">Motivo do suporte
              <textarea ref={motivoRef} rows={3} className="mt-1 w-full rounded border p-3" maxLength={500} value={motivo} onChange={(e) => setMotivo(e.target.value)} />
            </label>
            {error && <p role="alert">{error}</p>}
            <div className="flex flex-wrap gap-3">
              <button disabled={busy || motivo.trim().length < 5} className="rounded bg-primary px-4 py-2 text-primary-foreground disabled:opacity-50" onClick={acessar}>{busy ? "Abrindo conta..." : "Confirmar acesso"}</button>
              <Dialog.Close asChild><button disabled={busy} className="rounded border px-4 py-2">Cancelar</button></Dialog.Close>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>}
    </Dialog.Root>
  </div>;
}
