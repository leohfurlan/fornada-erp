"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { pwaTipos, type PwaTipo } from "@/lib/pwa";

interface PwaConta {
  usuario_id: string; nome: string; email: string; negocio: string;
  sinais: Record<PwaTipo, { quantidade: number; ultimo_em: string | null }>;
}
const labels: Record<PwaTipo, string> = {
  convite_exibido: "Convite exibido", adiado: "Adiou a instalação", instalar_clicado: "Clicou em instalar",
  confirmacao_aceita: "Aceitou instalar", confirmacao_recusada: "Recusou a confirmação",
  instalacao_sinalizada: "Instalação sinalizada pelo navegador", acesso_app: "Acessou pelo aplicativo",
};
function usePwaContas(q: string, offset: number) {
  return useQuery({ queryKey: ["admin", "pwa", q, offset], queryFn: async () =>
    (await api.get<{ items: PwaConta[]; total: number; suggestions: string[] }>("/admin/pwa/usuarios", { params: { q, offset } })).data });
}
export function PwaAdmin({ q, offset, onSearchChange }: { q: string; offset: number; onSearchChange: (value: string) => void }) {
  const query = usePwaContas(q, offset);
  return <section aria-label="Adesão ao aplicativo" className="space-y-3 rounded-lg border p-4">
    <h2 className="text-lg font-semibold">Adesão ao aplicativo</h2>
    <p className="text-sm text-muted-foreground">Os sinais são independentes. Sem confirmação não significa que a pessoa não instalou. Não detectamos desinstalações.</p>
    {query.isLoading && <p>Carregando adesão...</p>}
    {query.isError && <p role="alert">Não foi possível carregar a adesão. <button className="underline" onClick={() => void query.refetch()}>Tentar novamente</button></p>}
    {query.data?.items.length === 0 && <p>Nenhuma conta encontrada.</p>}
    {query.data?.items.length === 0 && query.data.suggestions.length > 0 && <div className="text-sm">
      <p className="text-muted-foreground">Não encontrei uma correspondência. Você quis dizer:</p>
      <div className="flex flex-wrap gap-2">{query.data.suggestions.map((suggestion) => <button key={suggestion}
        type="button" className="text-primary underline" onClick={() => onSearchChange(suggestion)}>{suggestion}</button>)}</div>
    </div>}
    {query.data?.items.map((item) => <article key={item.usuario_id} className="space-y-2 border-t pt-3">
      <h3 className="font-medium break-words">{item.nome} · {item.negocio}</h3><p className="text-sm break-words">{item.email}</p>
      {!item.sinais.instalacao_sinalizada.quantidade && !item.sinais.acesso_app.quantidade && <p className="text-sm">Sem confirmação de instalação ou uso pelo aplicativo.</p>}
      <dl className="grid gap-2 text-sm sm:grid-cols-2">{pwaTipos.map((tipo) => <div key={tipo}>
        <dt className="text-muted-foreground">{labels[tipo]}</dt>
        <dd>{item.sinais[tipo].ultimo_em ? `${item.sinais[tipo].quantidade} registro(s) · ${new Date(item.sinais[tipo].ultimo_em!).toLocaleString("pt-BR")}` : "Sem registro"}</dd>
      </div>)}</dl>
    </article>)}
    {query.data && <p className="text-sm text-muted-foreground">{query.data.total} conta(s). Paginação compartilhada com a lista de contas.</p>}
  </section>;
}
