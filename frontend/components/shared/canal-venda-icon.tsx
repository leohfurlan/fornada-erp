import {
  Instagram,
  MessageCircle,
  ShoppingBag,
  Truck,
  Tag,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { CanalVenda } from "@/types";

interface CanalConfig {
  label: string;
  Icon: LucideIcon;
  className: string;
}

const CANAL_CONFIG: Record<CanalVenda, CanalConfig> = {
  loja_fisica: {
    label: "Loja física",
    Icon: ShoppingBag,
    className: "bg-blue-100 text-blue-800",
  },
  whatsapp: {
    label: "WhatsApp",
    Icon: MessageCircle,
    className: "bg-green-100 text-green-800",
  },
  ifood: {
    label: "iFood",
    Icon: Truck,
    className: "bg-red-100 text-red-800",
  },
  instagram: {
    label: "Instagram",
    Icon: Instagram,
    className: "bg-pink-100 text-pink-800",
  },
  outro: {
    label: "Outro",
    Icon: Tag,
    className: "bg-slate-100 text-slate-800",
  },
};

export const CANAIS_VENDA: { value: CanalVenda; label: string; Icon: LucideIcon }[] = (
  Object.entries(CANAL_CONFIG) as [CanalVenda, CanalConfig][]
).map(([value, cfg]) => ({ value, label: cfg.label, Icon: cfg.Icon }));

interface CanalVendaIconProps {
  canal: CanalVenda;
  className?: string;
  showLabel?: boolean;
}

export function CanalVendaBadge({ canal, className, showLabel = true }: CanalVendaIconProps) {
  const cfg = CANAL_CONFIG[canal];
  const { Icon } = cfg;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
        cfg.className,
        className
      )}
    >
      <Icon className="h-3 w-3" />
      {showLabel && cfg.label}
    </span>
  );
}
