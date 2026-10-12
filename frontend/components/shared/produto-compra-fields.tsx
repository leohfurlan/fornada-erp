"use client";

import { DecimalInput } from "@/components/shared/decimal-input";
import type { ProdutoDados } from "@/types/compras";
import { erroNome, nomeMaiusculo } from "@/lib/nomes";

const input = "w-full rounded-lg border bg-background px-3 py-2.5 text-sm";
export function ProdutoCompraFields({ value, onChange, prefix }: {
  value: ProdutoDados; onChange: (value: ProdutoDados) => void; prefix: string;
}) {
  const set = (patch: Partial<ProdutoDados>) => onChange({ ...value, ...patch });
  return <div className="space-y-3">
    {(["nome", "marca", "fabricante", "variante"] as const).map((key) => {
      const labels = { nome: "Nome do produto na embalagem", marca: "Marca",
        fabricante: "Fabricante (se conhecido)", variante: "Variante (branco, ao leite...)" };
      return <div key={key}><label htmlFor={prefix + key} className="text-xs">{labels[key]}</label>
        <input id={prefix + key} className={input} maxLength={200} value={key === "nome" ? nomeMaiusculo(value.nome) : value[key] ?? ""}
          aria-invalid={key === "nome" && !!erroNome(value.nome)}
          onChange={(e) => {
            const text = key === "nome" ? nomeMaiusculo(e.target.value) : e.target.value;
            e.target.setCustomValidity(key === "nome" ? erroNome(text) ?? "" : "");
            set({ [key]: text || (key === "fabricante" || key === "variante" ? null : "") });
          }} />
        {key === "nome" && <p className="text-xs text-muted-foreground">Nome em letras maiúsculas, sem emojis.</p>}
        {key === "nome" && value.nome && erroNome(value.nome) && <p role="alert" className="text-xs text-destructive">{erroNome(value.nome)}</p>}
      </div>;
    })}
    <div className="grid grid-cols-2 gap-2">
      <div><label htmlFor={prefix + "conteudo"} className="text-xs">Conteúdo por embalagem</label>
        <DecimalInput id={prefix + "conteudo"} value={value.conteudo_embalagem}
          onChange={(v) => set({ conteudo_embalagem: String(v) })} /></div>
      <div><label htmlFor={prefix + "unidade"} className="text-xs">Unidade do conteúdo</label>
        <input id={prefix + "unidade"} className={input} value={value.unidade_conteudo}
          placeholder="kg, g, ml, l ou un" onChange={(e) => set({ unidade_conteudo: e.target.value })} /></div>
    </div>
    <div><label htmlFor={prefix + "gtin"} className="text-xs">GTIN/EAN confirmado (opcional)</label>
      <input id={prefix + "gtin"} className={input} inputMode="numeric" value={value.gtin ?? ""}
        maxLength={14} onChange={(e) => set({ gtin: e.target.value || null })} />
      <p className="text-xs text-muted-foreground">Use o código de barras da embalagem. Código da loja fica separado.</p>
    </div>
    <details className="text-xs"><summary>Conversão específica do conteúdo</summary>
      <label htmlFor={prefix + "fator"}>1 unidade do conteúdo equivale a quantas unidades do material?</label>
      <DecimalInput id={prefix + "fator"} value={value.fator_para_principal ?? ""}
        onChange={(v) => set({ fator_para_principal: v > 0 ? String(v) : null })} />
      <p className="text-muted-foreground">Preencha apenas se não houver conversão métrica ou alternativa cadastrada.</p>
    </details>
  </div>;
}
