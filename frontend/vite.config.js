import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],

  // Prevent Vite from pre-bundling MapLibre.
  // MapLibre manages its own web worker, which can conflict
  // with Vite's dependency optimizer.
  optimizeDeps: {
    exclude: ["maplibre-gl"],
  },
});
