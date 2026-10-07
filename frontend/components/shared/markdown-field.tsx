"use client";

import { useId, useRef, useState } from "react";
import { MarkdownContent } from "@/components/shared/markdown-content";
import { cn } from "@/lib/utils";

interface MarkdownFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  onBlur?: () => void;
  name?: string;
  required?: boolean;
  maxLength?: number;
  rows?: number;
  placeholder?: string;
}

export function MarkdownField({ label, value, onChange, onBlur, name, required, maxLength, rows = 4, placeholder }: MarkdownFieldProps) {
  const id = useId();
  const textarea = useRef<HTMLTextAreaElement>(null);
  const [preview, setPreview] = useState(false);

  function format(prefix: string, suffix: string, fallback: string): void {
    const field = textarea.current;
    if (!field) return;
    const start = field.selectionStart;
    const end = field.selectionEnd;
    const selected = value.slice(start, end) || fallback;
    const next = value.slice(0, start) + prefix + selected + suffix + value.slice(end);
    if (maxLength !== undefined && next.length > maxLength) return;
    onChange(next);
    requestAnimationFrame(() => {
      field.focus();
      field.setSelectionRange(start + prefix.length, start + prefix.length + selected.length);
    });
  }

  return <div className="space-y-2">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <label htmlFor={id} className="text-sm font-medium">{label}</label>
      <div className="flex gap-1">
        <button type="button" aria-pressed={!preview} aria-label={`${label}: editar`} className={cn("rounded px-3 py-1 text-xs", !preview && "bg-muted font-semibold")} onClick={() => setPreview(false)}>Editar</button>
        <button type="button" aria-pressed={preview} aria-label={`${label}: prévia`} className={cn("rounded px-3 py-1 text-xs", preview && "bg-muted font-semibold")} onClick={() => setPreview(true)}>Prévia</button>
      </div>
    </div>
    <div className="rounded-lg border bg-background">
      {!preview && <div className="flex flex-wrap gap-1 border-b p-1" role="group" aria-label={`Formatação de ${label}`}>
        <button type="button" aria-label={`${label}: negrito`} className="rounded px-3 py-1 text-sm font-bold hover:bg-muted" onClick={() => format("**", "**", "texto")}>B</button>
        <button type="button" aria-label={`${label}: itálico`} className="rounded px-3 py-1 text-sm italic hover:bg-muted" onClick={() => format("*", "*", "texto")}>I</button>
        <button type="button" aria-label={`${label}: título`} className="rounded px-3 py-1 text-xs hover:bg-muted" onClick={() => format("\n## ", "\n", "Título")}>Título</button>
        <button type="button" aria-label={`${label}: lista`} className="rounded px-3 py-1 text-xs hover:bg-muted" onClick={() => format("\n- ", "\n", "Item")}>Lista</button>
        <button type="button" aria-label={`${label}: link`} className="rounded px-3 py-1 text-xs hover:bg-muted" onClick={() => format("[", "](https://)", "texto do link")}>Link</button>
      </div>}
      {/* Mantém o campo obrigatório montado e validável mesmo ao consultar a prévia. */}
      <textarea id={id} ref={textarea} name={name} rows={rows} required={required} maxLength={maxLength} value={value} onChange={(event) => onChange(event.target.value)} onBlur={onBlur} onInvalid={() => { setPreview(false); requestAnimationFrame(() => textarea.current?.focus()); }} tabIndex={preview ? -1 : undefined} placeholder={placeholder} aria-describedby={`${id}-hint`} className={cn("block w-full resize-y rounded-lg bg-background p-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary", preview && "sr-only")} />
      {preview && <div className="min-h-24 p-3" role="region" aria-label={`Prévia de ${label}`}>
        {value.trim() ? <MarkdownContent>{value}</MarkdownContent> : <p className="text-sm text-muted-foreground">Nenhum texto para visualizar.</p>}
      </div>}
    </div>
    <p id={`${id}-hint`} className="text-xs text-muted-foreground">Aceita Markdown: **negrito**, *itálico*, títulos, listas, links e tabelas.</p>
  </div>;
}
