import { describe, expect, it } from "vitest";
import { custoReferencia, referenciaCusto } from "@/lib/custo-referencia";

describe("custo por unidade de referência", () => {
  it.each([
    ["g", "0.0135", "kg", 13.5],
    ["mg", "0.0001", "kg", 100],
    ["kg", "13.50", "kg", 13.5],
    ["mL", "0.012", "L", 12],
    ["ml", "0.012", "L", 12],
    ["L", "12", "L", 12],
    ["un", "2.70", "un", 2.7],
    ["dz", "24", "un", 2],
  ])("%s: custo %s vira %s", (unidade, custo_medio, base, valor) => {
    expect(custoReferencia({ unidade, custo_medio })).toEqual({ unidade: base, valor });
  });

  it("preserva o custo de uma receita de 200 g ao exibir por kg", () => {
    const custo = custoReferencia({ unidade: "g", custo_medio: "0.0135" });
    expect(custo.valor * (200 / 1000)).toBeCloseTo(2.7);
  });

  it("usa equivalência cadastrada para embalagens antigas", () => {
    expect(custoReferencia({ unidade: "cx", custo_medio: "2.70", unidades_alternativas: [{ unidade: "g", fator: "0.005" }] })).toEqual({ unidade: "kg", valor: 13.5 });
  });

  it("não inventa conversão de embalagem sem equivalência", () => {
    expect(referenciaCusto("pct")).toEqual({ unidade: "pct", fator: 1 });
    expect(referenciaCusto("cx", [{ unidade: "g", fator: "0" }])).toEqual({ unidade: "cx", fator: 1 });
  });
});
