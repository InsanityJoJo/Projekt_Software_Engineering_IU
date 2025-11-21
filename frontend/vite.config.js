import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  test: {
    // Enable global test APIs (describe, it, expect, etc.) without imports
    globals: true,
    // Test environment - use happy-dom for browser API simulation
    // happy-dom is lighter and faster than jsdom
    environment: "happy-dom",
    // Include test files
    include: ["tests/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}"],
    // Coverage configuration
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      // Include source files for coverage
      include: ["src/**/*.{js,ts,jsx,tsx,svelte}"],
      // Exclude test files and node_modules
      exclude: [
        "node_modules/",
        "src/**/*.spec.js",
        "tests/**/*.test.js",
        "src/main.js", // Entry point, typically not covered
        "src/assets/**",
      ],
      // Coverage thresholds (optional - enforces minimum coverage)
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 70,
        statements: 80,
      },
    },
    // Setup files to run before tests
    // setupFiles: ['./tests/setup.js'],
  },
});
