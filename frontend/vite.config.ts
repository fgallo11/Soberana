import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    // en desarrollo, proxy al API local para no pelear con CORS
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
