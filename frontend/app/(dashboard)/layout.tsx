"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  BookOpen,
  Calendar,
  ChefHat,
  ChevronRight,
  LayoutDashboard,
  LogOut,
  MoreHorizontal,
  Package,
  Settings,
  ShoppingBag,
  ShoppingCart,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/use-auth-store";
import { useDashboardResumo } from "@/hooks/use-dashboard";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

interface NavItemMais extends NavItem {
  subtitulo: string;
  iconBg: string;
  iconColor: string;
}

const navPrincipal: NavItem[] = [
  { href: "/", label: "Início", icon: LayoutDashboard },
  { href: "/receitas", label: "Receitas", icon: BookOpen },
  { href: "/agenda", label: "Agenda", icon: Calendar },
  { href: "/producao", label: "Produção", icon: ChefHat },
  { href: "/pedidos", label: "Pedidos", icon: ShoppingCart },
];

const navMais: NavItemMais[] = [
  {
    href: "/vendas",
    label: "Vendas",
    icon: ShoppingBag,
    subtitulo: "Pronta entrega e multicanal",
    iconBg: "bg-orange-50",
    iconColor: "text-orange-500",
  },
  {
    href: "/estoque",
    label: "Estoque",
    icon: Package,
    subtitulo: "Ingredientes e produtos prontos",
    iconBg: "bg-green-50",
    iconColor: "text-green-600",
  },
  {
    href: "/configuracoes",
    label: "Configurações",
    icon: Settings,
    subtitulo: "Custos, valor/hora e etapas",
    iconBg: "bg-blue-50",
    iconColor: "text-blue-600",
  },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, logout, usuario } = useAuthStore();
  const [maisAberto, setMaisAberto] = useState(false);
  const { data: resumo } = useDashboardResumo();
  const criticos = resumo?.total_ingredientes_criticos ?? 0;

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, router]);

  // Fecha menu "Mais" ao mudar de rota
  useEffect(() => {
    setMaisAberto(false);
  }, [pathname]);

  if (!isAuthenticated) return null;

  const ativo = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  const maisAtivo = navMais.some((i) => ativo(i.href));

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header mobile */}
      <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
        <div className="flex h-14 items-center justify-between px-4">
          <span className="font-bold text-primary text-lg">Fornada</span>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground hidden sm:block">{usuario?.nome}</span>
            <button
              onClick={() => {
                logout();
                router.push("/login");
              }}
              className="p-2 rounded-lg hover:bg-muted"
              aria-label="Sair"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Conteúdo */}
      <main className="flex-1 px-4 py-6 pb-24 max-w-2xl md:max-w-5xl mx-auto w-full">
        {children}
      </main>

      {/* Nav inferior */}
      <nav className="fixed bottom-0 left-0 right-0 border-t bg-background z-40">
        <div className="flex justify-around">
          {navPrincipal.map(({ href, label, icon: Icon }) => {
            const isAtivo = ativo(href);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "relative flex flex-col items-center gap-0.5 py-3 px-3 text-xs transition-colors",
                  isAtivo ? "text-primary" : "text-muted-foreground hover:text-foreground"
                )}
              >
                {isAtivo && (
                  <span className="absolute top-0 left-[20%] right-[20%] h-0.5 rounded-b-sm bg-primary" />
                )}
                <Icon className="h-5 w-5" />
                <span>{label}</span>
              </Link>
            );
          })}
          <button
            type="button"
            onClick={() => setMaisAberto((v) => !v)}
            className={cn(
              "relative flex flex-col items-center gap-0.5 py-3 px-3 text-xs transition-colors",
              maisAtivo || maisAberto
                ? "text-primary"
                : "text-muted-foreground hover:text-foreground"
            )}
            aria-label="Mais opções"
          >
            {(maisAtivo || maisAberto) && (
              <span className="absolute top-0 left-[20%] right-[20%] h-0.5 rounded-b-sm bg-primary" />
            )}
            <div className="relative">
              <MoreHorizontal className="h-5 w-5" />
              {criticos > 0 && (
                <span className="absolute -top-1.5 -right-2 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
                  {criticos}
                </span>
              )}
            </div>
            <span>Mais</span>
          </button>
        </div>

        {/* Sheet "Mais" */}
        {maisAberto && (
          <>
            <div
              className="fixed inset-0 bg-black/30 z-40"
              onClick={() => setMaisAberto(false)}
              aria-hidden
            />
            <div className="absolute bottom-full left-0 right-0 bg-background border-t shadow-lg z-50 max-w-2xl md:max-w-5xl mx-auto">
              <div className="p-2 space-y-0.5">
                {navMais.map(({ href, label, subtitulo, icon: Icon, iconBg, iconColor }) => {
                  const mostrarBadge = href === "/estoque" && criticos > 0;
                  return (
                    <Link
                      key={href}
                      href={href}
                      className={cn(
                        "flex items-center gap-3 rounded-lg px-3 py-3 transition-colors",
                        ativo(href) ? "bg-primary/5" : "hover:bg-muted"
                      )}
                    >
                      <div
                        className={cn(
                          "flex h-9 w-9 shrink-0 items-center justify-center rounded-xl",
                          iconBg
                        )}
                      >
                        <Icon className={cn("h-5 w-5", iconColor)} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-foreground">{label}</span>
                          {mostrarBadge && (
                            <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1.5 text-[11px] font-bold text-white">
                              {criticos}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">{subtitulo}</p>
                      </div>
                      <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                    </Link>
                  );
                })}
              </div>
            </div>
          </>
        )}
      </nav>
    </div>
  );
}
