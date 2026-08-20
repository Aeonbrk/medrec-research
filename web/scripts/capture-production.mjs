import { chromium } from "@playwright/test"
import { spawn } from "node:child_process"
import { createServer } from "node:net"
import process from "node:process"

const root = new URL("../../", import.meta.url).pathname
const port = await new Promise((resolve, reject) => {
  const server = createServer()
  server.once("error", reject)
  server.listen(0, "127.0.0.1", () => {
    const address = server.address()
    if (!address || typeof address === "string") {
      reject(new Error("unable to allocate loopback screenshot port"))
      return
    }
    server.close((error) => (error ? reject(error) : resolve(address.port)))
  })
})

const harness = spawn("python3", ["scripts/production-harness.py"], {
  cwd: new URL("../", import.meta.url).pathname,
  env: {
    ...process.env,
    MEDREC_HARNESS_PORT: String(port),
    PYTHONPATH: `${root}src`,
  },
  stdio: ["ignore", "pipe", "inherit"],
})

await new Promise((resolve, reject) => {
  harness.once("error", reject)
  harness.once("exit", (code) => reject(new Error(`production harness exited with ${code}`)))
  harness.stdout.setEncoding("utf8")
  harness.stdout.once("data", resolve)
})

const browser = await chromium.launch()
try {
  const desktop = await browser.newPage({ viewport: { width: 1440, height: 1024 } })
  await desktop.goto(`http://127.0.0.1:${port}/?theme=light`, { waitUntil: "networkidle" })
  await desktop.screenshot({
    path: `${root}docs/assets/research-console/after-desktop.png`,
    fullPage: true,
  })

  const desktopDark = await browser.newPage({
    colorScheme: "dark",
    viewport: { width: 1440, height: 1024 },
  })
  await desktopDark.goto(`http://127.0.0.1:${port}/?theme=dark`, {
    waitUntil: "networkidle",
  })
  await desktopDark.screenshot({
    path: `${root}docs/assets/research-console/after-desktop-dark.png`,
    fullPage: true,
  })

  const mobile = await browser.newPage({
    colorScheme: "dark",
    deviceScaleFactor: 1,
    hasTouch: true,
    isMobile: true,
    viewport: { width: 390, height: 844 },
  })
  await mobile.goto(`http://127.0.0.1:${port}/?theme=dark`, {
    waitUntil: "networkidle",
  })
  await mobile.screenshot({
    path: `${root}docs/assets/research-console/after-mobile.png`,
    fullPage: true,
  })
} finally {
  await browser.close()
  harness.kill("SIGINT")
}
