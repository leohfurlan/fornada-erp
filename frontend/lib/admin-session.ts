export interface ContaAdmin {
  id: string;
  tenant_id: string;
  nome: string;
  email: string;
  negocio: string;
  ativo: boolean;
  is_superuser: boolean;
}

export interface SessaoSuporte {
  id: string;
  expires_at: string;
  conta: ContaAdmin;
  operador_id: string;
}

const key = "fornada-suporte";

export function getSupportSession(): SessaoSuporte | null {
  if (typeof window === "undefined") return null;
  try {
    const value = window.sessionStorage.getItem(key);
    return value ? JSON.parse(value) as SessaoSuporte : null;
  } catch {
    return null;
  }
}

export function setSupportSession(session: SessaoSuporte): void {
  window.sessionStorage.setItem(key, JSON.stringify(session));
}

export function clearSupportSession(): void {
  if (typeof window !== "undefined") window.sessionStorage.removeItem(key);
}
