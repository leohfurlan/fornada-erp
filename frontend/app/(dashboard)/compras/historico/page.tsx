"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useIngredientes } from "@/hooks/use-estoque";
import { useDetalheCompra, useFornecedoresCompra, useHistoricoCompras } from "@/hooks/use-compras-comerciais";
import { custoCompra, dataCompra, decimalCompra, erroCompras } from "@/lib/compras";
import { formatMoney } from "@/lib/utils";

const input = "w-full rounded-lg border bg-background px-3 py-2.5 text-sm";
function Historico() {
  const params = useSearchParams();
  const [material, setMaterial] = useState(params.get("ingrediente_id") ?? "");
  const [fornecedor, setFornecedor] = useState("");
  const [marca, setMarca] = useState("");
  const [inicio, setInicio] = useState("");
  const [fim, setFim] = useState("");
  const [offset, setOffset] = useState(0);
  const [selecionada, setSelecionada] = useState(params.get("compra_id") ?? "");
  const materiais = useIngredientes();
  const lojas = useFornecedoresCompra();
  const historico = useHistoricoCompras({ ingrediente_id: material || undefined,
    fornecedor_id: fornecedor || undefined, marca: marca || undefined,
    data_inicio: inicio || undefined, data_fim: fim || undefined, limit: 20, offset });
  const detalhe = useDetalheCompra(selecionada);
  function filtrar(set: (value: string) => void, value: string) { set(value); setOffset(0); }
  return <div className="space-y-5 pb-8">
    <Link className="text-sm text-muted-foreground" href="/compras">← Compras</Link>
    <h1 className="text-xl font-bold">Histórico de compras</h1>
    <p className="text-sm text-muted-foreground">Consulte o que você comprou e pagou. Os preços são das compras registradas.</p>
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <div><label className="text-xs" htmlFor="hist-material">Material</label>
        <select id="hist-material" className={input} value={material} onChange={(e) => filtrar(setMaterial, e.target.value)}>
          <option value="">Todos os materiais</option>{materiais.data?.map((m) => <option key={m.id} value={m.id}>{m.nome}</option>)}</select></div>
      <div><label className="text-xs" htmlFor="hist-loja">Loja</label>
        <select id="hist-loja" className={input} value={fornecedor} onChange={(e) => filtrar(setFornecedor, e.target.value)}>
          <option value="">Todas as lojas</option>{lojas.data?.map((l) => <option key={l.id} value={l.id}>{l.nome}</option>)}</select></div>
      <div><label className="text-xs" htmlFor="hist-marca">Marca</label><input id="hist-marca" className={input} value={marca} onChange={(e) => filtrar(setMarca, e.target.value)} /></div>
      <div className="grid grid-cols-2 gap-2">
        <div><label className="text-xs" htmlFor="hist-inicio">Data inicial</label><input id="hist-inicio" className={input} type="date" value={inicio} onChange={(e) => filtrar(setInicio, e.target.value)} /></div>
        <div><label className="text-xs" htmlFor="hist-fim">Data final</label><input id="hist-fim" className={input} type="date" value={fim} onChange={(e) => filtrar(setFim, e.target.value)} /></div>
      </div>
    </div>
    {(inicio || fim) && <p className="text-xs text-muted-foreground">Compras sem data identificada ficam fora do filtro de período.</p>}
    {historico.error && <p role="alert" className="text-sm text-destructive">{erroCompras(historico.error)}</p>}
    {historico.isLoading && <p>Carregando compras...</p>}
    {historico.data?.itens.map((compra) => <button type="button" key={compra.id} onClick={() => setSelecionada(compra.id)}
      className="w-full rounded-xl border p-3 text-left space-y-1">
      <p className="break-words font-medium">{compra.fornecedor_nome_snapshot ?? compra.estabelecimento_original ?? "Loja não identificada"}</p>
      <p className="text-sm">{dataCompra(compra.data_compra)} · {formatMoney(compra.total_selecionado)} · {compra.quantidade_itens} item(ns)</p>
      {!compra.metadados_completos && <p className="text-xs text-muted-foreground">Alguns dados comerciais não foram informados.</p>}
    </button>)}
    {!historico.isLoading && historico.data?.total === 0 && <p className="text-sm text-muted-foreground">Nenhuma compra encontrada.</p>}
    {historico.data && historico.data.total > 0 && <div className="flex items-center justify-between gap-2">
      <button className="rounded-lg border p-2 text-sm disabled:opacity-40" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 20))}>Anterior</button>
      <span className="text-xs">{offset + 1}–{Math.min(offset + 20, historico.data.total)} de {historico.data.total}</span>
      <button className="rounded-lg border p-2 text-sm disabled:opacity-40" disabled={offset + 20 >= historico.data.total} onClick={() => setOffset(offset + 20)}>Próxima</button>
    </div>}
    {selecionada && <section className="rounded-xl border border-primary p-3 space-y-3" aria-label="Detalhes da compra">
      <h2 className="font-semibold">Detalhes da compra</h2>
      {detalhe.error && <p role="alert" className="text-sm text-destructive">{erroCompras(detalhe.error)}</p>}
      {detalhe.isLoading && <p>Carregando detalhes...</p>}
      {detalhe.data && <>
        <p className="text-sm break-words">{detalhe.data.fornecedor_nome_snapshot ?? detalhe.data.estabelecimento_original ?? "Loja não identificada"} · {dataCompra(detalhe.data.data_compra)}</p>
        <p className="text-xs text-muted-foreground">Registrada em {new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short", timeZone: "America/Sao_Paulo" }).format(new Date(detalhe.data.data_registro))} · {detalhe.data.origem}</p>
        {detalhe.data.itens.map((it) => <article className="border-t pt-3 space-y-1" key={it.id}>
          <p className="font-medium break-words">{it.snapshot.nome_material}</p>
          <p className="text-sm break-words">{it.snapshot.nome_produto ?? "Produto não identificado"} · Marca: {it.snapshot.marca ?? "não informada"}</p>
          <p className="text-xs">Variante: {it.snapshot.variante ?? "não informada"} · Fabricante: {it.snapshot.fabricante ?? "não informado"}</p>
          {it.snapshot.descricao_original && <p className="text-xs break-words">Na nota: {it.snapshot.descricao_original}</p>}
          {it.snapshot.quantidade_original && it.snapshot.unidade_original && <p className="text-sm">Compra: {decimalCompra(it.snapshot.quantidade_original)} {it.snapshot.unidade_original} · {it.snapshot.custo_unitario_original ? formatMoney(it.snapshot.custo_unitario_original) : "Preço original não identificado"}/unidade da nota</p>}
          {it.snapshot.conteudo_embalagem && <p className="text-xs">Embalagem: {decimalCompra(it.snapshot.conteudo_embalagem)} {it.snapshot.unidade_conteudo}</p>}
          <p className="text-sm">Estoque: {decimalCompra(it.quantidade_principal)} {it.snapshot.unidade_principal}</p>
          <p className="text-sm">Preço comparável: {custoCompra(it.custo_normalizado)}/{it.snapshot.unidade_principal} · Total: {formatMoney(it.preco_total)}</p>
          {it.snapshot.aprovacao_excepcional && <p className="text-xs text-amber-800">Compra excepcional, sem aprovação permanente.</p>}
        </article>)}
      </>}
      <button type="button" className="rounded-lg border px-3 py-2 text-sm" onClick={() => setSelecionada("")}>Fechar detalhes</button>
    </section>}
  </div>;
}
export default function HistoricoComprasPage() {
  return <Suspense fallback={<p>Carregando histórico...</p>}><Historico /></Suspense>;
}
