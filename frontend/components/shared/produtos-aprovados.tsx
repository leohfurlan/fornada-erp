"use client";

import { useState } from "react";
import Link from "next/link";
import { ProdutoCompraFields } from "@/components/shared/produto-compra-fields";
import { useCatalogoCompra, useFornecedoresCompra, useProdutosCompra, useVinculosCompra } from "@/hooks/use-compras-comerciais";
import { decimalCompra, erroCompras, produtoVazio } from "@/lib/compras";
import type { FornecedorCompra, ProdutoCompra, ProdutoDados } from "@/types/compras";

const input = "w-full rounded-lg border bg-background px-3 py-2.5 text-sm";
const button = "rounded-lg border px-3 py-2 text-sm disabled:opacity-50";
export function ProdutosAprovados({ ingredienteId }: { ingredienteId: string }) {
  const produtos = useProdutosCompra();
  const fornecedores = useFornecedoresCompra();
  const vinculos = useVinculosCompra();
  const gravar = useCatalogoCompra();
  const [produto, setProduto] = useState<ProdutoDados>(produtoVazio());
  const [editando, setEditando] = useState<ProdutoCompra | null>(null);
  const [aberto, setAberto] = useState(false);
  const [aprovado, setAprovado] = useState(true);
  const [lojas, setLojas] = useState<string[]>([]);
  const [loja, setLoja] = useState({ nome: "", cnpj: "" });
  const [editandoLoja, setEditandoLoja] = useState<FornecedorCompra | null>(null);
  const [mensagem, setMensagem] = useState("");
  const [erro, setErro] = useState("");
  const [correcoes, setCorrecoes] = useState<Record<string, string>>({});
  const meusProdutos = produtos.data?.filter((p) => p.ingrediente_id === ingredienteId) ?? [];
  const ids = meusProdutos.map((p) => p.id);
  const meusVinculos = vinculos.data?.filter((v) => ids.includes(v.produto_id)) ?? [];

  async function executar(action: Parameters<typeof gravar.mutateAsync>[0]) {
    setErro(""); setMensagem("");
    try { await gravar.mutateAsync(action); setMensagem("Cadastro atualizado."); return true; }
    catch (e) { setErro(erroCompras(e)); return false; }
  }
  function editar(p: ProdutoCompra) {
    setEditando(p); setProduto({ nome: p.nome, marca: p.marca, fabricante: p.fabricante,
      variante: p.variante, conteudo_embalagem: p.conteudo_embalagem,
      unidade_conteudo: p.unidade_conteudo, fator_para_principal: p.fator_para_principal, gtin: p.gtin });
    setAprovado(p.aprovado); setLojas(p.fornecedores_aprovados); setAberto(true);
  }
  async function salvarProduto() {
    const dados = { ...produto, aprovado, fornecedores_aprovados: lojas,
      ...(editando ? { revisao: editando.revisao } : { ingrediente_id: ingredienteId }) };
    if (await executar({ recurso: "produtos", id: editando?.id, dados })) {
      setAberto(false); setEditando(null); setProduto(produtoVazio()); setLojas([]);
    }
  }
  async function salvarLoja() {
    const dados = { nome: loja.nome, cnpj: loja.cnpj || null,
      ...(editandoLoja ? { revisao: editandoLoja.revisao } : {}) };
    if (await executar({ recurso: "fornecedores", id: editandoLoja?.id, dados })) {
      setLoja({ nome: "", cnpj: "" }); setEditandoLoja(null);
    }
  }
  return <section className="space-y-4 border-t pt-5">
    <div><h2 className="font-semibold">Produtos aprovados</h2>
      <p className="text-sm text-muted-foreground">Marcas e embalagens que você usa neste material. O cadastro não muda seu estoque.</p></div>
    {(produtos.error || fornecedores.error || vinculos.error) && <p role="alert" className="text-sm text-destructive">Não foi possível carregar os cadastros de compras.</p>}
    {mensagem && <p role="status" className="text-sm text-green-700">{mensagem}</p>}
    {erro && <p role="alert" className="text-sm text-destructive">{erro}</p>}
    {meusProdutos.map((p) => <article className="rounded-xl border p-3 space-y-2" key={p.id}>
      <p className="font-medium break-words">{p.nome} · {p.marca}</p>
      <p className="text-sm">{p.variante ?? "Variante não informada"} · {decimalCompra(p.conteudo_embalagem)} {p.unidade_conteudo} por embalagem</p>
      <p className="text-xs text-muted-foreground">{p.aprovado ? "Aprovado para este material" : "Aprovação pendente"} · Fabricante: {p.fabricante ?? "não informado"}</p>
      <div className="flex flex-wrap gap-2">
        <button type="button" className={button} onClick={() => editar(p)}>Editar {p.marca}</button>
        <button type="button" className={button} disabled={gravar.isPending} onClick={async () => {
          if (confirm("Inativar este produto? O histórico será preservado.")) {
            await executar({ recurso: "produtos", id: p.id, revisao: p.revisao, remover: true });
          }
        }}>Inativar</button>
      </div>
    </article>)}
    {!produtos.isLoading && !meusProdutos.length && <p className="text-sm text-muted-foreground">Nenhum produto comercial cadastrado.</p>}
    <button type="button" className={button} onClick={() => {
      setEditando(null); setProduto(produtoVazio()); setLojas([]); setAprovado(true); setAberto(true);
    }}>Adicionar produto aprovado</button>
    {aberto && <div className="rounded-xl border p-3 space-y-3">
      <h3 className="font-medium">{editando ? "Editar produto" : "Novo produto para compra"}</h3>
      <ProdutoCompraFields prefix="cadastro-produto-" value={produto} onChange={setProduto} />
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={aprovado} onChange={(e) => setAprovado(e.target.checked)} />Produto aprovado para este material</label>
      <fieldset className="space-y-2"><legend className="text-sm font-medium">Lojas aprovadas para este produto</legend>
        {fornecedores.data?.map((f) => <label className="flex items-center gap-2 text-sm" key={f.id}>
          <input type="checkbox" checked={lojas.includes(f.id)} onChange={(e) => setLojas(e.target.checked ? [...lojas, f.id] : lojas.filter((id) => id !== f.id))} />
          <span>{f.nome}{f.cnpj ? " · " + f.cnpj : ""}</span></label>)}
        {!fornecedores.data?.length && <p className="text-xs">Cadastre uma loja abaixo ou aprove na próxima compra.</p>}
      </fieldset>
      <div className="flex gap-2"><button type="button" className={button} disabled={gravar.isPending} onClick={salvarProduto}>Salvar produto</button>
        <button type="button" className={button} onClick={() => setAberto(false)}>Cancelar edição</button></div>
    </div>}
    <details className="rounded-xl border p-3 space-y-3"><summary className="cursor-pointer text-sm font-medium">Lojas e fornecedores da sua conta</summary>
      <div className="space-y-2 pt-3">
        <label className="text-xs" htmlFor="cadastro-loja-nome">Nome da loja</label>
        <input id="cadastro-loja-nome" className={input} value={loja.nome} onChange={(e) => setLoja({ ...loja, nome: e.target.value })} />
        <label className="text-xs" htmlFor="cadastro-loja-cnpj">CNPJ (se conhecido)</label>
        <input id="cadastro-loja-cnpj" className={input} value={loja.cnpj} onChange={(e) => setLoja({ ...loja, cnpj: e.target.value })} />
        <button type="button" className={button} disabled={gravar.isPending} onClick={salvarLoja}>{editandoLoja ? "Salvar loja" : "Cadastrar loja"}</button>
        {editandoLoja && <button type="button" className={button} onClick={() => { setEditandoLoja(null); setLoja({ nome: "", cnpj: "" }); }}>Cancelar edição da loja</button>}
        {fornecedores.data?.map((f) => <div key={f.id} className="border-t pt-2 space-y-1">
          <p className="text-sm break-words">{f.nome} · {f.cnpj ?? "CNPJ não informado"}</p>
          <div className="flex gap-2">
            <button type="button" className={button} onClick={() => { setEditandoLoja(f); setLoja({ nome: f.nome, cnpj: f.cnpj ?? "" }); }}>Editar loja</button>
            <button type="button" className={button} disabled={gravar.isPending} onClick={async () => {
              if (confirm("Inativar esta loja? As compras anteriores serão preservadas.")) {
                await executar({ recurso: "fornecedores", id: f.id, revisao: f.revisao, remover: true });
              }
            }}>Inativar loja</button>
          </div></div>)}
      </div>
    </details>
    {!!meusVinculos.length && <details className="rounded-xl border p-3">
      <summary className="cursor-pointer text-sm font-medium">Descrições e códigos já confirmados</summary>
      {meusVinculos.map((v) => <div className="space-y-2 border-t py-3" key={v.id}>
        <p className="text-sm break-words">{v.valor_original}</p>
        <p className="text-xs text-muted-foreground">{fornecedores.data?.find((f) => f.id === v.fornecedor_id)?.nome ?? "Loja inativa"} · {v.tipo === "codigo_loja" ? "Código desta loja" : "Descrição da nota"}</p>
        <select aria-label={"Corrigir destino de " + v.valor_original} className={input}
          value={correcoes[v.id] ?? v.produto_id} onChange={(e) => setCorrecoes({ ...correcoes, [v.id]: e.target.value })}>
          {produtos.data?.map((p) => <option value={p.id} key={p.id}>{p.nome} · {p.marca}</option>)}
        </select>
        <div className="flex gap-2">
          <button type="button" className={button} disabled={gravar.isPending} onClick={async () => {
            const target = produtos.data?.find((p) => p.id === (correcoes[v.id] ?? v.produto_id));
            if (target) await executar({ recurso: "vinculos", id: v.id, dados: {
              revisao: v.revisao, produto_id: target.id, produto_revisao: target.revisao } });
          }}>Confirmar correção</button>
          <button type="button" className={button} disabled={gravar.isPending} onClick={async () => {
            if (confirm("Remover esta associação? O histórico será preservado.")) {
              await executar({ recurso: "vinculos", id: v.id, revisao: v.revisao, remover: true });
            }
          }}>Remover associação</button>
        </div>
      </div>)}
    </details>}
    <Link className="block text-sm text-primary" href={"/compras/historico?ingrediente_id=" + ingredienteId}>Ver compras deste material</Link>
  </section>;
}
