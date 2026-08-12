import { describe, expect, it } from "vitest"

import {
  candidateState,
  laneState,
  matchesQuery,
  stableSort,
  validateActionContext,
  validateActionDecision,
  type CandidateStatus,
  type ResearchLane,
} from "@/lib/domain"

const candidate = (patch: Partial<CandidateStatus> = {}): CandidateStatus => ({
  candidate_id: "molerec",
  display_name: "MoleRec",
  readiness: "comparison_ready",
  source_gate: "pass",
  license_gate: "pass",
  evidence: [],
  ...patch,
})

const lane = (patch: Partial<ResearchLane> = {}): ResearchLane => ({
  lane_id: "molerec",
  model_id: "molerec",
  stage: "safedrug",
  attempt_status: "completed",
  conclusion: "accepted",
  packet_complete: true,
  h2_go_eligible: true,
  current: true,
  h2_action: "go",
  blockers: [],
  evidence_urls: [],
  ...patch,
})

describe("research state mapping", () => {
  it("maps only fully gated candidates to pass", () => {
    expect(candidateState(candidate())).toBe("pass")
    expect(candidateState(candidate({ license_gate: "unresolved" }))).toBe(
      "attention"
    )
    expect(candidateState(candidate({ source_gate: "fail" }))).toBe("blocked")
  })

  it("fails lane state closed when currentness or blockers fail", () => {
    expect(laneState(lane())).toBe("pass")
    expect(laneState(lane({ packet_complete: false }))).toBe("attention")
    expect(laneState(lane({ current: false }))).toBe("blocked")
    expect(laneState(lane({ blockers: ["packet-incomplete"] }))).toBe("blocked")
  })

  it("filters Chinese and machine identifiers and sorts stably", () => {
    expect(
      matchesQuery(["候选基线", ["MoleRec", "comparison_ready"]], "molerec")
    ).toBe(true)
    const values = [
      candidate({ candidate_id: "b" }),
      candidate({ candidate_id: "a" }),
    ]
    expect(
      stableSort(
        values,
        (item) => item.candidate_id,
        candidateState,
        "identity",
        "asc"
      ).map((item) => item.candidate_id)
    ).toEqual(["a", "b"])
  })
})

describe("action schema validation", () => {
  it("does not accept hidden disabled context fields", () => {
    expect(() =>
      validateActionContext({
        enabled: false,
        kind: "action_context",
        reason_code: "invented",
        schema_version: 1,
      })
    ).toThrow("malformed:context_fields")
  })

  it("distinguishes blocked, allowed, and malformed decisions", () => {
    expect(
      validateActionDecision({
        kind: "action_decision",
        reason_code: "authority_bundle_missing",
        request: null,
        schema_version: 1,
        status: "blocked",
      }).status
    ).toBe("blocked")
    expect(() =>
      validateActionDecision({
        kind: "action_decision",
        reason_code: "allowed",
        request: null,
        schema_version: 1,
        status: "allowed",
      })
    ).toThrow("malformed:decision_shape")
  })
})
