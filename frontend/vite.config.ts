import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

// In dev, proxy API + health to the local backend so the SPA is same-origin.
// Override the target with VITE_API_TARGET (default: a local backend on :8000).
const target = process.env.VITE_API_TARGET || "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg", "apple-touch-icon.png", "icon-192.png", "icon-512.png"],
      manifest: {
        name: "Fitness Tracker",
        short_name: "Fitness",
        description: "Self-hosted fitness & nutrition tracker",
        lang: "en",
        theme_color: "#11936a",
        background_color: "#0a0b0f",
        display: "standalone",
        start_url: "/",
        scope: "/",
        icons: [
          { src: "icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      workbox: {
        navigateFallback: "/index.html",
        globPatterns: ["**/*.{js,css,html,svg,png,woff2}"],
        // Exercise illustrations live on the jsDelivr CDN. We don't precache ~870
        // images (too large); instead cache each lazily the first time it's viewed
        // online, so the picker's thumbnails work offline afterwards.
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/cdn\.jsdelivr\.net\/gh\/yuhonas\/free-exercise-db/,
            handler: "CacheFirst",
            options: {
              cacheName: "exercise-images",
              expiration: { maxEntries: 1000, maxAgeSeconds: 60 * 60 * 24 * 60 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      "/api": { target, changeOrigin: true },
      "/health": { target, changeOrigin: true },
    },
  },
});
