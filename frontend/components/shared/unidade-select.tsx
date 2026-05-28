"use client";

import { forwardRef } from "react";
import { cn } from "@/lib/utils";
import { UNIDADES_MEDIDA, UNIDADES_VENDA, type UnidadeOption } from "@/lib/unidades";

interface UnidadeSelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, "children"> {
  /** "medida" para ingredientes/estoque, "venda" para rendimento de receita. */
  tipo: "medida" | "venda";
  placeholder?: string;
  className?: string;
}

const labelByCategoria: Record<UnidadeOption["categoria"], string> = {
  peso: "Peso",
  volume: "Volume",
  contagem: "Contagem",
};

/**
 * Select padronizado de unidades. Agrupado por categoria (peso/volume/contagem)
 * para evitar que a confeiteira erre digitando "kgs" ou "litros" e quebre
 * o matching de OCR e o custo médio.
 */
export const UnidadeSelect = forwardRef<HTMLSelectElement, UnidadeSelectProps>(
  ({ tipo, placeholder = "Selecione...", className, ...rest }, ref) => {
    const opcoes = tipo === "medida" ? UNIDADES_MEDIDA : UNIDADES_VENDA;

    // Agrupa por categoria preservando a ordem original
    const grupos = opcoes.reduce<Record<string, UnidadeOption[]>>((acc, op) => {
      (acc[op.categoria] ??= []).push(op);
      return acc;
    }, {});

    return (
      <select
        ref={ref}
        className={cn(
          "w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary bg-background",
          className
        )}
        {...rest}
      >
        <option value="">{placeholder}</option>
        {Object.entries(grupos).map(([cat, items]) => (
          <optgroup key={cat} label={labelByCategoria[cat as UnidadeOption["categoria"]]}>
            {items.map((op) => (
              <option key={op.value} value={op.value}>
                {op.label}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
    );
  }
);
UnidadeSelect.displayName = "UnidadeSelect";
