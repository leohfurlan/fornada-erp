import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { Providers } from "./providers";

const inter = localFont({
  src: "./fonts/InterLatin.woff2",
  display: "swap",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "Fornada — ERP para confeiteiras",
  description: "Você produz. O sistema organiza.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
