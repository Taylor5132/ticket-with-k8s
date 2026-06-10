import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const strip = (path: string) => path.replace(/^\/api/, "");

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // regex key must come before /api/performances so it wins
      "^/api/performances/[^/]+/seat-availability": {
        target: "http://booking-api:8000",
        changeOrigin: true,
        rewrite: strip,
      },
      "/api/auth": {
        target: "http://auth-service:8000",
        changeOrigin: true,
        rewrite: strip,
      },
      "/api/saved": {
        target: "http://saved-service:8000",
        changeOrigin: true,
        rewrite: strip,
      },
      "/api/payments": {
        target: "http://payment-service:8000",
        changeOrigin: true,
        rewrite: strip,
      },
      "/api/queue": {
        target: "http://booking-api:8000",
        changeOrigin: true,
        rewrite: strip,
      },
      "/api/booking-requests": {
        target: "http://booking-api:8000",
        changeOrigin: true,
        rewrite: strip,
      },
      "/api/bookings": {
        target: "http://booking-api:8000",
        changeOrigin: true,
        rewrite: strip,
      },
      "/api/performances": {
        target: "http://event-service:8000",
        changeOrigin: true,
        rewrite: strip,
      },
    },
  },
});
