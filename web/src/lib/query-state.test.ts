import { describe, expect, it } from "vitest"

import { defaultViewState } from "@/lib/domain"
import { parseViewState, serializeViewState } from "@/lib/query-state"

describe("URL query view state", () => {
  it("omits defaults and round-trips non-default values", () => {
    expect(serializeViewState(defaultViewState)).toBe("")
    const search = serializeViewState({
      section: "hitl",
      query: "molerec SHA",
      status: "blocked",
      sort: "state",
      order: "desc",
      theme: "dark",
      density: "comfortable",
    })
    expect(parseViewState(search)).toEqual({
      section: "hitl",
      query: "molerec SHA",
      status: "blocked",
      sort: "state",
      order: "desc",
      theme: "dark",
      density: "comfortable",
    })
  })

  it("fails closed to defaults for unsupported values and caps search length", () => {
    const parsed = parseViewState(
      `?section=admin&status=ready&sort=count&theme=neon&density=tiny&q=${"x".repeat(200)}`
    )
    expect({ ...parsed, query: "" }).toEqual(defaultViewState)
    expect(parsed.query).toHaveLength(160)
  })
})
