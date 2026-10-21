import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AjustarEstoqueDialog } from "@/components/shared/ajustar-estoque-dialog";
import type { Ingrediente } from "@/types";

const mocks = vi.hoisted(() => ({ ajustar: vi.fn() }));

vi.mock("@/hooks/use-estoque", () => ({
  useAjustarEstoque: () => ({ mutateAsync: mocks.ajustar, isPending: false }),
}));

const ingrediente: Ingrediente = {
  id: "farinha",
  tenant_id: "tenant",
  codigo: 1,
  tipo: "ingrediente",
  nome: "Farinha",
  unidade: "kg",
  unidades_alternativas: [],
  estoque_atual: "2.5",
  quantidade_reservada: "0",
  saldo: "2.5",
  estoque_minimo: "0",
  custo_medio: "8.5",
  data_custo_atualizado: null,
  status_estoque: "ok",
};

beforeEach(() => {
  cleanup();
  mocks.ajustar.mockReset();
  mocks.ajustar.mockResolvedValue(ingrediente);
});

describe("ajuste manual de estoque", () => {
  it("avisa quando a quantidade continua igual ao saldo atual", async () => {
    render(<AjustarEstoqueDialog item={ingrediente} />);
    fireEvent.click(screen.getByRole("button", { name: "Ajustar estoque de Farinha" }));

    expect(await screen.findByText("Essa quantidade já está cadastrada. Nenhum ajuste será registrado.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salvar ajuste" })).toBeDisabled();
    expect(mocks.ajustar).not.toHaveBeenCalled();
  });

  it("define a quantidade correta e envia o saldo alvo", async () => {
    render(<AjustarEstoqueDialog item={ingrediente} />);
    fireEvent.click(screen.getByRole("button", { name: "Ajustar estoque de Farinha" }));

    expect(await screen.findByText("Estoque cadastrado:")).toBeInTheDocument();
    expect(screen.getByText("Estoque cadastrado:").parentElement).toHaveTextContent("2,5 kg");
    const input = screen.getByLabelText("Quantidade correta em estoque (kg)");
    fireEvent.change(input, { target: { value: "1.25" } });
    expect(screen.getByText("O estoque diminuirá em 1,25 kg.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Salvar ajuste" }));
    await waitFor(() => expect(mocks.ajustar).toHaveBeenCalledWith({ quantidade_alvo: "1.25" }));
    await waitFor(() => expect(screen.queryByText("Ajustar estoque")).not.toBeInTheDocument());
  });

  it("impede saldo abaixo da quantidade reservada", async () => {
    render(
      <AjustarEstoqueDialog
        item={{ ...ingrediente, quantidade_reservada: "1.5" }}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: "Ajustar estoque de Farinha" }));
    fireEvent.change(await screen.findByLabelText("Quantidade correta em estoque (kg)"), {
      target: { value: "1" },
    });

    expect(screen.getByRole("alert")).toHaveTextContent("não pode ficar abaixo de 1,5 kg reservado");
    expect(screen.getByRole("button", { name: "Salvar ajuste" })).toBeDisabled();
    expect(mocks.ajustar).not.toHaveBeenCalled();
  });

  it("mostra a resposta do servidor quando o ajuste não pode ser salvo", async () => {
    mocks.ajustar.mockRejectedValue({ response: { data: { detail: "Conflito de estoque" } } });
    render(<AjustarEstoqueDialog item={ingrediente} />);
    fireEvent.click(screen.getByRole("button", { name: "Ajustar estoque de Farinha" }));
    fireEvent.change(await screen.findByLabelText("Quantidade correta em estoque (kg)"), {
      target: { value: "3" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Salvar ajuste" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Conflito de estoque");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });
});
