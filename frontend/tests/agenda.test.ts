import { describe, it, expect } from "vitest";
import {
  corDoItem,
  diasDaSemana,
  inicioSemana,
  toDateKey,
  fromDateKey,
} from "@/lib/agenda";
import { calcularMover, calcularMoverDia } from "@/app/(dashboard)/agenda/mover";
import type { AgendaItem } from "@/types";

function fakeItem(over: Partial<AgendaItem> = {}): AgendaItem {
  return {
    id: "1",
    tenant_id: "t",
    titulo: "Item",
    tipo: "tarefa",
    data: "2026-06-03",
    hora_inicio: null,
    hora_fim: null,
    cor: null,
    concluido: false,
    observacoes: null,
    receita_id: null,
    pedido_id: null,
    ordem_producao_id: null,
    nome_receita: null,
    nome_pedido: null,
    numero_op: null,
    duracao_minutos: null,
    created_at: "",
    updated_at: "",
    ...over,
  };
}

describe("inicioSemana", () => {
  it("retorna a segunda-feira da semana (quarta → segunda)", () => {
    // 2026-06-03 é quarta.
    const seg = inicioSemana(fromDateKey("2026-06-03"));
    expect(toDateKey(seg)).toBe("2026-06-01");
  });

  it("domingo ainda pertence à semana iniciada na segunda anterior", () => {
    const seg = inicioSemana(fromDateKey("2026-06-07")); // domingo
    expect(toDateKey(seg)).toBe("2026-06-01");
  });
});

describe("diasDaSemana", () => {
  it("retorna 7 dias de segunda a domingo", () => {
    const dias = diasDaSemana(fromDateKey("2026-06-03")).map(toDateKey);
    expect(dias).toEqual([
      "2026-06-01",
      "2026-06-02",
      "2026-06-03",
      "2026-06-04",
      "2026-06-05",
      "2026-06-06",
      "2026-06-07",
    ]);
  });
});

describe("corDoItem", () => {
  it("usa cor customizada quando presente", () => {
    expect(corDoItem({ cor: "#123456", tipo: "tarefa" })).toBe("#123456");
  });

  it("usa cor padrão do tipo quando sem cor", () => {
    expect(corDoItem({ cor: null, tipo: "receita" })).toBe("#f97316");
  });
});

describe("calcularMover", () => {
  it("preserva a duração ao mover para outra hora", () => {
    const item = fakeItem({
      hora_inicio: "08:00:00",
      hora_fim: "10:00:00",
      duracao_minutos: 120,
    });
    const payload = calcularMover(item, "2026-06-05", 14);
    expect(payload).toEqual({
      data: "2026-06-05",
      hora_inicio: "14:00:00",
      hora_fim: "16:00:00",
    });
  });

  it("usa 60 min para item que era de dia inteiro", () => {
    const payload = calcularMover(fakeItem(), "2026-06-05", 9);
    expect(payload.hora_inicio).toBe("09:00:00");
    expect(payload.hora_fim).toBe("10:00:00");
  });
});

describe("calcularMoverDia", () => {
  it("muda só a data e preserva o horário", () => {
    const item = fakeItem({ hora_inicio: "08:00:00", hora_fim: "09:00:00" });
    expect(calcularMoverDia(item, "2026-06-10")).toEqual({
      data: "2026-06-10",
      hora_inicio: "08:00:00",
      hora_fim: "09:00:00",
    });
  });
});
