import { defineConfig, devices } from "@playwright/test"

const port = process.env.MEDREC_HARNESS_PORT ?? "41731"
const baseURL = `http://127.0.0.1:${port}`

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  workers: 1,
  reporter: "line",
  use: {
    baseURL,
    trace: "retain-on-failure",
  },
  webServer: {
    command: "PYTHONPATH=../src python3 scripts/production-harness.py",
    url: baseURL,
    reuseExistingServer: false,
    timeout: 30_000,
    env: { MEDREC_HARNESS_PORT: port },
  },
  projects: [
    { name: "desktop-chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile-chromium", use: { ...devices["Pixel 7"] } },
  ],
})
