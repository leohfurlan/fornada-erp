"use client";

import { Check } from "lucide-react";
import { formatQuantidade } from "@/lib/utils";

export type KitchenIngredient = { id?: string; name: string; quantity: string; unit: string };

export function KitchenIngredients({ ingredients, checkedIds, disabled, onCheck }: {
  ingredients: KitchenIngredient[]; checkedIds: string[]; disabled: boolean;
  onCheck: (id: string, checked: boolean) => void;
}) {
  return <div className="mt-6 space-y-3">
    <p role="status" className="text-base text-muted-foreground">{ingredients.filter((item, index) => checkedIds.includes(item.id ?? `ingredient-${index}`)).length} de {ingredients.length} ingredientes à mão</p>
    <ul className="space-y-3">{ingredients.map((item, index) => {
      const id = item.id ?? `ingredient-${index}`;
      const checked = checkedIds.includes(id);
      return <li key={id}>
        <button type="button" disabled={disabled} aria-pressed={checked}
          aria-label={checked ? `Desmarcar ingrediente ${item.name}` : `Confirmar ingrediente ${item.name} à mão`}
          onClick={() => {
            if (disabled) return;
            onCheck(id, !checked);
            if (!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
              try { navigator.vibrate?.(15); } catch { /* Optional device feedback. */ }
            }
          }}
          className="flex min-h-16 w-full items-center gap-4 rounded-2xl border bg-card p-4 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring disabled:opacity-50 sm:p-6">
          <span aria-hidden="true" className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 transition-colors duration-200 motion-reduce:transition-none ${checked ? "border-success bg-success text-success-foreground" : "border-muted-foreground"}`}><Check className={`h-5 w-5 transition-opacity duration-200 motion-reduce:transition-none ${checked ? "opacity-100" : "opacity-0"}`} /></span>
          <span className="flex min-w-0 flex-1 flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <span className={`break-words text-xl font-semibold sm:text-2xl ${checked ? "line-through" : ""}`}>{item.name}</span>
            <span className={`text-xl text-primary transition-opacity duration-200 motion-reduce:transition-none ${checked ? "opacity-90" : "opacity-100"}`}>{formatQuantidade(item.quantity)} {item.unit}</span>
          </span>
        </button>
      </li>;
    })}</ul>
  </div>;
}
