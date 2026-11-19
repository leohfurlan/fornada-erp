"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useCriarReceita } from "@/hooks/use-receitas";
import { FormReceita, type ReceitaFormValues } from "@/components/shared/form-receita";

export default function NovaReceitaPage() {
  const router = useRouter();
  const criar = useCriarReceita();

  const onSubmit = async (data: ReceitaFormValues) => {
    const payload = {
      ...data,
      // margem chega como percentual (30) e API espera decimal (0.30)
      margem_desejada: data.margem_desejada / 100,
      // 0 no input significa "não informado" — envia null pra API.
      preco_de_venda_real: data.preco_de_venda_real > 0 ? data.preco_de_venda_real : null,
      modo_preparo: data.modo_preparo || null,
      ingredientes: data.ingredientes.map((item) => ({
        ingrediente_id: item.origem_tipo === "material" ? item.ingrediente_id : null,
        receita_componente_id: item.origem_tipo === "receita_base" ? item.receita_componente_id : null,
        quantidade: item.quantidade,
        unidade: item.unidade,
      })),
      etapas: data.etapas.map((e, i) => ({ ...e, ordem: i })),
    };
    const receita = await criar.mutateAsync(payload);
    router.push(`/receitas/${receita.id}`);
  };

  return (
    <div className="space-y-5 pb-8">
      <Link href="/receitas" className="flex items-center gap-1 text-sm text-muted-foreground">
        <ArrowLeft className="h-4 w-4" />
        Voltar
      </Link>

      <h1 className="text-xl font-bold">Nova receita</h1>

      <FormReceita
        onSubmit={onSubmit}
        textoBotao="Salvar receita"
        textoBotaoLoading="Calculando custo..."
        isPending={criar.isPending}
        isError={criar.isError}
      />
    </div>
  );
}
