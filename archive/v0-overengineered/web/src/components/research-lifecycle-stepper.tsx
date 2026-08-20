import * as React from "react"
import {
  IconCheck,
  IconCpu,
  IconGavel,
  IconPencil,
  IconServer,
  IconSparkles,
} from "@tabler/icons-react"

export type LifecycleStage = "setup" | "draft" | "signoff" | "monitor" | "decision"

export interface StepItem {
  id: LifecycleStage
  label: string
  sublabel: string
  icon: React.ComponentType<{ className?: string }>
}

const STEPS: StepItem[] = [
  {
    id: "setup",
    label: "1. 环境预检",
    sublabel: "Git & 319 集群",
    icon: IconServer,
  },
  {
    id: "draft",
    label: "2. 契约拟定",
    sublabel: "AI 团队审阅",
    icon: IconSparkles,
  },
  {
    id: "signoff",
    label: "3. 签核冻结",
    sublabel: "H1 权限确认",
    icon: IconPencil,
  },
  {
    id: "monitor",
    label: "4. 319 算力监控",
    sublabel: "GPU 训练进度",
    icon: IconCpu,
  },
  {
    id: "decision",
    label: "5. 结论决策",
    sublabel: "H2 证据包判定",
    icon: IconGavel,
  },
]

const STAGE_ORDER: Record<LifecycleStage, number> = {
  setup: 1,
  draft: 2,
  signoff: 3,
  monitor: 4,
  decision: 5,
}

export function ResearchLifecycleStepper({
  activeStage,
  currentStage,
  onSelectStage,
}: {
  activeStage: LifecycleStage
  currentStage: LifecycleStage
  onSelectStage: (stage: LifecycleStage) => void
}) {
  const currentOrder = STAGE_ORDER[currentStage]

  return (
    <nav aria-label="科研任务生命周期" className="w-full">
      <ol className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
        {STEPS.map((step) => {
          const stepOrder = STAGE_ORDER[step.id]
          const isCompleted = stepOrder < currentOrder
          const isCurrent = step.id === currentStage
          const isSelected = step.id === activeStage
          const Icon = step.icon

          return (
            <li key={step.id}>
              <button
                type="button"
                onClick={() => onSelectStage(step.id)}
                className={`group relative flex w-full flex-col justify-between rounded-xl border p-3 text-left transition-colors ${
                  isSelected
                    ? "border-primary bg-primary/10 shadow-sm ring-1 ring-primary/40"
                    : isCurrent
                      ? "border-primary/50 bg-card hover:border-primary/80"
                      : isCompleted
                        ? "border-emerald-500/30 bg-card/60 hover:bg-muted/40"
                        : "border-border/60 bg-muted/20 text-muted-foreground hover:bg-muted/40"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div
                    className={`flex size-7 items-center justify-center rounded-lg ${
                      isCompleted
                        ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
                        : isCurrent
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {isCompleted ? (
                      <IconCheck className="size-4 stroke-[2.5]" />
                    ) : (
                      <Icon className="size-4" />
                    )}
                  </div>
                  {isCurrent && (
                    <span className="flex size-2 rounded-full bg-primary animate-pulse" />
                  )}
                </div>

                <div className="mt-2.5 min-w-0">
                  <div className="flex items-center gap-1">
                    <p
                      className={`truncate text-xs font-semibold ${
                        isSelected
                          ? "text-primary"
                          : isCurrent
                            ? "text-foreground"
                            : "text-foreground/80"
                      }`}
                    >
                      {step.label}
                    </p>
                  </div>
                  <p className="truncate text-[0.7rem] text-muted-foreground">
                    {step.sublabel}
                  </p>
                </div>
              </button>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
