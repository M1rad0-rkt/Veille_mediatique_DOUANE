import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Le navigateur parle uniquement à Vite (même origine) ; /api est relayé vers FastAPI.
// Avantage : le cookie de session (httpOnly) fonctionne sans configuration CORS particulière.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": { target: process.env.VITE_PROXY_TARGET || "http://localhost:8000", changeOrigin: true } },
  },
});
