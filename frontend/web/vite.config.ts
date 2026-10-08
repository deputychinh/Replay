import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

declare const process: { env: Record<string, string | undefined> };

const API = process.env.RELAY_API ?? 'http://localhost:8030';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5190,
    strictPort: true,
    // Same origin in dev, like CloudFront → ALB in AWS: the refresh cookie just works.
    proxy: { '/api': { target: API, ws: true } },
  },
  build: { target: 'es2022', sourcemap: true },
  test: { globals: true, environment: 'jsdom', setupFiles: ['./src/test-setup.ts'], css: false },
});
