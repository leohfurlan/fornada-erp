import { describe, expect, it } from "vitest";
import { percentualParaTaxa, taxaParaPercentual } from "@/lib/taxas";

describe("taxas decimais", () => {
  it.each([['0.2750', '27,5'], ['0.0300', '3'], ['0.0325', '3,25'], ['0.0001', '0,01'], ['0', '0']])("exibe %s como %s", (taxa, percentual) => {
    expect(taxaParaPercentual(taxa)).toBe(percentual);
    expect(taxaParaPercentual(percentualParaTaxa(percentual))).toBe(percentual);
  });
  it("envia string decimal exata, sem artefato binário", () => {
    expect(percentualParaTaxa('27,5')).toBe('0.275');
    expect(percentualParaTaxa('3.25')).toBe('0.0325');
    expect(percentualParaTaxa('')).toBe('0');
  });
});
