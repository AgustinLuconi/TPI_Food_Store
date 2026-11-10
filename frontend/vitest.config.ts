import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'

// Config de tests separada de vite.config.ts: los tests no necesitan los plugins de React/Tailwind
// y así los tipos de `vite` y de `vitest` no se mezclan.
export default defineConfig({
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.ts'],
  },
})
