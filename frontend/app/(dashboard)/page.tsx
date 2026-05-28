import Link from "next/link";
import { BookOpen, Package, Settings } from "lucide-react";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Bem-vinda ao Fornada</h1>
        <p className="text-muted-foreground text-sm">Por onde você quer começar?</p>
      </div>

      <div className="grid gap-3">
        <Link
          href="/receitas"
          className="flex items-center gap-4 rounded-xl border bg-card p-4 hover:bg-accent transition-colors"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
            <BookOpen className="h-5 w-5 text-primary" />
          </div>
          <div>
            <p className="font-medium">Receitas</p>
            <p className="text-sm text-muted-foreground">Calcule o custo das suas receitas</p>
          </div>
        </Link>

        <Link
          href="/estoque"
          className="flex items-center gap-4 rounded-xl border bg-card p-4 hover:bg-accent transition-colors"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
            <Package className="h-5 w-5 text-primary" />
          </div>
          <div>
            <p className="font-medium">Estoque</p>
            <p className="text-sm text-muted-foreground">Controle seus ingredientes</p>
          </div>
        </Link>

        <Link
          href="/configuracoes"
          className="flex items-center gap-4 rounded-xl border bg-card p-4 hover:bg-accent transition-colors"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
            <Settings className="h-5 w-5 text-primary" />
          </div>
          <div>
            <p className="font-medium">Configurações</p>
            <p className="text-sm text-muted-foreground">Custos, valor/hora e etapas padrão</p>
          </div>
        </Link>
      </div>
    </div>
  );
}
