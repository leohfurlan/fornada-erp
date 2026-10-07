"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { DecimalInput } from "@/components/shared/decimal-input";
import { ProdutoCompraFields } from "@/components/shared/produto-compra-fields";
import { useIngredientes } from "@/hooks/use-estoque";
import { useFornecedoresCompra, useLerCompra, usePreverCompra, useProdutosCompra,
  useReconhecerCompra, useSalvarCompra } from "@/hooks/use-compras-comerciais";
import { custoCompra, dadosObservados, decimalCompra, erroCompras, produtoVazio, totalItem } from "@/lib/compras";
import { formatMoney } from "@/lib/utils";
import type { CompraRevisada, ItemLido, ItemRevisado, LeituraCompra, PreviaCompra,
  ProdutoDados, ResultadoCompra } from "@/types/compras";

interface ItemEdicao {
  origem: ItemLido;
  incluir: boolean;
  ingrediente_id: string;
  criar_novo: boolean;
  nome: string;
  tipo: string;
  unidade_principal: string;
  quantidade: string;
  unidade: string;
  custo_unitario: string;
  desconto_item: string;
  preco_total: string;
  modo_produto: "existente" | "novo" | "sem";
  produto_id: string;
  produto_novo: ProdutoDados;
  aprovar_produto: boolean;
  aprovar_fornecedor: boolean;
  aceitar_excecao: boolean;
  guardar_vinculo: boolean;
  escolha_manual: boolean;
}
const input = "w-full rounded-lg border bg-background px-3 py-2.5 text-sm";
const botao = "rounded-lg border px-3 py-2.5 text-sm disabled:opacity-50";
function editarItem(item: ItemLido): ItemEdicao {
  return { origem: item, incluir: true, ingrediente_id: item.ingrediente_id ?? "",
    criar_novo: false, nome: item.nome_match ?? "", tipo: item.tipo_sugerido,
    unidade_principal: item.unidade_sugerida, quantidade: item.quantidade ?? "",
    unidade: item.unidade ?? "", custo_unitario: item.preco_unitario ?? "",
    desconto_item: item.desconto_item ?? "0", preco_total: item.preco_total ?? "",
    modo_produto: item.produto_id ? "existente" : "novo", produto_id: item.produto_id ?? "",
    produto_novo: { ...produtoVazio(item.descricao), marca: item.marca_observada ?? "",
      fabricante: item.fabricante_observado, variante: item.variante_observada,
      conteudo_embalagem: item.conteudo_observado ?? "",
      unidade_conteudo: item.unidade_conteudo_observada ?? "kg" },
    aprovar_produto: false, aprovar_fornecedor: false, aceitar_excecao: false,
    guardar_vinculo: false, escolha_manual: false };
}
function itemManual(): ItemLido {
  return { indice: 0, descricao: "", quantidade: null, unidade: null, preco_unitario: null,
    preco_total: null, desconto_item: null, marca_observada: null, fabricante_observado: null,
    variante_observada: null, conteudo_observado: null, unidade_conteudo_observada: null,
    codigo_loja: null, gtin: null, gtin_confirmado: false, ingrediente_id: null,
    nome_match: null, produto_id: null, produto_revisao: null, reconhecimento: "nenhum",
    score: 0, explicacao: "Escolha o material e o produto.", pendencias: [], candidatos: [],
    vinculo_id: null, vinculo_revisao: null, tipo_sugerido: "ingrediente", unidade_sugerida: "kg" };
}
export default function CompraComercialPage() {
  const [etapa, setEtapa] = useState<"captura" | "revisao" | "concluido">("captura");
  const [itens, setItens] = useState<ItemEdicao[]>([]);
  const [leitura, setLeitura] = useState<LeituraCompra | null>(null);
  const [loja, setLoja] = useState("");
  const [fornecedor, setFornecedor] = useState("");
  const [cnpj, setCnpj] = useState("");
  const [data, setData] = useState("");
  const [identidade, setIdentidade] = useState("");
  const [identidadeConfirmada, setIdentidadeConfirmada] = useState(false);
  const [duplicidadeConfirmada, setDuplicidadeConfirmada] = useState(false);
  const [erro, setErro] = useState("");
  const [previa, setPrevia] = useState<{ dados: PreviaCompra; assinatura: string } | null>(null);
  const [resumo, setResumo] = useState<ResultadoCompra | null>(null);
  const tentativa = useRef<{ assinatura: string; chave: string } | null>(null);
  const versao = useRef(0);
  const sequenciaLoja = useRef(0);
  const arquivo = useRef<HTMLInputElement>(null);
  const ingredientes = useIngredientes();
  const produtos = useProdutosCompra();
  const fornecedores = useFornecedoresCompra();
  const ler = useLerCompra();
  const prever = usePreverCompra();
  const reconhecer = useReconhecerCompra();
  const salvar = useSalvarCompra();

  function invalidar() { versao.current += 1; setPrevia(null); setErro(""); }
  function atualizar(idx: number, patch: Partial<ItemEdicao>) {
    invalidar(); setItens((current) => current.map((it, pos) => pos === idx ? { ...it, ...patch } : it));
  }
  async function foto(file?: File) {
    if (!file) return;
    setErro("");
    try {
      const response = await ler.mutateAsync(file);
      invalidar(); tentativa.current = null;
      setLeitura(response); setItens(response.itens.map(editarItem));
      setLoja(response.estabelecimento ?? ""); setFornecedor(response.fornecedor_id ?? "");
      setCnpj(response.cnpj_observado ?? ""); setData(response.data_compra ?? "");
      setIdentidade(response.identidade_nota ?? ""); setIdentidadeConfirmada(false);
      setDuplicidadeConfirmada(false); setEtapa("revisao");
    } catch (e) { setErro(erroCompras(e)); }
  }
  async function escolherLoja(id: string) {
    invalidar(); setFornecedor(id);
    const seq = ++sequenciaLoja.current;
    if (!leitura) return;
    try {
      const response = await reconhecer.mutateAsync({ fornecedor_id: id || null,
        itens: itens.map((it) => dadosObservados(it.origem)) });
      if (seq !== sequenciaLoja.current) return;
      setItens((current) => current.map((it, idx) => {
        const sugestao = response.itens[idx];
        if (it.escolha_manual || !sugestao) return it;
        return { ...it, origem: sugestao, ingrediente_id: sugestao.ingrediente_id ?? "",
          produto_id: sugestao.produto_id ?? "",
          modo_produto: sugestao.produto_id ? "existente" : "novo" };
      }));
    } catch (e) { if (seq === sequenciaLoja.current) setErro(erroCompras(e)); }
  }
  const incluidos = itens.filter((it) => it.incluir);
  const payload: CompraRevisada = {
    estabelecimento: loja.trim() || null, data_compra: data || null,
    total_nota: leitura?.total_nota ?? null,
    fornecedor_id: fornecedor || null,
    fornecedor_novo: !fornecedor && loja.trim() ? { nome: loja.trim(), cnpj: cnpj.trim() || null } : null,
    identidade_nota: identidade.trim() || null, identidade_confirmada: identidadeConfirmada,
    confirmar_duplicidade: duplicidadeConfirmada, origem: leitura ? "web_ocr" : "web_manual",
    itens: incluidos.map((it): ItemRevisado => {
      const p = produtos.data?.find((prod) => prod.id === it.produto_id);
      return { ingrediente_id: it.criar_novo ? null : it.ingrediente_id || null,
        criar_novo: it.criar_novo, nome: it.nome || "Material", tipo: it.tipo,
        unidade_principal: it.criar_novo ? it.unidade_principal : null,
        descricao_original: it.origem.descricao, quantidade: it.quantidade,
        unidade: it.unidade, custo_unitario: it.custo_unitario, desconto_item: it.desconto_item || "0",
        preco_total: it.preco_total, produto_id: it.modo_produto === "existente" ? it.produto_id || null : null,
        produto_revisao: it.modo_produto === "existente" ? it.origem.produto_revisao ?? p?.revisao ?? null : null,
        produto_novo: it.modo_produto === "novo" ? it.produto_novo : null,
        codigo_loja: it.origem.codigo_loja, gtin_confirmado: it.origem.gtin_confirmado ? it.origem.gtin : null,
        aprovar_produto: it.aprovar_produto, aprovar_fornecedor: it.aprovar_fornecedor,
        aceitar_excecao: it.aceitar_excecao, guardar_vinculo: it.guardar_vinculo,
        conflito_vinculo: it.guardar_vinculo && it.origem.vinculo_id && it.origem.vinculo_revisao
          ? { id: it.origem.vinculo_id, revisao: it.origem.vinculo_revisao } : null };
    }),
  };
  const assinatura = JSON.stringify(payload);
  async function conferir() {
    setErro("");
    const current = versao.current;
    try {
      const result = await prever.mutateAsync(payload);
      if (current === versao.current) setPrevia({ dados: result, assinatura });
    } catch (e) { if (current === versao.current) setErro(erroCompras(e)); }
  }
  async function confirmar() {
    if (!previa?.dados.pode_confirmar || previa.assinatura !== assinatura) return;
    setErro("");
    if (tentativa.current?.assinatura !== assinatura) {
      tentativa.current = { assinatura, chave: crypto.randomUUID() };
    }
    try {
      const result = await salvar.mutateAsync({ payload, chave: tentativa.current.chave });
      setResumo(result); setEtapa("concluido");
    } catch (e) { setErro(erroCompras(e)); }
  }
  if (etapa === "concluido" && resumo) return <div className="space-y-5">
    <h1 className="text-xl font-bold">Compra registrada!</h1>
    <p>{resumo.ingredientes_atualizados} material(is) atualizado(s) e {resumo.ingredientes_criados} novo(s). Total: {formatMoney(resumo.total_selecionado)}.</p>
    <Link className="block text-primary" href={"/compras/historico?compra_id=" + resumo.compra_id}>Ver compra no histórico</Link>
    <Link className="block text-primary" href="/estoque">Ver estoque</Link>
    <button className={botao} onClick={() => { invalidar(); setEtapa("captura"); setResumo(null); tentativa.current = null; }}>Registrar outra compra</button>
  </div>;
  if (etapa === "captura") return <div className="space-y-5">
    <Link className="text-sm text-muted-foreground" href="/estoque">← Voltar</Link>
    <h1 className="text-xl font-bold">Entrada de compra</h1>
    <p className="text-sm text-muted-foreground">Fotografe o cupom e confira os produtos, quantidades e preços antes de salvar.</p>
    <input ref={arquivo} type="file" accept="image/*" capture="environment" className="hidden"
      aria-label="Foto do cupom" onChange={(e) => { void foto(e.target.files?.[0]); e.target.value = ""; }} />
    <button className="w-full rounded-xl border-2 border-dashed border-primary p-10 text-primary disabled:opacity-50"
      disabled={ler.isPending} onClick={() => arquivo.current?.click()}>{ler.isPending ? "Lendo o cupom..." : "Fotografar cupom ou escolher imagem"}</button>
    <button className={botao} onClick={() => {
      invalidar(); tentativa.current = null; setLeitura(null); setItens([editarItem(itemManual())]);
      setLoja(""); setFornecedor(""); setCnpj(""); setData(""); setIdentidade("");
      setIdentidadeConfirmada(false); setDuplicidadeConfirmada(false); setEtapa("revisao");
    }}>Registrar compra manualmente</button>
    {erro && <p role="alert" className="text-sm text-destructive">{erro}</p>}
    <Link href="/compras/historico" className="block text-primary">Histórico de compras</Link>
    <Link href="/compras/lista" className="block text-primary">Lista de compras</Link>
  </div>;
  return <div className="space-y-5 pb-8">
    <button className={botao} disabled={salvar.isPending} onClick={() => { invalidar(); sequenciaLoja.current += 1; setEtapa("captura"); }}>← Refazer ou cancelar</button>
    <h1 className="text-xl font-bold">Conferir itens</h1>
    <p className="text-sm text-muted-foreground">Vincule o produto comprado ao material da receita. Quantidade da nota e quantidade de estoque são conferidas separadamente.</p>
    {leitura?.aviso_mock && <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">Modo demonstração: itens de exemplo, sem leitura real.</p>}
    <fieldset disabled={salvar.isPending} className="space-y-5">
      <div className="space-y-3 rounded-xl border p-3">
        <label className="text-xs" htmlFor="loja-compra">Loja da compra</label>
        <select id="loja-compra" className={input} value={fornecedor} onChange={(e) => { void escolherLoja(e.target.value); }}>
          <option value="">Cadastrar loja ou manter desconhecida</option>
          {fornecedores.data?.map((f) => <option key={f.id} value={f.id}>{f.nome}{f.cnpj ? " · " + f.cnpj : ""}</option>)}
        </select>
        <label className="text-xs" htmlFor="nome-nota">Nome da loja na nota</label>
        <input id="nome-nota" className={input} value={loja} onChange={(e) => { invalidar(); setLoja(e.target.value); }} />
        {!fornecedor && <><label className="text-xs" htmlFor="cnpj-compra">CNPJ da loja (se conhecido)</label>
          <input id="cnpj-compra" className={input} value={cnpj} onChange={(e) => { invalidar(); setCnpj(e.target.value); }} /></>}
        <label className="text-xs" htmlFor="data-compra">Data da compra (deixe vazio se não identificada)</label>
        <input id="data-compra" type="date" className={input} value={data} onChange={(e) => { invalidar(); setData(e.target.value); }} />
        {leitura?.data_original && !leitura.data_compra && <p className="text-xs">Confira a data lida: {leitura.data_original}</p>}
        <details><summary className="text-xs">Identidade fiscal da nota</summary>
          <input className={input} aria-label="Chave fiscal" value={identidade} maxLength={44} onChange={(e) => { invalidar(); setIdentidade(e.target.value); setIdentidadeConfirmada(false); }} />
          <label className="flex gap-2 text-xs"><input type="checkbox" checked={identidadeConfirmada} onChange={(e) => { invalidar(); setIdentidadeConfirmada(e.target.checked); }} />Conferi a chave de 44 dígitos na nota</label>
        </details>
      </div>
      {itens.map((it, idx) => <article className="space-y-3 rounded-xl border p-3" key={idx}>
        <div className="flex justify-between gap-2"><p className="min-w-0 break-words font-medium">{it.origem.descricao || "Item manual"}</p>
          <label className="shrink-0 text-xs"><input type="checkbox" checked={it.incluir} onChange={(e) => atualizar(idx, { incluir: e.target.checked })} /> Incluir</label></div>
        {it.incluir && <>
          <p className="text-xs text-muted-foreground">{it.origem.explicacao}</p>
          {it.origem.pendencias.map((pendencia) => <p className="text-xs text-amber-800" key={pendencia}>{pendencia}</p>)}
          {!leitura && <><label htmlFor={"desc-" + idx} className="text-xs">Descrição do produto comprado</label>
            <input id={"desc-" + idx} className={input} value={it.origem.descricao} onChange={(e) => atualizar(idx, { origem: { ...it.origem, descricao: e.target.value } })} /></>}
          <label htmlFor={"material-" + idx} className="text-xs">Material das receitas</label>
          <select id={"material-" + idx} className={input} value={it.criar_novo ? "novo" : it.ingrediente_id}
            onChange={(e) => { const m = ingredientes.data?.find((ing) => ing.id === e.target.value);
              atualizar(idx, { ingrediente_id: m?.id ?? "", criar_novo: e.target.value === "novo",
                nome: m?.nome ?? "", tipo: m?.tipo ?? "ingrediente", unidade_principal: m?.unidade ?? "kg",
                produto_id: "", modo_produto: "novo", escolha_manual: true,
                origem: { ...it.origem, produto_revisao: null } }); }}>
            <option value="">Selecione um material existente...</option>
            {ingredientes.data?.map((m) => <option key={m.id} value={m.id}>{m.nome}</option>)}
            <option value="novo">Cadastrar novo material</option>
          </select>
          {it.criar_novo && <div className="space-y-2">
            <label className="text-xs" htmlFor={"nome-material-" + idx}>Nome do novo material</label>
            <input id={"nome-material-" + idx} className={input} value={it.nome} onChange={(e) => atualizar(idx, { nome: e.target.value })} />
            <select aria-label={"Tipo do material " + (idx + 1)} className={input} value={it.tipo} onChange={(e) => atualizar(idx, { tipo: e.target.value })}>
              {["ingrediente", "embalagem", "insumo", "descartavel", "outro"].map((tipo) => <option key={tipo}>{tipo}</option>)}</select>
            <input aria-label={"Unidade principal do material " + (idx + 1)} className={input} value={it.unidade_principal} placeholder="kg, g, ml, l ou un" onChange={(e) => atualizar(idx, { unidade_principal: e.target.value })} />
          </div>}
          <label htmlFor={"produto-" + idx} className="text-xs">Produto e embalagem comprados</label>
          <select id={"produto-" + idx} className={input}
            value={it.modo_produto === "existente" ? it.produto_id : it.modo_produto}
            onChange={(e) => { const p = produtos.data?.find((prod) => prod.id === e.target.value);
              atualizar(idx, { modo_produto: p ? "existente" : e.target.value === "sem" ? "sem" : "novo",
                produto_id: p?.id ?? "", escolha_manual: true,
                origem: { ...it.origem, produto_revisao: p?.revisao ?? null } }); }}>
            <option value="novo">Informar novo produto comercial</option>
            <option value="sem">Compra medida, sem produto identificado</option>
            {produtos.data?.filter((p) => p.ingrediente_id === it.ingrediente_id).map((p) => <option value={p.id} key={p.id}>{p.nome} · {p.marca} · {decimalCompra(p.conteudo_embalagem)} {p.unidade_conteudo}{!p.aprovado ? " (pendente)" : ""}</option>)}
          </select>
          {it.modo_produto === "novo" && <ProdutoCompraFields prefix={"compra-" + idx + "-"} value={it.produto_novo} onChange={(v) => atualizar(idx, { produto_novo: v })} />}
          <div className="grid grid-cols-2 gap-2">
            <div><label htmlFor={"qtd-" + idx} className="text-xs">Quantidade na nota</label>
              <DecimalInput id={"qtd-" + idx} value={it.quantidade} onChange={(v) => atualizar(idx, { quantidade: String(v), preco_total: totalItem(String(v), it.custo_unitario, it.desconto_item) })} /></div>
            <div><label htmlFor={"un-" + idx} className="text-xs">Unidade na nota</label>
              <input id={"un-" + idx} className={input} value={it.unidade} placeholder="un, kg, g..." onChange={(e) => atualizar(idx, { unidade: e.target.value })} /></div>
            <div><label htmlFor={"custo-" + idx} className="text-xs">Preço por unidade da nota (R$)</label>
              <DecimalInput id={"custo-" + idx} value={it.custo_unitario} onChange={(v) => atualizar(idx, { custo_unitario: String(v), preco_total: totalItem(it.quantidade, String(v), it.desconto_item) })} /></div>
            <div><label htmlFor={"desconto-" + idx} className="text-xs">Desconto deste item (R$)</label>
              <DecimalInput id={"desconto-" + idx} value={it.desconto_item} onChange={(v) => atualizar(idx, { desconto_item: String(v), preco_total: totalItem(it.quantidade, it.custo_unitario, String(v)) })} /></div>
          </div>
          <label htmlFor={"total-" + idx} className="text-xs">Total pago pelo item (R$)</label>
          <DecimalInput id={"total-" + idx} value={it.preco_total} onChange={(v) => atualizar(idx, { preco_total: String(v) })} />
          <details><summary className="text-xs">Código e identificação lidos</summary>
            <input className={input} aria-label={"Código da loja item " + (idx + 1)} value={it.origem.codigo_loja ?? ""} onChange={(e) => atualizar(idx, { origem: { ...it.origem, codigo_loja: e.target.value || null } })} />
            {it.origem.gtin && <label className="flex gap-2 text-xs"><input type="checkbox" checked={it.origem.gtin_confirmado} onChange={(e) => atualizar(idx, { origem: { ...it.origem, gtin_confirmado: e.target.checked } })} />Conferi que {it.origem.gtin} é o código universal da embalagem</label>}
          </details>
          <div className="space-y-2 rounded-lg bg-muted/30 p-3">
            <label className="flex gap-2 text-sm"><input type="checkbox" checked={it.aprovar_produto} disabled={it.aceitar_excecao}
              onChange={(e) => atualizar(idx, { aprovar_produto: e.target.checked })} />Aprovar este produto para o material</label>
            <label className="flex gap-2 text-sm"><input type="checkbox" checked={it.aprovar_fornecedor} disabled={it.aceitar_excecao}
              onChange={(e) => atualizar(idx, { aprovar_fornecedor: e.target.checked })} />Aprovar esta loja para este produto</label>
            <label className="flex gap-2 text-sm"><input type="checkbox" checked={it.guardar_vinculo} disabled={it.aceitar_excecao}
              onChange={(e) => atualizar(idx, { guardar_vinculo: e.target.checked })} />Guardar esta descrição/código para próximas compras nesta loja</label>
            <label className="flex gap-2 text-sm"><input type="checkbox" checked={it.aceitar_excecao}
              onChange={(e) => atualizar(idx, { aceitar_excecao: e.target.checked,
                ...(e.target.checked ? { aprovar_produto: false, aprovar_fornecedor: false, guardar_vinculo: false } : {}) })} />Registrar apenas esta compra, sem aprovação permanente</label>
          </div>
        </>}
      </article>)}
      {!leitura && <button className={botao} type="button" onClick={() => {
        invalidar(); const next = editarItem(itemManual()); next.origem.indice = itens.length; setItens([...itens, next]);
      }}>Adicionar item</button>}
      {previa && <div className="rounded-xl border border-primary p-3 space-y-3" aria-label="Prévia do estoque">
        <h2 className="font-medium">Conferência da entrada</h2>
        {previa.dados.itens.map((it) => <div key={it.indice} className="space-y-1">
          <p className="text-sm">{it.nome_material}: {decimalCompra(it.quantidade_principal)} {it.unidade_principal} no estoque</p>
          <p className="text-xs">{custoCompra(it.custo_normalizado)}/{it.unidade_principal} · total {formatMoney(it.preco_total)}</p>
          {it.pendencias.map((pendencia) => <p className="text-xs text-amber-800" key={pendencia}>{pendencia}</p>)}
        </div>)}
        {!!previa.dados.duplicidade.length && <div className="space-y-2 text-sm text-amber-800">
          <p>Esta nota já aparece no histórico. Confira antes de repetir.</p>
          {previa.dados.duplicidade.map((d) => <Link key={d.compra_id} className="block underline" href={"/compras/historico?compra_id=" + d.compra_id}>Ver compra anterior</Link>)}
        </div>}
      </div>}
      {duplicidadeConfirmada && <p className="text-xs text-amber-800">Você escolheu registrar outra compra com a mesma identidade fiscal.</p>}
      {(previa?.dados.duplicidade.length || duplicidadeConfirmada) ? <label className="flex gap-2 text-sm">
        <input type="checkbox" checked={duplicidadeConfirmada} onChange={(e) => { invalidar(); setDuplicidadeConfirmada(e.target.checked); }} />Conferi o histórico e quero repetir esta nota</label> : null}
    </fieldset>
    {erro && <p role="alert" className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{erro}</p>}
    <button className={botao + " w-full"} type="button" disabled={!incluidos.length || prever.isPending || salvar.isPending || reconhecer.isPending} onClick={conferir}>{prever.isPending ? "Conferindo..." : "Conferir entrada no estoque"}</button>
    <button className="w-full rounded-lg bg-primary px-4 py-3 text-primary-foreground disabled:opacity-50" type="button"
      disabled={!previa?.dados.pode_confirmar || previa.assinatura !== assinatura || salvar.isPending} onClick={confirmar}>
      {salvar.isPending ? "Salvando..." : "Salvar compra"}
    </button>
  </div>;
}
