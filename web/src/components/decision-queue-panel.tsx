import {
  IconChecklist,
  IconCircleCheck,
  IconRefresh,
} from "@tabler/icons-react"

import type { ExecutionControlState } from "@/App"
import { StateBadge } from "@/components/state-badge"
import { Button } from "@/components/ui/button"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import type { ExecutionRecord, ResearchLane, RowState } from "@/lib/domain"

export type PendingKind = "authority" | "h1" | "execution" | "packet"

export type PendingItem = {
  id: string
  kind: PendingKind
  title: string
  summary: string
  state: RowState
  lane?: ResearchLane
  record?: ExecutionRecord
}

function QueueState({
  execution,
  onRetry,
}: {
  execution: ExecutionControlState
  onRetry: () => void
}) {
  if (execution.phase === "ready") return null
  if (execution.phase === "loading") {
    return (
      <div
        className="border-b px-3 py-3 text-xs text-muted-foreground"
        role="status"
      >
        正在读取 durable queue
      </div>
    )
  }
  const label = {
    unavailable: "execution control unavailable",
    malformed: "execution response malformed",
    transport: "execution transport failure",
  }[execution.phase]
  return (
    <div
      className="flex items-center justify-between gap-2 border-b px-3 py-3 text-xs text-destructive"
      role="alert"
    >
      <span>{label}</span>
      <Button type="button" size="sm" variant="outline" onClick={onRetry}>
        <IconRefresh data-icon="inline-start" />
        重试
      </Button>
    </div>
  )
}

export function DecisionQueuePanel({
  execution,
  items,
  onRetry,
  onSelect,
  selected,
}: {
  execution: ExecutionControlState
  items: PendingItem[]
  onRetry: () => void
  onSelect: (selected: string) => void
  selected: string
}) {
  return (
    <section
      className="min-w-0 overflow-hidden rounded-xl border border-border bg-card shadow-xs"
      aria-label="待决队列"
    >
      <header className="flex min-h-12 items-center justify-between border-b px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold">待决队列</h2>
          <p className="text-xs text-muted-foreground">{items.length} 项</p>
        </div>
        <IconChecklist aria-hidden="true" className="text-muted-foreground" />
      </header>
      <QueueState execution={execution} onRetry={onRetry} />
      {items.length ? (
        <ul className="divide-y" aria-label="待决研究事项">
          {items.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className="flex min-h-16 w-full items-start gap-2 px-3 py-3 text-left hover:bg-muted/60 data-active:bg-accent data-active:text-accent-foreground"
                data-active={selected === item.id || undefined}
                aria-current={selected === item.id ? "true" : undefined}
                aria-controls="pending-detail"
                onClick={() => onSelect(item.id)}
              >
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium">
                    {item.title}
                  </span>
                  <span className="mt-1 block text-xs break-words text-muted-foreground">
                    {item.summary}
                  </span>
                </span>
                <StateBadge
                  state={item.state}
                  className={
                    selected === item.id
                      ? item.state === "blocked"
                        ? "border-destructive bg-destructive text-background"
                        : "border-accent-foreground/30 bg-accent-foreground text-accent"
                      : undefined
                  }
                />
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <Empty className="min-h-52 rounded-none border-0">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <IconCircleCheck aria-hidden="true" />
            </EmptyMedia>
            <EmptyTitle>没有待决事项</EmptyTitle>
            <EmptyDescription>当前公开投影中没有未处置记录。</EmptyDescription>
          </EmptyHeader>
        </Empty>
      )}
    </section>
  )
}
