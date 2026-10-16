import Image from "next/image";
import { cn } from "@/lib/utils";

interface BrandLogoProps {
  variant?: "primary" | "ink" | "white";
  className?: string;
  priority?: boolean;
}

/** Identidade oficial aprovada: Forno aberto rosa e marrom, versão 2. */
export function BrandLogo({ variant = "primary", className, priority = false }: BrandLogoProps) {
  return (
    <Image
      src={`/brand/forno-v2/logo-horizontal-${variant}.svg`}
      alt="Fornada"
      width={512}
      height={160}
      className={cn("h-auto w-48", className)}
      priority={priority}
    />
  );
}
