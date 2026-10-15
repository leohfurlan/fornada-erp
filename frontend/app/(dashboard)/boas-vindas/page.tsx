"use client";

import Link from "next/link";
import { useAuthStore } from "@/stores/use-auth-store";

const passos = [
  { titulo: "1. Configure seus custos", texto: "Informe seu valor por hora e os gastos da loja para calcular preços que cubram sua produção.", href: "/configuracoes/geral" },
  { titulo: "2. Cadastre seus ingredientes", texto: "Cadastre os ingredientes e as embalagens usados nas receitas. Se já tiver produtos em casa, informe a quantidade e o custo inicial no estoque.", href: "/estoque" },
  { titulo: "3. Registre suas compras e abasteça o estoque", texto: "Escolha uma imagem ou PDF do cupom para o sistema ler, ou registre a compra manualmente. Confira o produto, a quantidade e o total pago. Nos itens desconhecidos, escolha o ingrediente ou a embalagem correspondente e informe o conteúdo da embalagem quando necessário. Confira o resumo e toque em Salvar compra: só então a entrada é registrada no estoque e os custos são atualizados.", href: "/compras" },
  { titulo: "4. Prepare suas receitas", texto: "Defina os ingredientes, o rendimento e o tempo de preparo. Consulte custos e preços sugeridos.", href: "/receitas" },
  { titulo: "5. Planeje a produção", texto: "Crie uma produção, acompanhe o preparo e registre a quantidade que ficou pronta.", href: "/producao" },
  { titulo: "6. Registre pedidos e vendas", texto: "Organize encomendas e registre as vendas dos produtos prontos.", href: "/pedidos" },
];

export default function BoasVindasPage() {
  const usuario = useAuthStore((state) => state.usuario);
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold">Boas-vindas ao Fornada{usuario?.nome ? `, ${usuario.nome.split(" ")[0]}` : ""}!</h1>
        <p className="mt-2 text-muted-foreground">Você produz. Vamos ajudar a organizar sua loja, um passo de cada vez.</p>
      </header>
      <ol className="space-y-3">
        {passos.map((passo) => (
          <li key={passo.href} className="rounded-xl border p-4">
            <h2 className="font-semibold">{passo.titulo}</h2>
            <p className="my-2 text-sm text-muted-foreground">{passo.texto}</p>
            <Link href={passo.href} className="text-sm font-medium text-primary underline">Abrir esta etapa</Link>
          </li>
        ))}
      </ol>
      <Link href="/" className="block rounded-lg bg-primary p-3 text-center font-medium text-primary-foreground">Ir para o Início</Link>
      <p className="text-sm text-muted-foreground">Você pode consultar este guia novamente na página Início.</p>
    </div>
  );
}
