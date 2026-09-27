import { defineConfig } from "vite";

// Preact JSX via Vite's built-in transform (no Babel preset, fewer dependencies to license-check).
// `npm run dev` proxies /api to the sandbox API; in Docker, nginx does the same.
export default defineConfig({
  oxc: { jsx: { runtime: "automatic", importSource: "preact" } },
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://127.0.0.1:18083", rewrite: (path) => path.replace(/^\/api/, "") } },
  },
  build: { outDir: "dist", sourcemap: false },
});
