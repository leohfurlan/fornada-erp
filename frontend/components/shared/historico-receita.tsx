"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { MarkdownContent } from "@/components/shared/markdown-content";
import { formatDataHora, formatQuantidade } from "@/lib/utils";

interface Versao {
  versao: number;
  created_at: string;
  responsavel: string | null;
  origem: string;
  snapshot: {
    nome: string; categoria: string; rendimento: string; rendimento_unidade: string;
    modo_preparo: string | null;
    ingredientes: { nome: string; quantidade: string; unidade: string }[];
    etapas: { nome: string; duracao_minutos: number }[];
    ficha_tecnica: { descricao_produto?: string; especificacao_final?: string;
      passos?: { descricao: string; quantidade?: string; unidade: string; instrucao?: string; especificacao?: string }[] } | null;
  };
}

export function HistoricoReceita({ id }: { id: string }) {
  const [pagina, setPagina] = useState(0);
  const { data, isPending, isError } = useQuery<Versao[]>({
    queryKey: ["receita-versoes", id, pagina],
    queryFn: async () => (await api.get(`/receitas/${id}/versoes`, {
      params: { offset: pagina * 20, limit: 20 },
    })).data,
  });
  return <section className="space-y-3 rounded-xl border p-4">
    <h2 className="font-semibold">Histórico de versões</h2>
    {isPending && <p>Carregando histórico...</p>}
    {isError && <p role="alert">Não foi possível carregar o histórico.</p>}
    {data?.length === 0 && <p className="text-sm text-muted-foreground">O histórico será registrado a partir da próxima edição.</p>}
    {data?.map((item) => <details key={item.versao} className="rounded-lg border p-3">
      <summary className="cursor-pointer text-sm">Versão {item.versao} · {formatDataHora(item.created_at)} · {item.responsavel ?? "Responsável não registrado"}
        {item.origem === "base_anterior" && " · Conteúdo anterior à primeira edição registrada"}
      </summary>
      <div className="mt-3 space-y-3 text-sm">
        <p className="font-medium">{item.snapshot.nome}</p>
        <p>{item.snapshot.categoria} · Rendimento: {formatQuantidade(item.snapshot.rendimento)} {item.snapshot.rendimento_unidade}</p>
        <h3 className="font-medium">Ingredientes</h3>
        <ul>{item.snapshot.ingredientes.map((i, n) => <li key={n}>{formatQuantidade(i.quantidade)} {i.unidade} — {i.nome}</li>)}</ul>
        <h3 className="font-medium">Preparo</h3>
        <MarkdownContent children={item.snapshot.modo_preparo ?? ""} />
        <ol>{item.snapshot.etapas.map((e, n) => <li key={n}>{n + 1}. {e.nome} · {formatQuantidade(e.duracao_minutos)} min</li>)}</ol>
        {item.snapshot.ficha_tecnica && <>
          <h3 className="font-medium">Montagem</h3>
          <MarkdownContent children={item.snapshot.ficha_tecnica.descricao_produto ?? ""} />
          <MarkdownContent children={item.snapshot.ficha_tecnica.especificacao_final ?? ""} />
          <ol>{item.snapshot.ficha_tecnica.passos?.map((p, n) => <li key={n} className="mb-2">
            <p>{n + 1}. {formatQuantidade(p.quantidade)} {p.unidade} — {p.descricao}</p>
            <MarkdownContent children={p.especificacao ?? ""} />
            <MarkdownContent children={p.instrucao ?? ""} />
          </li>)}</ol>
        </>}
      </div>
    </details>)}
    <div className="flex gap-3 text-sm">
      <button disabled={pagina === 0 || isPending} onClick={() => setPagina(pagina - 1)}>Mais recentes</button>
      <button disabled={!data || data.length < 20 || isPending} onClick={() => setPagina(pagina + 1)}>Mais antigas</button>
    </div>
  </section>;
}
