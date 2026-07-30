import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';

// Portal rule: relative paths only (game runs inside an iframe on a CDN path).
export default defineConfig({
  base: './',
  plugins: [tailwindcss()],
  build: {
    target: 'es2020',
    assetsInlineLimit: 8192,
  },
});
