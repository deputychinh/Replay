import { defineConfig, devices } from '@playwright/test';

// Needs the local stack: `make up` (Postgres, Redis, LocalStack, Mailpit), the API on :8030 and the worker.
export default defineConfig({
  testDir: 'e2e',
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: 'http://localhost:5190',
    trace: 'retain-on-failure',
    ...devices['Desktop Chrome'],
    viewport: { width: 1440, height: 900 },
    channel: process.env.CI ? undefined : 'chrome',
  },
  webServer: { command: 'npm run dev -w @relay/web', url: 'http://localhost:5190', reuseExistingServer: true },
});
