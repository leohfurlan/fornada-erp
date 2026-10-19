import { useState } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { KitchenIngredients } from "@/components/shared/kitchen-ingredients";

afterEach(cleanup);
it("confirma e desmarca pelo card inteiro mantendo as quantidades legíveis", () => {
  function Ingredients() {
    const [ids, setIds] = useState<string[]>([]);
    return <KitchenIngredients ingredients={[{ name: "Farinha", quantity: "0.5", unit: "kg" }]} checkedIds={ids} disabled={false} onCheck={(id, checked) => setIds(checked ? [id] : [])} />;
  }
  render(<Ingredients />);
  fireEvent.click(screen.getByRole("button", { name: "Confirmar ingrediente Farinha à mão" }));
  expect(screen.getByText("Farinha")).toHaveClass("line-through");
  expect(screen.getByText("0,5 kg")).toBeVisible();
  expect(screen.getByText("1 de 1 ingredientes à mão")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Desmarcar ingrediente Farinha" }));
  expect(screen.getByText("Farinha")).not.toHaveClass("line-through");
  expect(screen.getByText("0 de 1 ingredientes à mão")).toBeVisible();
});
