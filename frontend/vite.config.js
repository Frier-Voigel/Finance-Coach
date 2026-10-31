import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/ingest": "http://localhost:8000",
      "/transactions": "http://localhost:8000",
      "/rules": "http://localhost:8000",
      "/recurring": "http://localhost:8000",
      "/profile": "http://localhost:8000",
      "/goals": "http://localhost:8000",
      "/plan": "http://localhost:8000",
      "/whatif": "http://localhost:8000",
      "/nudges": "http://localhost:8000",
      "/reports": "http://localhost:8000",
      "/voice": "http://localhost:8000",
      "/coach": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
