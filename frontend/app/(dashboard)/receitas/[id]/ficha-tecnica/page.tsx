"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { AxiosError } from "axios";
import { useReceitas } from "@/hooks/use-receitas";
import { useIngredientes } from "@/hooks/use-estoque";
import { formatQuantidade } from "@/lib/utils";
import { sanitizeDecimalInput } from "@/lib/decimal";
import { MoneyDisplay } from "@/components/shared/money-display";
import { useConsumoComposicao } from "@/hooks/use-ficha-tecnica";
import { useFichaTecnica, useSalvarFichaTecnica, type FichaTecnica, type PassoMontagem } from "@/hooks/use-ficha-tecnica";

const campo = "w-full rounded-lg border bg-background p-2 text-sm";
function QuantidadeCampo({ value, onChange, required = false }: { value: string | null; onChange: (valor: string | null) => void; required?: boolean }) {
  return <input required={required} inputMode="decimal" pattern="[0-9]+([,.][0-9]{1,4})?" className={campo} value={(value ?? "").replace(".", ",")} onChange={e => onChange(sanitizeDecimalInput(e.target.value).replace(",", ".") || null)} />;
}
export default function FichaPage() {
  const { id } = useParams<{ id: string }>();
  return <Editor key={id} id={id} />;
}
function Editor({ id }: { id: string }) {
  const consulta = useFichaTecnica(id);
  const salvar = useSalvarFichaTecnica(id);
  const receitas = useReceitas();
  const materiais = useIngredientes();
  const consumo = useConsumoComposicao(id);
  const [ficha, setFicha] = useState<FichaTecnica | null>(null);
  const [mensagem, setMensagem] = useState("");
  useEffect(() => { if (consulta.data && !ficha) setFicha(consulta.data); }, [consulta.data, ficha]);
  if (consulta.isError) return <p role="alert">Não foi possível carregar a ficha técnica.</p>;
  if (!ficha) return <p>Carregando ficha técnica...</p>;
  const editar = (index: number, patch: Partial<PassoMontagem>) => setFicha({ ...ficha, passos: ficha.passos.map((p, i) => i === index ? { ...p, ...patch } : p) });
  const mover = (index: number, destino: number) => {
    const passos = [...ficha.passos];
    [passos[index], passos[destino]] = [passos[destino], passos[index]];
    setFicha({ ...ficha, passos });
  };
  return <form className="mx-auto max-w-3xl space-y-5 pb-8" onSubmit={async (event) => {
    event.preventDefault(); setMensagem("");
    try { const data = await salvar.mutateAsync(ficha); setFicha(data); setMensagem("Ficha técnica salva."); }
    catch (error) {
      const detail = error instanceof AxiosError ? error.response?.data?.detail : undefined;
      setMensagem(typeof detail === "string" ? detail : "Não foi possível salvar. Confira as quantidades e os limites informados.");
    }
  }}>
    <Link href={`/receitas/${id}`} className="text-sm text-primary">← Voltar à receita</Link>
    <h1 className="text-xl font-bold">Ficha técnica do produto</h1>
    <p className="text-sm text-muted-foreground">Descreva uma unidade do produto na ordem de montagem. Vincule receitas-base, ingredientes e embalagens para calcular custos e consumir o estoque de componentes prontos.</p>
    <label className="flex items-start gap-2"><input type="checkbox" checked={!!ficha.composicao_ativa} onChange={e => setFicha({ ...ficha, composicao_ativa: e.target.checked })} />Produto final - Usar montagem com materiais listados para calcular custo.</label>
    {ficha.composicao_ativa && <p className="text-sm text-muted-foreground">O custo usa os componentes abaixo e o tempo de montagem da receita. A lista antiga de ingredientes é preservada, mas não é somada novamente.</p>}
    {consulta.data?.composicao_ativa && <section className="space-y-2 rounded-xl bg-muted/40 p-4">
      <h2 className="font-semibold">Composição salva — por fornada</h2>
      {consumo.data?.map(item => <p key={item.id} className="flex flex-wrap justify-between gap-2 text-sm"><span>{item.nome}</span><strong>{formatQuantidade(item.quantidade_por_fornada)} {item.unidade}</strong></p>)}
      {consumo.isError && <p className="text-sm text-destructive">Não foi possível consultar o consumo salvo.</p>}
      {receitas.data?.find(r => r.id === id)?.custo && <p className="text-sm">Custo salvo por unidade de rendimento: <MoneyDisplay value={receitas.data.find(r => r.id === id)?.custo?.custo_por_unidade} /></p>}
      <p className="text-xs text-muted-foreground">Este resumo é atualizado ao salvar. As camadas continuam separadas na montagem.</p>
    </section>}
    <label className="block">Descrição do produto<textarea required maxLength={2000} className={campo} value={ficha.descricao_produto} onChange={e => setFicha({ ...ficha, descricao_produto: e.target.value })} /></label>
    <label className="block">Apresentação final e dimensões<textarea maxLength={1000} className={campo} value={ficha.especificacao_final} onChange={e => setFicha({ ...ficha, especificacao_final: e.target.value })} /></label>
    <ol className="space-y-4">{ficha.passos.map((passo, index) => <li key={index} className="space-y-3 rounded-xl border p-4">
      <div className="flex flex-wrap items-center gap-3"><strong>Etapa {index + 1}</strong>
        <button type="button" disabled={index === 0} onClick={() => mover(index, index - 1)} aria-label={`Subir etapa ${index + 1}`}>↑</button>
        <button type="button" disabled={index === ficha.passos.length - 1} onClick={() => mover(index, index + 1)} aria-label={`Descer etapa ${index + 1}`}>↓</button>
        <button type="button" className="text-destructive" onClick={() => { if (confirm("Remover esta etapa?")) setFicha({ ...ficha, passos: ficha.passos.filter((_, i) => i !== index) }); }}>Remover</button>
      </div>
      <label className="block">Tipo<select className={campo} value={passo.tipo} onChange={e => editar(index, { tipo: e.target.value as PassoMontagem["tipo"] })}>{["componente", "ingrediente", "embalagem", "acabamento"].map(tipo => <option key={tipo}>{tipo}</option>)}</select></label>
      <label className="block">Componente ou material<input required maxLength={300} className={campo} value={passo.descricao} onChange={e => editar(index, { descricao: e.target.value })} /></label>
      <label className="block">Vincular ao cadastro<select required={!!ficha.composicao_ativa} className={campo} value={passo.receita_base_id ? `r:${passo.receita_base_id}` : passo.ingrediente_id ? `i:${passo.ingrediente_id}` : ""} onChange={e => {
        const [tipo, alvo] = e.target.value.split(":");
        if (tipo === "r") { const base = receitas.data?.find(r => r.id === alvo); editar(index, { receita_base_id: alvo, ingrediente_id: null, tipo: "componente", descricao: base?.nome ?? passo.descricao }); }
        else if (tipo === "i") { const material = materiais.data?.find(m => m.id === alvo); editar(index, { ingrediente_id: alvo, receita_base_id: null, tipo: material?.tipo === "embalagem" ? "embalagem" : "ingrediente", descricao: material?.nome ?? passo.descricao }); }
        else editar(index, { receita_base_id: null, ingrediente_id: null });
      }}><option value="">Sem vínculo (somente instrução)</option>
        <optgroup label="Receitas-base e componentes prontos">{receitas.data?.filter(r => r.id !== id).map(r => <option key={r.id} value={`r:${r.id}`}>{r.nome} — rende {formatQuantidade(r.rendimento)} {r.rendimento_unidade}</option>)}</optgroup>
        <optgroup label="Ingredientes e embalagens">{materiais.data?.map(m => <option key={m.id} value={`i:${m.id}`}>{m.nome} ({m.unidade})</option>)}</optgroup>
      </select></label>
      <div className="grid grid-cols-2 gap-3">
        <label>Quantidade nominal<QuantidadeCampo required value={passo.quantidade} onChange={valor => editar(index, { quantidade: valor ?? "" })} /></label>
        <label>Unidade<select className={campo} value={passo.unidade} onChange={e => editar(index, { unidade: e.target.value as PassoMontagem["unidade"] })}>{["g", "kg", "ml", "l", "un"].map(un => <option key={un}>{un}</option>)}</select></label>
        <label>Mínimo (opcional)<QuantidadeCampo value={passo.quantidade_minima} onChange={valor => editar(index, { quantidade_minima: valor })} /></label>
        <label>Máximo (opcional)<QuantidadeCampo value={passo.quantidade_maxima} onChange={valor => editar(index, { quantidade_maxima: valor })} /></label>
      </div>
      <label className="block">Dimensões, capacidade ou padrão<input maxLength={500} className={campo} placeholder="Ex.: copo de 300 ml; camada de 15 × 15 cm" value={passo.especificacao} onChange={e => editar(index, { especificacao: e.target.value })} /></label>
      <label className="block">Instrução de montagem<textarea maxLength={1000} className={campo} value={passo.instrucao} onChange={e => editar(index, { instrucao: e.target.value })} /></label>
    </li>)}</ol>
    <button type="button" className="rounded-lg border px-4 py-2" disabled={ficha.passos.length >= 100} onClick={() => setFicha({ ...ficha, passos: [...ficha.passos, { descricao: "", tipo: "componente", quantidade: "", quantidade_minima: null, quantidade_maxima: null, unidade: "g", especificacao: "", instrucao: "" }] })}>Adicionar etapa</button>
    <div className="flex flex-wrap gap-3"><button disabled={salvar.isPending || !ficha.passos.length} className="rounded-lg bg-primary px-4 py-2 text-primary-foreground">{salvar.isPending ? "Salvando..." : "Salvar ficha técnica"}</button>
    <button type="button" className="rounded-lg border px-4 py-2" onClick={async () => { if (confirm("Recarregar e descartar alterações locais?")) { const result = await consulta.refetch(); if (result.data) { setFicha(result.data); setMensagem(""); } } }}>Recarregar</button></div>
    {mensagem && <p role="status">{mensagem}</p>}
  </form>;
}
