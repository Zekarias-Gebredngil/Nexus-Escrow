import react from "./frontend/node_modules/@vitejs/plugin-react/dist/index.js";
import { defineConfig } from "./frontend/node_modules/vite/dist/node/index.js";

export default defineConfig({
  root: ".",
  cacheDir: "../.vite-cache",
  plugins: [react()],
  build: {
    outDir: "../dist/frontend",
    emptyOutDir: true
  },
  server: {
    host: "0.0.0.0",
    port: 5173
  }
});
