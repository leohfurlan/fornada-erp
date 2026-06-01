"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  BookOpen,
  CalendarDays,
  ChefHat,
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

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

// 4 atalhos prioritários na navegação inferior + "Mais" pro restante.
// "Agenda" e "Produção" são os fluxos de planejamento do dia a dia.
const navPrincipal: NavItem[] = [
  { href: "/", label: "Início", icon: LayoutDashboard },
  { href: "/agenda", label: "Agenda", icon: CalendarDays },
  { href: "/producao", label: "Produção", icon: ChefHat },
  { href: "/pedidos", label: "Pedidos", icon: ShoppingCart },
];

const navMais: NavItem[] = [
  { href: "/vendas", label: "Vendas", icon: ShoppingBag },
  { href: "/receitas", label: "Receitas", icon: BookOpen },
  { href: "/estoque", label: "Estoque", icon: Package },
  { href: "/configuracoes", label: "Configurações", icon: Settings },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, logout, usuario } = useAuthStore();
  const [maisAberto, setMaisAberto] = useState(false);

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
          {navPrincipal.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex flex-col items-center gap-0.5 py-3 px-4 text-xs transition-colors",
                ativo(href) ? "text-primary" : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Icon className="h-5 w-5" />
              <span>{label}</span>
            </Link>
          ))}
          <button
            type="button"
            onClick={() => setMaisAberto((v) => !v)}
            className={cn(
              "flex flex-col items-center gap-0.5 py-3 px-4 text-xs transition-colors",
              maisAtivo || maisAberto
                ? "text-primary"
                : "text-muted-foreground hover:text-foreground"
            )}
            aria-label="Mais opções"
          >
            <MoreHorizontal className="h-5 w-5" />
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
                {navMais.map(({ href, label, icon: Icon }) => (
                  <Link
                    key={href}
                    href={href}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-3 text-sm transition-colors",
                      ativo(href)
                        ? "bg-primary/10 text-primary"
                        : "hover:bg-muted text-foreground"
                    )}
                  >
                    <Icon className="h-5 w-5" />
                    {label}
                  </Link>
                ))}
              </div>
            </div>
          </>
        )}
      </nav>
    </div>
  );
}
