import { spawn } from "node:child_process"
import { createServer } from "node:net"
import { mkdir, readFile } from "node:fs/promises"
import process from "node:process"

const root = new URL("../../", import.meta.url).pathname
const output = `${root}runtime/lighthouse/research-console.json`
await mkdir(`${root}runtime/lighthouse`, { recursive: true })

const port = await new Promise((resolve, reject) => {
  const server = createServer()
  server.once("error", reject)
  server.listen(0, "127.0.0.1", () => {
    const address = server.address()
    if (!address || typeof address === "string") {
      reject(new Error("unable to allocate loopback Lighthouse port"))
      return
    }
    server.close((error) => (error ? reject(error) : resolve(address.port)))
  })
})

const harness = spawn("python3", ["scripts/production-harness.py"], {
  cwd: new URL("../", import.meta.url).pathname,
  env: { ...process.env, MEDREC_HARNESS_PORT: String(port), PYTHONPATH: `${root}src` },
  stdio: ["ignore", "pipe", "inherit"],
})

await new Promise((resolve, reject) => {
  harness.once("error", reject)
  harness.once("exit", (code) => reject(new Error(`production harness exited with ${code}`)))
  harness.stdout.once("data", resolve)
})

try {
  await new Promise((resolve, reject) => {
    const lighthouse = spawn(
      new URL("../node_modules/.bin/lighthouse", import.meta.url).pathname,
      [
        `http://127.0.0.1:${port}/?theme=light`,
        "--quiet",
        "--chrome-flags=--headless=new --no-sandbox",
        "--preset=desktop",
        "--only-categories=performance,accessibility,best-practices",
        "--output=json",
        `--output-path=${output}`,
      ],
      { stdio: "inherit" }
    )
    lighthouse.on("error", reject)
    lighthouse.on("exit", (code) =>
      code === 0 ? resolve() : reject(new Error(`Lighthouse exited ${code}`))
    )
  })
  const report = JSON.parse(await readFile(output, "utf8"))
  const scores = Object.fromEntries(
    ["performance", "accessibility", "best-practices"].map((category) => [
      category,
      Math.round(report.categories[category].score * 100),
    ])
  )
  process.stdout.write(`${JSON.stringify(scores)}\n`)
  if (Object.values(scores).some((score) => score < 90)) {
    throw new Error(`Lighthouse target missed: ${JSON.stringify(scores)}`)
  }
} finally {
  harness.kill("SIGINT")
}
