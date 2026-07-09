import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import type { ProxyOptions } from "vite";

const apiProxy: ProxyOptions = {
  target: "http://api:8000",
  changeOrigin: true,
  secure: false,
};

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/auth": apiProxy,
      "/chat": apiProxy,
      "/threads": apiProxy,
      "/admin": apiProxy,
      "/health": apiProxy,
    },
  },
});
