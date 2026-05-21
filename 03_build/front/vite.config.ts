import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// SPEC-034 — Vite config for the Pulse front-end shell.
// `@/` path alias matches the design preview's import style (`@/components/ui/...`)
// and shadcn's default convention.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    // Phase-1 dev proxy to the local Pulse FastAPI (spec 001). Front talks to the
    // API via /api in dev so we don't hard-code hosts; prod uses VITE_API_BASE.
    proxy: {
      "/api": {
        target: process.env.VITE_API_BASE ?? "http://localhost:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
