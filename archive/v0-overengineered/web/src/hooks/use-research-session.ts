import * as React from "react"

import { fetchJson, TransportError } from "@/lib/api"
import {
  validateActionDecision,
  validateContractAIResult,
  validateDecisionPacketControl,
  validateExecutionControl,
  validateExecutionStreamEvent,
  validateHarnessState,
  validateHitlControl,
  validateResearchContract,
  validateResearchLoop,
  validateTransportControlResult,
  type ActionDecision,
  type ContractAIResult,
  type DecisionPacketControl,
  type ExecutionControl,
  type HarnessState,
  type HitlControl,
  type ResearchContract,
  type ResearchLoop,
  type TransportControlOperation,
} from "@/lib/domain"

export type LoadFailure = "malformed" | "transport"

export type LoopState =
  | { phase: "loading" }
  | { phase: "ready"; value: ResearchLoop }
  | { phase: "unavailable" | LoadFailure }

export type ActionState =
  | { phase: "idle" }
  | { phase: "submitting" }
  | { phase: "allowed" | "blocked"; decision: ActionDecision }
  | { phase: LoadFailure }

export type HitlControlState =
  | { phase: "loading" }
  | { phase: "ready"; value: HitlControl }
  | { phase: "submitting" | "rejected" | LoadFailure }

export type ContractState =
  | { phase: "loading" }
  | { phase: "ready"; value: ResearchContract }
  | { phase: "unavailable" | LoadFailure }

export type ContractAIState =
  | { phase: "idle" | "submitting" }
  | { phase: "ready"; value: ContractAIResult }
  | { phase: "error" | LoadFailure }

export type PacketState =
  | { phase: "loading" }
  | { phase: "ready"; value: DecisionPacketControl }
  | { phase: "unavailable" | LoadFailure }

export type ExecutionControlState =
  | { phase: "loading" }
  | { phase: "ready"; value: ExecutionControl }
  | { phase: "unavailable" | LoadFailure }

export type ExecutionStreamState =
  | "connecting"
  | "live"
  | "reconnecting"
  | "malformed"

export type TransportControlState =
  | { phase: "idle" }
  | {
      phase: "submitting" | "succeeded" | "rejected" | LoadFailure
      operation: TransportControlOperation
      requestId: string
    }

export type ResearchSessionState = {
  harness: HarnessState | null
  failure: LoadFailure | null
  loop: LoopState
  hitl: HitlControlState
  contract: ContractState
  contractAI: ContractAIState
  packets: PacketState
  action: ActionState
  execution: ExecutionControlState
  executionStream: ExecutionStreamState
  transportControl: TransportControlState
}

type SessionAction =
  | { type: "LOAD_START" }
  | { type: "HARNESS_SUCCESS"; payload: HarnessState }
  | { type: "HARNESS_FAILURE"; payload: LoadFailure }
  | { type: "SET_LOOP"; payload: LoopState }
  | { type: "SET_HITL"; payload: HitlControlState }
  | { type: "SET_CONTRACT"; payload: ContractState }
  | { type: "SET_CONTRACT_AI"; payload: ContractAIState }
  | { type: "SET_PACKETS"; payload: PacketState }
  | { type: "SET_ACTION"; payload: ActionState }
  | { type: "SET_EXECUTION"; payload: ExecutionControlState }
  | { type: "SET_EXECUTION_STREAM"; payload: ExecutionStreamState }
  | { type: "SET_TRANSPORT_CONTROL"; payload: TransportControlState }

const initialSessionState: ResearchSessionState = {
  harness: null,
  failure: null,
  loop: { phase: "loading" },
  hitl: { phase: "loading" },
  contract: { phase: "loading" },
  contractAI: { phase: "idle" },
  packets: { phase: "loading" },
  action: { phase: "idle" },
  execution: { phase: "loading" },
  executionStream: "connecting",
  transportControl: { phase: "idle" },
}

function sessionReducer(
  state: ResearchSessionState,
  action: SessionAction
): ResearchSessionState {
  switch (action.type) {
    case "LOAD_START":
      return {
        ...state,
        harness: null,
        failure: null,
        loop: { phase: "loading" },
        hitl: { phase: "loading" },
        contract: { phase: "loading" },
        contractAI: { phase: "idle" },
        packets: { phase: "loading" },
        action: { phase: "idle" },
        execution: { phase: "loading" },
        transportControl: { phase: "idle" },
      }
    case "HARNESS_SUCCESS":
      return { ...state, harness: action.payload, failure: null }
    case "HARNESS_FAILURE":
      return { ...state, failure: action.payload, harness: null }
    case "SET_LOOP":
      return { ...state, loop: action.payload }
    case "SET_HITL":
      return { ...state, hitl: action.payload }
    case "SET_CONTRACT":
      return { ...state, contract: action.payload }
    case "SET_CONTRACT_AI":
      return { ...state, contractAI: action.payload }
    case "SET_PACKETS":
      return { ...state, packets: action.payload }
    case "SET_ACTION":
      return { ...state, action: action.payload }
    case "SET_EXECUTION":
      return { ...state, execution: action.payload }
    case "SET_EXECUTION_STREAM":
      return { ...state, executionStream: action.payload }
    case "SET_TRANSPORT_CONTROL":
      return { ...state, transportControl: action.payload }
    default:
      return state
  }
}

export function failureKind(error: unknown): LoadFailure {
  return error instanceof TransportError || error instanceof TypeError
    ? "transport"
    : "malformed"
}

export function useResearchSession() {
  const [state, dispatch] = React.useReducer(
    sessionReducer,
    initialSessionState
  )
  const inFlight = React.useRef(false)
  const executionInFlight = React.useRef(false)
  const loadInFlight = React.useRef(false)
  const executionRecoveryRequired = React.useRef(false)

  const refreshExecution = React.useCallback(async (force = false) => {
    if (
      executionInFlight.current ||
      (!force && (loadInFlight.current || executionRecoveryRequired.current))
    ) {
      return
    }
    executionInFlight.current = true
    try {
      const value = validateExecutionControl(await fetchJson("/api/executions"))
      executionRecoveryRequired.current = false
      dispatch({ type: "SET_EXECUTION", payload: { phase: "ready", value } })
    } catch (error) {
      executionRecoveryRequired.current = true
      dispatch({
        type: "SET_EXECUTION",
        payload: {
          phase:
            error instanceof TransportError && error.status === 503
              ? "unavailable"
              : failureKind(error),
        },
      })
    } finally {
      executionInFlight.current = false
    }
  }, [])

  const load = React.useCallback(async () => {
    if (loadInFlight.current) return
    loadInFlight.current = true
    dispatch({ type: "LOAD_START" })
    inFlight.current = false
    executionRecoveryRequired.current = false

    try {
      const nextHarness = validateHarnessState(
        await fetchJson("/api/harness-state")
      )
      dispatch({ type: "HARNESS_SUCCESS", payload: nextHarness })
    } catch (error) {
      loadInFlight.current = false
      dispatch({ type: "HARNESS_FAILURE", payload: failureKind(error) })
      return
    }

    try {
      const nextLoop = validateResearchLoop(
        await fetchJson("/api/research-loop")
      )
      dispatch({
        type: "SET_LOOP",
        payload: { phase: "ready", value: nextLoop },
      })
    } catch (error) {
      dispatch({
        type: "SET_LOOP",
        payload: {
          phase:
            error instanceof TransportError && error.status === 503
              ? "unavailable"
              : failureKind(error),
        },
      })
    }

    try {
      dispatch({
        type: "SET_HITL",
        payload: {
          phase: "ready",
          value: validateHitlControl(await fetchJson("/api/hitl-control")),
        },
      })
    } catch (error) {
      dispatch({
        type: "SET_HITL",
        payload: { phase: failureKind(error) },
      })
    }

    try {
      dispatch({
        type: "SET_CONTRACT",
        payload: {
          phase: "ready",
          value: validateResearchContract(await fetchJson("/api/contract")),
        },
      })
    } catch (error) {
      dispatch({
        type: "SET_CONTRACT",
        payload: {
          phase:
            error instanceof TransportError && error.status === 503
              ? "unavailable"
              : failureKind(error),
        },
      })
    }

    try {
      dispatch({
        type: "SET_PACKETS",
        payload: {
          phase: "ready",
          value: validateDecisionPacketControl(
            await fetchJson("/api/decision-packets")
          ),
        },
      })
    } catch (error) {
      dispatch({
        type: "SET_PACKETS",
        payload: {
          phase:
            error instanceof TransportError && error.status === 503
              ? "unavailable"
              : failureKind(error),
        },
      })
    }

    loadInFlight.current = false
    await refreshExecution(true)
  }, [refreshExecution])

  React.useEffect(() => {
    void load()
  }, [load])

  React.useEffect(() => {
    if (!state.harness) return
    const source = new EventSource("/api/execution-events")
    dispatch({ type: "SET_EXECUTION_STREAM", payload: "connecting" })
    source.onopen = () =>
      dispatch({ type: "SET_EXECUTION_STREAM", payload: "live" })
    source.onerror = () =>
      dispatch({ type: "SET_EXECUTION_STREAM", payload: "reconnecting" })

    const receive = (message: Event) => {
      if (!(message instanceof MessageEvent)) return
      try {
        validateExecutionStreamEvent(JSON.parse(message.data) as unknown)
      } catch {
        source.close()
        dispatch({ type: "SET_EXECUTION_STREAM", payload: "malformed" })
        dispatch({
          type: "SET_EXECUTION",
          payload: { phase: "malformed" },
        })
        return
      }
      void refreshExecution()
    }

    source.addEventListener("execution", receive)
    return () => {
      source.removeEventListener("execution", receive)
      source.close()
    }
  }, [state.harness, refreshExecution])

  const requestAction = React.useCallback(async () => {
    const context = state.harness?.action_context
    if (!context?.enabled || inFlight.current) return
    inFlight.current = true
    dispatch({ type: "SET_ACTION", payload: { phase: "submitting" } })
    try {
      const decision = validateActionDecision(
        await fetchJson("/api/action-requests", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            kind: "action_request_input",
            request_id: context.request_id,
            schema_version: 1,
          }),
        })
      )
      dispatch({
        type: "SET_ACTION",
        payload: { phase: decision.status, decision },
      })
    } catch (error) {
      dispatch({
        type: "SET_ACTION",
        payload: { phase: failureKind(error) },
      })
    }
  }, [state.harness])

  const submitHitl = React.useCallback(
    async (path: "/api/h1" | "/api/h2", payload: Record<string, unknown>) => {
      dispatch({ type: "SET_HITL", payload: { phase: "submitting" } })
      try {
        await fetchJson(path, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        })
        await load()
      } catch (error) {
        dispatch({
          type: "SET_HITL",
          payload: {
            phase:
              error instanceof TransportError && error.status === 409
                ? "rejected"
                : failureKind(error),
          },
        })
      }
    },
    [load]
  )

  const requestContractAI = React.useCallback(
    async (operation: "draft" | "challenge") => {
      dispatch({ type: "SET_CONTRACT_AI", payload: { phase: "submitting" } })
      try {
        const value = validateContractAIResult(
          await fetchJson("/api/contract-ai", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              kind: "contract_ai_input",
              operation,
              request_id: crypto.randomUUID(),
              schema_version: 1,
            }),
          })
        )
        dispatch({
          type: "SET_CONTRACT_AI",
          payload: { phase: "ready", value },
        })
      } catch (error) {
        dispatch({
          type: "SET_CONTRACT_AI",
          payload: {
            phase:
              error instanceof TransportError && error.status === 503
                ? "error"
                : failureKind(error),
          },
        })
      }
    },
    []
  )

  const controlTransport = React.useCallback(
    async (requestId: string, operation: TransportControlOperation) => {
      if (state.transportControl.phase === "submitting") return
      dispatch({
        type: "SET_TRANSPORT_CONTROL",
        payload: { phase: "submitting", operation, requestId },
      })
      try {
        const result = validateTransportControlResult(
          await fetchJson("/api/execution-control", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              kind: "transport_control_input",
              operation,
              request_id: requestId,
              schema_version: 1,
            }),
          })
        )
        if (
          result.operation !== operation ||
          result.record.request_id !== requestId
        ) {
          throw new Error("malformed:transport_control.binding")
        }
        dispatch({
          type: "SET_TRANSPORT_CONTROL",
          payload: {
            phase: "succeeded",
            operation,
            requestId,
          },
        })
        await refreshExecution(true)
      } catch (error) {
        dispatch({
          type: "SET_TRANSPORT_CONTROL",
          payload: {
            phase:
              error instanceof TransportError && error.status === 409
                ? "rejected"
                : failureKind(error),
            operation,
            requestId,
          },
        })
      }
    },
    [refreshExecution, state.transportControl.phase]
  )

  return {
    state,
    load,
    requestAction,
    submitHitl,
    requestContractAI,
    controlTransport,
  }
}
