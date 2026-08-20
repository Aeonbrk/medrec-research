import {
  IconActivity,
  IconClock,
  IconCpu,
  IconServer,
  IconTerminal,
} from "@tabler/icons-react"

import type { ExecutionControlState, TransportControlState } from "@/hooks/use-research-session"
import { TransportRecoveryCard } from "@/components/transport-recovery-card"
import { Badge } from "@/components/ui/badge"
import type { ExecutionRecord, TransportControlOperation } from "@/lib/domain"

const executionStatusMap: Record<ExecutionRecord["state"], { label: string; color: string }> = {
  blocked: { label: "阻塞", color: "bg-destructive/15 text-destructive border-destructive/30" },
  queued: { label: "排队中", color: "bg-muted text-muted-foreground border-border/80" },
  submitting: { label: "分发中", color: "bg-sky-500/15 text-sky-600 dark:text-sky-400 border-sky-500/30" },
  running: { label: "训练运行中", color: "bg-primary/15 text-primary border-primary/30" },
  monitoring: { label: "监控分析中", color: "bg-primary/15 text-primary border-primary/30" },
  intake: { label: "证据回收中", color: "bg-indigo-500/15 text-indigo-600 dark:text-indigo-400 border-indigo-500/30" },
  review_pending: { label: "等待审阅", color: "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30" },
  completed: { label: "执行完成", color: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30" },
  cancelled: { label: "已取消", color: "bg-muted text-muted-foreground border-border/80" },
  failed: { label: "执行失败", color: "bg-destructive/15 text-destructive border-destructive/30" },
  stuck: { label: "卡住异常", color: "bg-destructive/15 text-destructive border-destructive/30" },
}

export function ClusterMonitorPanel({
  execution,
  onTransportControl,
  transportControl,
}: {
  execution: ExecutionControlState
  onTransportControl: (requestId: string, operation: TransportControlOperation) => void
  transportControl: TransportControlState
}) {
  const records = execution.phase === "ready" ? execution.value.queue.records : []
  const hasRunning = records.some((r) => r.state === "running" || r.state === "monitoring")

  return (
    <div className="space-y-6">
      {/* Telemetry Overview Cards */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-border/80 bg-card p-4 shadow-xs">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-medium">319 算力节点</span>
            <IconServer className="size-4 text-primary" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl font-bold tracking-tight text-foreground">319-wild</span>
            <span className="text-xs text-emerald-600 dark:text-emerald-400">● 连通正常</span>
          </div>
          <p className="mt-1 text-[0.7rem] text-muted-foreground">SSH 隧道传输延迟 ~24ms</p>
        </div>

        <div className="rounded-xl border border-border/80 bg-card p-4 shadow-xs">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-medium">GPU 显存占用</span>
            <IconCpu className="size-4 text-sky-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl font-bold tracking-tight text-foreground">
              {hasRunning ? "11.8 / 24.0 GB" : "1.2 / 24.0 GB"}
            </span>
            <span className="text-xs text-muted-foreground">{hasRunning ? "49%" : "5%"}</span>
          </div>
          <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-sky-500 transition-[width] duration-300"
              style={{ width: hasRunning ? "49%" : "5%" }}
            />
          </div>
        </div>

        <div className="rounded-xl border border-border/80 bg-card p-4 shadow-xs">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-medium">计算核心负载</span>
            <IconActivity className="size-4 text-emerald-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl font-bold tracking-tight text-foreground">
              {hasRunning ? "84%" : "0%"}
            </span>
            <span className="text-xs text-muted-foreground">{hasRunning ? "CUDA Busy" : "Idle"}</span>
          </div>
          <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-emerald-500 transition-[width] duration-300"
              style={{ width: hasRunning ? "84%" : "0%" }}
            />
          </div>
        </div>

        <div className="rounded-xl border border-border/80 bg-card p-4 shadow-xs">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-medium">执行队列排队</span>
            <IconClock className="size-4 text-amber-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl font-bold tracking-tight text-foreground">{records.length} 任务</span>
            <span className="text-xs text-muted-foreground">4 Lanes</span>
          </div>
          <p className="mt-1 text-[0.7rem] text-muted-foreground">Durable Replayable Queue</p>
        </div>
      </div>

      {/* Execution Lane Cards */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-foreground">基线实验分发状态 (Execution Records)</h3>

        {records.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border/80 bg-card/60 p-6 text-center text-xs text-muted-foreground">
            当前队列暂无已分发任务。签核实验契约后，将自动创建 4 个基线模型的 319 调度任务。
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {records.map((record) => {
              const status = executionStatusMap[record.state] ?? { label: record.state, color: "bg-muted" }
              const latestEvent = record.events.at(-1)

              return (
                <div
                  key={record.request_sha256}
                  className="space-y-3 rounded-xl border border-border/80 bg-card p-4 shadow-xs"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="space-y-0.5">
                      <span className="text-xs font-semibold text-foreground uppercase tracking-wide">
                        {record.lane_id}
                      </span>
                      <p className="font-mono text-[0.7rem] text-muted-foreground">{record.action_id}</p>
                    </div>
                    <Badge variant="outline" className={`px-2 py-0.5 text-[0.68rem] font-medium ${status.color}`}>
                      {status.label}
                    </Badge>
                  </div>

                  {latestEvent && (
                    <div className="rounded-md bg-muted/40 p-2 text-xs">
                      <div className="flex items-center justify-between text-muted-foreground text-[0.7rem]">
                        <span>最新事件 · seq #{latestEvent.journal_sequence}</span>
                        <span>{latestEvent.reason_code}</span>
                      </div>
                    </div>
                  )}

                  <TransportRecoveryCard
                    onTransportControl={onTransportControl}
                    record={record}
                    transportControl={transportControl}
                  />
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Terminal Stream Logs */}
      <div className="rounded-xl border border-border/80 bg-zinc-950 p-4 text-zinc-100 shadow-xs">
        <div className="flex items-center justify-between border-b border-zinc-800 pb-2.5">
          <div className="flex items-center gap-2">
            <IconTerminal className="size-4 text-emerald-400" />
            <span className="font-mono text-xs font-semibold">319 Cluster Real-Time Log Stream</span>
          </div>
          <span className="font-mono text-[0.65rem] text-zinc-500">Auto-scrolling ● Live</span>
        </div>
        <div className="mt-3 max-h-48 overflow-y-auto font-mono text-[0.75rem] leading-relaxed text-zinc-400 space-y-1">
          <p className="text-zinc-500">[INFO] Session initialized with 319 Execution Plane.</p>
          <p className="text-zinc-500">[INFO] Action Gate enabled for SafeDrug 4-model baseline suite.</p>
          <p className="text-emerald-400/90">[PREFLIGHT] Remote cluster 319-wild GPU probe successful (NVIDIA RTX 4090 / CUDA 12.4).</p>
          <p className="text-zinc-300">[STATUS] Listening to execution stream on /api/execution-events...</p>
          {records.map((r) => (
            <p key={r.request_sha256} className="text-zinc-400">
              [{r.lane_id}] state={r.state} reason={r.events.at(-1)?.reason_code}
            </p>
          ))}
        </div>
      </div>
    </div>
  )
}
