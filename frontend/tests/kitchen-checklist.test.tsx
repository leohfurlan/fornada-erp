import { useState } from "react";
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { KitchenChecklist, type KitchenStep } from "@/components/shared/kitchen-checklist";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });
const blocks: KitchenStep[] = [
  { id: "ingredients-1", section: "ingredients", title: "Ingredientes", markdown: "Farinha" },
  { id: "step-1", section: "steps", checkable: true, title: "Misturar", markdown: "Misture bem. [Ajuda](https://example.com)" },
  { id: "step-2", section: "steps", checkable: true, title: "Assar", markdown: "Asse por 30 minutos." },
];

it("não transforma modo de preparo ou montagem em checklist nem os conta no progresso", () => {
  render(<KitchenChecklist blocks={[
    { id: "preparation-text", section: "preparation", title: "Modo de preparo", markdown: "1. Misture\n2. Asse" },
    { id: "assembly-1", section: "assembly", title: "Montagem", markdown: "Sirva." },
  ]} section="preparation" completedIds={["preparation-text", "assembly-1"]} disabled={false} onComplete={vi.fn()} onReset={vi.fn()} />);
  expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "0");
  expect(screen.getByText("0 de 0 etapas concluídas")).toBeVisible();
  expect(screen.queryByRole("button", { name: /etapa/ })).not.toBeInTheDocument();
});
function Checklist({ steps = blocks }: { steps?: KitchenStep[] }) {
  const [ids, setIds] = useState<string[]>([]);
  return <KitchenChecklist blocks={steps} section="steps" completedIds={ids} disabled={false}
    onComplete={(id, completed) => setIds(current => completed ? [...current, id] : current.filter(item => item !== id))}
    onReset={() => setIds([])} />;
}

it("marca fora de ordem, mantém dimensões/classes estruturais, calcula e reverte conclusão total", () => {
  render(<Checklist />);
  const card = screen.getByRole("article", { name: "Etapa 2" });
  const classes = card.className;
  fireEvent.click(screen.getByRole("button", { name: "Marcar etapa 2 como concluída" }));
  expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "50");
  expect(screen.getByRole("heading", { name: "Assar" })).toHaveClass("line-through");
  expect(card.className).toBe(classes);
  expect(screen.getByText("Asse por 30 minutos.")).toBeVisible();
  fireEvent.click(screen.getByRole("article", { name: "Etapa 1" }));
  expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");
  expect(screen.getByText("Pronto! Bom apetite.")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Desmarcar etapa 2" }));
  expect(screen.queryByText("Pronto! Bom apetite.")).not.toBeInTheDocument();
  expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "50");
});

it("preserva links e não duplica a marcação do botão interno", () => {
  const onComplete = vi.fn();
  render(<KitchenChecklist blocks={blocks} section="steps" completedIds={[]} disabled={false} onComplete={onComplete} onReset={vi.fn()} />);
  fireEvent.click(screen.getByRole("link", { name: "Ajuda" }));
  expect(onComplete).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Marcar etapa 1 como concluída" }));
  expect(onComplete).toHaveBeenCalledTimes(1);
  expect(onComplete).toHaveBeenCalledWith("step-1", true);
});

it("só reinicia após confirmar e mantém a receita visível", () => {
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  render(<Checklist />);
  fireEvent.click(screen.getByRole("article", { name: "Etapa 1" }));
  fireEvent.click(screen.getByRole("button", { name: "Reiniciar etapas" }));
  expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "50");
  confirm.mockReturnValue(true);
  fireEvent.click(screen.getByRole("button", { name: "Reiniciar etapas" }));
  expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "0");
  expect(screen.getByRole("heading", { name: "Misturar" })).toBeVisible();
});

it.each([0, 1])("trata %i etapa sem divisão por zero", count => {
  render(<Checklist steps={blocks.slice(1, count + 1)} />);
  expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "0");
  expect(screen.queryByText("Pronto! Bom apetite.")).not.toBeInTheDocument();
  if (count) {
    fireEvent.click(screen.getByRole("article", { name: "Etapa 1" }));
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");
  }
});

it("suprime feedback tátil com movimento reduzido e ignora comandos desabilitados", () => {
  const vibrate = vi.fn();
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: true })));
  Object.defineProperty(navigator, "vibrate", { configurable: true, value: vibrate });
  const onComplete = vi.fn();
  const props = { blocks, section: "steps", checkable: true, completedIds: [], onComplete, onReset: vi.fn() };
  const { rerender } = render(<KitchenChecklist {...props} disabled={false} />);
  fireEvent.click(screen.getByRole("article", { name: "Etapa 1" }));
  expect(vibrate).not.toHaveBeenCalled();
  rerender(<KitchenChecklist {...props} disabled />);
  fireEvent.click(screen.getByRole("article", { name: "Etapa 1" }));
  expect(onComplete).toHaveBeenCalledTimes(1);
  vi.unstubAllGlobals();
});
