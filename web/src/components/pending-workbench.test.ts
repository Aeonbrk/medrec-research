import { describe, expect, it } from "vitest"

import {
  aggregateTableRows,
  permittedTransportOperations,
} from "@/components/pending-workbench"
import type { ExecutionRecord } from "@/lib/domain"

function executionRecord(
  state: ExecutionRecord["state"],
  reasonCode: string
): ExecutionRecord {
  return {
    action_id: "request_reproduction",
    blockers: [],
    contract_sha256: "a".repeat(64),
    declaration_id: "gamenet-request_reproduction",
    events: [
      {
        event_sha256: "b".repeat(64),
        journal_sequence: 1,
        kind: "execution_event",
        occurred_at: "2026-08-18T12:00:00Z",
        outcome: "pending",
        reason_code: reasonCode,
        schema_version: 1,
        sequence: 1,
        state,
      },
    ],
    h1_approval_sha256: "c".repeat(64),
    h2_decision_sha256: null,
    lane_id: "gamenet",
    outcome: "pending",
    request_id: "action-context-recovery",
    request_sha256: "d".repeat(64),
    schema_version: 1,
    state,
  }
}

describe("aggregateTableRows", () => {
  it("accepts public aggregate rows", () => {
    expect(
      aggregateTableRows([
        { metric: "f1", interval: [0.4, 0.6] },
        { metric: "prauc", interval: [0.3, 0.5] },
      ])
    ).toEqual([
      { metric: "f1", interval: [0.4, 0.6] },
      { metric: "prauc", interval: [0.3, 0.5] },
    ])
  })

  it("rejects unavailable or non-tabular projections", () => {
    expect(aggregateTableRows(null)).toBeNull()
    expect(aggregateTableRows([])).toBeNull()
    expect(aggregateTableRows(["not-a-row"])).toBeNull()
    expect(aggregateTableRows([["not", "a", "row"]])).toBeNull()
  })
})

describe("permittedTransportOperations", () => {
  it("offers cancellation for active fixed transport", () => {
    expect(
      permittedTransportOperations(
        executionRecord("monitoring", "aris-state-observed")
      )
    ).toEqual(["cancel"])
  })

  it("offers bounded recovery only for a transport failure", () => {
    expect(
      permittedTransportOperations(
        executionRecord("review_pending", "aris-transport-unreachable")
      )
    ).toEqual(["resume", "cancel"])
    expect(
      permittedTransportOperations(
        executionRecord("review_pending", "scientific-anomaly")
      )
    ).toEqual([])
  })
})
