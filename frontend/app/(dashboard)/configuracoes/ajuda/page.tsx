import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function ConfiguracoesAjudaPage() {
  return (
    <div className="space-y-6">
      <Link
        href="/configuracoes"
        className="flex items-center gap-1 text-sm text-muted-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Voltar
      </Link>

      <div>
        <h1 className="text-xl font-bold">Entendendo os custos da sua produção</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Sem esses 3 conceitos, é impossível saber se você está lucrando de verdade.
        </p>
      </div>

      {/* MOD */}
      <section className="space-y-3 rounded-xl border bg-card p-4">
        <h2 className="font-bold text-lg">
          Mão de Obra Direta <span className="text-primary">(MOD)</span>
        </h2>
        <p className="text-sm">
          É o tempo em que <strong>você está com a mão na massa</strong> trabalhando em uma receita
          específica. Você poderia estar fazendo outra coisa, mas escolheu produzir aquele bolo.
        </p>
        <div className="rounded-lg bg-muted/50 p-3 text-sm space-y-1.5">
          <p className="font-medium">Exemplos numa confeitaria:</p>
          <ul className="space-y-1 ml-4 list-disc text-muted-foreground">
            <li>Bater massa de bolo</li>
            <li>Rechear, montar e cobrir</li>
            <li>Modelar brigadeiros</li>
            <li>Decorar e finalizar</li>
            <li>Embalar o produto pronto para entrega</li>
          </ul>
        </div>
        <div className="rounded-lg bg-primary/5 border border-primary/20 p-3 text-sm">
          <strong>Como o Fornada calcula:</strong> soma todas as etapas da receita marcadas como
          "Mão de obra direta" e multiplica pelo seu <em>valor/hora</em>.
        </div>
      </section>

      {/* MOI */}
      <section className="space-y-3 rounded-xl border bg-card p-4">
        <h2 className="font-bold text-lg">
          Mão de Obra Indireta <span className="text-primary">(MOI)</span>
        </h2>
        <p className="text-sm">
          É o tempo que você gasta com o <strong>negócio em geral</strong>, sem estar produzindo um
          item específico. Ninguém te paga diretamente por esse tempo, mas ele existe e custa caro
          se você ignorar.
        </p>
        <div className="rounded-lg bg-muted/50 p-3 text-sm space-y-1.5">
          <p className="font-medium">Exemplos:</p>
          <ul className="space-y-1 ml-4 list-disc text-muted-foreground">
            <li>Lavar louça, organizar a cozinha</li>
            <li>Comprar ingredientes (ir ao mercado, atacadista)</li>
            <li>Responder cliente no WhatsApp</li>
            <li>Postar nos Stories, fazer foto do produto</li>
            <li>Conferir estoque, fazer planilha</li>
          </ul>
        </div>
        <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-sm text-amber-900">
          <strong>Atenção:</strong> ao cadastrar uma etapa, marque como <em>indireta</em> se ela não
          é exclusiva de uma receita (ex: limpeza geral do dia).
        </div>
      </section>

      {/* Custos fixos */}
      <section className="space-y-3 rounded-xl border bg-card p-4">
        <h2 className="font-bold text-lg">Custos Operacionais Mensais</h2>
        <p className="text-sm">
          É <strong>tudo que você paga todo mês</strong> para manter a produção funcionando — esteja
          você fazendo 1 bolo ou 100.
        </p>
        <div className="rounded-lg bg-muted/50 p-3 text-sm space-y-1.5">
          <p className="font-medium">Some no mês:</p>
          <ul className="space-y-1 ml-4 list-disc text-muted-foreground">
            <li>Conta de luz e gás da cozinha</li>
            <li>Água</li>
            <li>Aluguel (se for cozinha alugada) ou parte da conta de casa</li>
            <li>Internet</li>
            <li>Embalagens genéricas (sacolas, caixas padrão)</li>
            <li>Material de limpeza, papel toalha</li>
            <li>Mensalidade do Fornada ou outras assinaturas do negócio</li>
          </ul>
        </div>
        <div className="rounded-lg bg-muted/50 p-3 text-sm space-y-1">
          <p className="font-medium">❌ Não inclua aqui:</p>
          <ul className="space-y-1 ml-4 list-disc text-muted-foreground">
            <li>Ingredientes (cada compra entra separada, no estoque)</li>
            <li>Embalagem específica de um produto (vai no custo da receita)</li>
            <li>Seu salário (isso é o valor/hora)</li>
          </ul>
        </div>
      </section>

      {/* Valor da hora */}
      <section className="space-y-3 rounded-xl border bg-card p-4">
        <h2 className="font-bold text-lg">Valor da Hora</h2>
        <p className="text-sm">
          Quanto vale 1 hora do <strong>seu trabalho</strong>. Não é o que sobra no fim do mês — é o
          que você define ganhar pelo seu tempo.
        </p>
        <div className="rounded-lg bg-muted/50 p-3 text-sm">
          <p className="font-medium mb-1">Como calcular:</p>
          <p className="text-muted-foreground">
            Pense em quanto você gostaria de ganhar por mês com o que faz <em>(ex: R$ 3.000)</em> e
            divida pela quantidade de horas que pretende trabalhar no mês <em>(ex: 160h)</em>:
          </p>
          <p className="mt-2 font-mono text-center">3000 ÷ 160 = <strong>R$ 18,75/h</strong></p>
        </div>
        <div className="rounded-lg bg-primary/5 border border-primary/20 p-3 text-sm">
          <strong>Não trabalhe de graça:</strong> mesmo que você não tire esse valor todo mês no
          começo, o sistema precisa saber quanto seu tempo vale para sugerir preços justos.
        </div>
      </section>

      {/* Como o sistema usa */}
      <section className="space-y-3 rounded-xl border bg-card p-4">
        <h2 className="font-bold text-lg">Como o Fornada calcula o preço da sua receita</h2>
        <div className="rounded-lg bg-muted/50 p-3 text-sm space-y-2 font-mono">
          <p>Custo dos ingredientes</p>
          <p>+ Custo operacional rateado <span className="font-sans text-muted-foreground">(custo mensal ÷ horas mensais × tempo total da receita)</span></p>
          <p>+ Mão de obra direta <span className="font-sans text-muted-foreground">(valor/hora × tempo ativo da receita)</span></p>
          <p className="border-t pt-2">= Custo total</p>
          <p>÷ Rendimento <span className="font-sans text-muted-foreground">(quantas unidades a receita rende)</span></p>
          <p className="border-t pt-2">= Custo por unidade</p>
          <p>÷ (1 - margem desejada)</p>
          <p className="border-t pt-2 text-primary font-bold">= Preço sugerido</p>
        </div>
        <p className="text-sm text-muted-foreground">
          Tudo isso acontece automaticamente. Você só precisa cadastrar uma vez e o sistema recalcula
          sozinho sempre que algo mudar (preço de ingrediente, valor/hora, etc).
        </p>
      </section>

      <div className="rounded-xl bg-primary/10 border border-primary/20 p-4 text-center">
        <p className="font-medium">Pronto pra configurar?</p>
        <Link
          href="/configuracoes/geral"
          className="mt-2 inline-block rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
        >
          Ir para Custos e Valor da Hora
        </Link>
      </div>
    </div>
  );
}
