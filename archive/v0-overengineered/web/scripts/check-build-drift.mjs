import { mkdtemp, readdir, readFile, rm } from "node:fs/promises"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { spawn } from "node:child_process"
import process from "node:process"

const webRoot = new URL("../", import.meta.url).pathname
const committedRoot = new URL("../../src/medrec_research/web/", import.meta.url).pathname
const temporary = await mkdtemp(join(tmpdir(), "medrec-web-drift-"))

async function files(root, relative = "") {
  const entries = await readdir(join(root, relative), { withFileTypes: true })
  const result = []
  for (const entry of entries) {
    const path = join(relative, entry.name)
    if (entry.name === "__pycache__") continue
    if (entry.isDirectory()) result.push(...(await files(root, path)))
    else if (path !== "__init__.py") result.push(path)
  }
  return result.sort()
}

try {
  await new Promise((resolve, reject) => {
    const build = spawn(
      new URL("../node_modules/.bin/vite", import.meta.url).pathname,
      ["build", "--outDir", temporary, "--emptyOutDir"],
      { cwd: webRoot, stdio: "inherit" }
    )
    build.on("error", reject)
    build.on("exit", (code) => (code === 0 ? resolve() : reject(new Error(`vite exited ${code}`))))
  })
  const actual = await files(committedRoot)
  const rebuilt = await files(temporary)
  if (JSON.stringify(actual) !== JSON.stringify(rebuilt)) {
    throw new Error(`production asset file set drifted\ncommitted=${actual}\nrebuilt=${rebuilt}`)
  }
  for (const path of actual) {
    const [left, right] = await Promise.all([
      readFile(join(committedRoot, path)),
      readFile(join(temporary, path)),
    ])
    if (!left.equals(right)) throw new Error(`production asset drifted: ${path}`)
  }
  process.stdout.write(`production assets match clean rebuild (${actual.length} files)\n`)
} finally {
  await rm(temporary, { recursive: true, force: true })
}
