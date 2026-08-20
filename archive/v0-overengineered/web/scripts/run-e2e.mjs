import { spawn } from "node:child_process"
import { createServer } from "node:net"
import process from "node:process"

const port = await new Promise((resolve, reject) => {
  const server = createServer()
  server.once("error", reject)
  server.listen(0, "127.0.0.1", () => {
    const address = server.address()
    if (!address || typeof address === "string") {
      reject(new Error("unable to allocate loopback test port"))
      return
    }
    const selected = address.port
    server.close((error) => (error ? reject(error) : resolve(selected)))
  })
})

const child = spawn(
  new URL("../node_modules/.bin/playwright", import.meta.url).pathname,
  ["test", ...process.argv.slice(2)],
  {
    env: { ...process.env, MEDREC_HARNESS_PORT: String(port) },
    stdio: "inherit",
  }
)

child.on("exit", (code, signal) => {
  process.exitCode = signal ? 1 : (code ?? 1)
})
