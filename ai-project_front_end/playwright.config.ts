import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/ui/generated',
<<<<<<< HEAD
  snapshotDir: './tests/ui/baseline',
  snapshotPathTemplate: '{snapshotDir}/{arg}{ext}',
=======
>>>>>>> 0f64092fd6c7abac3f72736aa6652163d25e1b0b
  timeout: 60_000,
  expect: {
    timeout: 10_000
  },
  fullyParallel: false,
  retries: 0,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'tests/ui/reports/html', open: 'never' }]
  ],
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure'
  },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 4173',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: true,
    timeout: 120_000
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] }
    }
  ]
})
