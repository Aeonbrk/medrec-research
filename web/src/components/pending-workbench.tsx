import {
  IconActivity,
  IconAlertTriangle,
  IconChecklist,
  IconCircleCheck,
  IconDatabase,
  IconFileAnalytics,
  IconLock,
  IconPlayerPlay,
  IconPlayerStop,
  IconRefresh,
} from "@tabler/icons-react"

import type {
  ContractState,
  ExecutionControlState,
  ExecutionStreamState,
  HitlControlState,
  LoopState,
  PacketState,
  TransportControlState,
} from "@/App"
import { EvidenceDisclosure } from "@/components/evidence-disclosure"
import { StateBadge } from "@/components/state-badge"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import type {
  ExecutionDeclaration,
  ExecutionRecord,
  HarnessState,
  PublicJson,
  ResearchLane,
  RowState,
  TransportControlOperation,
} from "@/lib/domain"

type PendingKind = "authority" | "h1" | "execution" | "packet"

type PendingItem = {
  id: string
  kind: PendingKind
  title: string
  summary: string
  state: RowState
  lane?: ResearchLane
  record?: ExecutionRecord
}

const executionLabels: Record<ExecutionRecord["state"], string> = {
  blocked: "阻塞",
  queued: "排队",
  submitting: "提交中",
  running: "运行中",
  monitoring: "监控中",
  intake: "证据回收",
  review_pending: "等待审阅",
  completed: "完成",
  cancelled: "已取消",
  failed: "失败",
  stuck: "卡住",
}

function shortSha(value: string) {
  return `${value.slice(0, 10)}...${value.slice(-6)}`
}

function dateTime(value: string) {
  const parsed = new Date(value)
  return Number.isNaN(parsed.valueOf())
    ? value
    : new Intl.DateTimeFormat("zh-CN", {
        dateStyle: "medium",
        timeStyle: "medium",
        hour12: false,
      }).format(parsed)
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

function displayPublicJson(value: PublicJson) {
  return typeof value === "string" ? value : JSON.stringify(value)
}

function executionState(record: ExecutionRecord): RowState {
  if (["blocked", "cancelled", "failed", "stuck"].includes(record.state)) {
    return "blocked"
  }
  if (record.state === "completed" && record.outcome === "succeeded") {
    return "pass"
  }
  return "attention"
}

export function permittedTransportOperations(
  record: ExecutionRecord
): TransportControlOperation[] {
  if (["submitting", "running", "monitoring"].includes(record.state)) {
    return ["cancel"]
  }
  const reason = record.events.at(-1)!.reason_code
  if (
    record.state === "review_pending" &&
    reason.startsWith("aris-transport-")
  ) {
    return ["resume", "cancel"]
  }
  return []
}

function pendingItems({
  execution,
  harness,
  hitl,
  loop,
}: {
  execution: ExecutionControlState
  harness: HarnessState
  hitl: HitlControlState
  loop: LoopState
}) {
  const items: PendingItem[] = []
  if (
    harness.status.condition !== "current" ||
    harness.status.blockers.length
  ) {
    items.push({
      id: "authority",
      kind: "authority",
      title: "项目权威与硬门",
      summary:
        harness.status.primary_blocker?.reason_code ?? harness.status.condition,
      state: "blocked",
    })
  }
  if (hitl.phase !== "ready" || !hitl.value.h1.current) {
    items.push({
      id: "h1",
      kind: "h1",
      title: "H1 研究契约",
      summary:
        hitl.phase === "ready" && hitl.value.h1.enabled
          ? "等待 H 签核"
          : "契约缺失或不可签核",
      state:
        hitl.phase === "ready" && hitl.value.h1.enabled
          ? "attention"
          : "blocked",
    })
  }
  if (execution.phase === "ready") {
    const records = [...execution.value.queue.records].sort(
      (left, right) =>
        right.events.at(-1)!.journal_sequence -
        left.events.at(-1)!.journal_sequence
    )
    for (const record of records) {
      items.push({
        id: `execution:${record.request_sha256}`,
        kind: "execution",
        title: `${record.lane_id} / ${record.action_id}`,
        summary: `${executionLabels[record.state]} · ${record.events.at(-1)!.reason_code}`,
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
        title: `${lane.model_id} Decision Packet`,
        summary: lane.packet_complete
          ? "等待 H2 决策"
          : (lane.blockers[0] ?? "证据包未完成"),
        state:
          lane.current && lane.packet_complete && lane.blockers.length === 0
            ? "attention"
            : "blocked",
        lane,
      })
    }
  }
  return items
}

function StreamBadge({ state }: { state: ExecutionStreamState }) {
  const label = {
    connecting: "SSE 连接中",
    live: "SSE live",
    reconnecting: "SSE 恢复中",
    malformed: "SSE 格式错误",
  }[state]
  return (
    <Badge
      variant={state === "live" ? "outline" : "secondary"}
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      {state === "live" ? (
        <IconActivity data-icon="inline-start" />
      ) : (
        <IconRefresh data-icon="inline-start" />
      )}
      {label}
    </Badge>
  )
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

function PendingQueue({
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
      className="min-w-0 border border-border bg-surface-raised"
      aria-label="待决队列"
    >
      <header className="flex min-h-12 items-center justify-between border-b px-3 py-2">
        <div>
          <h2 className="text-sm font-semibold">待决队列</h2>
          <p className="text-xs text-muted-foreground">{items.length} 项</p>
        </div>
        <IconChecklist aria-hidden="true" className="text-primary" />
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

function Definition({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 border-b py-2 last:border-b-0">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1 font-mono text-xs break-all">{value}</dd>
    </div>
  )
}

function ExecutionDetail({
  declaration,
  onTransportControl,
  record,
  transportControl,
}: {
  declaration?: ExecutionDeclaration
  onTransportControl: (
    requestId: string,
    operation: TransportControlOperation
  ) => void
  record: ExecutionRecord
  transportControl: TransportControlState
}) {
  const operations = permittedTransportOperations(record)
  const controlState =
    transportControl.phase !== "idle" &&
    transportControl.requestId === record.request_id
      ? transportControl
      : null
  const submitting = controlState?.phase === "submitting"
  return (
    <div className="space-y-5">
      <div>
        <p className="font-mono text-[0.68rem] font-semibold text-primary uppercase">
          Execution
        </p>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <h2 className="text-lg font-semibold">{record.lane_id}</h2>
          <StateBadge
            state={executionState(record)}
            label={executionLabels[record.state]}
          />
        </div>
        <p className="mt-2 text-sm text-muted-foreground">
          {record.events.at(-1)!.reason_code}
        </p>
      </div>
      {record.blockers.length > 0 && (
        <Alert variant="destructive">
          <IconLock aria-hidden="true" />
          <AlertTitle>执行被硬门阻塞</AlertTitle>
          <AlertDescription>{record.blockers.join(" · ")}</AlertDescription>
        </Alert>
      )}
      {operations.length > 0 && (
        <section className="space-y-2" aria-labelledby="transport-takeover">
          <h3 id="transport-takeover" className="text-sm font-semibold">
            异常接管
          </h3>
          <div className="flex flex-wrap gap-2">
            {operations.includes("resume") && (
              <Button
                type="button"
                size="sm"
                disabled={submitting}
                onClick={() => onTransportControl(record.request_id, "resume")}
              >
                <IconPlayerPlay data-icon="inline-start" />
                恢复固定传输
              </Button>
            )}
            {operations.includes("cancel") && (
              <Button
                type="button"
                size="sm"
                variant="destructive"
                disabled={submitting}
                onClick={() => onTransportControl(record.request_id, "cancel")}
              >
                <IconPlayerStop data-icon="inline-start" />
                取消固定作业
              </Button>
            )}
          </div>
          {controlState && (
            <p
              className={
                controlState.phase === "rejected" ||
                controlState.phase === "malformed" ||
                controlState.phase === "transport"
                  ? "text-xs text-destructive"
                  : "text-xs text-muted-foreground"
              }
              role="status"
              aria-live="polite"
            >
              {
                {
                  submitting: "正在提交固定控制动作",
                  succeeded: "固定控制动作已记录",
                  rejected: "当前状态拒绝该控制动作",
                  malformed: "控制响应格式不可用",
                  transport: "控制动作传输失败，结果未知",
                }[controlState.phase]
              }
            </p>
          )}
        </section>
      )}
      <section aria-labelledby="execution-basis">
        <h3 id="execution-basis" className="text-sm font-semibold">
          依据
        </h3>
        <Table className="mt-2">
          <TableHeader>
            <TableRow>
              <TableHead>序号</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>原因</TableHead>
              <TableHead>时间</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {record.events.map((event) => (
              <TableRow key={event.event_sha256}>
                <TableCell>{event.sequence}</TableCell>
                <TableCell>{executionLabels[event.state]}</TableCell>
                <TableCell className="whitespace-normal">
                  {event.reason_code}
                </TableCell>
                <TableCell className="whitespace-normal">
                  {dateTime(event.occurred_at)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </section>
      <section aria-labelledby="execution-artifacts">
        <h3 id="execution-artifacts" className="text-sm font-semibold">
          原始工件标识
        </h3>
        <dl className="mt-2 border-y">
          <Definition label="request_id" value={record.request_id} />
          <Definition label="request_sha256" value={record.request_sha256} />
          <Definition label="contract_sha256" value={record.contract_sha256} />
          <Definition
            label="h1_approval_sha256"
            value={record.h1_approval_sha256}
          />
          <Definition label="declaration_id" value={record.declaration_id} />
          {declaration ? (
            <>
              <Definition
                label="source_revision"
                value={declaration.source_revision}
              />
              <Definition
                label="environment_id"
                value={declaration.environment_id}
              />
              <Definition
                label="resource_profile_id"
                value={declaration.resource_profile_id}
              />
            </>
          ) : null}
        </dl>
      </section>
    </div>
  )
}

function PacketDetail({
  lane,
  packets,
}: {
  lane: ResearchLane
  packets: PacketState
}) {
  const packet =
    packets.phase === "ready"
      ? packets.value.packets.find((item) => item.lane_id === lane.lane_id)
      : undefined
  const evidence = lane.evidence_urls.map((url, index) => ({
    label: `${lane.lane_id}-evidence-${index + 1}`,
    url,
  }))
  const rawRows = packet ? aggregateTableRows(packet.raw_aggregate_table) : null
  const rawColumns = rawRows
    ? [...new Set(rawRows.flatMap((row) => Object.keys(row)))]
    : []
  return (
    <div className="space-y-5">
      <div>
        <p className="font-mono text-[0.68rem] font-semibold text-primary uppercase">
          Decision Packet
        </p>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <h2 className="text-lg font-semibold">{lane.model_id}</h2>
          <StateBadge
            state={
              lane.current && lane.packet_complete ? "attention" : "blocked"
            }
            label={lane.conclusion}
          />
        </div>
        <p className="mt-2 text-sm text-muted-foreground">
          {lane.stage} · {lane.attempt_status}
        </p>
      </div>
      <section aria-labelledby="packet-basis">
        <h3 id="packet-basis" className="text-sm font-semibold">
          依据
        </h3>
        <dl className="mt-2 border-y">
          <Definition
            label="packet_complete"
            value={String(lane.packet_complete)}
          />
          <Definition label="current" value={String(lane.current)} />
          <Definition
            label="h2_go_eligible"
            value={String(lane.h2_go_eligible)}
          />
          <Definition label="h2_action" value={lane.h2_action ?? "pending"} />
        </dl>
        {lane.blockers.length > 0 && (
          <Alert variant="destructive" className="mt-3">
            <IconAlertTriangle aria-hidden="true" />
            <AlertTitle>Decision Packet 不可决策</AlertTitle>
            <AlertDescription>{lane.blockers.join(" · ")}</AlertDescription>
          </Alert>
        )}
        {packet ? (
          <>
            <h3 className="mt-4 text-sm font-semibold">聚合依据</h3>
            <dl className="mt-2 border-y">
              <Definition
                label="outcomes"
                value={JSON.stringify(packet.outcomes)}
              />
              <Definition
                label="uncertainty"
                value={JSON.stringify(packet.uncertainty)}
              />
              <Definition
                label="validity"
                value={`${packet.validity} · ${packet.go_eligible ? "go eligible" : "not go eligible"}`}
              />
            </dl>
          </>
        ) : null}
      </section>
      <section aria-labelledby="packet-artifacts">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 id="packet-artifacts" className="text-sm font-semibold">
            原始工件
          </h3>
          {evidence.length ? <EvidenceDisclosure evidence={evidence} /> : null}
        </div>
        {packets.phase !== "ready" ? (
          <Alert variant="destructive" className="mt-3">
            <IconDatabase aria-hidden="true" />
            <AlertTitle>Decision Packet 依据不可用</AlertTitle>
            <AlertDescription>
              服务端没有返回当前 packet projection。
            </AlertDescription>
          </Alert>
        ) : rawRows ? (
          <div
            className="mt-3 overflow-x-auto border-y focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
            role="region"
            aria-label="Decision Packet 公开聚合数据表"
            tabIndex={0}
          >
            <Table>
              <caption className="px-2 py-2 text-left text-xs text-muted-foreground">
                服务端 receipt 提供的公开聚合数据表
              </caption>
              <TableHeader>
                <TableRow>
                  {rawColumns.map((column) => (
                    <TableHead key={column}>{column}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {rawRows.map((row, index) => (
                  <TableRow key={`aggregate-row-${index}`}>
                    {rawColumns.map((column) => (
                      <TableCell key={column} className="whitespace-normal">
                        {column in row ? displayPublicJson(row[column]) : "—"}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : (
          <Alert className="mt-3">
            <IconDatabase aria-hidden="true" />
            <AlertTitle>聚合 outcomes 原始数据表未公开</AlertTitle>
            <AlertDescription>
              当前 API 返回 outcomes 与
              uncertainty，但没有曲线或对应原始聚合数据表；
              不能据此推断未公开的曲线结论。
            </AlertDescription>
          </Alert>
        )}
      </section>
    </div>
  )
}

function AuthorityDetail({ harness }: { harness: HarnessState }) {
  return (
    <div className="space-y-5">
      <div>
        <p className="font-mono text-[0.68rem] font-semibold text-primary uppercase">
          Authority
        </p>
        <h2 className="mt-1 text-lg font-semibold">项目权威与硬门</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          {harness.status.condition} · {harness.status.payload.stage}
        </p>
      </div>
      <div className="space-y-2">
        {harness.status.blockers.map((blocker) => (
          <Alert
            variant="destructive"
            key={`${blocker.category}:${blocker.reason_code}`}
          >
            <IconLock aria-hidden="true" />
            <AlertTitle>{blocker.reason_code}</AlertTitle>
            <AlertDescription>
              {blocker.category}
              {blocker.candidate_id ? ` · ${blocker.candidate_id}` : ""}
            </AlertDescription>
          </Alert>
        ))}
      </div>
      <dl className="border-y">
        <Definition
          label="snapshot_sha256"
          value={harness.status.snapshot_sha256}
        />
        <Definition
          label="valid_until"
          value={dateTime(harness.status.valid_until)}
        />
      </dl>
    </div>
  )
}

function H1Detail({
  contract,
  hitl,
  loop,
}: {
  contract: ContractState
  hitl: HitlControlState
  loop: LoopState
}) {
  const control = hitl.phase === "ready" ? hitl.value : null
  return (
    <div className="space-y-5">
      <div>
        <p className="font-mono text-[0.68rem] font-semibold text-primary uppercase">
          H1
        </p>
        <h2 className="mt-1 text-lg font-semibold">结构化研究契约</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          {control?.h1.current
            ? `current · ${control.h1.owner ?? "unknown"}`
            : control?.h1.enabled
              ? "等待 H 签核"
              : "不可签核"}
        </p>
      </div>
      <Alert variant={control?.h1.enabled ? "default" : "destructive"}>
        <IconFileAnalytics aria-hidden="true" />
        <AlertTitle>结构化契约问卷</AlertTitle>
        <AlertDescription>
          问题、假设、数据、证据职责、停止条件、资源和修复预算均来自服务端登记的
          contract；只有 H1 明确接受后才会冻结执行。
        </AlertDescription>
      </Alert>
      {contract.phase === "ready" ? (
        <section aria-labelledby="contract-questionnaire">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 id="contract-questionnaire" className="text-sm font-semibold">
              问卷字段
            </h3>
            <Badge variant="outline">
              {contract.value.status} · {contract.value.ai.status}
            </Badge>
          </div>
          <dl className="mt-2 border-y">
            {contract.value.questionnaire.map((field) => (
              <Definition
                key={field.id}
                label={`${field.label} · ${field.provenance}`}
                value={field.value}
              />
            ))}
          </dl>
          {contract.value.ai.status !== "ready" && (
            <Alert className="mt-3">
              <IconAlertTriangle aria-hidden="true" />
              <AlertTitle>AI 草案/质询不可用</AlertTitle>
              <AlertDescription>
                {contract.value.ai.reason_code}
              </AlertDescription>
            </Alert>
          )}
        </section>
      ) : (
        <Alert variant="destructive">
          <IconAlertTriangle aria-hidden="true" />
          <AlertTitle>契约问卷不可用</AlertTitle>
          <AlertDescription>
            {contract.phase === "loading"
              ? "正在读取当前 contract。"
              : "服务端没有返回 current contract；H1 保持关闭。"}
          </AlertDescription>
        </Alert>
      )}
      <dl className="border-y">
        <Definition
          label="contract_sha256"
          value={
            loop.phase === "ready"
              ? (loop.value.contract_sha256 ?? "missing")
              : "unavailable"
          }
        />
        <Definition
          label="h1_enabled"
          value={String(control?.h1.enabled ?? false)}
        />
        <Definition
          label="h1_current"
          value={String(control?.h1.current ?? false)}
        />
      </dl>
    </div>
  )
}

function DetailPanel({
  contract,
  execution,
  harness,
  hitl,
  item,
  loop,
  onTransportControl,
  packets,
  transportControl,
}: {
  contract: ContractState
  execution: ExecutionControlState
  harness: HarnessState
  hitl: HitlControlState
  item?: PendingItem
  loop: LoopState
  onTransportControl: (
    requestId: string,
    operation: TransportControlOperation
  ) => void
  packets: PacketState
  transportControl: TransportControlState
}) {
  const declaration =
    item?.record && execution.phase === "ready"
      ? execution.value.registry.declarations.find(
          (candidate) =>
            candidate.declaration_id === item.record?.declaration_id
        )
      : undefined
  return (
    <section
      id="pending-detail"
      className="min-w-0 border border-border bg-surface-raised p-4 lg:max-h-[calc(100svh-11.5rem)] lg:overflow-y-auto"
      aria-label="待决详情"
      tabIndex={0}
    >
      {!item ? (
        <Empty className="min-h-72 rounded-none border-0">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <IconChecklist aria-hidden="true" />
            </EmptyMedia>
            <EmptyTitle>当前无需审阅</EmptyTitle>
            <EmptyDescription>所有公开投影均已处置。</EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : item.kind === "authority" ? (
        <AuthorityDetail harness={harness} />
      ) : item.kind === "h1" ? (
        <H1Detail contract={contract} hitl={hitl} loop={loop} />
      ) : item.record ? (
        <ExecutionDetail
          declaration={declaration}
          onTransportControl={onTransportControl}
          record={item.record}
          transportControl={transportControl}
        />
      ) : item.lane ? (
        <PacketDetail lane={item.lane} packets={packets} />
      ) : null}
    </section>
  )
}

export function PendingWorkbench({
  actionPanel,
  contract,
  decisionPanel,
  execution,
  executionStream,
  harness,
  hitl,
  loop,
  packets,
  onSelect,
  onRetry,
  onTransportControl,
  selected,
  transportControl,
}: {
  actionPanel: React.ReactNode
  contract: ContractState
  decisionPanel: React.ReactNode
  execution: ExecutionControlState
  executionStream: ExecutionStreamState
  harness: HarnessState
  hitl: HitlControlState
  loop: LoopState
  packets: PacketState
  onSelect: (selected: string) => void
  onRetry: () => void
  onTransportControl: (
    requestId: string,
    operation: TransportControlOperation
  ) => void
  selected: string
  transportControl: TransportControlState
}) {
  const items = pendingItems({ execution, harness, hitl, loop })
  const current = items.find((item) => item.id === selected) ?? items[0]
  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3 border-b pb-3">
        <div>
          <p className="font-mono text-[0.68rem] font-semibold text-primary uppercase">
            HITL control
          </p>
          <h2 className="mt-1 text-xl font-semibold">待决工作台</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {harness.status.project_id} · {harness.status.condition} ·{" "}
            {shortSha(harness.status.snapshot_sha256)}
          </p>
        </div>
        <StreamBadge state={executionStream} />
      </header>
      <p
        className="sr-only"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        {current ? `已选择 ${current.title}` : "当前没有待决事项"}
      </p>
      <div className="grid min-w-0 gap-3 lg:grid-cols-[minmax(16rem,0.8fr)_minmax(24rem,1.5fr)_minmax(19rem,0.9fr)] lg:items-start">
        <PendingQueue
          execution={execution}
          items={items}
          onRetry={onRetry}
          onSelect={onSelect}
          selected={current?.id ?? ""}
        />
        <DetailPanel
          contract={contract}
          execution={execution}
          harness={harness}
          hitl={hitl}
          item={current}
          loop={loop}
          onTransportControl={onTransportControl}
          packets={packets}
          transportControl={transportControl}
        />
        <aside className="min-w-0 space-y-3" aria-label="决策操作">
          {actionPanel}
          {decisionPanel}
        </aside>
      </div>
    </div>
  )
}
