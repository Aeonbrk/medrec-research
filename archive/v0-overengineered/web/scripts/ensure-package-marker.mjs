import { writeFile } from "node:fs/promises"
import { fileURLToPath } from "node:url"

const marker = fileURLToPath(
  new URL("../../src/medrec_research/web/__init__.py", import.meta.url)
)

await writeFile(marker, '"""Built MedRec research console package resources."""\n')
