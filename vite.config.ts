import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { VitePWA } from "vite-plugin-pwa";
import path from "path";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'masked-icon.svg'],
      manifest: {
        name: 'Akcume Trading AI Bot',
        short_name: 'AI Bot',
        description: 'AI Trading Bot Dashboard',
        theme_color: '#0a4ed6',
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          }
        ]
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}']
      }
    })
  ],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    host: "0.0.0.0",
    port: 8080,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      },
    },
    watch: {
      ignored: [
        "**/node_modules/**",
        "**/.venv/**",
        "**/chroma_db/**",
        "**/__pycache__/**",
        "**/.pytest_cache/**",
        "**/public/data/**",
        "**/*.db",
        "**/*.db-*",
        "**/*.sqlite",
        "**/*.log",
        "**/news_cache.json",
        "**/*.gz"
      ]
    }
  },
});
