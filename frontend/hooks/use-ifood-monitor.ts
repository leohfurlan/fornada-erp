import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/use-auth-store";
import { getSupportSession } from "@/lib/admin-session";

export interface IfoodOption {
  name: string;
  quantity: string;
  unitPrice: string | null;
  price: string | null;
  totalPrice: string | null;
  options: IfoodOption[];
}

export interface IfoodOrder {
  id: string;
  ultimo_evento: string;
  evento_em: string;
  aviso_whatsapp?: string | null;
  snapshot: {
    id: string;
    displayId: string;
    isTest: boolean;
    createdAt: string;
    orderType: string;
    orderTiming: string;
    merchant: { id: string; name: string };
    items: (IfoodOption & { totalPrice: string | null })[];
    total: {
      subTotal: string;
      deliveryFee: string;
      additionalFees: string;
      benefits: string;
      orderAmount: string;
    };
  };
}

export interface IfoodMonitor {
  habilitado: boolean;
  intervalo_segundos: number;
  loja_nome: string | null;
  merchant_id: string | null;
  ultima_consulta: string | null;
  ultima_recepcao: string | null;
  erro: string | null;
  eventos_pendentes: number;
  alertas_habilitados?: boolean;
  whatsapp_habilitado?: boolean;
  whatsapp_final?: string | null;
  pedidos: IfoodOrder[];
  eventos: {
    event_id: string;
    order_id: string | null;
    codigo: string;
    ocorrido_em: string;
    ack_em: string | null;
    processado_em: string | null;
    erro: string | null;
  }[];
}

export function useIfoodMonitor() {
  const user = useAuthStore((s) => s.usuario);
  const support = getSupportSession();
  return useQuery<IfoodMonitor>({
    queryKey: ["ifood-monitor", user?.tenant_id, user?.id, support?.id],
    queryFn: async () => (await api.get<IfoodMonitor>("/integracoes/ifood/monitor")).data,
    refetchInterval: 10000,
  });
}
