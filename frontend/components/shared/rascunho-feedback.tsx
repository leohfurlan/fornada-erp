"use client";

import * as Dialog from "@radix-ui/react-dialog";

interface Props {
  message: string;
  pending: boolean;
  leave: (save: boolean) => void;
  stay: () => void;
}

export function RascunhoFeedback({ message, pending, leave, stay }: Props) {
  return <>
    {message && <p role="status" className="text-sm text-muted-foreground">{message}</p>}
    <Dialog.Root open={pending} onOpenChange={open => { if (!open) stay(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-sm -translate-x-1/2 -translate-y-1/2 space-y-4 rounded-xl bg-background p-5 shadow-xl">
          <Dialog.Title className="text-lg font-semibold">Deseja salvar como rascunho?</Dialog.Title>
          <Dialog.Description className="text-sm text-muted-foreground">Guarde suas alterações neste dispositivo para continuar depois.</Dialog.Description>
          {message.startsWith("Não foi possível") && <p role="alert" className="text-sm text-destructive">{message}</p>}
          <div className="flex flex-col gap-2">
            <button type="button" className="rounded-lg bg-primary px-4 py-3 text-primary-foreground" onClick={() => leave(true)}>Salvar rascunho e sair</button>
            <button type="button" className="rounded-lg border px-4 py-3" onClick={stay}>Continuar editando</button>
            <button type="button" className="rounded-lg px-4 py-3 text-destructive" onClick={() => leave(false)}>Descartar e sair</button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  </>;
}
