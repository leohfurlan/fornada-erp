"use client";
import * as Dialog from "@radix-ui/react-dialog";
import { usePwaInstall } from "@/components/shared/pwa-provider";

export function PwaInstall() {
  const pwa = usePwaInstall();
  if (!pwa) return null;
  return <>
    {pwa.error && <p role="alert" className="rounded border p-3 text-sm">{pwa.error}</p>}
    <Dialog.Root open={pwa.open} onOpenChange={(open) => { if (!open) pwa.dismiss(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl border bg-background p-5 shadow-xl">
          <Dialog.Title className="text-lg font-semibold">Deseja instalar o aplicativo Fornada?</Dialog.Title>
          <Dialog.Description className="my-3 text-sm text-muted-foreground">Acesse pela tela inicial do celular, com mais praticidade. O navegador pedirá sua confirmação.</Dialog.Description>
          <div className="flex flex-wrap gap-3">
            <button className="rounded bg-primary px-4 py-3 text-primary-foreground" disabled={pwa.busy} onClick={() => pwa.install("automatico")}>Instalar</button>
            <Dialog.Close asChild><button className="rounded border px-4 py-3">Agora não</button></Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  </>;
}
export function PwaInstallMenu() {
  const pwa = usePwaInstall();
  return pwa?.available ? <button className="rounded border px-3 py-2 text-sm" onClick={() => pwa.install("menu")}>Instalar aplicativo</button> : null;
}
