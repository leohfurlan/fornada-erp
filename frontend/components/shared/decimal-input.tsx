"use client";

import { forwardRef, useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { formatDecimalInput, parseDecimalBR, sanitizeDecimalInput } from "@/lib/decimal";

interface DecimalInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "onChange" | "value" | "type"> {
  value?: number | string;
  onChange?: (value: number) => void;
  className?: string;
}

/**
 * Input para valores decimais em pt-BR.
 *
 * - Aceita vírgula ou ponto como separador decimal na digitação
 * - Sempre devolve `number` (com ponto) no onChange para integrar com forms
 * - Em mobile, abre teclado numérico via inputMode="decimal"
 *
 * Substitui `<input type="number">` que tem comportamento inconsistente com
 * vírgula entre navegadores/sistemas operacionais.
 */
export const DecimalInput = forwardRef<HTMLInputElement, DecimalInputProps>(
  ({ value, onChange, className, ...rest }, ref) => {
    const [texto, setTexto] = useState<string>(() => formatDecimalInput(value));

    // Sincroniza quando o valor externo muda (ex: form.reset)
    useEffect(() => {
      const externo = formatDecimalInput(value);
      // Evita sobrescrever enquanto o usuário digita "1," (estado intermediário)
      if (parseDecimalBR(texto) !== parseDecimalBR(externo)) {
        setTexto(externo);
      }
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [value]);

    return (
      <input
        ref={ref}
        type="text"
        inputMode="decimal"
        autoComplete="off"
        className={cn(
          "w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary",
          className
        )}
        value={texto}
        onChange={(e) => {
          const limpo = sanitizeDecimalInput(e.target.value);
          setTexto(limpo);
          onChange?.(parseDecimalBR(limpo));
        }}
        onBlur={(e) => {
          // Normaliza visualmente ao sair: "1," vira "1"
          const num = parseDecimalBR(e.target.value);
          setTexto(num === 0 && e.target.value === "" ? "" : formatDecimalInput(num));
        }}
        {...rest}
      />
    );
  }
);
DecimalInput.displayName = "DecimalInput";
