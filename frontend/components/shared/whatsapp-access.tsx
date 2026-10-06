"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AxiosError } from "axios";
import { useAuthStore } from "@/stores/use-auth-store";
import { mascararWhatsApp } from "@/lib/telefone";
import { useCadastrarWhatsApp, useEntrarWhatsApp, useSolicitarWhatsApp, useVerificarWhatsApp, useVincularWhatsApp, useWhatsAppDisponivel, type AuthTokens, type CadastroWhatsApp } from "@/hooks/use-whatsapp-auth";

const campo = "w-full rounded-lg border bg-background p-3 text-sm";
export function WhatsAppAccess({ vincular = false }: { vincular?: boolean }) {
  const router = useRouter();
  const config = useWhatsAppDisponivel();
  const solicitar = useSolicitarWhatsApp();
  const verificar = useVerificarWhatsApp();
  const entrar = useEntrarWhatsApp();
  const cadastrar = useCadastrarWhatsApp();
  const associar = useVincularWhatsApp();
  const auth = useAuthStore();
  const [etapa, setEtapa] = useState<"telefone" | "codigo" | "cadastro" | "concluido">("telefone");
  const [regiao, setRegiao] = useState("BR");
  const [telefone, setTelefone] = useState("");
  const [codigo, setCodigo] = useState("");
  const [desafio, setDesafio] = useState("");
  const [espera, setEspera] = useState(0);
  const [erro, setErro] = useState("");
  const [dados, setDados] = useState<CadastroWhatsApp>({ prova: "", nome: "", nome_negocio: "", email: "", endereco: { pais: "BR", cep: "", logradouro: "", numero: "", complemento: "", bairro: "", cidade: "", estado: "" } });
  useEffect(() => {
    if (!espera) return;
    const timer = setTimeout(() => setEspera(valor => Math.max(0, valor - 1)), 1000);
    return () => clearTimeout(timer);
  }, [espera]);
  const aguarde = solicitar.isPending || verificar.isPending || entrar.isPending || cadastrar.isPending || associar.isPending;
  const sessao = (tokens: AuthTokens, novo: boolean) => { auth.setTokens(tokens.access_token, tokens.refresh_token); auth.setUsuario(tokens.usuario); router.push(novo ? "/boas-vindas" : "/"); };
  const enviar = async () => {
    const resposta = await solicitar.mutateAsync({ telefone, regiao });
    setDesafio(resposta.desafio); setCodigo(""); setEspera(resposta.reenviar_em); setEtapa("codigo");
  };
  const falha = (error: unknown) => {
    const detail = error instanceof AxiosError ? error.response?.data?.detail : null;
    setErro(typeof detail === "string" ? detail : "Não foi possível concluir. Confira os dados e tente novamente.");
  };
  if (config.isLoading) return <p>Carregando acesso...</p>;
  if (!config.data?.ativo) return <div className="space-y-3"><p>O acesso por WhatsApp ainda não está disponível.</p>{!vincular && <a className="text-primary underline" href="/login?email=1">Entrar por e-mail</a>}</div>;
  if (etapa === "concluido") return <p role="status">WhatsApp vinculado à sua conta.</p>;
  return <form className="mx-auto w-full max-w-md space-y-4" onSubmit={async e => {
    e.preventDefault(); setErro("");
    try {
      if (etapa === "telefone") await enviar();
      else if (etapa === "codigo") {
        const prova = (await verificar.mutateAsync({ desafio, codigo })).prova;
        if (vincular) { const usuario = await associar.mutateAsync({ prova }); auth.setUsuario(usuario); setEtapa("concluido"); }
        else { const resultado = await entrar.mutateAsync({ prova }); if (resultado.tokens) sessao(resultado.tokens, false); else { setDados({ ...dados, prova: resultado.onboarding_prova ?? "", endereco: { ...dados.endereco, pais: regiao } }); setEtapa("cadastro"); } }
      } else sessao(await cadastrar.mutateAsync(dados), true);
    } catch (error) { falha(error); }
  }}>
    <h1 className="text-2xl font-bold">{vincular ? "Vincular WhatsApp" : etapa === "cadastro" ? "Conheça sua loja" : "Entrar com WhatsApp"}</h1>
    {etapa === "telefone" && <>
      <p className="text-sm text-muted-foreground">Vamos enviar um código para confirmar seu número.</p>
      <label className="block">País/região<select className={campo} value={regiao} onChange={e => { setRegiao(e.target.value); setTelefone(""); }}>{[["BR", "Brasil (+55)"], ["PT", "Portugal (+351)"], ["US", "Estados Unidos (+1)"], ["AR", "Argentina (+54)"]].map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <label className="block">Número do WhatsApp<input required type="tel" autoComplete="tel-national" className={campo} value={telefone} placeholder={regiao === "BR" ? "(11) 99999-9999" : "Número nacional"} onChange={e => setTelefone(mascararWhatsApp(e.target.value, regiao))} /></label>
    </>}
    {etapa === "codigo" && <>
      <p className="text-sm">Digite o código enviado para {telefone}. Ele vale por 5 minutos.</p>
      <label className="block">Código de acesso<input required inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} className={campo} value={codigo} onChange={e => setCodigo(e.target.value.replace(/\D/g, "").slice(0, 6))} /></label>
      <button type="button" className="text-primary underline disabled:opacity-50" disabled={espera > 0 || aguarde} onClick={async () => { setErro(""); try { await enviar(); } catch (error) { falha(error); } }}>{espera ? `Reenviar em ${espera}s` : "Reenviar código"}</button>
      <button type="button" className="ml-4 text-sm underline" disabled={aguarde} onClick={() => { setEtapa("telefone"); setErro(""); }}>Alterar número</button>
    </>}
    {etapa === "cadastro" && <>
      <p className="text-sm text-muted-foreground">WhatsApp validado. Complete seus dados para começar.</p>
      {([ ["nome", "Seu nome"], ["nome_negocio", "Nome da confeitaria/loja"], ["email", "E-mail"] ] as const).map(([key, label]) => <label key={key} className="block">{label}<input required maxLength={key === "email" ? 254 : 200} type={key === "email" ? "email" : "text"} className={campo} value={dados[key]} onChange={e => setDados({ ...dados, [key]: e.target.value })} /></label>)}
      <fieldset className="space-y-3"><legend className="font-semibold">Endereço da loja</legend>
      <label className="block">País da loja<select className={campo} value={dados.endereco.pais} onChange={e => setDados({ ...dados, endereco: { ...dados.endereco, pais: e.target.value } })}>{[["BR", "Brasil"], ["PT", "Portugal"], ["US", "Estados Unidos"], ["AR", "Argentina"]].map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      {([ ["cep", "CEP/código postal"], ["logradouro", "Rua/avenida"], ["numero", "Número"], ["complemento", "Complemento (opcional)"], ["bairro", "Bairro"], ["cidade", "Cidade"], ["estado", "Estado/região"] ] as const).map(([key, label]) => <label key={key} className="block">{label}<input required={key !== "complemento"} maxLength={key === "logradouro" ? 200 : key === "numero" ? 30 : key === "cep" ? 20 : 100} className={campo} value={dados.endereco[key]} onChange={e => setDados({ ...dados, endereco: { ...dados.endereco, [key]: e.target.value } })} /></label>)}
      </fieldset>
    </>}
    {erro && <p role="alert" className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{erro}</p>}
    <button disabled={aguarde} className="w-full rounded-lg bg-primary p-3 font-medium text-primary-foreground">{aguarde ? "Aguarde..." : etapa === "telefone" ? "Receber código" : etapa === "codigo" ? "Validar código" : "Concluir cadastro"}</button>
    {!vincular && <a href="/login?email=1" className="block text-center text-sm text-primary underline">Já tenho conta por e-mail</a>}
  </form>;
}
