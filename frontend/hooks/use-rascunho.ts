"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuthStore } from "@/stores/use-auth-store";

function matchesShape(value: unknown, example: unknown): boolean {
  if (example === null || example === undefined) return true;
  if (Array.isArray(example)) return Array.isArray(value) && value.every(item => matchesShape(item, example[0]));
  if (typeof example === "object") return !!value && typeof value === "object" &&
    Object.entries(example).every(([field, sample]) => matchesShape((value as Record<string, unknown>)[field], sample));
  return typeof value === typeof example;
}

/** Synchronous local writes also protect against mobile process termination. */
export function useRascunho<T extends object>(id: string, initial: T | null, restore: (value: T) => void) {
  const usuario = useAuthStore(s => s.usuario);
  const key = usuario ? `fornada:rascunho:v1:${usuario.tenant_id}:${usuario.id}:${id}` : null;
  const baseline = useRef<string | null>(null);
  const latest = useRef<T | null>(null);
  const dirty = useRef(false);
  const initialized = useRef<string | null>(null);
  const restoreRef = useRef(restore);
  restoreRef.current = restore;
  const [message, setMessage] = useState("");
  const [readyKey, setReadyKey] = useState<string | null>(null);
  const [pending, setPending] = useState<(() => void) | null>(null);

  const persist = useCallback((value: T) => {
    latest.current = value;
    dirty.current = JSON.stringify(value) !== baseline.current;
    if (!key || initialized.current !== key) return;
    try {
      if (dirty.current) localStorage.setItem(key, JSON.stringify({ value, savedAt: new Date().toISOString() }));
      else localStorage.removeItem(key);
      setMessage(dirty.current ? "Rascunho salvo automaticamente neste dispositivo." : "");
      return true;
    } catch {
      setMessage("Não foi possível salvar o rascunho neste dispositivo. Mantenha esta página aberta e tente salvar novamente.");
      return false;
    }
  }, [key]);

  useEffect(() => {
    if (!key || initial === null || initialized.current === key) return;
    initialized.current = key;
    setReadyKey(key);
    baseline.current = JSON.stringify(initial);
    latest.current = initial;
    dirty.current = false;
    try {
      const raw = localStorage.getItem(key);
      if (raw) {
        const draft = JSON.parse(raw);
        // Only accept the same top-level shape; old revisions remain intact for API conflict checks.
        if (!matchesShape(draft.value, initial)) throw new Error("invalid draft");
        latest.current = draft.value;
        dirty.current = JSON.stringify(draft.value) !== baseline.current;
        restoreRef.current(draft.value);
        setMessage("Rascunho recuperado. Você pode continuar de onde parou.");
      } else restoreRef.current(initial);
    } catch {
      restoreRef.current(initial);
      setMessage("Não foi possível recuperar o rascunho neste dispositivo.");
    }
  }, [key, initial]);

  const complete = useCallback((saved?: T, submitted?: T) => {
    if (submitted && JSON.stringify(latest.current) !== JSON.stringify(submitted)) {
      baseline.current = JSON.stringify(saved ?? submitted);
      if (latest.current !== null) persist(latest.current);
      return;
    }
    if (key) {
      try { localStorage.removeItem(key); } catch { /* Keep the saved server result usable. */ }
    }
    baseline.current = JSON.stringify(saved ?? latest.current);
    latest.current = saved ?? latest.current;
    dirty.current = false;
    setMessage("");
  }, [key, persist]);

  const requestExit = useCallback((action: () => void) => {
    if (!dirty.current) action();
    else setPending(() => action);
  }, []);

  useEffect(() => {
    if (!key || readyKey !== key) return;
    const flush = () => { if (dirty.current && latest.current !== null) persist(latest.current); };
    const unload = (event: BeforeUnloadEvent) => {
      if (!dirty.current) return;
      flush();
      event.preventDefault();
      event.returnValue = "";
    };
    const click = (event: MouseEvent) => {
      if (!dirty.current || event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      const target = event.target instanceof Element ? event.target.closest<HTMLAnchorElement | HTMLButtonElement>("a[href], [data-rascunho-sair]") : null;
      if (!target || target instanceof HTMLAnchorElement && (target.target === "_blank" || target.hasAttribute("download") || target.href === location.href || target.getAttribute("href")?.startsWith("#"))) return;
      event.preventDefault();
      event.stopPropagation();
      requestExit(() => target.click());
    };
    // Keep a same-page entry so browser/device Back can ask before unmounting the editor.
    const url = location.href;
    let guarded = false;
    const arm = () => {
      if (!guarded && dirty.current) {
        history.pushState({ ...history.state, fornadaDraftGuard: true }, "", url);
        guarded = true;
      }
    };
    const pop = () => {
      if (!guarded) return;
      guarded = false;
      if (!dirty.current) { history.back(); return; }
      history.pushState({ ...history.state, fornadaDraftGuard: true }, "", url);
      guarded = true;
      requestExit(() => { guarded = false; history.go(-2); });
    };
    arm();
    document.addEventListener("input", arm);
    document.addEventListener("change", arm);
    document.addEventListener("click", arm);
    document.addEventListener("click", click, true);
    window.addEventListener("beforeunload", unload);
    window.addEventListener("pagehide", flush);
    document.addEventListener("visibilitychange", flush);
    window.addEventListener("popstate", pop);
    return () => {
      document.removeEventListener("input", arm);
      document.removeEventListener("change", arm);
      document.removeEventListener("click", arm);
      document.removeEventListener("click", click, true);
      window.removeEventListener("beforeunload", unload);
      window.removeEventListener("pagehide", flush);
      document.removeEventListener("visibilitychange", flush);
      window.removeEventListener("popstate", pop);
    };
  }, [key, readyKey, persist, requestExit]);

  const leave = (save: boolean) => {
    if (save && latest.current !== null && persist(latest.current) !== true) return;
    if (!save) complete();
    dirty.current = false;
    const action = pending;
    setPending(null);
    action?.();
  };
  return { persist, complete, requestExit, message, pending: !!pending, leave, stay: () => setPending(null) };
}
