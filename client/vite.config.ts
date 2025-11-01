import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { compression } from "vite-plugin-compression2";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // Brotli and Gzip compression for production
    compression({
      algorithm: "gzip",
      threshold: 1024, // Only compress files larger than 1KB
    }),
    compression({
      algorithm: "brotliCompress",
      threshold: 1024,
      deleteOriginalAssets: false,
    }),
  ],
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
  build: {
    // Enable source maps for easier debugging (only in dev)
    sourcemap: false,
    // SPDX-License-Identifier: Proprietary
    // Copyright © 2025 Liran Rouzentur. All rights reserved.
    // כל הזכויות שמורות © 2025 לירן רויזנטור.
    // קוד זה הינו קנייני וסודי. אין להעתיק, לערוך, להפיץ או לעשות בו שימוש ללא אישור מפורש.
    // © 2025 Лиран Ройзентур. Все права защищены.
    // Этот программный код является собственностью владельца.
    // Запрещается копирование, изменение, распространение или использование без явного разрешения.
    // Optimize chunk splitting
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          // Separate vendor chunks for better caching
          if (id.includes("node_modules")) {
            if (id.includes("react") || id.includes("react-dom")) {
              return "react-vendor";
            }
            return "vendor";
          }
          // Separate skeleton components (lazy loaded)
          if (id.includes("LandingPageSkeleton")) {
            return "skeleton";
          }
        },
        // Optimize asset file names for better caching
        assetFileNames: (assetInfo) => {
          const info = assetInfo.name?.split(".");
          const ext = info?.[info.length - 1];
          if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(ext || "")) {
            return `assets/images/[name]-[hash][extname]`;
          } else if (/woff2?|ttf|eot/i.test(ext || "")) {
            return `assets/fonts/[name]-[hash][extname]`;
          }
          return `assets/[name]-[hash][extname]`;
        },
        chunkFileNames: "assets/js/[name]-[hash].js",
        entryFileNames: "assets/js/[name]-[hash].js",
      },
    },
    // Increase chunk size warning limit
    chunkSizeWarningLimit: 1000,
    // Enable minification with esbuild (faster than terser)
    minify: "esbuild",
    // Target modern browsers for smaller bundles
    target: "es2020",
    // Enable CSS code splitting
    cssCodeSplit: true,
    // Report compressed size (slower but useful)
    reportCompressedSize: true,
  },
  // Optimize dependencies
  optimizeDeps: {
    include: ["react", "react-dom"],
    // Exclude heavy dependencies from pre-bundling
    exclude: [],
  },
  // Performance hints
  esbuild: {
    // Drop console and debugger in production
    drop: process.env.NODE_ENV === "production" ? ["console", "debugger"] : [],
  },
});
