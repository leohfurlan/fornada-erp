"use client";

import { useEffect, useMemo, useState } from "react";
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type ColumnOrderState,
  type ColumnSizingState,
  type SortingState,
  type VisibilityState,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ArrowUpDown, Columns3, GripVertical, RotateCcw } from "lucide-react";
import { EstoqueBadge } from "@/components/shared/estoque-badge";
import { MoneyDisplay } from "@/components/shared/money-display";
import { TIPOS_PRODUTO } from "@/lib/unidades";
import { cn, formatDataHora, formatQuantidade } from "@/lib/utils";
import type { Ingrediente } from "@/types";

/**
 * Tabela de estoque para desktop com:
 * - Ordenação (click no cabeçalho)
 * - Resize manual de colunas (alça vertical no canto direito do cabeçalho)
 * - Reordenação de colunas (drag-and-drop pelo handle ≡ à esquerda do cabeçalho)
 * - Visibility (botão Colunas abre menu com checkboxes)
 * - Persistência em localStorage (chave fornada:estoque:cols-v1)
 *
 * Mobile usa cards expansíveis (componente separado em estoque/page.tsx).
 */

const STORAGE_KEY = "fornada:estoque:cols-v1";

interface PreferenciasColunas {
  order: ColumnOrderState;
  visibility: VisibilityState;
  sizing: ColumnSizingState;
}

const tipoLabel = (value: string) =>
  TIPOS_PRODUTO.find((t) => t.value === value)?.label ?? value;

interface TabelaEstoqueDesktopProps {
  ingredientes: Ingrediente[];
}

export function TabelaEstoqueDesktop({ ingredientes }: TabelaEstoqueDesktopProps) {
  const colunas = useMemo<ColumnDef<Ingrediente>[]>(
    () => [
      {
        id: "codigo",
        accessorKey: "codigo",
        header: "Cód.",
        size: 70,
        minSize: 60,
        cell: ({ getValue }) => (
          <span className="font-mono text-xs text-muted-foreground">
            {String(getValue() as number).padStart(3, "0")}
          </span>
        ),
        meta: { align: "right" } as const,
      },
      {
        id: "tipo",
        accessorKey: "tipo",
        header: "Tipo",
        size: 120,
        cell: ({ getValue }) => (
          <span className="inline-block rounded-full bg-muted px-2 py-0.5 text-xs">
            {tipoLabel(getValue() as string)}
          </span>
        ),
      },
      {
        id: "nome",
        accessorKey: "nome",
        header: "Descrição",
        size: 240,
        cell: ({ row }) => (
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium">{row.original.nome}</span>
              <EstoqueBadge status={row.original.status_estoque} />
            </div>
            <p className="text-xs text-muted-foreground">{row.original.unidade}</p>
          </div>
        ),
      },
      {
        id: "estoque_atual",
        accessorKey: "estoque_atual",
        header: "Estoque",
        size: 100,
        cell: ({ getValue }) => formatQuantidade(getValue() as string),
        meta: { align: "right" } as const,
        sortingFn: numericSort,
      },
      {
        id: "quantidade_reservada",
        accessorKey: "quantidade_reservada",
        header: "Reservado",
        size: 110,
        cell: ({ getValue }) => (
          <span className="text-muted-foreground">{formatQuantidade(getValue() as string)}</span>
        ),
        meta: { align: "right" } as const,
        sortingFn: numericSort,
      },
      {
        id: "saldo",
        accessorKey: "saldo",
        header: "Saldo",
        size: 100,
        cell: ({ getValue }) => (
          <span className="font-medium">{formatQuantidade(getValue() as string)}</span>
        ),
        meta: { align: "right" } as const,
        sortingFn: numericSort,
      },
      {
        id: "estoque_minimo",
        accessorKey: "estoque_minimo",
        header: "Mínimo",
        size: 100,
        cell: ({ getValue }) => (
          <span className="text-muted-foreground">{formatQuantidade(getValue() as string)}</span>
        ),
        meta: { align: "right" } as const,
        sortingFn: numericSort,
      },
      {
        id: "custo_medio",
        accessorKey: "custo_medio",
        header: "Custo (R$)",
        size: 110,
        cell: ({ getValue }) => <MoneyDisplay value={getValue() as string} size="sm" />,
        meta: { align: "right" } as const,
        sortingFn: numericSort,
      },
      {
        id: "data_custo_atualizado",
        accessorKey: "data_custo_atualizado",
        header: "Data custo",
        size: 140,
        cell: ({ getValue }) => (
          <span className="text-xs text-muted-foreground">{formatDataHora(getValue() as string)}</span>
        ),
        meta: { align: "right" } as const,
      },
    ],
    []
  );

  const defaultOrder = useMemo(() => colunas.map((c) => c.id!), [colunas]);

  // Estado controlado e persistido
  const [columnOrder, setColumnOrder] = useState<ColumnOrderState>(defaultOrder);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
  const [columnSizing, setColumnSizing] = useState<ColumnSizingState>({});
  const [sorting, setSorting] = useState<SortingState>([{ id: "codigo", desc: false }]);
  const [hidratado, setHidratado] = useState(false);

  // Carrega preferências salvas
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const prefs = JSON.parse(raw) as PreferenciasColunas;
        if (prefs.order?.length) setColumnOrder(prefs.order);
        if (prefs.visibility) setColumnVisibility(prefs.visibility);
        if (prefs.sizing) setColumnSizing(prefs.sizing);
      }
    } catch {
      // ignora corrupção do localStorage
    }
    setHidratado(true);
  }, []);

  // Salva preferências a cada mudança (após hidratação para não sobrescrever com defaults)
  useEffect(() => {
    if (!hidratado) return;
    const prefs: PreferenciasColunas = {
      order: columnOrder,
      visibility: columnVisibility,
      sizing: columnSizing,
    };
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    } catch {
      // localStorage cheio ou bloqueado
    }
  }, [columnOrder, columnVisibility, columnSizing, hidratado]);

  const table = useReactTable({
    data: ingredientes,
    columns: colunas,
    state: { columnOrder, columnVisibility, columnSizing, sorting },
    onColumnOrderChange: setColumnOrder,
    onColumnVisibilityChange: setColumnVisibility,
    onColumnSizingChange: setColumnSizing,
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    columnResizeMode: "onChange",
    enableColumnResizing: true,
  });

  const resetar = () => {
    setColumnOrder(defaultOrder);
    setColumnVisibility({});
    setColumnSizing({});
    setSorting([{ id: "codigo", desc: false }]);
  };

  return (
    <div className="space-y-2">
      {/* Toolbar */}
      <div className="flex justify-end">
        <MenuColunas table={table} onResetar={resetar} />
      </div>

      {/* Tabela: w-full preenche o container; minWidth garante scroll horizontal
          se as colunas somadas forem maiores que a tela. */}
      <div className="overflow-x-auto rounded-xl border w-full">
        <table
          className="text-sm w-full"
          style={{ minWidth: table.getCenterTotalSize() }}
        >
          <thead className="bg-muted/30">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const align = (header.column.columnDef.meta as { align?: string } | undefined)?.align;
                  const sorted = header.column.getIsSorted();
                  return (
                    <th
                      key={header.id}
                      colSpan={header.colSpan}
                      style={{ width: header.getSize() }}
                      className="relative px-3 py-2 text-xs font-semibold text-muted-foreground select-none group"
                      draggable={!header.column.getIsResizing()}
                      onDragStart={(e) => {
                        if (header.column.getIsResizing()) { e.preventDefault(); return; }
                        handleDragStart(e, header.column.id);
                      }}
                      onDragOver={(e) => e.preventDefault()}
                      onDrop={(e) => handleDrop(e, header.column.id, table)}
                    >
                      <div
                        className={cn(
                          "flex items-center gap-1",
                          align === "right" && "flex-row-reverse text-right"
                        )}
                      >
                        <GripVertical className="h-3 w-3 text-muted-foreground/40 cursor-grab opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                        <button
                          type="button"
                          onClick={header.column.getToggleSortingHandler()}
                          className="inline-flex items-center gap-1 hover:text-foreground truncate"
                        >
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          {sorted === "asc" ? (
                            <ArrowUp className="h-3 w-3 shrink-0" />
                          ) : sorted === "desc" ? (
                            <ArrowDown className="h-3 w-3 shrink-0" />
                          ) : (
                            <ArrowUpDown className="h-3 w-3 shrink-0 opacity-30" />
                          )}
                        </button>
                      </div>

                      {/* Handle de resize — 8px de área de toque, 2px visíveis.
                          stopPropagation evita acionar o drag de reorder. */}
                      <div
                        onMouseDown={(e) => {
                          e.stopPropagation();
                          header.getResizeHandler()(e);
                        }}
                        onTouchStart={(e) => {
                          e.stopPropagation();
                          header.getResizeHandler()(e);
                        }}
                        onClick={(e) => e.stopPropagation()}
                        draggable={false}
                        className={cn(
                          "absolute right-0 top-0 h-full w-2 cursor-col-resize select-none touch-none",
                          "flex items-center justify-end pr-[1px]",
                          header.column.getIsResizing() ? "opacity-100" : "opacity-0 group-hover:opacity-100",
                        )}
                      >
                        <div className={cn(
                          "w-0.5 h-4 rounded-full transition-colors",
                          header.column.getIsResizing() ? "bg-primary" : "bg-muted-foreground/40"
                        )} />
                      </div>
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y">
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="hover:bg-muted/30">
                {row.getVisibleCells().map((cell) => {
                  const align = (cell.column.columnDef.meta as { align?: string } | undefined)?.align;
                  return (
                    <td
                      key={cell.id}
                      style={{ width: cell.column.getSize(), maxWidth: cell.column.getSize() }}
                      className={cn(
                        "px-3 py-2 tabular-nums",
                        align === "right" && "text-right",
                        align === "center" && "text-center"
                      )}
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// -------- Helpers --------

function numericSort(
  rowA: { getValue: (id: string) => unknown },
  rowB: { getValue: (id: string) => unknown },
  columnId: string
): number {
  const av = parseFloat(String(rowA.getValue(columnId) ?? "0"));
  const bv = parseFloat(String(rowB.getValue(columnId) ?? "0"));
  return av - bv;
}

function handleDragStart(e: React.DragEvent<HTMLTableCellElement>, columnId: string) {
  e.dataTransfer.setData("text/plain", columnId);
  e.dataTransfer.effectAllowed = "move";
}

function handleDrop<T>(
  e: React.DragEvent<HTMLTableCellElement>,
  destinoId: string,
  table: ReturnType<typeof useReactTable<T>>
) {
  e.preventDefault();
  const origemId = e.dataTransfer.getData("text/plain");
  if (!origemId || origemId === destinoId) return;

  const ordem = table.getState().columnOrder.length
    ? [...table.getState().columnOrder]
    : table.getAllLeafColumns().map((c) => c.id);

  const fromIdx = ordem.indexOf(origemId);
  const toIdx = ordem.indexOf(destinoId);
  if (fromIdx === -1 || toIdx === -1) return;

  ordem.splice(toIdx, 0, ordem.splice(fromIdx, 1)[0]);
  table.setColumnOrder(ordem);
}

// -------- Menu de visibilidade de colunas --------

function MenuColunas<T>({
  table,
  onResetar,
}: {
  table: ReturnType<typeof useReactTable<T>>;
  onResetar: () => void;
}) {
  const [aberto, setAberto] = useState(false);

  // Fecha ao clicar fora
  useEffect(() => {
    if (!aberto) return;
    const handler = (e: MouseEvent) => {
      const alvo = e.target as HTMLElement;
      if (!alvo.closest("[data-menu-colunas]")) setAberto(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [aberto]);

  return (
    <div className="relative" data-menu-colunas>
      <button
        type="button"
        onClick={() => setAberto((v) => !v)}
        className="flex items-center gap-1.5 rounded-lg border bg-card px-3 py-1.5 text-sm hover:bg-muted"
      >
        <Columns3 className="h-4 w-4" />
        Colunas
      </button>

      {aberto && (
        <div className="absolute right-0 top-full mt-1 z-20 w-56 rounded-xl border bg-popover shadow-lg p-2 space-y-0.5">
          <p className="px-2 py-1 text-xs font-semibold text-muted-foreground">
            Exibir colunas
          </p>
          {table.getAllLeafColumns().map((col) => (
            <label
              key={col.id}
              className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted cursor-pointer"
            >
              <input
                type="checkbox"
                checked={col.getIsVisible()}
                onChange={col.getToggleVisibilityHandler()}
                className="h-4 w-4 accent-primary"
              />
              {flexRender(col.columnDef.header, {
                column: col,
                header: undefined as never,
                table: undefined as never,
              } as never)}
            </label>
          ))}
          <div className="border-t mt-1 pt-1">
            <button
              type="button"
              onClick={() => {
                onResetar();
                setAberto(false);
              }}
              className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm text-muted-foreground hover:bg-muted"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Restaurar padrão
            </button>
          </div>
          <p className="px-2 pt-1 text-[10px] text-muted-foreground leading-tight">
            💡 Arraste o cabeçalho para reordenar. Arraste a borda direita para redimensionar.
          </p>
        </div>
      )}
    </div>
  );
}
