import { describe, expect, it } from "vitest"

import {
  candidateState,
  laneState,
  matchesQuery,
  stableSort,
  validateActionContext,
  validateActionDecision,
  validateExecutionControl,
  validateExecutionStreamEvent,
  type CandidateStatus,
  type ResearchLane,
} from "@/lib/domain"

const actionIds = [
  "refresh_authorization",
  "resolve_source_license",
  "advance_readiness",
  "refresh_remote_preflight",
  "request_reproduction",
  "submit_reproduction_evidence",
  "request_next_lane",
  "submit_human_review",
  "begin_discovery",
]

const laneIds = ["gamenet", "safedrug", "molerec", "retain", "leap-safedrug"]

function executionFixture() {
  return {
    kind: "execution_control",
    schema_version: 1,
    queue: { kind: "execution_queue", records: [], schema_version: 1 },
    registry: {
      action_ids: actionIds,
      declarations: laneIds.flatMap((laneId) =>
        actionIds.map((actionId) => ({
          action_id: actionId,
          baseline_id: laneId,
          blockers:
            actionId === "request_reproduction" ? ["license-unresolved"] : [],
          declaration_id: `${laneId}-${actionId}`,
          declaration_sha256: "a".repeat(64),
          environment_id: `medrec-${laneId}`,
          evidence_schema_id: "public-safe-v1",
          kind: actionId === "request_reproduction" ? "remote" : "local",
          lane_id: laneId,
          resource_profile_id: "single-gpu-low-cost",
          schema_version: 1,
          source_revision: "b".repeat(40),
        }))
      ),
      initial_lane_id: "gamenet",
      kind: "execution_declaration_registry",
      lane_ids: laneIds,
      schema_version: 1,
    },
  }
}

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

describe("execution projection validation", () => {
  it("accepts only the closed final-five declaration matrix", () => {
    const control = validateExecutionControl(executionFixture())
    expect(control.registry.declarations).toHaveLength(45)
    expect(control.queue.records).toEqual([])
  })

  it("rejects browser-forbidden declaration fields", () => {
    const fixture = executionFixture()
    fixture.registry.declarations[0] = {
      ...fixture.registry.declarations[0],
      host: "319-wild",
    } as (typeof fixture.registry.declarations)[number]
    expect(() => validateExecutionControl(fixture)).toThrow(
      "malformed:execution.declarations.0"
    )
  })

  it("binds SSE cursors to the journal sequence", () => {
    const event = {
      event_id: "7",
      request_sha256: "c".repeat(64),
      event: {
        event_sha256: "d".repeat(64),
        journal_sequence: 7,
        kind: "execution_event",
        occurred_at: "2026-08-13T00:00:00Z",
        outcome: "pending",
        reason_code: "execution-queued",
        schema_version: 1,
        sequence: 1,
        state: "queued",
      },
    }
    expect(validateExecutionStreamEvent(event).event_id).toBe("7")
    expect(() =>
      validateExecutionStreamEvent({ ...event, event_id: "8" })
    ).toThrow("malformed:execution_stream.cursor")
  })
})
