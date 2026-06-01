"use client";

import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  Calendar,
  ChefHat,
  Package,
  ShoppingBag,
  type LucideIcon,
} from "lucide-react";
import { useDashboardResumo, type AlertaEstoque } from "@/hooks/use-dashboard";
import { useAuthStore } from "@/stores/use-auth-store";
import { cn, formatMoney, formatQuantidade } from "@/lib/utils";

function getSaudacao(): string {
  const hora = new Date().getHours();
  if (hora < 12) return "Bom dia";
  if (hora < 18) return "Boa tarde";
  return "Boa noite";
}

function capitalizar(texto: string): string {
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

export default function DashboardPage() {
  const { data, isLoading } = useDashboardResumo();
  const router = useRouter();
  const { usuario } = useAuthStore();

  const dataHoje = capitalizar(
    new Intl.DateTimeFormat("pt-BR", {
      weekday: "long",
      day: "numeric",
      month: "long",
    }).format(new Date())
  );

  const alertas = data?.alertas_estoque ?? [];
  const primeiroNome = usuario?.nome?.split(" ")[0] ?? "";

  return (
    <div className="space-y-6">
      {/* Saudação */}
      <div>
        <h1 className="text-xl font-semibold">
          {getSaudacao()}
          {primeiroNome ? `, ${primeiroNome}` : ""}
        </h1>
        <p className="text-sm text-muted-foreground">{dataHoje}</p>
      </div>

      {/* Métricas */}
      <div className="grid grid-cols-2 gap-3">
        <MetricaCard
          valor={formatMoney(data?.faturamento_semana)}
          label="Faturado esta semana"
          loading={isLoading}
          className="border-orange-200 bg-orange-50"
          valorClassName="text-orange-700"
        />
        <MetricaCard
          valor={String(data?.pedidos_em_aberto ?? 0)}
          label="Pedidos em aberto"
          loading={isLoading}
        />
        <MetricaCard
          valor={String(data?.ops_hoje ?? 0)}
          label="OPs planejadas hoje"
          loading={isLoading}
        />
        <MetricaCard
          valor={String(alertas.length)}
          label="Itens em alerta"
          loading={isLoading}
          className={alertas.length > 0 ? "border-amber-200 bg-amber-50" : undefined}
          valorClassName={alertas.length > 0 ? "text-amber-700" : undefined}
        />
      </div>

      {/* Alertas de estoque */}
      {alertas.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Estoque em alerta
          </h2>
          <div className="space-y-2">
            {alertas.slice(0, 3).map((alerta) => (
              <AlertaCard key={alerta.ingrediente_id} alerta={alerta} />
            ))}
          </div>
          {alertas.length > 3 && (
            <p className="text-xs text-muted-foreground">
              + {alertas.length - 3}{" "}
              {alertas.length - 3 === 1 ? "outro item" : "outros itens"}
            </p>
          )}
          <button
            type="button"
            onClick={() => router.push("/estoque")}
            className="text-xs text-primary"
          >
            Ver estoque completo
          </button>
        </section>
      )}

      {/* Ações rápidas */}
      <section className="space-y-2">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Ações rápidas
        </h2>
        <div className="grid grid-cols-2 gap-3">
          <AcaoRapida
            icon={ChefHat}
            iconBg="bg-orange-100"
            iconColor="text-orange-600"
            label="Nova OP"
            subtitulo="Iniciar produção"
            onClick={() => router.push("/producao/nova")}
          />
          <AcaoRapida
            icon={ShoppingBag}
            iconBg="bg-violet-100"
            iconColor="text-violet-600"
            label="Registrar venda"
            subtitulo="Pronta entrega"
            onClick={() => router.push("/vendas/nova")}
          />
          <AcaoRapida
            icon={Package}
            iconBg="bg-green-100"
            iconColor="text-green-600"
            label="Entrada de compra"
            subtitulo="Atualizar estoque"
            onClick={() => router.push("/estoque")}
          />
          <AcaoRapida
            icon={Calendar}
            iconBg="bg-blue-100"
            iconColor="text-blue-600"
            label="Ver agenda"
            subtitulo="Planejamento do dia"
            onClick={() => router.push("/agenda")}
          />
        </div>
      </section>
    </div>
  );
}

function MetricaCard({
  valor,
  label,
  loading,
  className,
  valorClassName,
}: {
  valor: string;
  label: string;
  loading?: boolean;
  className?: string;
  valorClassName?: string;
}) {
  return (
    <div className={cn("rounded-xl border bg-card p-4", className)}>
      {loading ? (
        <div className="h-7 w-20 rounded bg-muted animate-pulse" />
      ) : (
        <p className={cn("text-2xl font-bold", valorClassName)}>{valor}</p>
      )}
      <p className="mt-1 text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

function AlertaCard({ alerta }: { alerta: AlertaEstoque }) {
  const grave = alerta.status === "critico" || alerta.status === "zerado";
  return (
    <div
      className={cn(
        "flex items-start gap-2 rounded-xl border px-4 py-3",
        grave ? "border-red-200 bg-red-50" : "border-amber-200 bg-amber-50"
      )}
    >
      <AlertTriangle
        className={cn("mt-0.5 h-4 w-4 shrink-0", grave ? "text-red-500" : "text-amber-500")}
      />
      <div className="min-w-0">
        <p className="text-sm font-medium">{alerta.nome}</p>
        <p className="text-xs text-muted-foreground">
          {formatQuantidade(alerta.estoque_atual)} {alerta.unidade} restante · mínimo:{" "}
          {formatQuantidade(alerta.estoque_minimo)} {alerta.unidade}
        </p>
      </div>
    </div>
  );
}

function AcaoRapida({
  icon: Icon,
  iconBg,
  iconColor,
  label,
  subtitulo,
  onClick,
}: {
  icon: LucideIcon;
  iconBg: string;
  iconColor: string;
  label: string;
  subtitulo: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-xl border bg-card p-4 text-left transition-transform active:scale-95"
    >
      <div className={cn("flex h-8 w-8 items-center justify-center rounded-lg", iconBg)}>
        <Icon className={cn("h-4 w-4", iconColor)} />
      </div>
      <p className="mt-2 text-sm font-medium">{label}</p>
      <p className="text-xs text-muted-foreground">{subtitulo}</p>
    </button>
  );
}
