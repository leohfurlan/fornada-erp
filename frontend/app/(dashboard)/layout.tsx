"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { BookOpen, Package, LayoutDashboard, LogOut, Settings } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/use-auth-store";

const navItems = [
  { href: "/", label: "Início", icon: LayoutDashboard },
  { href: "/receitas", label: "Receitas", icon: BookOpen },
  { href: "/estoque", label: "Estoque", icon: Package },
  { href: "/configuracoes", label: "Ajustes", icon: Settings },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, logout, usuario } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, router]);

  if (!isAuthenticated) return null;

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
      <main className="flex-1 px-4 py-6 pb-24 max-w-2xl md:max-w-5xl mx-auto w-full">{children}</main>

      {/* Nav inferior mobile */}
      <nav className="fixed bottom-0 left-0 right-0 border-t bg-background z-40">
        <div className="flex justify-around">
          {navItems.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex flex-col items-center gap-0.5 py-3 px-4 text-xs transition-colors",
                  active ? "text-primary" : "text-muted-foreground hover:text-foreground"
                )}
              >
                <Icon className="h-5 w-5" />
                <span>{label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
