import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/sse": {
        target: "http://localhost:8000",
        changeOrigin: true,
        ws: false, // SSE, not WebSocket
        configure: (proxy, _options) => {
          proxy.on("proxyReq", (proxyReq, req, _res) => {
            console.log("Proxying SSE request:", req.url);
          });
        },
      },
      "/assets": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
