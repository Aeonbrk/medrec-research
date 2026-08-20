import * as React from "react"
import {
  IconCheck,
  IconCpu,
  IconDatabase,
  IconFileCertificate,
  IconPencil,
  IconSparkles,
  IconUsers,
} from "@tabler/icons-react"

import type { ContractAIState, ContractState, HitlControlState } from "@/hooks/use-research-session"
import { TeamCompositionConsole } from "@/components/team-composition-console"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

const PRESET_MODELS = [
  { id: "safedrug", name: "SafeDrug (Main)", desc: "双分子图与 DDI 损失惩罚基线" },
  { id: "gamenet", name: "GAMENet", desc: "图增强双向 RNN 记忆推荐网络" },
  { id: "retain", name: "RETAIN", desc: "两级注意力机制可解释就诊推荐" },
  { id: "leap", name: "LEAP", desc: "序列到序列多标签处方生成" },
  { id: "molerec", name: "MoleRec", desc: "分子子图感知自适应推荐" },
]

export function ContractCockpitCard({
  contract,
  contractAI,
  hitl,
  onContractAI,
  onSignoff,
}: {
  contract: ContractState
  contractAI: ContractAIState
  hitl: HitlControlState
  onContractAI: (operation: "draft" | "challenge") => void
  onSignoff: (researcherId: string, reason: string) => void
}) {
  const [selectedModel, setSelectedModel] = React.useState("safedrug")
  const [researcherId, setResearcherId] = React.useState("researcher-lead")
  const [reason, setReason] = React.useState("确认基线复现契约规范 / MIMIC-III patient-disjoint")

  const hitlControl = hitl.phase === "ready" ? hitl.value : null
  const isH1Current = hitlControl?.h1.current === true
  const isH1Enabled = hitlControl?.h1.enabled === true
  const isSubmitting = hitl.phase === "submitting" || contractAI.phase === "submitting"

  const hasContract = contract.phase === "ready"

  return (
    <div className="space-y-6">
      {/* Header & Status Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-border/80 bg-card p-5 shadow-xs">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="flex size-6 items-center justify-center rounded-md bg-primary/10 text-primary">
              <IconFileCertificate className="size-4" />
            </span>
            <h2 className="text-base font-semibold tracking-tight sm:text-lg">
              科研复现契约规范 (Research Contract)
            </h2>
            <Badge
              variant={isH1Current ? "outline" : "secondary"}
              className={
                isH1Current
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                  : "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400"
              }
            >
              {isH1Current
                ? `已签核冻结 (${hitlControl?.h1.owner ?? "H"})`
                : isH1Enabled
                  ? "待人工签核 (H1 Ready)"
                  : "草案拟定中"}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground sm:text-sm">
            锁定实验假设、评估协议、MIMIC-III 数据划分与 319 算力预算，确保科研不可篡改与绝对可复现。
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onContractAI("draft")}
            disabled={isSubmitting}
            className="gap-1.5 text-xs shadow-2xs"
          >
            <IconSparkles className="size-3.5 text-primary" />
            <span>AI 起草/更新契约</span>
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onContractAI("challenge")}
            disabled={isSubmitting || !hasContract}
            className="gap-1.5 text-xs shadow-2xs"
          >
            <IconUsers className="size-3.5 text-sky-500" />
            <span>AI 团队质询评审</span>
          </Button>
        </div>
      </div>

      {/* Model Selection Pills */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
        {PRESET_MODELS.map((model) => {
          const isSelected = selectedModel === model.id
          return (
            <button
              key={model.id}
              type="button"
              onClick={() => setSelectedModel(model.id)}
              className={`flex flex-col justify-between rounded-xl border p-3 text-left transition-all ${
                isSelected
                  ? "border-primary bg-primary/5 shadow-2xs ring-1 ring-primary/40"
                  : "border-border/60 bg-card/60 hover:bg-muted/30"
              }`}
            >
              <div className="flex items-center justify-between gap-1">
                <span className="font-semibold text-xs text-foreground">{model.name}</span>
                {isSelected && <IconCheck className="size-3.5 text-primary" />}
              </div>
              <p className="mt-1.5 line-clamp-2 text-[0.7rem] text-muted-foreground">
                {model.desc}
              </p>
            </button>
          )
        })}
      </div>

      {/* Contract Detail & Visual Breakdown */}
      {hasContract ? (
        <div className="grid gap-5 lg:grid-cols-12">
          {/* Main Contract Specs (7 cols) */}
          <div className="space-y-4 rounded-xl border border-border/80 bg-card p-5 shadow-xs lg:col-span-7">
            <h3 className="text-sm font-semibold text-foreground">契约核心要素 (Protected Contract Digest)</h3>
            
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-border/60 bg-muted/20 p-3">
                <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                  <IconDatabase className="size-3.5" />
                  <span>数据集与划分</span>
                </div>
                <p className="mt-1 text-xs font-semibold text-foreground">MIMIC-III (patient-disjoint)</p>
                <p className="text-[0.7rem] text-muted-foreground">患者级隔离划分，防跨访视信息泄漏</p>
              </div>

              <div className="rounded-lg border border-border/60 bg-muted/20 p-3">
                <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                  <IconCpu className="size-3.5" />
                  <span>算力与停止预算</span>
                </div>
                <p className="mt-1 text-xs font-semibold text-foreground">1x GPU · 8h Max · 2 Retries</p>
                <p className="text-[0.7rem] text-muted-foreground">超出自动熔断，防无效耗费算力</p>
              </div>
            </div>

            <div className="space-y-2 pt-1">
              <p className="text-xs font-medium text-muted-foreground">契约问卷字段</p>
              <div className="divide-y divide-border/60 rounded-lg border border-border/60 bg-muted/10 text-xs">
                {contract.value.questionnaire.map((field) => (
                  <div key={field.id} className="flex flex-col gap-1 p-2.5 sm:flex-row sm:items-baseline sm:justify-between">
                    <span className="font-medium text-muted-foreground sm:w-1/3">{field.label}</span>
                    <span className="font-mono text-foreground sm:w-2/3 break-all">{field.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* AI Review Team / Teammates Console (5 cols) */}
          <div className="space-y-4 rounded-xl border border-border/80 bg-card p-5 shadow-xs lg:col-span-5">
            <h3 className="text-sm font-semibold text-foreground">多智能体审查意见 (Agent Swarm Review)</h3>
            <TeamCompositionConsole
              output={contractAI.phase === "ready" ? contractAI.value.output : null}
              reasonCode={contract.value.ai.reason_code}
              status={contract.value.ai.status}
              config={
                contractAI.phase === "ready" && contractAI.value.team_config
                  ? contractAI.value.team_config
                  : undefined
              }
            />
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-border/80 bg-card/60 p-8 text-center">
          <div className="mx-auto flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <IconSparkles className="size-6" />
          </div>
          <h3 className="mt-3 text-base font-semibold">尚未载入已登记契约</h3>
          <p className="mx-auto mt-1 max-w-md text-xs text-muted-foreground sm:text-sm">
            点击下方按钮，由 AI 专家团队自动基于 SafeDrug 4-Model 基线协议生成严谨的复现契约。
          </p>
          <Button
            type="button"
            onClick={() => onContractAI("draft")}
            disabled={isSubmitting}
            className="mt-4 gap-2 shadow-sm"
          >
            <IconSparkles className="size-4" />
            <span>✨ 一键生成复现契约 (SafeDrug 4-Model)</span>
          </Button>
        </div>
      )}

      {/* Human Sign-off Box (H1 Gate) */}
      <div className="rounded-xl border border-primary/30 bg-gradient-to-br from-card to-primary/5 p-5 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-3">
          <div className="flex items-center gap-2">
            <span className="flex size-6 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <IconPencil className="size-3.5" />
            </span>
            <h3 className="text-sm font-semibold text-foreground">
              人工签核与执行冻结 (Human H1 Sign-off)
            </h3>
          </div>
          <span className="text-[0.7rem] text-muted-foreground">
            {isH1Current ? "契约已生效，具备 319 下发权限" : "签署后即锁定科学环境，自动调度 319"}
          </span>
        </div>

        {isH1Current ? (
          <div className="mt-4 flex items-center gap-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3.5 text-xs text-emerald-700 dark:text-emerald-300">
            <IconCheck className="size-5 shrink-0 stroke-[2.5]" />
            <div className="space-y-0.5">
              <p className="font-semibold">实验契约已由 {hitlControl?.h1.owner ?? "负责人"} 签核生效</p>
              <p className="text-muted-foreground dark:text-emerald-400/80">
                科学假设与环境约束已锁定，当前处于执行与证据生成阶段。如需变更假设，请创建新的研究轮次。
              </p>
            </div>
          </div>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault()
              onSignoff(researcherId, reason)
            }}
            className="mt-4 space-y-4"
          >
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <label htmlFor="researcher-id" className="text-xs font-medium text-muted-foreground">
                  研究负责人 ID (Signer ID)
                </label>
                <Input
                  id="researcher-id"
                  value={researcherId}
                  onChange={(e) => setResearcherId(e.target.value)}
                  placeholder="例如 researcher-lead"
                  className="h-9 text-xs"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="signoff-reason" className="text-xs font-medium text-muted-foreground">
                  签核理由 (Decision Rationale)
                </label>
                <Input
                  id="signoff-reason"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="签核理由说明"
                  className="h-9 text-xs"
                  required
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-1">
              <Button
                type="submit"
                disabled={isSubmitting || !isH1Enabled}
                className="gap-2 px-5 text-xs font-semibold shadow-sm"
              >
                <IconCheck className="size-4" />
                <span>✍️ 审核通过并签核冻结 (Freeze & Dispatch)</span>
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
