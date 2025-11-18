import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  test: {
    // Enable global test APIs (describe, it, expect, etc.) without imports
    globals: true,
    // Test environment
    environment: "node",
    // Include test files
    include: ["tests/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}"],
    // Coverage configuration
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      exclude: ["node_modules/", "src/**/*.spec.js", "tests/**/*.test.js"],
    },
  },
});
