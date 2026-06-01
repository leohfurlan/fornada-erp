"use client";

import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useAtualizarReceita, useReceita } from "@/hooks/use-receitas";
import { FormReceita, type ReceitaFormValues } from "@/components/shared/form-receita";

export default function EditarReceitaPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: receita, isLoading } = useReceita(id);
  const atualizar = useAtualizarReceita(id);

  const onSubmit = async (data: ReceitaFormValues) => {
    const payload = {
      ...data,
      margem_desejada: data.margem_desejada / 100,
      preco_de_venda_real: data.preco_de_venda_real > 0 ? data.preco_de_venda_real : null,
      modo_preparo: data.modo_preparo || null,
      etapas: data.etapas.map((e, i) => ({ ...e, ordem: i })),
    };
    await atualizar.mutateAsync(payload);
    router.push(`/receitas/${id}`);
  };

  if (isLoading || !receita) {
    return (
      <div className="space-y-4">
        <div className="h-6 w-40 rounded bg-muted animate-pulse" />
        <div className="h-40 rounded-xl bg-muted animate-pulse" />
      </div>
    );
  }

  // Mapeia receita do backend → valores iniciais do form
  const valoresIniciais: ReceitaFormValues = {
    nome: receita.nome,
    categoria: receita.categoria,
    rendimento: parseFloat(receita.rendimento),
    rendimento_unidade: receita.rendimento_unidade,
    margem_desejada: parseFloat(receita.margem_desejada) * 100, // decimal → percentual
    preco_de_venda_real: receita.preco_de_venda_real
      ? parseFloat(receita.preco_de_venda_real)
      : 0,
    modo_preparo: receita.modo_preparo ?? "",
    ingredientes: receita.ingredientes.map((ri) => ({
      ingrediente_id: ri.ingrediente_id,
      quantidade: parseFloat(ri.quantidade),
      unidade: ri.unidade,
    })),
    etapas: receita.etapas.map((e) => ({
      nome: e.nome,
      duracao_minutos: e.duracao_minutos,
      tipo_mao_obra: e.tipo_mao_obra,
      ordem: e.ordem,
    })),
  };

  return (
    <div className="space-y-5 pb-8">
      <Link href={`/receitas/${id}`} className="flex items-center gap-1 text-sm text-muted-foreground">
        <ArrowLeft className="h-4 w-4" />
        Voltar
      </Link>

      <h1 className="text-xl font-bold">Editar receita</h1>

      <FormReceita
        key={id} /* força remount com novos defaultValues quando trocar de id */
        valoresIniciais={valoresIniciais}
        onSubmit={onSubmit}
        textoBotao="Salvar alterações"
        textoBotaoLoading="Salvando..."
        isPending={atualizar.isPending}
        isError={atualizar.isError}
      />
    </div>
  );
}
