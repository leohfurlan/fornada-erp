import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import IfoodPage from "@/app/(dashboard)/configuracoes/integracoes/ifood/page";
import type { IfoodMonitor } from "@/hooks/use-ifood-monitor";

const state = vi.hoisted(() => ({
  data: undefined as IfoodMonitor | undefined,
  isLoading: false,
  isError: false,
  refetch: vi.fn(),
}));
vi.mock("@/hooks/use-ifood-monitor", () => ({ useIfoodMonitor: () => state }));

function fixture(): IfoodMonitor {
  return {
    habilitado: true, intervalo_segundos: 30, loja_nome: "Teste - loja",
    merchant_id: "merchant", ultima_consulta: new Date().toISOString(),
    ultima_recepcao: null, erro: null, eventos_pendentes: 0, pedidos: [], eventos: [],
  };
}

beforeEach(() => {
  cleanup(); state.data = fixture(); state.isLoading = false;
  state.isError = false; state.refetch.mockClear();
});

describe("monitor iFood", () => {
  it("explica o ambiente de teste e não oferece ações comerciais", () => {
    render(<IfoodPage />);
    expect(screen.getByText("Recebendo eventos de teste")).toBeInTheDocument();
    expect(screen.getByText(/Estoque, vendas e aceitação/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /aceitar|cancelar|confirmar pedido/i })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Atualizar tela" }));
    expect(state.refetch).toHaveBeenCalledOnce();
  });

  it("não mostra conexão ativa quando o worker está parado", () => {
    state.data = { ...fixture(), ultima_consulta: "2020-01-01T00:00:00Z" };
    render(<IfoodPage />);
    expect(screen.getByText("Aguardando comunicação")).toBeInTheDocument();
  });

  it("informa configuração ausente em outra conta", () => {
    state.data = { ...fixture(), habilitado: false, merchant_id: null, loja_nome: null };
    render(<IfoodPage />);
    expect(screen.getByText("Monitor não habilitado nesta conta")).toBeInTheDocument();
    expect(screen.queryByText("Teste - loja")).not.toBeInTheDocument();
  });

  it("preserva totais oficiais e mostra complementos aninhados", () => {
    state.data = { ...fixture(), pedidos: [{ id: "local-id", ultimo_evento: "PLACED",
      evento_em: new Date().toISOString(), snapshot: {
        id: "order-id", displayId: "1975", isTest: true, createdAt: new Date().toISOString(),
        orderType: "DELIVERY", orderTiming: "IMMEDIATE", merchant: { id: "merchant", name: "Teste - loja" },
        total: { subTotal: "21", deliveryFee: "5", additionalFees: "1", benefits: "0", orderAmount: "27" },
        items: [{ name: "Combo", quantity: "1", unitPrice: "5", price: "5", totalPrice: "16",
          options: [{ name: "Adicional", quantity: "1", unitPrice: "8", price: "8", totalPrice: null,
            options: [{ name: "Subadicional", quantity: "1", unitPrice: "3", price: "3", totalPrice: null, options: [] }] }] }],
      } }] };
    render(<IfoodPage />);
    expect(screen.getByText("Pedido 1975 · teste")).toBeInTheDocument();
    expect(screen.getByText(/1 × Subadicional/)).toBeInTheDocument();
    expect(screen.getByText(/R\$\s*27,00/)).toBeInTheDocument();
    expect(screen.getByText(/R\$\s*16,00/)).toBeInTheDocument();
  });

  it("trata indisponibilidade da API com tentativa de leitura", () => {
    state.isError = true;
    render(<IfoodPage />);
    expect(screen.getByRole("alert")).toHaveTextContent("Não foi possível consultar");
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(state.refetch).toHaveBeenCalledOnce();
  });
});
