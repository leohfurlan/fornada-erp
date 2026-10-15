"use client";

import { useId, useLayoutEffect, useRef, useState, type FormHTMLAttributes, type ReactNode } from "react";
import { errorMessage, fieldIssues, fieldLabel, formIssues, type FieldIssue } from "@/lib/validation";

type Control = HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement | HTMLButtonElement;

function controlLabel(field?: Control): string | undefined {
  if (field?.getAttribute("aria-label")) return field.getAttribute("aria-label")!;
  const label = field?.labels?.[0]?.cloneNode(true) as HTMLElement | undefined;
  label?.querySelectorAll("input,select,textarea,button,.field-validation-message").forEach(node => node.remove());
  return label?.textContent?.trim();
}

function nativeMessage(field: Control): string {
  const validity = field.validity;
  if (validity.valueMissing) return "Preencha este campo.";
  if (validity.typeMismatch) return field instanceof HTMLInputElement && field.type === "email" ? "Informe um e-mail válido." : "Informe um valor válido.";
  if (validity.tooShort) return `Informe pelo menos ${field.getAttribute("minlength")} caracteres.`;
  if (validity.tooLong) return `Use no máximo ${field.getAttribute("maxlength")} caracteres.`;
  if (validity.rangeUnderflow) return `Informe um valor maior ou igual a ${field.getAttribute("min")}.`;
  if (validity.rangeOverflow) return `Informe um valor menor ou igual a ${field.getAttribute("max")}.`;
  if (validity.customError) return field.validationMessage;
  return "Confira o formato informado neste campo.";
}

export function focusField(field: HTMLElement) {
  let parent = field.parentElement;
  while (parent) {
    if (parent instanceof HTMLDetailsElement) parent.open = true;
    parent = parent.parentElement;
  }
  field.focus();
  field.scrollIntoView?.({ block: "center", behavior: "smooth" });
}

/** Adapter scoped to legacy/native forms: preserves their state and existing descriptions. */
export function ValidationFeedback({ issues = [], error, errors, fallback }: {
  issues?: FieldIssue[]; error?: unknown; errors?: unknown; fallback?: string;
}) {
  const anchor = useRef<HTMLDivElement>(null);
  const id = useId();
  const [native, setNative] = useState<FieldIssue[]>([]);
  const [cleared, setCleared] = useState<string[]>([]);
  const signature = JSON.stringify([...issues, ...fieldIssues(error), ...formIssues(errors)]);
  const [resolved, setResolved] = useState<Array<FieldIssue & { label: string; field?: Control }>>([]);
  useLayoutEffect(() => { setCleared([]); }, [signature, error, errors]);
  useLayoutEffect(() => {
    const root = anchor.current?.closest("[data-validation-scope], form");
    if (!root) return;
    const invalid = (event: Event) => {
      if (!(event.target instanceof HTMLInputElement || event.target instanceof HTMLSelectElement || event.target instanceof HTMLTextAreaElement)) return;
      const field = event.target;
      const path = field.name || field.dataset.field || field.id;
      if (!path) return;
      event.preventDefault();
      setCleared(previous => previous.filter(p => p !== path));
      const message = nativeMessage(field);
      setNative(previous => [...previous.filter(i => i.path !== path), { path, message }]);
    };
    const changed = (event: Event) => {
      const field = event.target as Control;
      const paths = [field.name, field.dataset?.field, field.id].filter((path): path is string => !!path);
      if (!paths.length) return;
      setNative(previous => previous.filter(i => !paths.includes(i.path)));
      setCleared(previous => Array.from(new Set([...previous, ...paths])));
    };
    root.addEventListener("invalid", invalid, true);
    root.addEventListener("input", changed);
    root.addEventListener("change", changed);
    return () => {
      root.removeEventListener("invalid", invalid, true);
      root.removeEventListener("input", changed);
      root.removeEventListener("change", changed);
    };
  }, []);
  const effective = JSON.stringify([...JSON.parse(signature) as FieldIssue[], ...native].filter(i => !cleared.includes(i.path)));
  useLayoutEffect(() => {
    const root = anchor.current?.closest("[data-validation-scope], form");
    if (!root) return;
    const controls = Array.from(root.querySelectorAll<Control>("input,select,textarea,button[data-file-picker]"));
    const cleanup: Array<() => void> = [];
    const seen = new Set<string>();
    const next = (JSON.parse(effective) as FieldIssue[]).filter(issue => {
      const key = `${issue.path}:${issue.message}`;
      if (seen.has(key)) return false;
      seen.add(key); return true;
    }).map((issue, index) => {
      const matches = controls.filter(c => [c.name, c.dataset.field, c.id].includes(issue.path));
      const field = matches.find(c => !(c instanceof HTMLInputElement && c.type === "file")) ?? matches[0];
      const explicitLabel = controlLabel(field);
      const itemLabel = field?.closest<HTMLElement>("[data-validation-label]")?.dataset.validationLabel;
      const context = itemLabel ? [itemLabel] : fieldLabel(issue.path).split(" — ").slice(0, -1);
      const label = explicitLabel ? [...context, explicitLabel].join(" — ") : fieldLabel(issue.path);
      if (field) {
        const previousInvalid = field.getAttribute("aria-invalid");
        const previousDescription = field.getAttribute("aria-describedby");
        const message = document.createElement("p");
        message.id = `${id}-${index}`;
        message.className = "text-xs text-destructive field-validation-message";
        message.textContent = `${label}: ${issue.message}`;
        field.after(message);
        field.setAttribute("aria-invalid", "true");
        field.setAttribute("aria-describedby", [previousDescription, message.id].filter(Boolean).join(" "));
        cleanup.push(() => {
          message.remove();
          if (previousInvalid === null) field.removeAttribute("aria-invalid"); else field.setAttribute("aria-invalid", previousInvalid);
          if (previousDescription === null) field.removeAttribute("aria-describedby"); else field.setAttribute("aria-describedby", previousDescription);
        });
      }
      return { ...issue, label, field };
    });
    setResolved(next);
    const first = next.find(i => i.field)?.field;
    if (first && !cleared.length) focusField(first);
    return () => cleanup.forEach(fn => fn());
  }, [effective, id]);
  const general = error && !fieldIssues(error).length ? errorMessage(error, fallback) : "";
  if (!resolved.length && !general) return <div ref={anchor} />;
  return <div ref={anchor} role="alert" className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive space-y-1">
    {resolved.length > 0 && <p>Confira os campos indicados:</p>}
    {resolved.map((issue, index) => <p key={`${issue.path}-${index}`}>
      {issue.field ? <button type="button" className="text-left underline" onClick={() => focusField(issue.field!)}>{issue.label}: {issue.message}</button> : `${issue.path ? issue.label : "Dados informados"}: ${issue.message}`}
    </p>)}
    {!!general && <p>{general}</p>}
  </div>;
}

export function ValidatedForm({ children, error, errors, issues, ...props }: FormHTMLAttributes<HTMLFormElement> & { error?: unknown; errors?: unknown; issues?: FieldIssue[] }) {
  return <form {...props}>{children}<ValidationFeedback error={error} errors={errors} issues={issues} /></form>;
}

export function ValidationScope({ children, issues, error, className, fallback }: { children: ReactNode; issues?: FieldIssue[]; error?: unknown; className?: string; fallback?: string }) {
  return <div data-validation-scope className={className}>{children}<ValidationFeedback issues={issues} error={error} fallback={fallback} /></div>;
}
