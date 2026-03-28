/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      thresholds: {
        statements: 90,
        branches: 90,
        functions: 90,
        lines: 90
      },
      exclude: [
        'node_modules/',
        'dist/**',
        'src/setupTests.ts',
        'src/main.tsx',
        'src/vite-env.d.ts',
        '**/*.d.ts',
        '**/*.config.*',
        '**/types/**'
      ]
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  }
});
