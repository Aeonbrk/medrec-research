import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig, type Plugin } from "vite"

const stripWhitespaceOnlyLines: Plugin = {
  name: "strip-whitespace-only-lines",
  generateBundle(_, bundle) {
    for (const output of Object.values(bundle)) {
      if (output.type === "chunk")
        output.code = output.code.replace(/^[\t ]+$/gm, "")
    }
  },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(), stripWhitespaceOnlyLines],
  build: {
    outDir: "../src/medrec_research/web",
    emptyOutDir: true,
  },
  resolve: {
    alias: {
      "@": new URL("./src", import.meta.url).pathname,
    },
  },
})
