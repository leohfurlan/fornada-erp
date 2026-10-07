import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Fornada — ERP para confeiteiras",
  description: "Você produz. O sistema organiza.",
  applicationName: "Fornada",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [
      { url: "/brand/forno-v2/favicon.ico", sizes: "16x16 32x32 48x48 64x64", type: "image/x-icon" },
      { url: "/brand/forno-v2/favicon.svg", sizes: "any", type: "image/svg+xml" },
    ],
    apple: { url: "/brand/forno-v2/apple-touch-icon.png", sizes: "180x180", type: "image/png" },
  },
  appleWebApp: { capable: true, title: "Fornada", statusBarStyle: "default" },
};

export const viewport: Viewport = {
  themeColor: "#E7A0B3",
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
