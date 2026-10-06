"use client";

export interface UnidadeAlternativa {
  unidade: string;
  fator: string;
  observacao?: string | null;
}

interface Props {
  principal: string;
  value: UnidadeAlternativa[];
  onChange: (value: UnidadeAlternativa[]) => void;
}

export function UnidadesAlternativas({ principal, value, onChange }: Props) {
  const alterar = (index: number, campo: keyof UnidadeAlternativa, texto: string) => {
    onChange(value.map((item, i) => i === index ? { ...item, [campo]: texto } : item));
  };
  return <section className="rounded-xl border p-4 space-y-3">
    <h2 className="text-sm font-medium">Unidades alternativas</h2>
    <p className="text-xs text-muted-foreground">Estoque e custo ficam na unidade principal ({principal || "selecione acima"}). Informe quanto vale 1 unidade alternativa. Conversões g/kg e ml/L já são automáticas.</p>
    {value.map((item, index) => <div key={index} className="rounded-lg border p-3 space-y-2">
      <label className="block text-xs">Unidade (ex.: xícara, pacote)<input required maxLength={40} aria-label={`Unidade alternativa ${index + 1}`} value={item.unidade} onChange={e => alterar(index, "unidade", e.target.value)} className="mt-1 w-full rounded border p-2" /></label>
      <label className="block text-xs">1 {item.unidade || "unidade alternativa"} equivale a quantos {principal || "da unidade principal"}?<input required inputMode="decimal" pattern="[0-9]+([.,][0-9]{1,8})?" aria-label={`Fator ${index + 1}`} value={item.fator.replace(".", ",")} onChange={e => alterar(index, "fator", e.target.value.replace(",", "."))} className="mt-1 w-full rounded border p-2" /></label>
      <label className="block text-xs">Observação ou fonte<input maxLength={500} value={item.observacao || ""} onChange={e => alterar(index, "observacao", e.target.value)} className="mt-1 w-full rounded border p-2" /></label>
      <button type="button" className="text-xs text-destructive" onClick={() => { if (confirm("Remover esta conversão?")) onChange(value.filter((_, i) => i !== index)); }}>Remover conversão</button>
    </div>)}
    <button type="button" className="text-sm text-primary" onClick={() => onChange([...value, { unidade: "", fator: "", observacao: "" }])}>Adicionar unidade alternativa</button>
  </section>;
}
