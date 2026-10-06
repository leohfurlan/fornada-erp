import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Usuario } from "@/types";

export interface AuthTokens { access_token: string; refresh_token: string; usuario: Usuario }
export interface CadastroWhatsApp {
  prova: string; nome: string; nome_negocio: string; email: string;
  endereco: { pais: string; cep: string; logradouro: string; numero: string; complemento: string; bairro: string; cidade: string; estado: string };
}
export function useWhatsAppDisponivel() {
  return useQuery<{ ativo: boolean }>({ queryKey: ["whatsapp-disponivel"], queryFn: async () => (await api.get("/auth/whatsapp/disponibilidade")).data, retry: false });
}
export function useSolicitarWhatsApp() {
  return useMutation<{ desafio: string; reenviar_em: number }, Error, { telefone: string; regiao: string }>({ mutationFn: async data => (await api.post("/auth/whatsapp/solicitar", data)).data });
}
export function useVerificarWhatsApp() {
  return useMutation<{ prova: string }, Error, { desafio: string; codigo: string }>({ mutationFn: async data => (await api.post("/auth/whatsapp/verificar", data)).data });
}
export function useEntrarWhatsApp() {
  return useMutation<{ tokens: AuthTokens | null; onboarding_prova: string | null }, Error, { prova: string }>({ mutationFn: async data => (await api.post("/auth/whatsapp/entrar", data)).data });
}
export function useCadastrarWhatsApp() {
  return useMutation<AuthTokens, Error, CadastroWhatsApp>({ mutationFn: async data => (await api.post("/auth/whatsapp/cadastro", data)).data });
}
export function useVincularWhatsApp() {
  return useMutation<Usuario, Error, { prova: string }>({ mutationFn: async data => (await api.post("/auth/whatsapp/vincular", data)).data });
}
