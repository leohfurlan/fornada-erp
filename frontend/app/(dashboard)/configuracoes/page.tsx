import Link from "next/link";
import { ChevronRight, DollarSign, ListChecks, HelpCircle } from "lucide-react";

const cards = [
  {
    href: "/configuracoes/geral",
    titulo: "Custos e Valor da Hora",
    descricao: "Defina seu valor/hora e os custos fixos mensais",
    icone: DollarSign,
  },
  {
    href: "/configuracoes/etapas",
    titulo: "Etapas de Produção",
    descricao: "Cadastre etapas reutilizáveis (preparo, decoração, limpeza...)",
    icone: ListChecks,
  },
  {
    href: "/configuracoes/ajuda",
    titulo: "Ajuda — MOD, MOI e Custos",
    descricao: "Entenda os termos antes de cadastrar",
    icone: HelpCircle,
  },
];

export default function ConfiguracoesPage() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold">Configurações</h1>
        <p className="text-muted-foreground text-sm">
          Antes de começar, configure aqui o que vai fazer o sistema calcular seus preços corretamente
        </p>
      </div>

      <div className="space-y-2">
        {cards.map(({ href, titulo, descricao, icone: Icone }) => (
          <Link
            key={href}
            href={href}
            className="flex items-center gap-3 rounded-xl border bg-card p-4 hover:bg-accent transition-colors"
          >
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10">
              <Icone className="h-5 w-5 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium">{titulo}</p>
              <p className="text-sm text-muted-foreground">{descricao}</p>
            </div>
            <ChevronRight className="h-5 w-5 shrink-0 text-muted-foreground" />
          </Link>
        ))}
      </div>
    </div>
  );
}
