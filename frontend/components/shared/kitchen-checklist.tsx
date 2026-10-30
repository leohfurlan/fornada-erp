"use client";

import { Check } from "lucide-react";
import Link from "next/link";
import { MarkdownContent } from "@/components/shared/markdown-content";

export type KitchenStep = { id: string; section: string; title: string; markdown: string; checkable?: boolean };

interface KitchenChecklistProps {
  blocks: KitchenStep[];
  completedIds: string[];
  section: string;
  currentId?: string;
  recipeId?: string;
  disabled: boolean;
  onComplete: (id: string, completed: boolean) => void;
  onReset: () => void;
}

export function KitchenChecklist({ blocks, completedIds, section, currentId, recipeId, disabled, onComplete, onReset }: KitchenChecklistProps) {
  const steps = blocks.filter(block => block.checkable === true);
  const done = steps.filter(step => completedIds.includes(step.id)).length;
  const progress = steps.length ? done / steps.length * 100 : 0;
  const percent = Math.round(progress);
  const toggle = (step: KitchenStep) => {
    if (disabled) return;
    onComplete(step.id, !completedIds.includes(step.id));
    // The browser/device decides whether vibration is permitted. Reduced motion
    // also suppresses this optional feedback.
    if (!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
      try { navigator.vibrate?.(15); } catch { /* Optional platform capability. */ }
    }
  };

  return <div className="space-y-5">
    <div className="rounded-2xl border bg-card p-5 sm:p-8">
      <p role="status" className="text-lg font-semibold">{done} de {steps.length} etapas concluídas</p>
      <p className="mt-1 text-base text-muted-foreground">Progresso: {percent}%</p>
      <div role="progressbar" aria-label="Progresso do preparo" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent} className="mt-3 h-3 overflow-hidden rounded-full bg-muted">
        <div style={{ width: `${progress}%` }} className="h-full bg-success transition-[width] duration-200 motion-reduce:transition-none" />
      </div>
      <p aria-live="polite" className="mt-3 min-h-7 text-lg font-semibold text-success">{steps.length > 0 && done === steps.length ? "Pronto! Bom apetite." : ""}</p>
    </div>
    {steps.filter(step => step.section === section || (section === "preparation" && step.section === "steps")).map(step => {
      const completed = completedIds.includes(step.id);
      const number = steps.indexOf(step) + 1;
      const label = completed ? `Desmarcar etapa ${number}` : `Marcar etapa ${number} como concluída`;
      return <article key={step.id} aria-label={`Etapa ${number}`} className={`min-h-64 rounded-2xl border bg-card p-5 sm:p-8 ${currentId === step.id ? "border-primary" : ""}`}
        onClick={event => {
          // Links, timers, fields and the completion button own their events.
          if ((event.target as HTMLElement).closest("button, a, input, select, textarea, label, [role='button'], [role='checkbox']")) return;
          if (window.getSelection()?.toString()) return;
          toggle(step);
        }}>
        <button type="button" aria-label={label} aria-pressed={completed} disabled={disabled} onClick={() => toggle(step)} className="flex min-h-12 w-full items-start gap-4 rounded-xl text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring disabled:opacity-50">
          <span aria-hidden="true" className={`relative mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 transition-colors duration-200 motion-reduce:transition-none ${completed ? "border-success bg-success text-success-foreground" : "border-muted-foreground text-muted-foreground"}`}>
            <Check className={`absolute h-6 w-6 transition-opacity duration-200 motion-reduce:transition-none ${completed ? "opacity-100" : "opacity-0"}`} />
            <span className={`text-lg font-semibold transition-opacity duration-200 motion-reduce:transition-none ${completed ? "opacity-0" : "opacity-100"}`}>{number}</span>
          </span>
          <span className="min-w-0 flex-1">
            <span className="text-sm font-semibold uppercase tracking-widest text-muted-foreground">Etapa {number}</span>
            <span role="heading" aria-level={3} className={`mt-2 block break-words text-2xl font-bold sm:text-3xl ${completed ? "line-through" : ""}`}>{step.title}</span>
          </span>
        </button>
        <div className={`transition-opacity duration-200 motion-reduce:transition-none ${completed ? "opacity-90" : "opacity-100"}`}>
          <MarkdownContent className="mt-6 space-y-5 text-xl leading-relaxed sm:text-2xl">{step.markdown}</MarkdownContent>
        </div>
        <button type="button" aria-label={completed ? `Desfazer conclusão da etapa ${number}` : `Concluir etapa ${number}`} aria-pressed={completed} disabled={disabled} onClick={() => toggle(step)} className={`mt-6 inline-flex min-h-12 items-center justify-center gap-2 rounded-xl px-5 py-3 text-base font-semibold disabled:opacity-50 ${completed ? "border border-success text-success" : "bg-primary text-primary-foreground"}`}>
          <Check aria-hidden="true" className="h-5 w-5" />
          {completed ? "Etapa concluída · Desfazer" : "Concluir etapa"}
        </button>
      </article>;
    })}
    {(section === "steps" || section === "preparation") && !steps.length && <div className="space-y-3 rounded-2xl border border-dashed p-8 text-lg">
      <p>Esta receita ainda não tem etapas cadastradas.</p>
      {recipeId && <Link href={`/receitas/${encodeURIComponent(recipeId)}/editar`} className="inline-flex min-h-12 items-center rounded-xl border px-4 py-3 font-semibold text-primary">Cadastrar etapas na receita</Link>}
    </div>}
    {steps.length > 0 && <button type="button" disabled={disabled || done === 0} onClick={() => {
      if (window.confirm("Reiniciar etapas? Todas as marcações deste preparo serão apagadas.")) onReset();
    }} className="min-h-12 rounded-xl border px-5 text-base font-semibold hover:bg-muted disabled:opacity-40">Reiniciar etapas</button>}
  </div>;
}
