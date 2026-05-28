import { formatMoney } from "@/lib/utils";
import { cn } from "@/lib/utils";

interface MoneyDisplayProps {
  value: string | number | null | undefined;
  className?: string;
  size?: "sm" | "md" | "lg" | "xl";
}

const sizeClasses = {
  sm: "text-sm",
  md: "text-base",
  lg: "text-lg font-semibold",
  xl: "text-2xl font-bold",
};

export function MoneyDisplay({ value, className, size = "md" }: MoneyDisplayProps) {
  return (
    <span className={cn(sizeClasses[size], className)}>{formatMoney(value)}</span>
  );
}
