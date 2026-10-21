"use client";

import { cloneElement, type ReactElement } from "react";
import { Controller as BaseController, useForm as baseUseForm, type FieldValues, type FieldPath, type UseFormProps, type UseFormReturn, type ControllerProps } from "react-hook-form";
import { errorMessage, fieldIssues } from "@/lib/validation";
export { useFieldArray } from "react-hook-form";
export type { SubmitHandler } from "react-hook-form";

export function useForm<T extends FieldValues>(props?: UseFormProps<T>): UseFormReturn<T> {
  const form = baseUseForm<T>(props);
  const submit: typeof form.handleSubmit = (valid, invalid) => async event => {
    form.clearErrors();
    await form.handleSubmit(async (values, submitEvent) => {
      const snapshot = JSON.stringify(form.getValues());
      try { await valid(values, submitEvent); }
      catch (error) {
        if (JSON.stringify(form.getValues()) !== snapshot) return;
        const issues = fieldIssues(error);
        if (issues.length) issues.forEach(issue => form.setError((issue.path || "root.server") as Parameters<typeof form.setError>[0], { type: "server", message: issue.message }));
        else form.setError("root.server", { type: "server", message: errorMessage(error) });
      }
    }, invalid)(event);
  };
  return { ...form, handleSubmit: submit };
}

/** Some existing Controller renderers omitted name/ref, preventing precise server feedback. */
export function Controller<T extends FieldValues, N extends FieldPath<T>>(props: ControllerProps<T, N>) {
  return <BaseController {...props} render={args => {
    const child = props.render(args) as ReactElement<Record<string, unknown>>;
    const aliases: Record<string, string> = { taxa_ifood_pct: "taxa_ifood", taxa_cartao_pct: "taxa_cartao" };
    return cloneElement(child, { name: args.field.name, "data-field": aliases[args.field.name], ...(typeof child.type === "string" ? { ref: args.field.ref } : {}) });
  }} />;
}
