import { UNIDADES_MEDIDA } from "@/lib/unidades";

const input = "w-full rounded-lg border bg-background px-3 py-2.5 text-sm";

export function UnidadeCompraSelect({
  id,
  name,
  value,
  unidadesCadastradas = [],
  unidadeAtualLabel = "Unidade atual",
  required = false,
  onChange,
}: {
  id: string;
  name: string;
  value: string;
  unidadesCadastradas?: string[];
  unidadeAtualLabel?: string;
  required?: boolean;
  onChange: (value: string) => void;
}) {
  const padrao = new Set(UNIDADES_MEDIDA.map((unidade) => unidade.value));
  const cadastradas = [...new Set(unidadesCadastradas)].filter((unidade) => unidade && !padrao.has(unidade));
  const unidadeAtualDisponivel = !padrao.has(value) && !cadastradas.includes(value);

  return <select name={name} id={id} className={input} value={value} required={required}
    onChange={(event) => onChange(event.target.value)}>
    <option value="">Selecione a unidade</option>
    <optgroup label="Unidades de medida">
      {UNIDADES_MEDIDA.map((unidade) => <option key={unidade.value} value={unidade.value}>{unidade.label}</option>)}
    </optgroup>
    {cadastradas.length > 0 && <optgroup label="Já cadastradas no estoque">
      {cadastradas.map((unidade) => <option key={unidade} value={unidade}>{unidade}</option>)}
    </optgroup>}
    {value && unidadeAtualDisponivel && <optgroup label={unidadeAtualLabel}>
      <option value={value}>{value}</option>
    </optgroup>}
  </select>;
}
