// Vite config for React app (dev server and React plugin)
// Run: npm run dev then open http://localhost:5173
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, host: true }
});
