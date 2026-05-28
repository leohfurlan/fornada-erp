import { describe, it, expect } from "vitest";
import { formatMoney, formatDecimal, formatPercent, formatMinutos } from "@/lib/utils";

describe("formatMoney", () => {
  it("formata valor monetário em pt-BR", () => {
    expect(formatMoney(10.5)).toBe("R$ 10,50");
  });

  it("formata string numérica", () => {
    expect(formatMoney("25.99")).toBe("R$ 25,99");
  });

  it("retorna zero para null", () => {
    expect(formatMoney(null)).toBe("R$ 0,00");
  });
});

describe("formatMinutos", () => {
  it("exibe minutos abaixo de 1 hora", () => {
    expect(formatMinutos(45)).toBe("45 min");
  });

  it("exibe horas completas", () => {
    expect(formatMinutos(60)).toBe("1h");
  });

  it("exibe horas e minutos", () => {
    expect(formatMinutos(90)).toBe("1h 30min");
  });
});

describe("formatPercent", () => {
  it("formata decimal como percentual", () => {
    expect(formatPercent(0.3)).toBe("30%");
  });
});
