import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/ui/real',
  timeout: 90_000,
  expect: {
    timeout: 15_000
  },
  fullyParallel: false,
  retries: 0,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'tests/ui/reports/real-html', open: 'never' }]
  ],
  use: {
    baseURL: process.env.WEITESTING_FRONTEND_URL || 'http://127.0.0.1:4173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure'
  },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 4173',
    url: process.env.WEITESTING_FRONTEND_URL || 'http://127.0.0.1:4173',
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
