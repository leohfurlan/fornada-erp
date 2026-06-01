"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import {
  ArrowLeft,
  Camera,
  Check,
  CircleCheck,
  ClipboardList,
  Link2,
  Loader2,
  PlusCircle,
  Upload,
  X,
} from "lucide-react";
import { DecimalInput } from "@/components/shared/decimal-input";
import { UnidadeSelect } from "@/components/shared/unidade-select";
import { useIngredientes } from "@/hooks/use-estoque";
import { useConfirmarCompra, useProcessarCupom } from "@/hooks/use-compras";
import { cn, formatMoney } from "@/lib/utils";
import type {
  ApiError,
  ConfirmarCompraResponse,
  OcrComprasResponse,
  TipoIngrediente,
} from "@/types";
import type { AxiosError } from "axios";

type Etapa = "captura" | "revisao" | "concluido";

interface ItemEditavel {
  key: string;
  descricao: string;
  incluir: boolean;
  modo: "vincular" | "novo";
  ingrediente_id: string;
  nome: string;
  tipo: TipoIngrediente;
  unidade: string;
  quantidade: number;
  custo_unitario: number;
  score: number;
}

const TIPOS: { value: TipoIngrediente; label: string }[] = [
  { value: "ingrediente", label: "Ingrediente" },
  { value: "embalagem", label: "Embalagem" },
  { value: "insumo", label: "Insumo" },
  { value: "descartavel", label: "Descartável" },
  { value: "outro", label: "Outro" },
];

function itensDaResposta(resp: OcrComprasResponse): ItemEditavel[] {
  return resp.itens.map((it, i) => ({
    key: String(i),
    descricao: it.descricao,
    incluir: true,
    modo: it.ingrediente_id ? "vincular" : "novo",
    ingrediente_id: it.ingrediente_id ?? "",
    nome: it.nome_match ?? it.descricao,
    tipo: it.tipo_sugerido,
    unidade: it.unidade_sugerida,
    quantidade: parseFloat(it.quantidade) || 1,
    custo_unitario: parseFloat(it.preco_unitario) || 0,
    score: it.score,
  }));
}

export default function ComprasPage() {
  const [etapa, setEtapa] = useState<Etapa>("captura");
  const [itens, setItens] = useState<ItemEditavel[]>([]);
  const [estabelecimento, setEstabelecimento] = useState<string | null>(null);
  const [fonte, setFonte] = useState<string>("");
  const [resumo, setResumo] = useState<ConfirmarCompraResponse | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { data: ingredientes } = useIngredientes();
  const processar = useProcessarCupom();
  const confirmar = useConfirmarCompra();

  const erroProcessar = processar.error as AxiosError<ApiError> | null;
  const erroConfirmar = confirmar.error as AxiosError<ApiError> | null;

  const onArquivo = async (file: File | undefined) => {
    if (!file) return;
    const resp = await processar.mutateAsync(file);
    setItens(itensDaResposta(resp));
    setEstabelecimento(resp.estabelecimento);
    setFonte(resp.fonte);
    setEtapa("revisao");
  };

  const atualizar = (key: string, patch: Partial<ItemEditavel>) =>
    setItens((prev) => prev.map((it) => (it.key === key ? { ...it, ...patch } : it)));

  const escolherIngrediente = (key: string, ingredienteId: string) => {
    const ing = ingredientes?.find((i) => i.id === ingredienteId);
    atualizar(key, {
      ingrediente_id: ingredienteId,
      nome: ing?.nome ?? "",
      tipo: ing?.tipo ?? "ingrediente",
      unidade: ing?.unidade ?? "un",
    });
  };

  const incluidos = itens.filter((i) => i.incluir);
  const podeConfirmar =
    incluidos.length > 0 &&
    incluidos.every(
      (i) =>
        i.quantidade > 0 &&
        i.custo_unitario > 0 &&
        (i.modo === "vincular" ? !!i.ingrediente_id : i.nome.trim().length > 0)
    );

  const onConfirmar = async () => {
    const payload = {
      estabelecimento,
      itens: incluidos.map((i) => ({
        ingrediente_id: i.modo === "vincular" ? i.ingrediente_id : null,
        criar_novo: i.modo === "novo",
        nome: i.nome,
        tipo: i.tipo,
        unidade: i.unidade,
        quantidade: i.quantidade,
        custo_unitario: i.custo_unitario,
      })),
    };
    const r = await confirmar.mutateAsync(payload);
    setResumo(r);
    setEtapa("concluido");
  };

  // ---------- Etapa: captura ----------
  if (etapa === "captura") {
    return (
      <div className="space-y-6">
        <Link href="/estoque" className="flex items-center gap-1 text-sm text-muted-foreground">
          <ArrowLeft className="h-4 w-4" />
          Voltar
        </Link>

        <div className="space-y-1">
          <h1 className="text-xl font-bold">Entrada por cupom</h1>
          <p className="text-sm text-muted-foreground">
            Tire uma foto do cupom da compra. A gente lê os itens e atualiza seu
            estoque e o custo médio automaticamente.
          </p>
        </div>

        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={(e) => onArquivo(e.target.files?.[0])}
        />

        {processar.isPending ? (
          <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed py-16">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Lendo o cupom...</p>
          </div>
        ) : (
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="flex w-full flex-col items-center gap-3 rounded-2xl border-2 border-dashed border-primary/40 bg-primary/5 py-12 text-primary hover:bg-primary/10"
            >
              <Camera className="h-10 w-10" />
              <span className="text-base font-medium">Fotografar cupom</span>
            </button>
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="flex w-full items-center justify-center gap-2 rounded-lg border px-4 py-3 text-sm text-muted-foreground hover:bg-muted"
            >
              <Upload className="h-4 w-4" />
              Escolher imagem da galeria
            </button>
          </div>
        )}

        {erroProcessar?.response?.data?.detail && (
          <div className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {erroProcessar.response.data.detail}
          </div>
        )}

        <Link
          href="/compras/lista"
          className="flex items-center justify-center gap-2 rounded-lg border px-4 py-3 text-sm font-medium text-muted-foreground hover:bg-muted"
        >
          <ClipboardList className="h-4 w-4" />
          Ver lista de compras
        </Link>
      </div>
    );
  }

  // ---------- Etapa: concluído ----------
  if (etapa === "concluido" && resumo) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col items-center gap-3 py-8 text-center">
          <CircleCheck className="h-14 w-14 text-green-600" />
          <h1 className="text-xl font-bold">Compra registrada!</h1>
          <p className="text-sm text-muted-foreground">
            {resumo.ingredientes_atualizados} atualizado(s) e{" "}
            {resumo.ingredientes_criados} novo(s) no seu estoque. O custo médio já
            foi recalculado.
          </p>
        </div>
        <div className="flex flex-col gap-2">
          <Link
            href="/estoque"
            className="w-full rounded-lg bg-primary px-4 py-3 text-center text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Ver estoque
          </Link>
          <button
            type="button"
            onClick={() => {
              setEtapa("captura");
              setItens([]);
              setResumo(null);
              processar.reset();
              confirmar.reset();
            }}
            className="w-full rounded-lg border px-4 py-3 text-sm font-medium hover:bg-muted"
          >
            Registrar outra compra
          </button>
        </div>
      </div>
    );
  }

  // ---------- Etapa: revisão ----------
  return (
    <div className="space-y-5 pb-8">
      <button
        type="button"
        onClick={() => {
          setEtapa("captura");
          processar.reset();
        }}
        className="flex items-center gap-1 text-sm text-muted-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Refazer foto
      </button>

      <div className="space-y-1">
        <h1 className="text-xl font-bold">Conferir itens</h1>
        <p className="text-sm text-muted-foreground">
          {estabelecimento ? `${estabelecimento} · ` : ""}
          Revise quantidades e preços antes de salvar.
        </p>
        {fonte === "mock" && (
          <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">
            Modo demonstração (sem chave de OCR): itens de exemplo. Configure a
            leitura real nas configurações.
          </p>
        )}
      </div>

      <div className="space-y-3">
        {itens.map((it) => (
          <div
            key={it.key}
            className={cn(
              "rounded-xl border p-3 space-y-3 transition-opacity",
              !it.incluir && "opacity-50"
            )}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">{it.descricao}</p>
                {it.modo === "vincular" && it.score > 0 && (
                  <p className="text-[11px] text-muted-foreground">
                    Reconhecido automaticamente
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={() => atualizar(it.key, { incluir: !it.incluir })}
                className={cn(
                  "shrink-0 rounded-lg p-1.5",
                  it.incluir
                    ? "text-muted-foreground hover:bg-muted"
                    : "text-primary hover:bg-primary/10"
                )}
                aria-label={it.incluir ? "Ignorar item" : "Incluir item"}
              >
                {it.incluir ? <X className="h-4 w-4" /> : <Check className="h-4 w-4" />}
              </button>
            </div>

            {it.incluir && (
              <>
                {/* Alternância vincular x novo */}
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => atualizar(it.key, { modo: "vincular" })}
                    className={cn(
                      "flex items-center justify-center gap-1.5 rounded-lg border px-2 py-2 text-xs font-medium",
                      it.modo === "vincular"
                        ? "border-primary bg-primary/10 text-primary"
                        : "hover:bg-muted"
                    )}
                  >
                    <Link2 className="h-3.5 w-3.5" />
                    Existente
                  </button>
                  <button
                    type="button"
                    onClick={() => atualizar(it.key, { modo: "novo" })}
                    className={cn(
                      "flex items-center justify-center gap-1.5 rounded-lg border px-2 py-2 text-xs font-medium",
                      it.modo === "novo"
                        ? "border-primary bg-primary/10 text-primary"
                        : "hover:bg-muted"
                    )}
                  >
                    <PlusCircle className="h-3.5 w-3.5" />
                    Novo
                  </button>
                </div>

                {it.modo === "vincular" ? (
                  <select
                    className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary bg-background"
                    value={it.ingrediente_id}
                    onChange={(e) => escolherIngrediente(it.key, e.target.value)}
                  >
                    <option value="">Selecione o ingrediente...</option>
                    {ingredientes?.map((ing) => (
                      <option key={ing.id} value={ing.id}>
                        {ing.nome}
                      </option>
                    ))}
                  </select>
                ) : (
                  <div className="space-y-2">
                    <input
                      type="text"
                      value={it.nome}
                      onChange={(e) => atualizar(it.key, { nome: e.target.value })}
                      placeholder="Nome do ingrediente"
                      className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                    <div className="grid grid-cols-2 gap-2">
                      <select
                        className="w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary bg-background"
                        value={it.tipo}
                        onChange={(e) =>
                          atualizar(it.key, { tipo: e.target.value as TipoIngrediente })
                        }
                      >
                        {TIPOS.map((t) => (
                          <option key={t.value} value={t.value}>
                            {t.label}
                          </option>
                        ))}
                      </select>
                      <UnidadeSelect
                        tipo="medida"
                        value={it.unidade}
                        onChange={(e) => atualizar(it.key, { unidade: e.target.value })}
                      />
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-xs text-muted-foreground">Quantidade</label>
                    <DecimalInput
                      value={it.quantidade}
                      onChange={(v) => atualizar(it.key, { quantidade: v })}
                      placeholder="1"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground">Custo unit. (R$)</label>
                    <DecimalInput
                      value={it.custo_unitario}
                      onChange={(v) => atualizar(it.key, { custo_unitario: v })}
                      placeholder="0,00"
                    />
                  </div>
                </div>
              </>
            )}
          </div>
        ))}
      </div>

      {erroConfirmar?.response?.data?.detail && (
        <div className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {erroConfirmar.response.data.detail}
        </div>
      )}

      <button
        type="button"
        onClick={onConfirmar}
        disabled={!podeConfirmar || confirmar.isPending}
        className="w-full rounded-lg bg-primary px-4 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
      >
        {confirmar.isPending
          ? "Salvando..."
          : `Salvar ${incluidos.length} ${incluidos.length === 1 ? "item" : "itens"}`}
      </button>
    </div>
  );
}
