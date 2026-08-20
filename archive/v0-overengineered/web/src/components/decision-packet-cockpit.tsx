import * as React from "react"
import {
  IconBan,
  IconCheck,
  IconGavel,
  IconPlayerPause,
  IconRefresh,
} from "@tabler/icons-react"

import type { HitlControlState, LoopState, PacketState } from "@/hooks/use-research-session"
import { EvidenceInspectorPanel } from "@/components/evidence-inspector-panel"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import type { Evidence } from "@/lib/domain"

export type H2DecisionAction = "go" | "revise" | "hold" | "kill"

const ACTION_DESCRIPTIONS: Record<
  H2DecisionAction,
  { label: string; desc: string; variant: "default" | "destructive" | "outline" | "secondary"; icon: React.ComponentType<{ className?: string }> }
> = {
  go: {
    label: "Go · 确认通过",
    desc: "指标与科学语义验证通过，允许推进至下一比较通道或新方法研究。",
    variant: "default",
    icon: IconCheck,
  },
  revise: {
    label: "Revise · 调整重试",
    desc: "在预设调优预算内调整参数或补充收敛轮次，重新生成证据包。",
    variant: "outline",
    icon: IconRefresh,
  },
  hold: {
    label: "Hold · 暂缓决策",
    desc: "证据尚存疑虑或需要等待外部基线完成，暂时保留待决状态。",
    variant: "secondary",
    icon: IconPlayerPause,
  },
  kill: {
    label: "Kill · 废弃终止",
    desc: "存在不可修复的理论缺陷或表现不达标，永久终止该实验分支。",
    variant: "destructive",
    icon: IconBan,
  },
}

export function DecisionPacketCockpit({
  hitl,
  loop,
  onDecision,
  packets,
}: {
  hitl: HitlControlState
  loop: LoopState
  onDecision: (path: "/api/h2", payload: Record<string, unknown>) => void
  packets?: PacketState
}) {
  const lanes = loop.phase === "ready" ? loop.value.lanes : []
  const [selectedLaneId, setSelectedLaneId] = React.useState<string>(lanes[0]?.lane_id ?? "gamenet")
  const [selectedAction, setSelectedAction] = React.useState<H2DecisionAction>("go")
  const [researcherId, setResearcherId] = React.useState("researcher-lead")
  const [rationale, setRationale] = React.useState("复现结果符合指标区间，同意生成比较证据")

  const selectedLane = lanes.find((l) => l.lane_id === selectedLaneId) ?? lanes[0]
  const isSubmitting = hitl.phase === "submitting"

  const matchingPacket =
    packets?.phase === "ready"
      ? packets.value.packets.find((p) => p.lane_id === selectedLane?.lane_id)
      : undefined

  const evidenceList: Evidence[] = matchingPacket
    ? matchingPacket.attempts.flatMap((a) =>
        Object.entries(a.artifact_digests).map(([label, hash]) => ({
          kind: "safe_public" as const,
          label: `${a.attempt_id} · ${label}`,
          url: `#artifact-${hash.slice(0, 12)}`,
        }))
      )
    : []

  if (lanes.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border/80 bg-card/60 p-8 text-center text-xs text-muted-foreground">
        当前暂无可决策的证据包。请先完成实验契约签核与 319 算力执行。
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-border/80 bg-card p-5 shadow-xs">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="flex size-6 items-center justify-center rounded-md bg-primary/10 text-primary">
              <IconGavel className="size-4" />
            </span>
            <h2 className="text-base font-semibold tracking-tight sm:text-lg">
              研究结论决策与证据包判定 (Research Decision Gate)
            </h2>
          </div>
          <p className="text-xs text-muted-foreground sm:text-sm">
            审阅 319 生成的公开安全证据包（无患者隐私），人类研究员行使最高裁量权 (Go / Revise / Hold / Kill)。
          </p>
        </div>
      </div>

      {/* Lane Tabs */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {lanes.map((lane) => {
          const isSelected = selectedLane?.lane_id === lane.lane_id
          const isCompleted = lane.h2_action !== null

          return (
            <button
              key={lane.lane_id}
              type="button"
              onClick={() => setSelectedLaneId(lane.lane_id)}
              className={`flex flex-col justify-between rounded-xl border p-3 text-left transition-colors ${
                isSelected
                  ? "border-primary bg-primary/5 shadow-2xs ring-1 ring-primary/40"
                  : "border-border/60 bg-card/60 hover:bg-muted/30"
              }`}
            >
              <div className="flex items-center justify-between gap-1">
                <span className="font-semibold text-xs text-foreground uppercase tracking-wider">{lane.model_id}</span>
                {isCompleted ? (
                  <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[0.65rem]">
                    已决策 ({lane.h2_action})
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="text-[0.65rem]">
                    待决策
                  </Badge>
                )}
              </div>
              <p className="mt-1 text-[0.7rem] text-muted-foreground truncate">{lane.lane_id}</p>
            </button>
          )
        })}
      </div>

      {/* Selected Lane Evidence Overview */}
      {selectedLane && (
        <div className="grid gap-5 lg:grid-cols-12">
          {/* Evidence Details (6 cols) */}
          <div className="space-y-4 rounded-xl border border-border/80 bg-card p-5 shadow-xs lg:col-span-6">
            <h3 className="text-sm font-semibold text-foreground">
              {selectedLane.model_id} 证据包指标详情
            </h3>

            <div className="divide-y divide-border/60 rounded-lg border border-border/60 bg-muted/10 text-xs">
              <div className="flex items-center justify-between p-2.5">
                <span className="text-muted-foreground">所属阶段 (Stage)</span>
                <span className="font-mono font-medium">{selectedLane.stage}</span>
              </div>
              <div className="flex items-center justify-between p-2.5">
                <span className="text-muted-foreground">尝试状态 (Attempt)</span>
                <span className="font-mono font-medium">{selectedLane.attempt_status}</span>
              </div>
              <div className="flex items-center justify-between p-2.5">
                <span className="text-muted-foreground">证据包完整性</span>
                <Badge variant={selectedLane.packet_complete ? "outline" : "secondary"}>
                  {selectedLane.packet_complete ? "完整 (Complete)" : "生成中"}
                </Badge>
              </div>
              <div className="flex items-center justify-between p-2.5">
                <span className="text-muted-foreground">推进资格 (Go-Eligible)</span>
                <Badge variant={selectedLane.h2_go_eligible ? "outline" : "secondary"}>
                  {selectedLane.h2_go_eligible ? "符合推进标准" : "需人工审阅"}
                </Badge>
              </div>
            </div>

            {selectedLane.blockers.length > 0 && (
              <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
                {selectedLane.blockers.join(" · ")}
              </div>
            )}

            {matchingPacket && (
              <div className="pt-2">
                <EvidenceInspectorPanel
                  evidence={evidenceList}
                  packet={matchingPacket}
                  phase={packets?.phase ?? "ready"}
                />
              </div>
            )}
          </div>

          {/* Action Decision Form (6 cols) */}
          <div className="space-y-4 rounded-xl border border-border/80 bg-card p-5 shadow-xs lg:col-span-6">
            <h3 className="text-sm font-semibold text-foreground">
              裁决操作 (Choose Action)
            </h3>

            <div className="grid grid-cols-2 gap-2">
              {(["go", "revise", "hold", "kill"] as H2DecisionAction[]).map((actionKey) => {
                const conf = ACTION_DESCRIPTIONS[actionKey]
                const Icon = conf.icon
                const isSelected = selectedAction === actionKey

                return (
                  <button
                    key={actionKey}
                    type="button"
                    onClick={() => setSelectedAction(actionKey)}
                    className={`flex flex-col justify-between rounded-lg border p-2.5 text-left transition-colors ${
                      isSelected
                        ? "border-primary bg-primary/10 ring-1 ring-primary/40"
                        : "border-border/60 bg-muted/20 hover:bg-muted/40"
                    }`}
                  >
                    <div className="flex items-center gap-1.5 font-semibold text-xs">
                      <Icon className="size-3.5" />
                      <span>{conf.label}</span>
                    </div>
                    <p className="mt-1 line-clamp-2 text-[0.68rem] text-muted-foreground">
                      {conf.desc}
                    </p>
                  </button>
                )
              })}
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault()
                onDecision("/api/h2", {
                  action: selectedAction,
                  kind: "h2_decision_input",
                  lane_id: selectedLane.lane_id,
                  rationale,
                  researcher_id: researcherId,
                  schema_version: 1,
                })
              }}
              className="space-y-3 pt-2"
            >
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label htmlFor="h2-researcher-id" className="text-xs font-medium text-muted-foreground">
                    研究负责人 ID
                  </label>
                  <Input
                    id="h2-researcher-id"
                    value={researcherId}
                    onChange={(e) => setResearcherId(e.target.value)}
                    placeholder="researcher-lead"
                    className="h-9 text-xs"
                    required
                  />
                </div>
                <div className="space-y-1.5">
                  <label htmlFor="h2-rationale" className="text-xs font-medium text-muted-foreground">
                    决策理由说明
                  </label>
                  <Input
                    id="h2-rationale"
                    value={rationale}
                    onChange={(e) => setRationale(e.target.value)}
                    placeholder="说明决策科学依据"
                    className="h-9 text-xs"
                    required
                  />
                </div>
              </div>

              <Button
                type="submit"
                disabled={isSubmitting}
                className="w-full gap-2 text-xs font-semibold shadow-sm"
              >
                <IconCheck className="size-4" />
                <span>确认并提交 {selectedLane.model_id} 研究决策</span>
              </Button>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
