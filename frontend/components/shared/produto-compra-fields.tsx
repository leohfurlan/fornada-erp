"use client";

import { DecimalInput } from "@/components/shared/decimal-input";
import { UnidadeCompraSelect } from "@/components/shared/unidade-compra-select";
import type { ProdutoDados } from "@/types/compras";
import { erroNome, nomeMaiusculo } from "@/lib/nomes";
import { decimalCompra } from "@/lib/compras";

const input = "w-full rounded-lg border bg-background px-3 py-2.5 text-sm";
export function ProdutoCompraFields({ value, onChange, prefix, fieldPrefix = "", compacto = false, detalhesProdutoVisiveis = false, unidadesCadastradas = [], mostrarNomeProduto = true, unidadeEstoque }: {
  value: ProdutoDados; onChange: (value: ProdutoDados) => void; prefix: string; fieldPrefix?: string; compacto?: boolean;
  unidadesCadastradas?: string[];
  mostrarNomeProduto?: boolean;
  detalhesProdutoVisiveis?: boolean;
  unidadeEstoque?: string;
}) {
  const field = (key: string) => fieldPrefix ? `${fieldPrefix}.${key}` : key;
  const set = (patch: Partial<ProdutoDados>) => onChange({ ...value, ...patch });
  const campoTexto = (key: "nome" | "marca" | "fabricante" | "variante") => {
      const labels = { nome: compacto ? "Nome do produto comprado *" : "Nome do produto na embalagem *", marca: "Marca *",
        fabricante: "Fabricante (opcional)", variante: "Variante (opcional)" };
      return <div key={key}><label htmlFor={prefix + key} className="text-xs">{labels[key]}</label>
        <input name={field(key)} id={prefix + key} className={input} maxLength={200} required={key === "nome" || key === "marca"} value={key === "nome" ? nomeMaiusculo(value.nome) : value[key] ?? ""}
          aria-invalid={key === "nome" && !!value.nome && !!erroNome(value.nome)}
          onChange={(e) => {
            const text = key === "nome" ? nomeMaiusculo(e.target.value) : e.target.value;
            e.target.setCustomValidity(key === "nome" ? erroNome(text) ?? "" : "");
            set({ [key]: text || (key === "fabricante" || key === "variante" ? null : "") });
          }} />
        {key === "nome" && <p className="text-xs text-muted-foreground">Nome em letras maiúsculas, sem emojis.</p>}
        {key === "nome" && value.nome && erroNome(value.nome) && <p role="alert" className="text-xs text-destructive">{erroNome(value.nome)}</p>}
      </div>;
    };
  return <div className="space-y-3">
    {mostrarNomeProduto && campoTexto("nome")}
    {campoTexto("marca")}
    {compacto && !detalhesProdutoVisiveis ? <details className="space-y-3"><summary className="cursor-pointer text-xs">Fabricante e variante (opcional)</summary>
      {(["fabricante", "variante"] as const).map(campoTexto)}
    </details> : (["fabricante", "variante"] as const).map(campoTexto)}
    <p className="text-xs text-muted-foreground">Quantidade comprada conta embalagens; este conteúdo informa quanto cada uma acrescenta ao estoque.</p>
    <div className="grid grid-cols-2 gap-2">
      <div><label htmlFor={prefix + "conteudo"} className="text-xs">Conteúdo de cada embalagem *</label>
        <DecimalInput name={field("conteudo_embalagem")} id={prefix + "conteudo"} value={value.conteudo_embalagem}
          required onChange={(v) => set({ conteudo_embalagem: v > 0 ? String(v) : "" })} /></div>
      <div><label htmlFor={prefix + "unidade"} className="text-xs">Unidade do conteúdo *</label>
        <UnidadeCompraSelect name={field("unidade_conteudo")} id={prefix + "unidade"} value={value.unidade_conteudo}
          unidadesCadastradas={unidadesCadastradas} required onChange={(unidade_conteudo) => set({ unidade_conteudo })} /></div>
    </div>
    {Number(value.conteudo_embalagem) > 0 && <p className="text-sm font-medium">Cada embalagem comprada contém {decimalCompra(value.conteudo_embalagem)} {value.unidade_conteudo}.</p>}
    {unidadeEstoque && <p className="text-xs text-muted-foreground">Unidade de estoque do material: <strong>{unidadeEstoque}</strong>. O conteúdo da embalagem não altera essa unidade.</p>}
    <details open={!compacto}><summary className="cursor-pointer text-xs">Código de barras (opcional)</summary>
      <label htmlFor={prefix + "gtin"} className="text-xs">GTIN/EAN confirmado (opcional)</label>
      <input name={field("gtin")} id={prefix + "gtin"} className={input} inputMode="numeric" value={value.gtin ?? ""}
        maxLength={14} onChange={(e) => set({ gtin: e.target.value || null })} />
      <p className="text-xs text-muted-foreground">Use o código de barras da embalagem. Código da loja fica separado.</p>
    </details>
    <details className="text-xs"><summary>Conversão específica do conteúdo</summary>
      <p className="text-muted-foreground">Este campo não é o conteúdo do frasco. Use apenas para relacionar a unidade do conteúdo à unidade de estoque; conversões entre g e kg ou mL e L são automáticas.</p>
      <label htmlFor={prefix + "fator"}>{unidadeEstoque ? `1 ${value.unidade_conteudo} de conteúdo equivale a quantos ${unidadeEstoque} no estoque?` : `1 ${value.unidade_conteudo} de conteúdo equivale a quantas unidades de estoque?`}</label>
      <DecimalInput name={field("fator_para_principal")} id={prefix + "fator"} value={value.fator_para_principal ?? ""}
        onChange={(v) => set({ fator_para_principal: v > 0 ? String(v) : null })} />
      <p className="text-muted-foreground">Preencha apenas se não houver conversão métrica ou alternativa cadastrada.</p>
    </details>
  </div>;
}
