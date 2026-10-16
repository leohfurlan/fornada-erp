import { BrandLogo } from "@/components/shared/brand-logo";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-brand-cream px-4 py-8 sm:py-12">
      <div className="w-full max-w-md space-y-7 rounded-2xl border bg-card px-6 py-8 shadow-sm shadow-brand-brown/30 sm:px-8">
        <div className="space-y-2 text-center">
          <BrandLogo className="mx-auto w-56" priority />
          <p className="text-sm text-muted-foreground">Você produz. O sistema organiza.</p>
        </div>
        {children}
      </div>
    </main>
  );
}
