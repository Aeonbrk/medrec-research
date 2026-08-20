import { describe, expect, it } from "vitest"

import {
  aggregateTableRows,
  permittedTransportOperations,
  validateContractAIResult,
  type ExecutionRecord,
} from "@/lib/domain"

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

describe("validateContractAIResult with team compositions", () => {
  it("parses multi-agent team composition and roles cleanly", () => {
    const raw = {
      kind: "contract_ai_result",
      schema_version: 1,
      contract_sha256: "e".repeat(64),
      operation: "review_team",
      request_id: "req-team-1",
      status: "ready",
      reason_code: "local-ai-complete",
      output: "Multi-reviewer findings",
      h1_written: false,
      team_config: {
        kind: "team_composition_config",
        schema_version: 1,
        preset: "review_team",
        team_size: 3,
        display_mode: "tmux",
        complexity: "moderate",
        teammates: [
          {
            agent_id: "reviewer-sec",
            focus_dimension: "Security & EHR Privacy",
            read_only: true,
            role: "team-reviewer",
          },
          {
            agent_id: "reviewer-perf",
            focus_dimension: "Methodology & Performance",
            read_only: true,
            role: "team-reviewer",
          },
          {
            agent_id: "reviewer-arch",
            focus_dimension: "Architecture & Lineage",
            read_only: true,
            role: "team-reviewer",
          },
        ],
      },
    }

    const result = validateContractAIResult(raw)
    expect(result.status).toBe("ready")
    expect(result.operation).toBe("review_team")
    expect(result.team_config).toBeDefined()
    expect(result.team_config?.preset).toBe("review_team")
    expect(result.team_config?.display_mode).toBe("tmux")
    expect(result.team_config?.teammates).toHaveLength(3)
    expect(result.team_config?.teammates[0].agent_id).toBe("reviewer-sec")
  })
})
