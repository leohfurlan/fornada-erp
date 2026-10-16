import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "Fornada — ERP para confeiteiras",
    short_name: "Fornada",
    description: "Você produz. O sistema organiza.",
    lang: "pt-BR",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#FFF7FA",
    theme_color: "#E7A0B3",
    icons: [
      { src: "/brand/forno-v2/app-icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/brand/forno-v2/app-icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/brand/forno-v2/app-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
