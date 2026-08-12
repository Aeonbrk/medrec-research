import { describe, expect, it } from "vitest"

import { safeEvidenceUrl } from "@/components/evidence-disclosure"

describe("public evidence URL boundary", () => {
  it("accepts allowlisted HTTPS evidence without credentials", () => {
    expect(safeEvidenceUrl("https://github.com/example/project?ref=main")).toBe(
      "https://github.com/example/project?ref=main"
    )
  })

  it.each([
    "http://github.com/example/project",
    "https://user@github.com/example/project",
    "https://github.com:443/example/project",
    "https://github.com/example/project#token",
    "https://github.com/example/project?sig=private",
    "https://example.com/project",
  ])("rejects unsafe evidence URL %s", (value) => {
    expect(safeEvidenceUrl(value)).toBeNull()
  })
})
