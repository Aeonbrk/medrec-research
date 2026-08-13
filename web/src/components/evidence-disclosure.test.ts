// @vitest-environment jsdom

import * as React from "react"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it } from "vitest"

import {
  EvidenceDisclosure,
  safeEvidenceUrl,
} from "@/components/evidence-disclosure"

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

describe("evidence disclosure", () => {
  it("reveals public evidence and updates the accessible trigger label", async () => {
    const user = userEvent.setup()
    render(
      React.createElement(EvidenceDisclosure, {
        evidence: [
          {
            label: "GAMENet source",
            url: "https://github.com/sjy1203/GAMENet",
          },
        ],
      })
    )

    const trigger = screen.getByRole("button", { name: "展开公开证据" })
    expect(screen.queryByText("GAMENet source")).toBeNull()

    await user.click(trigger)

    expect(
      screen
        .getByRole("button", { name: "收起公开证据" })
        .getAttribute("aria-expanded")
    ).toBe("true")
    expect(screen.getByRole("link", { name: /GAMENet source/ })).not.toBeNull()
  })
})
