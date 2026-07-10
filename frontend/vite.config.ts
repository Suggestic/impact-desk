import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// The API runs separately (FastAPI on :8000). In dev we proxy /api -> backend
// and strip the prefix, so the frontend never hardcodes a host and there's no
// CORS to fight. In prod, serve both behind one origin or set VITE_API_BASE.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
