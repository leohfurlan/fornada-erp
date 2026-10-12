import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { UnidadeSelect } from "@/components/shared/unidade-select";

describe("unidades do cadastro e das receitas", () => {
  it("limita o novo cadastro a kg, L e un", () => {
    render(<UnidadeSelect tipo="medida" somenteBase />);
    expect(screen.getAllByRole("option").map((option) => option.getAttribute("value"))).toEqual(["", "kg", "L", "un"]);
  });

  it("preserva gramas e mililitros nos seletores das operações", () => {
    render(<UnidadeSelect tipo="medida" />);
    expect(screen.getByRole("option", { name: "Grama (g)" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Mililitro (mL)" })).toBeInTheDocument();
  });
});
