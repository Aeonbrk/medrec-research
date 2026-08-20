import * as React from "react"
import {
  IconChecklist,
  IconLayersLinked,
  IconServer,
  IconSparkles,
  IconUsers,
} from "@tabler/icons-react"

import type {
  ContractAIState,
  ContractState,
  ExecutionControlState,
  ExecutionStreamState,
  HitlControlState,
  LoopState,
  PacketState,
  TransportControlState,
} from "@/hooks/use-research-session"
import { BaselineMatrixTable } from "@/components/baseline-matrix-table"
import { ClusterMonitorPanel } from "@/components/cluster-monitor-panel"
import { ContractCockpitCard } from "@/components/contract-cockpit-card"
import { DecisionPacketCockpit } from "@/components/decision-packet-cockpit"
import { DecisionQueuePanel, type PendingItem } from "@/components/decision-queue-panel"
import { EnvironmentHealthBar } from "@/components/environment-health-bar"
import {
  ResearchLifecycleStepper,
  type LifecycleStage,
} from "@/components/research-lifecycle-stepper"
import { TeamCompositionConsole } from "@/components/team-composition-console"
import { Button } from "@/components/ui/button"
import type {
  ExecutionRecord,
  HarnessState,
  RowState,
  TransportControlOperation,
} from "@/lib/domain"

function executionState(record: ExecutionRecord): RowState {
  if (["blocked", "cancelled", "failed", "stuck"].includes(record.state)) {
    return "blocked"
  }
  if (record.state === "completed" && record.outcome === "succeeded") {
    return "pass"
  }
  return "attention"
}

function computePendingItems({
  execution,
  harness,
  hitl,
  loop,
}: {
  execution: ExecutionControlState
  harness: HarnessState
  hitl: HitlControlState
  loop: LoopState
}): PendingItem[] {
  const items: PendingItem[] = []
  if (harness.status.condition !== "current" || harness.status.blockers.length) {
    items.push({
      id: "authority",
      kind: "authority",
      title: "环境与权威预检",
      summary: harness.status.primary_blocker?.reason_code ?? harness.status.condition,
      state: "attention",
    })
  }
  if (hitl.phase !== "ready" || !hitl.value.h1.current) {
    items.push({
      id: "h1",
      kind: "h1",
      title: "实验复现契约",
      summary: hitl.phase === "ready" && hitl.value.h1.enabled ? "待研究员签核" : "契约草案拟定中",
      state: hitl.phase === "ready" && hitl.value.h1.enabled ? "attention" : "blocked",
    })
  }
  if (execution.phase === "ready") {
    const records = execution.value.queue.records.toSorted(
      (left, right) =>
        right.events.at(-1)!.journal_sequence - left.events.at(-1)!.journal_sequence
    )
    for (const record of records) {
      items.push({
        id: `execution:${record.request_sha256}`,
        kind: "execution",
        title: `${record.lane_id} 调度`,
        summary: `${record.state} · ${record.events.at(-1)!.reason_code}`,
        state: executionState(record),
        record,
      })
    }
  }
  if (loop.phase === "ready") {
    for (const lane of loop.value.lanes) {
      if (lane.h2_action !== null && lane.blockers.length === 0) continue
      items.push({
        id: `packet:${lane.lane_id}`,
        kind: "packet",
        title: `${lane.model_id} 证据决策`,
        summary: lane.packet_complete ? "等待 H2 决策" : (lane.blockers[0] ?? "证据包生成中"),
        state: lane.current && lane.packet_complete && lane.blockers.length === 0 ? "attention" : "blocked",
        lane,
      })
    }
  }
  return items
}

export function PendingWorkbench({
  actionPanel,
  contract,
  contractAI,
  execution,
  executionStream,
  harness,
  hitl,
  loop,
  onContractAI,
  onHitlDecision,
  onRetry,
  onSelect,
  onTransportControl,
  packets,
  selected,
  transportControl,
}: {
  actionPanel?: React.ReactNode
  contract: ContractState
  contractAI?: ContractAIState
  decisionPanel?: React.ReactNode
  execution: ExecutionControlState
  executionStream: ExecutionStreamState
  harness: HarnessState
  hitl: HitlControlState
  loop: LoopState
  onContractAI?: (operation: "draft" | "challenge") => void
  onHitlDecision?: (path: "/api/h1" | "/api/h2", payload: Record<string, unknown>) => void
  onRetry: () => void
  onSelect: (selected: string) => void
  onTransportControl: (requestId: string, operation: TransportControlOperation) => void
  packets: PacketState
  selected: string
  transportControl: TransportControlState
}) {
  // Infer current lifecycle stage from active system state
  const isH1Current = hitl.phase === "ready" && hitl.value.h1.current
  const hasRunningExecutions =
    execution.phase === "ready" &&
    execution.value.queue.records.some((r) => ["running", "monitoring", "queued"].includes(r.state))
  const hasDecisionPending =
    loop.phase === "ready" &&
    loop.value.lanes.some((l) => l.packet_complete && l.h2_action === null)

  const currentStage: LifecycleStage = React.useMemo(() => {
    if (hasDecisionPending) return "decision"
    if (hasRunningExecutions) return "monitor"
    if (isH1Current) return "monitor"
    if (contract.phase === "ready") return "signoff"
    return "draft"
  }, [hasDecisionPending, hasRunningExecutions, isH1Current, contract.phase])

  const [activeStage, setActiveStage] = React.useState<LifecycleStage>(currentStage)
  const [secondaryTab, setSecondaryTab] = React.useState<"matrix" | "queue" | "swarm">("matrix")

  // Sync active stage when current stage advances automatically
  React.useEffect(() => {
    setActiveStage(currentStage)
  }, [currentStage])

  const items = React.useMemo(
    () => computePendingItems({ execution, harness, hitl, loop }),
    [execution, harness, hitl, loop]
  )

  const handleSignoff = (researcherId: string, reason: string) => {
    if (!onHitlDecision) return
    onHitlDecision("/api/h1", {
      decision: "accept",
      kind: "h1_decision_input",
      rationale: reason,
      researcher_id: researcherId,
      schema_version: 1,
    })
  }

  const handleH2Decision = (path: "/api/h2", payload: Record<string, unknown>) => {
    if (!onHitlDecision) return
    onHitlDecision(path, payload)
  }

  return (
    <div className="space-y-6">
      {/* 1. Top Environment & Preflight Health Bar */}
      <EnvironmentHealthBar
        executionStream={executionStream}
        harness={harness}
        onRefresh={onRetry}
      />

      {/* 2. Research Lifecycle Progress Stepper */}
      <ResearchLifecycleStepper
        activeStage={activeStage}
        currentStage={currentStage}
        onSelectStage={setActiveStage}
      />

      {/* 3. Central Stage Cockpit View */}
      <section aria-label="核心任务工作台">
        {activeStage === "setup" && (
          <div className="space-y-4 rounded-xl border border-border/80 bg-card p-6 shadow-xs">
            <div className="flex items-center gap-2 border-b border-border/60 pb-3">
              <IconServer className="size-5 text-primary" />
              <div>
                <h3 className="text-sm font-semibold">科研环境与算力预检 (Preflight & Environment)</h3>
                <p className="text-xs text-muted-foreground">
                  Mac 为控制与编排终端，319 为独立 GPU 执行平面，严格保障零数据泄漏。
                </p>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-border/60 bg-muted/20 p-4">
                <span className="text-xs font-semibold text-foreground">本地 Harness 控制台</span>
                <p className="mt-1 text-xs text-muted-foreground">
                  Python 3.11 核心依赖与公开安全元数据投影已就绪，状态同步正常。
                </p>
              </div>
              <div className="rounded-lg border border-border/60 bg-muted/20 p-4">
                <span className="text-xs font-semibold text-foreground">远程 319 集群状态</span>
                <p className="mt-1 text-xs text-muted-foreground">
                  GPU 驱动与 MIMIC-III patient-disjoint 数据环境已就绪，通过隔离 Conda 环境运行基线。
                </p>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button
                type="button"
                onClick={() => setActiveStage("draft")}
                className="gap-1.5 text-xs shadow-xs"
              >
                <span>下一步：拟定复现契约</span>
                <IconSparkles className="size-3.5" />
              </Button>
            </div>
          </div>
        )}

        {(activeStage === "draft" || activeStage === "signoff") && (
          <ContractCockpitCard
            contract={contract}
            contractAI={contractAI ?? { phase: "idle" }}
            hitl={hitl}
            onContractAI={onContractAI ?? (() => {})}
            onSignoff={handleSignoff}
          />
        )}

        {activeStage === "monitor" && (
          <ClusterMonitorPanel
            execution={execution}
            onTransportControl={onTransportControl}
            transportControl={transportControl}
          />
        )}

        {activeStage === "decision" && (
          <DecisionPacketCockpit
            hitl={hitl}
            loop={loop}
            onDecision={handleH2Decision}
            packets={packets}
          />
        )}
      </section>

      {/* 4. Secondary Navigation & Exploration Tabs */}
      <section className="space-y-4 pt-2" aria-label="综合科研视图">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-2">
          <div className="flex items-center gap-1.5">
            <Button
              type="button"
              variant={secondaryTab === "matrix" ? "default" : "ghost"}
              size="sm"
              onClick={() => setSecondaryTab("matrix")}
              className="h-8 gap-1.5 text-xs font-medium"
            >
              <IconLayersLinked className="size-3.5" />
              <span>基线对比看板</span>
            </Button>

            <Button
              type="button"
              variant={secondaryTab === "queue" ? "default" : "ghost"}
              size="sm"
              onClick={() => setSecondaryTab("queue")}
              className="h-8 gap-1.5 text-xs font-medium"
            >
              <IconChecklist className="size-3.5" />
              <span>待决与审计队列 ({items.length})</span>
            </Button>

            <Button
              type="button"
              variant={secondaryTab === "swarm" ? "default" : "ghost"}
              size="sm"
              onClick={() => setSecondaryTab("swarm")}
              className="h-8 gap-1.5 text-xs font-medium"
            >
              <IconUsers className="size-3.5" />
              <span>多 Agent 团队</span>
            </Button>
          </div>
        </div>

        {secondaryTab === "matrix" && <BaselineMatrixTable />}

        {secondaryTab === "queue" && (
          <div className="grid gap-4 lg:grid-cols-12">
            <div className="lg:col-span-5">
              <DecisionQueuePanel
                execution={execution}
                items={items}
                onRetry={onRetry}
                onSelect={onSelect}
                selected={selected}
              />
            </div>
            <div className="lg:col-span-7">
              <div className="rounded-xl border border-border bg-card p-5 text-xs text-muted-foreground shadow-xs">
                <span className="font-semibold text-foreground">审计依据与动作上下文</span>
                <p className="mt-1">
                  该区域展示来自 Python Harness 的底层快照与 Action Gate 语义。在主驾驶舱中已自动编排所有前置操作。
                </p>
                {actionPanel && <div className="mt-3">{actionPanel}</div>}
              </div>
            </div>
          </div>
        )}

        {secondaryTab === "swarm" && (
          <div className="space-y-4">
            <TeamCompositionConsole
              config={
                contractAI?.phase === "ready" && contractAI.value.team_config
                  ? contractAI.value.team_config
                  : undefined
              }
              output={contractAI?.phase === "ready" ? contractAI.value.output : null}
            />
          </div>
        )}
      </section>
    </div>
  )
}
