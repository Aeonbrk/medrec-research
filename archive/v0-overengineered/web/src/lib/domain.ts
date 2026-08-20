export const sections = [
  "pending",
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
export const executionStates = [
  "blocked",
  "queued",
  "submitting",
  "running",
  "monitoring",
  "intake",
  "review_pending",
  "completed",
  "cancelled",
  "failed",
  "stuck",
] as const
export const executionOutcomes = [
  "pending",
  "succeeded",
  "failed",
  "stuck",
  "cancelled",
] as const

export type Section = (typeof sections)[number]
export type StatusFilter = (typeof statusFilters)[number]
export type SortField = (typeof sortFields)[number]
export type SortOrder = (typeof sortOrders)[number]
export type Theme = (typeof themes)[number]
export type Density = (typeof densities)[number]
export type RowState = Exclude<StatusFilter, "all">
export type ExecutionState = (typeof executionStates)[number]
export type ExecutionOutcome = (typeof executionOutcomes)[number]

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

export type ResearchContract = {
  kind: "research_contract"
  schema_version: 1
  contract_sha256: string
  status: "current" | "stale"
  source: {
    repository: string
    revision: string
    branch: string
  }
  questionnaire: Array<{
    id: string
    label: string
    provenance: "protected" | "derived"
    value: string
  }>
  ai: {
    status: "unavailable" | "ready" | "error"
    reason_code: string
  }
}

export type TeamCompositionPreset =
  | "review_team"
  | "debug_team"
  | "feature_team"
  | "fullstack_team"
  | "research_team"
  | "security_team"
  | "migration_team"

export type DisplayMode = "tmux" | "iterm2" | "in-process"

export type TeammateSpec = {
  agent_id: string
  focus_dimension: string
  read_only: boolean
  role: string
}

export type TeamCompositionConfig = {
  kind: "team_composition_config"
  schema_version: 1
  preset: TeamCompositionPreset | string
  team_size: number
  display_mode: DisplayMode
  teammates: TeammateSpec[]
  complexity: "simple" | "moderate" | "complex" | "very_complex"
}

export type ContractAIResult = {
  kind: "contract_ai_result"
  schema_version: 1
  contract_sha256: string
  operation: "draft" | "challenge" | "review_team" | "debug_team"
  request_id: string
  status: "unavailable" | "ready" | "error"
  reason_code: string
  output: string | null
  h1_written: false
  team_config?: TeamCompositionConfig
}

export type PublicJson =
  | null
  | boolean
  | number
  | string
  | PublicJson[]
  | { [key: string]: PublicJson }

export type DecisionPacketRecord = {
  packet_id: string
  packet_sha256: string
  lane_id: string
  conclusion: string
  validity: string
  current: boolean
  go_eligible: boolean
  required_outcomes: string[]
  outcomes: PublicJson
  uncertainty: PublicJson
  limitations: string[]
  blockers: string[]
  attempts: Array<{
    attempt_id: string
    lane_id: string
    status: string
    validity: string
    outcomes: PublicJson
    uncertainty: PublicJson
    artifact_digests: { [key: string]: string }
    deviations: string[]
  }>
  raw_aggregate_table: PublicJson
  raw_artifact_reason: string
}

export type DecisionPacketControl = {
  kind: "decision_packet_control"
  schema_version: 1
  contract_sha256: string
  blockers: string[]
  packets: DecisionPacketRecord[]
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

export type ExecutionEvent = {
  kind: "execution_event"
  schema_version: 1
  sequence: number
  journal_sequence: number
  state: ExecutionState
  outcome: ExecutionOutcome
  reason_code: string
  occurred_at: string
  event_sha256: string
}

export type ExecutionRecord = {
  schema_version: 1
  request_id: string
  request_sha256: string
  contract_sha256: string
  h1_approval_sha256: string
  h2_decision_sha256: string | null
  declaration_id: string
  lane_id: string
  action_id: string
  blockers: string[]
  state: ExecutionState
  outcome: ExecutionOutcome
  events: ExecutionEvent[]
}

export type ExecutionDeclaration = {
  schema_version: 1
  declaration_id: string
  declaration_sha256: string
  lane_id: string
  baseline_id: string
  action_id: string
  kind: "local" | "manual" | "remote"
  source_revision: string
  environment_id: string
  resource_profile_id: string
  evidence_schema_id: string
  blockers: string[]
}

export type ExecutionControl = {
  kind: "execution_control"
  schema_version: 1
  queue: {
    kind: "execution_queue"
    schema_version: 1
    records: ExecutionRecord[]
  }
  registry: {
    kind: "execution_declaration_registry"
    schema_version: 1
    initial_lane_id: string
    lane_ids: string[]
    action_ids: string[]
    declarations: ExecutionDeclaration[]
  }
}

export type TransportControlOperation = "resume" | "cancel"

export type TransportControlResult = {
  kind: "transport_control_result"
  schema_version: 1
  operation: TransportControlOperation
  record: ExecutionRecord
}

export type ExecutionStreamEvent = {
  event_id: string
  request_sha256: string
  event: ExecutionEvent
}

export type ViewState = {
  section: Section
  selected: string
  query: string
  status: StatusFilter
  sort: SortField
  order: SortOrder
  theme: Theme
  density: Density
}

export const defaultViewState: ViewState = {
  section: "pending",
  selected: "",
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
  return Object.keys(value).toSorted().join("|") === keys.toSorted().join("|")
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

function integerValue(value: unknown, field: string) {
  if (!Number.isInteger(value) || (value as number) < 1) {
    throw new Error(`malformed:${field}`)
  }
  return value as number
}

function nullableString(value: unknown, field: string) {
  if (value === null) return null
  return stringValue(value, field)
}

function enumMember<T extends string>(
  value: unknown,
  options: readonly T[],
  field: string
): T {
  const member = stringValue(value, field)
  if (!options.includes(member as T)) throw new Error(`malformed:${field}`)
  return member as T
}

function stringArray(value: unknown, field: string) {
  if (!Array.isArray(value)) throw new Error(`malformed:${field}`)
  return value.map((item, index) => stringValue(item, `${field}.${index}`))
}

function publicJson(value: unknown, field: string): PublicJson {
  if (
    value === null ||
    typeof value === "boolean" ||
    typeof value === "string"
  ) {
    return value
  }
  if (typeof value === "number" && Number.isFinite(value)) return value
  if (Array.isArray(value))
    return value.map((item, index) => publicJson(item, `${field}.${index}`))
  if (isRecord(value)) {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [
        key,
        publicJson(item, `${field}.${key}`),
      ])
    )
  }
  throw new Error(`malformed:${field}`)
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

export function validateResearchContract(value: unknown): ResearchContract {
  if (
    !isRecord(value) ||
    value.kind !== "research_contract" ||
    value.schema_version !== 1 ||
    !isRecord(value.source) ||
    !isRecord(value.ai) ||
    !Array.isArray(value.questionnaire)
  ) {
    throw new Error("malformed:research_contract")
  }
  const aiStatus = enumMember(
    value.ai.status,
    ["unavailable", "ready", "error"] as const,
    "research_contract.ai.status"
  )
  const status = enumMember(
    value.status,
    ["current", "stale"] as const,
    "research_contract.status"
  )
  return {
    kind: "research_contract",
    schema_version: 1,
    contract_sha256: stringValue(
      value.contract_sha256,
      "research_contract.contract_sha256"
    ),
    status,
    source: {
      branch: stringValue(
        value.source.branch,
        "research_contract.source.branch"
      ),
      repository: stringValue(
        value.source.repository,
        "research_contract.source.repository"
      ),
      revision: stringValue(
        value.source.revision,
        "research_contract.source.revision"
      ),
    },
    questionnaire: value.questionnaire.map((item, index) => {
      if (!isRecord(item)) {
        throw new Error(`malformed:research_contract.questionnaire.${index}`)
      }
      return {
        id: stringValue(item.id, `research_contract.questionnaire.${index}.id`),
        label: stringValue(
          item.label,
          `research_contract.questionnaire.${index}.label`
        ),
        provenance: enumMember(
          item.provenance,
          ["protected", "derived"] as const,
          `research_contract.questionnaire.${index}.provenance`
        ),
        value: stringValue(
          item.value,
          `research_contract.questionnaire.${index}.value`
        ),
      }
    }),
    ai: {
      status: aiStatus,
      reason_code: stringValue(
        value.ai.reason_code,
        "research_contract.ai.reason_code"
      ),
    },
  }
}

export function validateContractAIResult(value: unknown): ContractAIResult {
  if (
    !isRecord(value) ||
    value.kind !== "contract_ai_result" ||
    value.schema_version !== 1 ||
    value.h1_written !== false
  ) {
    throw new Error("malformed:contract_ai_result")
  }
  const output =
    value.output === null
      ? null
      : stringValue(value.output, "contract_ai.output")
  let teamConfig: TeamCompositionConfig | undefined
  if (isRecord(value.team_config)) {
    const rawConfig = value.team_config
    if (
      rawConfig.kind === "team_composition_config" &&
      rawConfig.schema_version === 1 &&
      Array.isArray(rawConfig.teammates)
    ) {
      teamConfig = {
        kind: "team_composition_config",
        schema_version: 1,
        preset: stringValue(rawConfig.preset, "team_config.preset"),
        team_size:
          typeof rawConfig.team_size === "number"
            ? rawConfig.team_size
            : rawConfig.teammates.length,
        display_mode: enumMember(
          rawConfig.display_mode,
          ["tmux", "iterm2", "in-process"] as const,
          "team_config.display_mode"
        ),
        complexity: enumMember(
          rawConfig.complexity,
          ["simple", "moderate", "complex", "very_complex"] as const,
          "team_config.complexity"
        ),
        teammates: rawConfig.teammates.map((item, idx) => {
          if (!isRecord(item)) throw new Error(`malformed:teammate.${idx}`)
          return {
            agent_id: stringValue(item.agent_id, `teammate.${idx}.agent_id`),
            focus_dimension: stringValue(
              item.focus_dimension,
              `teammate.${idx}.focus_dimension`
            ),
            read_only: Boolean(item.read_only),
            role: stringValue(item.role, `teammate.${idx}.role`),
          }
        }),
      }
    }
  }

  return {
    kind: "contract_ai_result",
    schema_version: 1,
    contract_sha256: stringValue(
      value.contract_sha256,
      "contract_ai.contract_sha256"
    ),
    operation: enumMember(
      value.operation,
      ["draft", "challenge", "review_team", "debug_team"] as const,
      "contract_ai.operation"
    ),
    request_id: stringValue(value.request_id, "contract_ai.request_id"),
    status: enumMember(
      value.status,
      ["unavailable", "ready", "error"] as const,
      "contract_ai.status"
    ),
    reason_code: stringValue(value.reason_code, "contract_ai.reason_code"),
    output,
    h1_written: false,
    team_config: teamConfig,
  }
}

export function validateDecisionPacketControl(
  value: unknown
): DecisionPacketControl {
  if (
    !isRecord(value) ||
    value.kind !== "decision_packet_control" ||
    value.schema_version !== 1 ||
    !Array.isArray(value.blockers) ||
    !Array.isArray(value.packets)
  ) {
    throw new Error("malformed:decision_packet_control")
  }
  return {
    kind: "decision_packet_control",
    schema_version: 1,
    contract_sha256: stringValue(
      value.contract_sha256,
      "decision_packet_control.contract_sha256"
    ),
    blockers: stringArray(value.blockers, "decision_packet_control.blockers"),
    packets: value.packets.map((raw, index) => {
      if (!isRecord(raw) || !Array.isArray(raw.attempts)) {
        throw new Error(`malformed:decision_packet.${index}`)
      }
      return {
        packet_id: stringValue(
          raw.packet_id,
          `decision_packet.${index}.packet_id`
        ),
        packet_sha256: stringValue(
          raw.packet_sha256,
          `decision_packet.${index}.packet_sha256`
        ),
        lane_id: stringValue(raw.lane_id, `decision_packet.${index}.lane_id`),
        conclusion: stringValue(
          raw.conclusion,
          `decision_packet.${index}.conclusion`
        ),
        validity: stringValue(
          raw.validity,
          `decision_packet.${index}.validity`
        ),
        current: booleanValue(raw.current, `decision_packet.${index}.current`),
        go_eligible: booleanValue(
          raw.go_eligible,
          `decision_packet.${index}.go_eligible`
        ),
        required_outcomes: stringArray(
          raw.required_outcomes,
          `decision_packet.${index}.required_outcomes`
        ),
        outcomes: publicJson(raw.outcomes, `decision_packet.${index}.outcomes`),
        uncertainty: publicJson(
          raw.uncertainty,
          `decision_packet.${index}.uncertainty`
        ),
        limitations: stringArray(
          raw.limitations,
          `decision_packet.${index}.limitations`
        ),
        blockers: stringArray(
          raw.blockers,
          `decision_packet.${index}.blockers`
        ),
        attempts: raw.attempts.map((attempt, attemptIndex) => {
          if (!isRecord(attempt) || !isRecord(attempt.artifact_digests)) {
            throw new Error(
              `malformed:decision_packet.${index}.attempt.${attemptIndex}`
            )
          }
          const artifactDigests: Record<string, string> = {}
          for (const [key, digest] of Object.entries(
            attempt.artifact_digests
          )) {
            artifactDigests[key] = stringValue(
              digest,
              `decision_packet.${index}.attempt.${attemptIndex}.artifact_digests.${key}`
            )
          }
          return {
            attempt_id: stringValue(
              attempt.attempt_id,
              `decision_packet.${index}.attempt.${attemptIndex}.attempt_id`
            ),
            lane_id: stringValue(
              attempt.lane_id,
              `decision_packet.${index}.attempt.${attemptIndex}.lane_id`
            ),
            status: stringValue(
              attempt.status,
              `decision_packet.${index}.attempt.${attemptIndex}.status`
            ),
            validity: stringValue(
              attempt.validity,
              `decision_packet.${index}.attempt.${attemptIndex}.validity`
            ),
            outcomes: publicJson(
              attempt.outcomes,
              `decision_packet.${index}.attempt.${attemptIndex}.outcomes`
            ),
            uncertainty: publicJson(
              attempt.uncertainty,
              `decision_packet.${index}.attempt.${attemptIndex}.uncertainty`
            ),
            artifact_digests: artifactDigests,
            deviations: stringArray(
              attempt.deviations,
              `decision_packet.${index}.attempt.${attemptIndex}.deviations`
            ),
          }
        }),
        raw_aggregate_table: publicJson(
          raw.raw_aggregate_table,
          `decision_packet.${index}.raw_aggregate_table`
        ),
        raw_artifact_reason: stringValue(
          raw.raw_artifact_reason,
          `decision_packet.${index}.raw_artifact_reason`
        ),
      }
    }),
  }
}

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
] as const

const laneIds = [
  "gamenet",
  "safedrug",
  "molerec",
  "retain",
  "leap-safedrug",
] as const

function executionEventValue(value: unknown, field: string): ExecutionEvent {
  if (
    !isRecord(value) ||
    !exactKeys(value, [
      "event_sha256",
      "journal_sequence",
      "kind",
      "occurred_at",
      "outcome",
      "reason_code",
      "schema_version",
      "sequence",
      "state",
    ]) ||
    value.kind !== "execution_event" ||
    value.schema_version !== 1
  ) {
    throw new Error(`malformed:${field}`)
  }
  return {
    kind: "execution_event",
    schema_version: 1,
    sequence: integerValue(value.sequence, `${field}.sequence`),
    journal_sequence: integerValue(
      value.journal_sequence,
      `${field}.journal_sequence`
    ),
    state: enumMember(value.state, executionStates, `${field}.state`),
    outcome: enumMember(value.outcome, executionOutcomes, `${field}.outcome`),
    reason_code: stringValue(value.reason_code, `${field}.reason_code`),
    occurred_at: stringValue(value.occurred_at, `${field}.occurred_at`),
    event_sha256: stringValue(value.event_sha256, `${field}.event_sha256`),
  }
}

function executionRecordValue(value: unknown, index: number): ExecutionRecord {
  const field = `execution.records.${index}`
  if (
    !isRecord(value) ||
    !exactKeys(value, [
      "action_id",
      "blockers",
      "contract_sha256",
      "declaration_id",
      "events",
      "h1_approval_sha256",
      "h2_decision_sha256",
      "lane_id",
      "outcome",
      "request_id",
      "request_sha256",
      "schema_version",
      "state",
    ]) ||
    value.schema_version !== 1 ||
    !Array.isArray(value.events) ||
    value.events.length === 0
  ) {
    throw new Error(`malformed:${field}`)
  }
  const events = value.events.map((item, eventIndex) =>
    executionEventValue(item, `${field}.events.${eventIndex}`)
  )
  if (
    events.some((event, eventIndex) => event.sequence !== eventIndex + 1) ||
    new Set(events.map((event) => event.journal_sequence)).size !==
      events.length
  ) {
    throw new Error(`malformed:${field}.events`)
  }
  const state = enumMember(value.state, executionStates, `${field}.state`)
  const outcome = enumMember(
    value.outcome,
    executionOutcomes,
    `${field}.outcome`
  )
  const latest = events.at(-1)!
  if (latest.state !== state || latest.outcome !== outcome) {
    throw new Error(`malformed:${field}.projection`)
  }
  return {
    schema_version: 1,
    request_id: stringValue(value.request_id, `${field}.request_id`),
    request_sha256: stringValue(
      value.request_sha256,
      `${field}.request_sha256`
    ),
    contract_sha256: stringValue(
      value.contract_sha256,
      `${field}.contract_sha256`
    ),
    h1_approval_sha256: stringValue(
      value.h1_approval_sha256,
      `${field}.h1_approval_sha256`
    ),
    h2_decision_sha256: nullableString(
      value.h2_decision_sha256,
      `${field}.h2_decision_sha256`
    ),
    declaration_id: stringValue(
      value.declaration_id,
      `${field}.declaration_id`
    ),
    lane_id: enumMember(value.lane_id, laneIds, `${field}.lane_id`),
    action_id: enumMember(value.action_id, actionIds, `${field}.action_id`),
    blockers: stringArray(value.blockers, `${field}.blockers`),
    state,
    outcome,
    events,
  }
}

function declarationValue(value: unknown, index: number): ExecutionDeclaration {
  const field = `execution.declarations.${index}`
  if (
    !isRecord(value) ||
    !exactKeys(value, [
      "action_id",
      "baseline_id",
      "blockers",
      "declaration_id",
      "declaration_sha256",
      "environment_id",
      "evidence_schema_id",
      "kind",
      "lane_id",
      "resource_profile_id",
      "schema_version",
      "source_revision",
    ]) ||
    value.schema_version !== 1
  ) {
    throw new Error(`malformed:${field}`)
  }
  const kind = enumMember(
    value.kind,
    ["local", "manual", "remote"] as const,
    `${field}.kind`
  )
  return {
    schema_version: 1,
    declaration_id: stringValue(
      value.declaration_id,
      `${field}.declaration_id`
    ),
    declaration_sha256: stringValue(
      value.declaration_sha256,
      `${field}.declaration_sha256`
    ),
    lane_id: enumMember(value.lane_id, laneIds, `${field}.lane_id`),
    baseline_id: stringValue(value.baseline_id, `${field}.baseline_id`),
    action_id: enumMember(value.action_id, actionIds, `${field}.action_id`),
    kind,
    source_revision: stringValue(
      value.source_revision,
      `${field}.source_revision`
    ),
    environment_id: stringValue(
      value.environment_id,
      `${field}.environment_id`
    ),
    resource_profile_id: stringValue(
      value.resource_profile_id,
      `${field}.resource_profile_id`
    ),
    evidence_schema_id: stringValue(
      value.evidence_schema_id,
      `${field}.evidence_schema_id`
    ),
    blockers: stringArray(value.blockers, `${field}.blockers`),
  }
}

export function validateExecutionControl(value: unknown): ExecutionControl {
  if (
    !isRecord(value) ||
    !exactKeys(value, ["kind", "queue", "registry", "schema_version"]) ||
    value.kind !== "execution_control" ||
    value.schema_version !== 1 ||
    !isRecord(value.queue) ||
    !isRecord(value.registry)
  ) {
    throw new Error("malformed:execution")
  }
  if (
    !exactKeys(value.queue, ["kind", "records", "schema_version"]) ||
    value.queue.kind !== "execution_queue" ||
    value.queue.schema_version !== 1 ||
    !Array.isArray(value.queue.records)
  ) {
    throw new Error("malformed:execution.queue")
  }
  if (
    !exactKeys(value.registry, [
      "action_ids",
      "declarations",
      "initial_lane_id",
      "kind",
      "lane_ids",
      "schema_version",
    ]) ||
    value.registry.kind !== "execution_declaration_registry" ||
    value.registry.schema_version !== 1 ||
    !Array.isArray(value.registry.action_ids) ||
    !Array.isArray(value.registry.lane_ids) ||
    !Array.isArray(value.registry.declarations)
  ) {
    throw new Error("malformed:execution.registry")
  }
  const registeredActions = stringArray(
    value.registry.action_ids,
    "execution.registry.action_ids"
  )
  const registeredLanes = stringArray(
    value.registry.lane_ids,
    "execution.registry.lane_ids"
  )
  const declarations = value.registry.declarations.map(declarationValue)
  const matrix = new Set(
    declarations.map((item) => `${item.lane_id}:${item.action_id}`)
  )
  if (
    registeredActions.join("|") !== actionIds.join("|") ||
    registeredLanes.join("|") !== laneIds.join("|") ||
    value.registry.initial_lane_id !== laneIds[0] ||
    declarations.length !== laneIds.length * actionIds.length ||
    matrix.size !== declarations.length
  ) {
    throw new Error("malformed:execution.registry.matrix")
  }
  return {
    kind: "execution_control",
    schema_version: 1,
    queue: {
      kind: "execution_queue",
      schema_version: 1,
      records: value.queue.records.map(executionRecordValue),
    },
    registry: {
      kind: "execution_declaration_registry",
      schema_version: 1,
      initial_lane_id: value.registry.initial_lane_id,
      lane_ids: registeredLanes,
      action_ids: registeredActions,
      declarations,
    },
  }
}

export function validateTransportControlResult(
  value: unknown
): TransportControlResult {
  if (
    !isRecord(value) ||
    !exactKeys(value, ["kind", "operation", "record", "schema_version"]) ||
    value.kind !== "transport_control_result" ||
    value.schema_version !== 1 ||
    (value.operation !== "resume" && value.operation !== "cancel")
  ) {
    throw new Error("malformed:transport_control")
  }
  return {
    kind: "transport_control_result",
    schema_version: 1,
    operation: value.operation,
    record: executionRecordValue(value.record, 0),
  }
}

export function validateExecutionStreamEvent(
  value: unknown
): ExecutionStreamEvent {
  if (
    !isRecord(value) ||
    !exactKeys(value, ["event", "event_id", "request_sha256"])
  ) {
    throw new Error("malformed:execution_stream")
  }
  const event = executionEventValue(value.event, "execution_stream.event")
  const eventId = stringValue(value.event_id, "execution_stream.event_id")
  if (!/^\d+$/.test(eventId) || Number(eventId) !== event.journal_sequence) {
    throw new Error("malformed:execution_stream.cursor")
  }
  return {
    event,
    event_id: eventId,
    request_sha256: stringValue(
      value.request_sha256,
      "execution_stream.request_sha256"
    ),
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

const approvedHosts = new Set([
  "aclanthology.org",
  "arxiv.org",
  "dl.acm.org",
  "doi.org",
  "github.com",
  "ieeexplore.ieee.org",
  "openreview.net",
  "proceedings.mlr.press",
  "pubmed.ncbi.nlm.nih.gov",
  "raw.githubusercontent.com",
])

const credentialKeys = new Set([
  "access_token",
  "api_key",
  "apikey",
  "auth",
  "authorization",
  "credential",
  "key",
  "password",
  "passwd",
  "secret",
  "sig",
  "signature",
  "token",
])

export function safeEvidenceUrl(value: string): string | null {
  try {
    const decoded = decodeURIComponent(value)
    if (
      [...decoded].some(
        (character) =>
          character.charCodeAt(0) < 32 || character.charCodeAt(0) === 127
      )
    ) {
      return null
    }
    const authority = value.match(/^https:\/\/([^/?#]+)/i)?.[1] ?? ""
    const parsed = new URL(value)
    if (
      parsed.protocol !== "https:" ||
      parsed.username ||
      parsed.password ||
      authority.includes(":") ||
      parsed.port ||
      parsed.hash ||
      !approvedHosts.has(parsed.hostname)
    ) {
      return null
    }
    for (const key of parsed.searchParams.keys()) {
      if (credentialKeys.has(key.toLocaleLowerCase("en"))) return null
    }
    return parsed.href
  } catch {
    return null
  }
}

export function aggregateTableRows(
  value: PublicJson
): Array<Record<string, PublicJson>> | null {
  if (!Array.isArray(value) || value.length === 0) return null
  if (
    value.some(
      (row) => row === null || typeof row !== "object" || Array.isArray(row)
    )
  ) {
    return null
  }
  return value as Array<Record<string, PublicJson>>
}

export function permittedTransportOperations(
  record: ExecutionRecord
): TransportControlOperation[] {
  if (["submitting", "running", "monitoring"].includes(record.state)) {
    return ["cancel"]
  }
  const reason = record.events.at(-1)?.reason_code ?? ""
  if (
    record.state === "review_pending" &&
    reason.startsWith("aris-transport-")
  ) {
    return ["resume", "cancel"]
  }
  return []
}

