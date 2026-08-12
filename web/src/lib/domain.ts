export const sections = [
  "overview",
  "candidates",
  "lineage",
  "hitl",
  "authority",
] as const
export const statusFilters = ["all", "pass", "attention", "blocked"] as const
export const sortFields = ["identity", "state"] as const
export const sortOrders = ["asc", "desc"] as const
export const themes = ["system", "light", "dark"] as const
export const densities = ["compact", "comfortable"] as const

export type Section = (typeof sections)[number]
export type StatusFilter = (typeof statusFilters)[number]
export type SortField = (typeof sortFields)[number]
export type SortOrder = (typeof sortOrders)[number]
export type Theme = (typeof themes)[number]
export type Density = (typeof densities)[number]
export type RowState = Exclude<StatusFilter, "all">

export type Evidence = {
  label: string
  url: string
}

export type CandidateStatus = {
  candidate_id: string
  display_name: string
  readiness: "registered" | "smoke_ready" | "comparison_ready"
  source_gate: "pass" | "fail" | "unresolved"
  license_gate: "pass" | "fail" | "unresolved"
  evidence: Evidence[]
}

export type LineageStatus = {
  layer: string
  upstream_repository: string
  candidate_ids: string[]
  evidence: Evidence[]
}

export type AuthorityDigest = {
  authority_id: string
  sha256: string
}

export type Blocker = {
  category: string
  reason_code: string
  candidate_id: string | null
}

export type NextAction = {
  action_id: string
  label: string
}

export type ProjectStatus = {
  kind: "project_status"
  schema_version: 1
  project_id: string
  condition: "current" | "stale" | "degraded"
  generated_at: string
  valid_until: string
  snapshot_sha256: string
  authorities: AuthorityDigest[]
  blockers: Blocker[]
  primary_blocker: Blocker | null
  next_action: NextAction | null
  permitted_actions: NextAction[]
  payload: {
    stage: string
    qualified_count: number
    review_state: string
    discovery_eligible: boolean
    candidates: CandidateStatus[]
    shared_lineage: LineageStatus[]
  }
}

export type ActionContext =
  | { enabled: false; kind: "action_context"; schema_version: 1 }
  | {
      enabled: true
      kind: "action_context"
      request_id: string
      schema_version: 1
    }

export type HarnessState = {
  kind: "harness_state"
  schema_version: 1
  action_context: ActionContext
  status: ProjectStatus
}

export type ResearchLane = {
  lane_id: string
  model_id: string
  stage: string
  attempt_status: string
  conclusion: string
  packet_complete: boolean
  h2_go_eligible: boolean
  current: boolean
  h2_action: string | null
  blockers: string[]
  evidence_urls: string[]
}

export type ResearchLoop = {
  kind: "research_loop_status"
  schema_version: 1
  contract_sha256: string | null
  h1_current: boolean
  stale: boolean
  status_sha256: string
  lanes: ResearchLane[]
  blockers: string[]
}

export type HitlControl = {
  kind: "hitl_control"
  schema_version: 1
  blockers: string[]
  h1: {
    current: boolean
    enabled: boolean
    owner: string | null
  }
  h2: Array<{
    current_action: string | null
    enabled: boolean
    go_eligible: boolean
    lane_id: string
  }>
}

export type ActionDecision =
  | {
      kind: "action_decision"
      schema_version: 1
      status: "allowed"
      reason_code: string
      request: { request_id: string; request_sha256: string }
    }
  | {
      kind: "action_decision"
      schema_version: 1
      status: "blocked"
      reason_code: string
      request: null
    }

export type ViewState = {
  section: Section
  query: string
  status: StatusFilter
  sort: SortField
  order: SortOrder
  theme: Theme
  density: Density
}

export const defaultViewState: ViewState = {
  section: "overview",
  query: "",
  status: "all",
  sort: "identity",
  order: "asc",
  theme: "system",
  density: "compact",
}

type RecordValue = Record<string, unknown>

export function isRecord(value: unknown): value is RecordValue {
  return value !== null && typeof value === "object" && !Array.isArray(value)
}

function exactKeys(value: RecordValue, keys: string[]) {
  return Object.keys(value).sort().join("|") === [...keys].sort().join("|")
}

function stringValue(value: unknown, field: string) {
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`malformed:${field}`)
  }
  return value
}

function booleanValue(value: unknown, field: string) {
  if (typeof value !== "boolean") throw new Error(`malformed:${field}`)
  return value
}

function stringArray(value: unknown, field: string) {
  if (!Array.isArray(value)) throw new Error(`malformed:${field}`)
  return value.map((item, index) => stringValue(item, `${field}.${index}`))
}

function evidenceArray(value: unknown, field: string): Evidence[] {
  if (!Array.isArray(value)) throw new Error(`malformed:${field}`)
  return value.map((item, index) => {
    if (!isRecord(item)) throw new Error(`malformed:${field}.${index}`)
    return {
      label: stringValue(item.label, `${field}.${index}.label`),
      url: stringValue(item.url, `${field}.${index}.url`),
    }
  })
}

function candidateValue(value: unknown, index: number): CandidateStatus {
  if (!isRecord(value)) throw new Error(`malformed:candidate.${index}`)
  const readiness = stringValue(value.readiness, `candidate.${index}.readiness`)
  const sourceGate = stringValue(
    value.source_gate,
    `candidate.${index}.source_gate`
  )
  const licenseGate = stringValue(
    value.license_gate,
    `candidate.${index}.license_gate`
  )
  if (!["registered", "smoke_ready", "comparison_ready"].includes(readiness)) {
    throw new Error(`malformed:candidate.${index}.readiness`)
  }
  if (!["pass", "fail", "unresolved"].includes(sourceGate)) {
    throw new Error(`malformed:candidate.${index}.source_gate`)
  }
  if (!["pass", "fail", "unresolved"].includes(licenseGate)) {
    throw new Error(`malformed:candidate.${index}.license_gate`)
  }
  return {
    candidate_id: stringValue(
      value.candidate_id,
      `candidate.${index}.candidate_id`
    ),
    display_name: stringValue(
      value.display_name,
      `candidate.${index}.display_name`
    ),
    readiness: readiness as CandidateStatus["readiness"],
    source_gate: sourceGate as CandidateStatus["source_gate"],
    license_gate: licenseGate as CandidateStatus["license_gate"],
    evidence: evidenceArray(value.evidence, `candidate.${index}.evidence`),
  }
}

function lineageValue(value: unknown, index: number): LineageStatus {
  if (!isRecord(value)) throw new Error(`malformed:lineage.${index}`)
  return {
    layer: stringValue(value.layer, `lineage.${index}.layer`),
    upstream_repository: stringValue(
      value.upstream_repository,
      `lineage.${index}.upstream_repository`
    ),
    candidate_ids: stringArray(
      value.candidate_ids,
      `lineage.${index}.candidate_ids`
    ),
    evidence: evidenceArray(value.evidence, `lineage.${index}.evidence`),
  }
}

function blockerValue(value: unknown, field: string): Blocker {
  if (!isRecord(value)) throw new Error(`malformed:${field}`)
  if (value.candidate_id !== null && typeof value.candidate_id !== "string") {
    throw new Error(`malformed:${field}.candidate_id`)
  }
  return {
    category: stringValue(value.category, `${field}.category`),
    reason_code: stringValue(value.reason_code, `${field}.reason_code`),
    candidate_id: value.candidate_id,
  }
}

export function validateProjectStatus(value: unknown): ProjectStatus {
  if (
    !isRecord(value) ||
    value.kind !== "project_status" ||
    value.schema_version !== 1
  ) {
    throw new Error("malformed:status")
  }
  if (!isRecord(value.payload)) throw new Error("malformed:payload")
  const condition = stringValue(value.condition, "condition")
  if (!["current", "stale", "degraded"].includes(condition)) {
    throw new Error("malformed:condition")
  }
  if (!Array.isArray(value.payload.candidates))
    throw new Error("malformed:candidates")
  if (!Array.isArray(value.payload.shared_lineage))
    throw new Error("malformed:lineage")
  if (!Array.isArray(value.authorities))
    throw new Error("malformed:authorities")
  if (!Array.isArray(value.blockers)) throw new Error("malformed:blockers")
  if (!Array.isArray(value.permitted_actions))
    throw new Error("malformed:permitted_actions")
  if (!Number.isInteger(value.payload.qualified_count)) {
    throw new Error("malformed:qualified_count")
  }
  const nextAction = value.next_action
  if (nextAction !== null && !isRecord(nextAction))
    throw new Error("malformed:next_action")
  const primaryBlocker = value.primary_blocker
  return {
    kind: "project_status",
    schema_version: 1,
    project_id: stringValue(value.project_id, "project_id"),
    condition: condition as ProjectStatus["condition"],
    generated_at: stringValue(value.generated_at, "generated_at"),
    valid_until: stringValue(value.valid_until, "valid_until"),
    snapshot_sha256: stringValue(value.snapshot_sha256, "snapshot_sha256"),
    authorities: value.authorities.map((item, index) => {
      if (!isRecord(item)) throw new Error(`malformed:authority.${index}`)
      return {
        authority_id: stringValue(
          item.authority_id,
          `authority.${index}.authority_id`
        ),
        sha256: stringValue(item.sha256, `authority.${index}.sha256`),
      }
    }),
    blockers: value.blockers.map((item, index) =>
      blockerValue(item, `blocker.${index}`)
    ),
    primary_blocker:
      primaryBlocker === null
        ? null
        : blockerValue(primaryBlocker, "primary_blocker"),
    next_action:
      nextAction === null
        ? null
        : {
            action_id: stringValue(
              nextAction.action_id,
              "next_action.action_id"
            ),
            label: stringValue(nextAction.label, "next_action.label"),
          },
    permitted_actions: value.permitted_actions.map((item, index) => {
      if (!isRecord(item))
        throw new Error(`malformed:permitted_action.${index}`)
      return {
        action_id: stringValue(
          item.action_id,
          `permitted_action.${index}.action_id`
        ),
        label: stringValue(item.label, `permitted_action.${index}.label`),
      }
    }),
    payload: {
      stage: stringValue(value.payload.stage, "payload.stage"),
      qualified_count: value.payload.qualified_count as number,
      review_state: stringValue(
        value.payload.review_state,
        "payload.review_state"
      ),
      discovery_eligible: booleanValue(
        value.payload.discovery_eligible,
        "payload.discovery_eligible"
      ),
      candidates: value.payload.candidates.map(candidateValue),
      shared_lineage: value.payload.shared_lineage.map(lineageValue),
    },
  }
}

export function validateActionContext(value: unknown): ActionContext {
  if (
    !isRecord(value) ||
    value.kind !== "action_context" ||
    value.schema_version !== 1
  ) {
    throw new Error("malformed:context")
  }
  const enabled = booleanValue(value.enabled, "context.enabled")
  const keys = enabled
    ? ["enabled", "kind", "request_id", "schema_version"]
    : ["enabled", "kind", "schema_version"]
  if (!exactKeys(value, keys)) throw new Error("malformed:context_fields")
  return enabled
    ? {
        enabled: true,
        kind: "action_context",
        request_id: stringValue(value.request_id, "context.request_id"),
        schema_version: 1,
      }
    : { enabled: false, kind: "action_context", schema_version: 1 }
}

export function validateHarnessState(value: unknown): HarnessState {
  if (
    !isRecord(value) ||
    value.kind !== "harness_state" ||
    value.schema_version !== 1
  ) {
    throw new Error("malformed:harness_state")
  }
  if (
    !exactKeys(value, ["action_context", "kind", "schema_version", "status"])
  ) {
    throw new Error("malformed:harness_state_fields")
  }
  return {
    kind: "harness_state",
    schema_version: 1,
    action_context: validateActionContext(value.action_context),
    status: validateProjectStatus(value.status),
  }
}

export function validateResearchLoop(value: unknown): ResearchLoop {
  if (
    !isRecord(value) ||
    value.kind !== "research_loop_status" ||
    value.schema_version !== 1
  ) {
    throw new Error("malformed:research_loop")
  }
  if (
    value.contract_sha256 !== null &&
    typeof value.contract_sha256 !== "string"
  ) {
    throw new Error("malformed:research_loop.contract_sha256")
  }
  if (!Array.isArray(value.lanes) || !Array.isArray(value.blockers)) {
    throw new Error("malformed:research_loop.collections")
  }
  return {
    kind: "research_loop_status",
    schema_version: 1,
    contract_sha256: value.contract_sha256,
    h1_current: booleanValue(value.h1_current, "research_loop.h1_current"),
    stale: booleanValue(value.stale, "research_loop.stale"),
    status_sha256: stringValue(
      value.status_sha256,
      "research_loop.status_sha256"
    ),
    blockers: stringArray(value.blockers, "research_loop.blockers"),
    lanes: value.lanes.map((lane, index) => {
      if (!isRecord(lane)) throw new Error(`malformed:lane.${index}`)
      if (lane.h2_action !== null && typeof lane.h2_action !== "string") {
        throw new Error(`malformed:lane.${index}.h2_action`)
      }
      return {
        lane_id: stringValue(lane.lane_id, `lane.${index}.lane_id`),
        model_id: stringValue(lane.model_id, `lane.${index}.model_id`),
        stage: stringValue(lane.stage, `lane.${index}.stage`),
        attempt_status: stringValue(
          lane.attempt_status,
          `lane.${index}.attempt_status`
        ),
        conclusion: stringValue(lane.conclusion, `lane.${index}.conclusion`),
        packet_complete: booleanValue(
          lane.packet_complete,
          `lane.${index}.packet_complete`
        ),
        h2_go_eligible: booleanValue(
          lane.h2_go_eligible,
          `lane.${index}.h2_go_eligible`
        ),
        current: booleanValue(lane.current, `lane.${index}.current`),
        h2_action: lane.h2_action,
        blockers: stringArray(lane.blockers, `lane.${index}.blockers`),
        evidence_urls: stringArray(
          lane.evidence_urls,
          `lane.${index}.evidence_urls`
        ),
      }
    }),
  }
}

export function validateHitlControl(value: unknown): HitlControl {
  if (
    !isRecord(value) ||
    value.kind !== "hitl_control" ||
    value.schema_version !== 1 ||
    !Array.isArray(value.blockers) ||
    !Array.isArray(value.h2) ||
    !isRecord(value.h1)
  ) {
    throw new Error("malformed:hitl_control")
  }
  if (value.h1.owner !== null && typeof value.h1.owner !== "string") {
    throw new Error("malformed:hitl_control.h1.owner")
  }
  return {
    kind: "hitl_control",
    schema_version: 1,
    blockers: stringArray(value.blockers, "hitl_control.blockers"),
    h1: {
      current: booleanValue(value.h1.current, "hitl_control.h1.current"),
      enabled: booleanValue(value.h1.enabled, "hitl_control.h1.enabled"),
      owner: value.h1.owner,
    },
    h2: value.h2.map((item, index) => {
      if (!isRecord(item)) throw new Error(`malformed:hitl_control.h2.${index}`)
      if (
        item.current_action !== null &&
        typeof item.current_action !== "string"
      ) {
        throw new Error(`malformed:hitl_control.h2.${index}.current_action`)
      }
      return {
        current_action: item.current_action,
        enabled: booleanValue(item.enabled, `hitl_control.h2.${index}.enabled`),
        go_eligible: booleanValue(
          item.go_eligible,
          `hitl_control.h2.${index}.go_eligible`
        ),
        lane_id: stringValue(item.lane_id, `hitl_control.h2.${index}.lane_id`),
      }
    }),
  }
}

export function validateActionDecision(value: unknown): ActionDecision {
  if (
    !isRecord(value) ||
    value.kind !== "action_decision" ||
    value.schema_version !== 1
  ) {
    throw new Error("malformed:decision")
  }
  const reasonCode = stringValue(value.reason_code, "decision.reason_code")
  if (value.status === "blocked" && value.request === null) {
    return {
      kind: "action_decision",
      schema_version: 1,
      status: "blocked",
      reason_code: reasonCode,
      request: null,
    }
  }
  if (value.status !== "allowed" || !isRecord(value.request)) {
    throw new Error("malformed:decision_shape")
  }
  return {
    kind: "action_decision",
    schema_version: 1,
    status: "allowed",
    reason_code: reasonCode,
    request: {
      request_id: stringValue(
        value.request.request_id,
        "decision.request.request_id"
      ),
      request_sha256: stringValue(
        value.request.request_sha256,
        "decision.request.request_sha256"
      ),
    },
  }
}

export function candidateState(candidate: CandidateStatus): RowState {
  if (candidate.source_gate === "fail" || candidate.license_gate === "fail")
    return "blocked"
  if (
    candidate.readiness === "comparison_ready" &&
    candidate.source_gate === "pass" &&
    candidate.license_gate === "pass"
  ) {
    return "pass"
  }
  return "attention"
}

export function laneState(lane: ResearchLane): RowState {
  if (lane.blockers.length > 0 || !lane.current) return "blocked"
  if (lane.h2_go_eligible && lane.packet_complete) return "pass"
  return "attention"
}

export function matchesQuery(parts: Array<string | string[]>, query: string) {
  const normalized = query.trim().toLocaleLowerCase("zh-CN")
  if (!normalized) return true
  return parts.flat().join(" ").toLocaleLowerCase("zh-CN").includes(normalized)
}

export function matchesStatus(state: RowState, filter: StatusFilter) {
  return filter === "all" || state === filter
}

export function stableSort<T>(
  values: T[],
  identity: (value: T) => string,
  state: (value: T) => string,
  field: SortField,
  order: SortOrder
) {
  const direction = order === "asc" ? 1 : -1
  const getter = field === "identity" ? identity : state
  return values
    .map((value, index) => ({ value, index }))
    .sort((left, right) => {
      const compared =
        getter(left.value).localeCompare(getter(right.value), "en") * direction
      return compared || left.index - right.index
    })
    .map(({ value }) => value)
}
