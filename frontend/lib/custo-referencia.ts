/** Quantidade da unidade principal equivalente a 1 kg, 1 L ou 1 un.
 * Embalagens só são convertidas quando há uma equivalência cadastrada.
 */
export function referenciaCusto(unidade: string, alternativas: ReadonlyArray<{ unidade: string; fator: string | number }> = []) {
  const metricas: Record<string, { unidade: string; fator: number }> = {
    kg: { unidade: "kg", fator: 1 }, g: { unidade: "kg", fator: 1000 },
    mg: { unidade: "kg", fator: 1000000 }, l: { unidade: "L", fator: 1 },
    ml: { unidade: "L", fator: 1000 }, un: { unidade: "un", fator: 1 },
    dz: { unidade: "un", fator: 1 / 12 },
  };
  const direta = metricas[unidade.trim().toLowerCase()];
  if (direta) return direta;
  for (const alternativa of alternativas) {
    const ref = metricas[alternativa.unidade.trim().toLowerCase()];
    const fator = Number(alternativa.fator);
    if (ref && Number.isFinite(fator) && fator > 0) {
      return { unidade: ref.unidade, fator: fator * ref.fator };
    }
  }
  // Não inventar quantidades por caixa, pacote ou lata de cadastros antigos.
  return { unidade, fator: 1 };
}

export function custoReferencia(item: { unidade: string; custo_medio: string | number; unidades_alternativas?: ReadonlyArray<{ unidade: string; fator: string | number }> }) {
  const ref = referenciaCusto(item.unidade, item.unidades_alternativas);
  return { unidade: ref.unidade, valor: Number(item.custo_medio) * ref.fator };
}
