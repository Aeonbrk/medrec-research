import * as React from "react"
import {
  IconAlertTriangle,
  IconArrowUpRight,
  IconBan,
  IconBracketsContain,
  IconCircleCheck,
  IconDatabaseSearch,
  IconFileAnalytics,
  IconFingerprint,
  IconGitBranch,
  IconLock,
  IconUserCheck,
  IconRefresh,
  IconRoute,
  IconSend,
  IconStack2,
  IconTimeline,
} from "@tabler/icons-react"

import type { ActionState, HitlControlState, LoopState } from "@/App"
import {
  EvidenceDisclosure,
  safeEvidenceUrl,
} from "@/components/evidence-disclosure"
import { StateBadge } from "@/components/state-badge"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { Separator } from "@/components/ui/separator"
import { Textarea } from "@/components/ui/textarea"
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  candidateState,
  laneState,
  matchesQuery,
  matchesStatus,
  stableSort,
  type CandidateStatus,
  type HarnessState,
  type LineageStatus,
  type ProjectStatus,
  type ResearchLane,
  type ViewState,
} from "@/lib/domain"

const stageLabels: Record<string, string> = {
  audit_blocked: "审计阻塞",
  benchmark_in_progress: "基线复现中",
  lane_proposed: "首个复现通道待确认",
  lane_characterizing: "首通道稳定性刻画",
  parallel_eligible: "可进入并行复现",
  review_pending: "比较范围待审查",
  discovery_eligible: "可开始新方法研究",
}

const actionLabels: Record<string, string> = {
  refresh_authorization: "刷新动作授权",
  resolve_source_license: "补齐来源与许可证证据",
  advance_readiness: "推进准备度硬门",
  refresh_remote_preflight: "刷新远端预检",
  request_reproduction: "生成复现工作请求",
  submit_reproduction_evidence: "提交复现证据请求",
  request_next_lane: "生成下一复现通道请求",
  submit_human_review: "提交比较范围审查请求",
  begin_discovery: "生成新方法研究请求",
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

function shortSha(value: string) {
  return `${value.slice(0, 10)}…${value.slice(-6)}`
}

function Raw({ children, title }: { children: string; title?: string }) {
  return (
    <code
      className="font-mono text-[0.72rem] break-all text-foreground"
      title={title ?? children}
    >
      {children}
    </code>
  )
}

function SectionHeading({
  eyebrow,
  title,
  description,
  aside,
}: {
  eyebrow: string
  title: string
  description: string
  aside?: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-3 border-b pb-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-3xl">
        <p className="mb-1 font-mono text-[0.68rem] font-semibold tracking-[0.16em] text-primary uppercase">
          {eyebrow}
        </p>
        <h2 className="text-lg font-semibold tracking-tight sm:text-xl">
          {title}
        </h2>
        <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
          {description}
        </p>
      </div>
      {aside}
    </div>
  )
}

function ConditionAlert({ status }: { status: ProjectStatus }) {
  if (status.condition === "current") return null
  const stale = status.condition === "stale"
  return (
    <Alert variant="destructive">
      <IconAlertTriangle aria-hidden="true" />
      <AlertTitle>{stale ? "项目状态已过期" : "项目状态已降级"}</AlertTitle>
      <AlertDescription>
        {stale
          ? "当前投影不是可用于动作的版本；动作请求保持关闭。下方数据仅用于审计。"
          : "harness 正在显示最后已知的公开安全投影；动作请求保持关闭。"}
      </AlertDescription>
    </Alert>
  )
}

function ActionPanel({
  harness,
  action,
  onRequest,
  onRetry,
}: {
  harness: HarnessState
  action: ActionState
  onRequest: () => void
  onRetry: () => void
}) {
  const { status, action_context: context } = harness
  const next = status.next_action
  const current = status.condition === "current"
  const canRequest =
    current && next !== null && context.enabled && action.phase === "idle"
  const submitting = action.phase === "submitting"
  let message = "状态有效，当前没有允许请求的动作。"
  let state = "no-action"
  if (!current) {
    state = status.condition
    message =
      status.condition === "stale"
        ? "状态已过期；动作请求关闭。"
        : "状态已降级；动作请求关闭。"
  } else if (next && !context.enabled) {
    state = "readonly"
    message = "状态允许下一步，但当前动作上下文不可用。服务未公开具体原因。"
  } else if (canRequest) {
    state = "ready"
    message = "状态与动作授权均为当前版本。"
  } else if (submitting) {
    state = "submitting"
    message = "正在生成内容寻址动作请求。"
  } else if (action.phase === "allowed") {
    state = "allowed"
    message = "动作请求已生成，尚未执行。"
  } else if (action.phase === "blocked") {
    state = "blocked"
    message = "动作请求被 gate 阻塞；请重新载入当前状态。"
  } else if (action.phase === "malformed") {
    state = "malformed"
    message = "动作决策格式不可用；动作请求保持关闭。"
  } else if (action.phase === "transport") {
    state = "transport"
    message = "动作请求传输失败；结果未知，请重新载入当前状态。"
  }

  return (
    <section
      className="border border-border bg-surface-raised"
      aria-labelledby="action-heading"
      aria-busy={submitting}
      data-action-state={state}
    >
      <div className="flex items-start gap-3 border-b px-4 py-3">
        <div className="grid size-8 shrink-0 place-items-center rounded-md bg-primary/10 text-primary">
          <IconLock aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <h3 id="action-heading" className="text-sm font-semibold">
            内容寻址动作请求
          </h3>
          <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
            只生成请求对象，不执行任务、不批准 H1/H2、不写入研究状态。
          </p>
        </div>
      </div>
      <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
        <div className="min-w-0">
          <p className="text-xs text-muted-foreground">下一动作</p>
          <p className="mt-1 text-sm font-medium">
            {next
              ? (actionLabels[next.action_id] ?? next.label)
              : "当前没有允许动作"}
          </p>
          <p
            className="mt-2 text-xs leading-relaxed text-muted-foreground"
            aria-live="polite"
          >
            {message}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            disabled={!canRequest}
            aria-disabled={!canRequest}
            onClick={onRequest}
            className="min-h-11"
          >
            <IconSend data-icon="inline-start" />
            {submitting
              ? "正在生成"
              : next
                ? (actionLabels[next.action_id] ?? next.label)
                : "不可用"}
          </Button>
          {(action.phase === "blocked" ||
            action.phase === "malformed" ||
            action.phase === "transport" ||
            (next !== null && !context.enabled) ||
            !current) && (
            <Button variant="outline" className="min-h-11" onClick={onRetry}>
              <IconRefresh data-icon="inline-start" />
              重新载入
            </Button>
          )}
        </div>
      </div>
      {action.phase === "allowed" && action.decision.status === "allowed" && (
        <div className="border-t bg-success-subtle px-4 py-3" tabIndex={-1}>
          <p className="flex items-center gap-2 text-sm font-medium text-success-foreground">
            <IconCircleCheck aria-hidden="true" />
            请求已生成，尚未执行
          </p>
          <dl className="mt-2 grid gap-2 text-xs sm:grid-cols-2">
            <div>
              <dt className="text-muted-foreground">request_id</dt>
              <dd className="mt-0.5">
                <Raw>{action.decision.request.request_id}</Raw>
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">request_sha256</dt>
              <dd className="mt-0.5">
                <Raw>{action.decision.request.request_sha256}</Raw>
              </dd>
            </div>
          </dl>
        </div>
      )}
      {action.phase === "blocked" && action.decision.status === "blocked" && (
        <div className="border-t bg-danger-subtle px-4 py-3" role="alert">
          <p className="flex items-center gap-2 text-sm font-medium text-destructive">
            <IconBan aria-hidden="true" />
            gate 阻塞：<Raw>{action.decision.reason_code}</Raw>
          </p>
        </div>
      )}
    </section>
  )
}

function Metric({
  icon: Icon,
  label,
  value,
  detail,
}: {
  icon: typeof IconStack2
  label: string
  value: React.ReactNode
  detail: string
}) {
  return (
    <div className="border-l-2 border-primary bg-surface-raised px-4 py-3">
      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
        <Icon className="text-primary" aria-hidden="true" />
        {label}
      </div>
      <div className="mt-2 text-2xl font-semibold tracking-tight tabular-nums">
        {value}
      </div>
      <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
    </div>
  )
}

function Overview({
  harness,
  loop,
  action,
  onRequest,
  onRetry,
}: {
  harness: HarnessState
  loop: LoopState
  action: ActionState
  onRequest: () => void
  onRetry: () => void
}) {
  const { status } = harness
  const passed = status.payload.candidates.filter(
    (item) => candidateState(item) === "pass"
  ).length
  const loopCount =
    loop.phase === "ready" && !loop.value.stale && loop.value.h1_current
      ? loop.value.lanes.length
      : null
  return (
    <div className="space-y-5">
      <SectionHeading
        eyebrow="CONTROL PLANE / BOUNDED HITL"
        title="当前研究状态，一屏完成可信判断"
        description="所有数值、门禁与证据均来自 Python harness；只有 H1/H2 是绑定当前记录的人工决策，界面不推断 readiness，也不补写科学结论。"
        aside={
          <StateBadge
            state={status.condition === "current" ? "pass" : "attention"}
            label={status.condition}
          />
        }
      />
      <ConditionAlert status={status} />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric
          icon={IconStack2}
          label="候选基线"
          value={status.payload.candidates.length}
          detail={`${passed} 个通过当前前端映射`}
        />
        <Metric
          icon={IconFileAnalytics}
          label="qualified_count"
          value={status.payload.qualified_count}
          detail={`review_state · ${status.payload.review_state}`}
        />
        <Metric
          icon={IconGitBranch}
          label="共享谱系层"
          value={status.payload.shared_lineage.length}
          detail="跨候选的公开上游证据"
        />
        <Metric
          icon={IconTimeline}
          label="HITL 通道"
          value={loopCount ?? "—"}
          detail={
            loopCount === null
              ? "状态不可用，不展示伪造详情"
              : "当前且通过 H1 gate"
          }
        />
      </div>
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.4fr)_minmax(19rem,0.6fr)]">
        <section
          className="border border-border bg-surface-raised"
          aria-labelledby="snapshot-heading"
        >
          <div className="flex items-center gap-3 border-b px-4 py-3">
            <IconRoute className="text-primary" aria-hidden="true" />
            <div>
              <h3 id="snapshot-heading" className="text-sm font-semibold">
                研究阶段与快照
              </h3>
              <p className="text-xs text-muted-foreground">
                时间与标识保留原始机器值
              </p>
            </div>
          </div>
          <dl className="grid gap-px bg-border sm:grid-cols-2">
            {[
              [
                "stage",
                stageLabels[status.payload.stage] ?? status.payload.stage,
              ],
              ["condition", status.condition],
              ["generated_at", dateTime(status.generated_at)],
              ["valid_until", dateTime(status.valid_until)],
            ].map(([label, value]) => (
              <div key={label} className="bg-background px-4 py-3">
                <dt className="font-mono text-[0.68rem] text-muted-foreground">
                  {label}
                </dt>
                <dd className="mt-1 text-sm font-medium">{value}</dd>
              </div>
            ))}
          </dl>
          <div className="border-t px-4 py-3">
            <p className="font-mono text-[0.68rem] text-muted-foreground">
              snapshot_sha256
            </p>
            <p className="mt-1">
              <Raw>{status.snapshot_sha256}</Raw>
            </p>
          </div>
        </section>
        <section
          className="border border-border bg-surface-raised p-4"
          aria-labelledby="blockers-heading"
        >
          <div className="flex items-center justify-between gap-3">
            <h3 id="blockers-heading" className="text-sm font-semibold">
              阻塞摘要
            </h3>
            <Badge variant={status.blockers.length ? "destructive" : "outline"}>
              {status.blockers.length} 项
            </Badge>
          </div>
          {status.blockers.length ? (
            <ul className="mt-3 space-y-3">
              {status.blockers.map((blocker, index) => (
                <li
                  key={`${blocker.reason_code}:${index}`}
                  className="border-l-2 border-destructive pl-3 text-sm"
                >
                  <Raw>{blocker.reason_code}</Raw>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {blocker.category}
                    {blocker.candidate_id ? ` · ${blocker.candidate_id}` : ""}
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
              <IconCircleCheck
                className="text-success-foreground"
                aria-hidden="true"
              />
              当前快照未声明 blocker
            </p>
          )}
        </section>
      </div>
      <ActionPanel
        harness={harness}
        action={action}
        onRequest={onRequest}
        onRetry={onRetry}
      />
    </div>
  )
}

function NoResults() {
  return (
    <Empty className="min-h-56 border">
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <IconDatabaseSearch aria-hidden="true" />
        </EmptyMedia>
        <EmptyTitle>没有匹配结果</EmptyTitle>
        <EmptyDescription>
          调整全局搜索或状态筛选；原始研究状态没有被修改。
        </EmptyDescription>
      </EmptyHeader>
    </Empty>
  )
}

function CandidateCards({ rows }: { rows: CandidateStatus[] }) {
  return (
    <div className="grid gap-3 md:hidden">
      {rows.map((candidate) => (
        <article
          key={candidate.candidate_id}
          className="border border-border bg-surface-raised p-4"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className="font-medium">{candidate.display_name}</h3>
              <Raw>{candidate.candidate_id}</Raw>
            </div>
            <StateBadge state={candidateState(candidate)} />
          </div>
          <dl className="mt-4 grid grid-cols-2 gap-3 text-xs">
            <div>
              <dt className="text-muted-foreground">readiness</dt>
              <dd className="mt-1 font-mono">{candidate.readiness}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">source_gate</dt>
              <dd className="mt-1 font-mono">{candidate.source_gate}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">license_gate</dt>
              <dd className="mt-1 font-mono">{candidate.license_gate}</dd>
            </div>
          </dl>
          <Separator className="my-3" />
          <EvidenceDisclosure evidence={candidate.evidence} />
        </article>
      ))}
    </div>
  )
}

function Candidates({
  status,
  view,
}: {
  status: ProjectStatus
  view: ViewState
}) {
  const filtered = status.payload.candidates.filter(
    (candidate) =>
      matchesQuery(
        [
          candidate.candidate_id,
          candidate.display_name,
          candidate.readiness,
          candidate.source_gate,
          candidate.license_gate,
          candidate.evidence.map((item) => item.label),
        ],
        view.query
      ) && matchesStatus(candidateState(candidate), view.status)
  )
  const rows = stableSort(
    filtered,
    (item) => item.candidate_id,
    candidateState,
    view.sort,
    view.order
  )
  return (
    <div className="space-y-5">
      <SectionHeading
        eyebrow="BASELINE CORE"
        title="候选基线门禁"
        description="readiness、来源与许可证分开呈现；Prediction Adapter 不在此界面改变任何科学行为。"
        aside={
          <Badge variant="outline">
            {rows.length} / {status.payload.candidates.length}
          </Badge>
        }
      />
      <ConditionAlert status={status} />
      {rows.length === 0 ? (
        <NoResults />
      ) : (
        <>
          <CandidateCards rows={rows} />
          <div className="hidden border border-border bg-surface-raised md:block">
            <Table className="density-table">
              <TableCaption className="px-4 pb-3 text-left">
                候选基线及其独立 gate；状态文字与图标共同表达结果。
              </TableCaption>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">候选</TableHead>
                  <TableHead scope="col">readiness</TableHead>
                  <TableHead scope="col">source_gate</TableHead>
                  <TableHead scope="col">license_gate</TableHead>
                  <TableHead scope="col">映射状态</TableHead>
                  <TableHead scope="col">公开证据</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((candidate) => (
                  <TableRow key={candidate.candidate_id}>
                    <TableCell>
                      <p className="font-medium">{candidate.display_name}</p>
                      <Raw>{candidate.candidate_id}</Raw>
                    </TableCell>
                    <TableCell>
                      <Raw>{candidate.readiness}</Raw>
                    </TableCell>
                    <TableCell>
                      <Raw>{candidate.source_gate}</Raw>
                    </TableCell>
                    <TableCell>
                      <Raw>{candidate.license_gate}</Raw>
                    </TableCell>
                    <TableCell>
                      <StateBadge state={candidateState(candidate)} />
                    </TableCell>
                    <TableCell>
                      <EvidenceDisclosure evidence={candidate.evidence} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </>
      )}
    </div>
  )
}

function repositoryLink(value: string) {
  const url = safeEvidenceUrl(value)
  return url ? (
    <a
      className="inline-flex items-center gap-1 text-primary hover:underline"
      href={url}
      target="_blank"
      rel="noopener noreferrer"
    >
      <Raw>{value}</Raw>
      <IconArrowUpRight aria-hidden="true" />
    </a>
  ) : (
    <Raw>{value}</Raw>
  )
}

function LineageCards({ rows }: { rows: LineageStatus[] }) {
  return (
    <div className="grid gap-3 md:hidden">
      {rows.map((item) => (
        <article
          key={item.layer}
          className="border border-border bg-surface-raised p-4"
        >
          <div className="flex items-center gap-2">
            <IconGitBranch className="text-primary" aria-hidden="true" />
            <h3>
              <Raw>{item.layer}</Raw>
            </h3>
          </div>
          <p className="mt-3 text-xs text-muted-foreground">上游仓库</p>
          <div className="mt-1 text-sm break-all">
            {repositoryLink(item.upstream_repository)}
          </div>
          <p className="mt-3 text-xs text-muted-foreground">关联候选</p>
          <div className="mt-1 flex flex-wrap gap-1">
            {item.candidate_ids.map((id) => (
              <Badge key={id} variant="outline" className="font-mono">
                {id}
              </Badge>
            ))}
          </div>
          <Separator className="my-3" />
          <EvidenceDisclosure evidence={item.evidence} />
        </article>
      ))}
    </div>
  )
}

function Lineage({ status, view }: { status: ProjectStatus; view: ViewState }) {
  const filtered = status.payload.shared_lineage.filter((item) =>
    matchesQuery(
      [
        item.layer,
        item.upstream_repository,
        item.candidate_ids,
        item.evidence.map((evidence) => evidence.label),
      ],
      view.query
    )
  )
  const rows = stableSort(
    filtered,
    (item) => item.layer,
    () => "pass",
    view.sort,
    view.order
  )
  return (
    <div className="space-y-5">
      <SectionHeading
        eyebrow="SHARED PROVENANCE"
        title="共享谱系"
        description="明确哪些候选共享上游实现、数据处理、切分或评估路径；共享不等于独立复现。"
        aside={<Badge variant="outline">{rows.length} 层</Badge>}
      />
      <ConditionAlert status={status} />
      {rows.length === 0 ? (
        <NoResults />
      ) : (
        <>
          <LineageCards rows={rows} />
          <div className="hidden border border-border bg-surface-raised md:block">
            <Table className="density-table">
              <TableCaption className="px-4 pb-3 text-left">
                共享谱系层、上游仓库、关联候选及公开证据。
              </TableCaption>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">层</TableHead>
                  <TableHead scope="col">上游仓库</TableHead>
                  <TableHead scope="col">关联候选</TableHead>
                  <TableHead scope="col">证据</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((item) => (
                  <TableRow key={item.layer}>
                    <TableCell>
                      <Raw>{item.layer}</Raw>
                    </TableCell>
                    <TableCell className="max-w-sm whitespace-normal">
                      {repositoryLink(item.upstream_repository)}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {item.candidate_ids.map((id) => (
                          <Badge
                            key={id}
                            variant="outline"
                            className="font-mono"
                          >
                            {id}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      <EvidenceDisclosure evidence={item.evidence} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </>
      )}
    </div>
  )
}

function LoopUnavailable({ phase }: { phase: LoopState["phase"] }) {
  const malformed = phase === "malformed"
  return (
    <Empty className="min-h-64 border">
      <EmptyHeader>
        <EmptyMedia variant="icon">
          {malformed ? (
            <IconAlertTriangle aria-hidden="true" />
          ) : (
            <IconTimeline aria-hidden="true" />
          )}
        </EmptyMedia>
        <EmptyTitle>
          {malformed ? "研究循环格式不可用" : "研究循环状态不可用"}
        </EmptyTitle>
        <EmptyDescription>
          {malformed
            ? "响应未通过既有 schema 校验，因此不展示 lane 详情。"
            : "stale、non-current 或后端不可用均由 Python harness fail closed；界面不会补造 lane 详情。"}
        </EmptyDescription>
      </EmptyHeader>
    </Empty>
  )
}

function LaneCards({ rows }: { rows: ResearchLane[] }) {
  return (
    <div className="grid gap-3 md:hidden">
      {rows.map((lane) => (
        <article
          key={lane.lane_id}
          className="border border-border bg-surface-raised p-4"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="font-medium">{lane.model_id}</h3>
              <Raw>{lane.lane_id}</Raw>
            </div>
            <StateBadge state={laneState(lane)} />
          </div>
          <dl className="mt-4 grid grid-cols-2 gap-3 text-xs">
            <div>
              <dt className="text-muted-foreground">stage</dt>
              <dd className="mt-1 font-mono">{lane.stage}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">attempt_status</dt>
              <dd className="mt-1 font-mono">{lane.attempt_status}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">conclusion</dt>
              <dd className="mt-1 font-mono">{lane.conclusion}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">h2_action</dt>
              <dd className="mt-1 font-mono">{lane.h2_action ?? "—"}</dd>
            </div>
          </dl>
          {lane.blockers.length > 0 && (
            <p className="mt-3 text-xs text-destructive">
              {lane.blockers.join(" · ")}
            </p>
          )}
        </article>
      ))}
    </div>
  )
}

function HumanDecisionPanel({
  hitl,
  onDecision,
}: {
  hitl: HitlControlState
  onDecision: (
    path: "/api/h1" | "/api/h2",
    payload: Record<string, unknown>
  ) => void
}) {
  const [researcher, setResearcher] = React.useState("")
  const [rationale, setRationale] = React.useState("")
  const [laneId, setLaneId] = React.useState("")
  const [action, setAction] = React.useState("hold")
  const ready = hitl.phase === "ready"
  const control = ready ? hitl.value : null
  const submitting = hitl.phase === "submitting"
  const h1Enabled = Boolean(control?.h1.enabled && !control.h1.current)
  const h2Lane = control?.h2.find((lane) => lane.lane_id === laneId)

  React.useEffect(() => {
    if (control?.h2.length && !laneId) setLaneId(control.h2[0].lane_id)
  }, [control, laneId])

  return (
    <section
      className="border border-border bg-surface-raised"
      aria-busy={submitting}
    >
      <div className="flex items-start gap-3 border-b px-4 py-3">
        <div className="grid size-8 shrink-0 place-items-center rounded-md bg-primary/10 text-primary">
          <IconUserCheck aria-hidden="true" />
        </div>
        <div>
          <h3 className="text-sm font-semibold">Human authority</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">
            你的决定绑定服务器当前 contract / packet；不会执行远程任务。
          </p>
        </div>
      </div>
      {!ready ? (
        <Alert
          variant={hitl.phase === "rejected" ? "destructive" : "default"}
          className="m-4"
        >
          <IconAlertTriangle aria-hidden="true" />
          <AlertTitle>
            {hitl.phase === "rejected"
              ? "科学决策被拒绝"
              : "人工控制状态不可用"}
          </AlertTitle>
          <AlertDescription>
            {hitl.phase === "rejected"
              ? "contract、H1 或 packet 已变化，或 go 不满足 usable + accepted 条件。请重新载入。"
              : "当前不能安全创建 H1/H2；研究状态保持不变。"}
          </AlertDescription>
        </Alert>
      ) : (
        <div className="grid gap-5 p-4 xl:grid-cols-2">
          <form
            className="space-y-3"
            onSubmit={(event) => {
              event.preventDefault()
              onDecision("/api/h1", {
                kind: "h1_input",
                schema_version: 1,
                owner: researcher,
                rationale,
              })
            }}
          >
            <div>
              <h4 className="text-sm font-semibold">H1 · 冻结当前复现契约</h4>
              <p className="mt-1 text-xs text-muted-foreground">
                {control?.h1.current
                  ? `current · ${control.h1.owner ?? "unknown"}`
                  : h1Enabled
                    ? "完整 production contract 已就绪，等待你的明确接受。"
                    : "production contract 缺失或无效。"}
              </p>
            </div>
            <label
              className="block text-xs font-medium"
              htmlFor="hitl-researcher"
            >
              研究负责人 ID
            </label>
            <Input
              id="hitl-researcher"
              value={researcher}
              onChange={(event) => setResearcher(event.target.value)}
              placeholder="例如 oian"
              autoComplete="off"
            />
            <label
              className="block text-xs font-medium"
              htmlFor="hitl-rationale"
            >
              决策理由（公开安全、单行）
            </label>
            <Textarea
              id="hitl-rationale"
              value={rationale}
              onChange={(event) =>
                setRationale(event.target.value.replace(/[\r\n]+/g, " "))
              }
              placeholder="说明为什么接受或如何处置证据"
            />
            <Button
              type="submit"
              disabled={!h1Enabled || !researcher || submitting}
              aria-disabled={!h1Enabled || !researcher || submitting}
              className="min-h-11"
            >
              明确接受并创建 H1
            </Button>
          </form>
          <form
            className="space-y-3 border-t pt-5 xl:border-t-0 xl:border-l xl:pt-0 xl:pl-5"
            onSubmit={(event) => {
              event.preventDefault()
              onDecision("/api/h2", {
                kind: "h2_input",
                schema_version: 1,
                lane_id: laneId,
                researcher,
                action,
                rationale,
              })
            }}
          >
            <div>
              <h4 className="text-sm font-semibold">H2 · 处置当前证据包</h4>
              <p className="mt-1 text-xs text-muted-foreground">
                go 仅在 current + complete + usable + accepted 时成立。
              </p>
            </div>
            <label className="block text-xs font-medium" htmlFor="hitl-lane">
              lane
            </label>
            <select
              id="hitl-lane"
              className="min-h-11 w-full rounded-lg border border-input bg-background px-3 text-sm"
              value={laneId}
              onChange={(event) => setLaneId(event.target.value)}
              disabled={!control?.h2.length}
            >
              {control?.h2.map((lane) => (
                <option key={lane.lane_id} value={lane.lane_id}>
                  {lane.lane_id} · {lane.current_action ?? "pending"}
                </option>
              ))}
            </select>
            <label className="block text-xs font-medium" htmlFor="hitl-action">
              决策
            </label>
            <select
              id="hitl-action"
              className="min-h-11 w-full rounded-lg border border-input bg-background px-3 text-sm"
              value={action}
              onChange={(event) => setAction(event.target.value)}
            >
              <option value="hold">hold</option>
              <option value="revise">revise</option>
              <option value="kill">kill</option>
              <option value="go" disabled={!h2Lane?.go_eligible}>
                go
              </option>
            </select>
            <Button
              type="submit"
              disabled={!h2Lane?.enabled || !researcher || submitting}
              aria-disabled={!h2Lane?.enabled || !researcher || submitting}
              className="min-h-11"
            >
              创建 H2 决策
            </Button>
          </form>
        </div>
      )}
      {control?.blockers.length ? (
        <div className="border-t px-4 py-3 text-xs text-destructive">
          {control.blockers.join(" · ")}
        </div>
      ) : null}
    </section>
  )
}

function Hitl({
  loop,
  hitl,
  view,
  onDecision,
}: {
  loop: LoopState
  hitl: HitlControlState
  view: ViewState
  onDecision: (
    path: "/api/h1" | "/api/h2",
    payload: Record<string, unknown>
  ) => void
}) {
  if (loop.phase === "loading")
    return (
      <div className="space-y-4">
        <SectionHeading
          eyebrow="HUMAN IN THE LOOP"
          title="HITL 循环"
          description="正在读取当前 H1 与 lane 证据包状态。"
        />
        <div className="h-64 animate-pulse bg-muted" />
      </div>
    )
  if (loop.phase !== "ready")
    return (
      <div className="space-y-5">
        <SectionHeading
          eyebrow="HUMAN IN THE LOOP"
          title="HITL 循环"
          description="仅显示 Python harness 判定为 current 的研究循环状态。"
        />
        <LoopUnavailable phase={loop.phase} />
      </div>
    )
  const filtered = loop.value.lanes.filter(
    (lane) =>
      matchesQuery(
        [
          lane.lane_id,
          lane.model_id,
          lane.stage,
          lane.attempt_status,
          lane.conclusion,
          lane.h2_action ?? "",
          lane.blockers,
        ],
        view.query
      ) && matchesStatus(laneState(lane), view.status)
  )
  const rows = stableSort(
    filtered,
    (item) => item.lane_id,
    laneState,
    view.sort,
    view.order
  )
  return (
    <div className="space-y-5">
      <SectionHeading
        eyebrow="HUMAN IN THE LOOP"
        title="HITL 循环"
        description="H1 current 只允许审查当前 evidence packet；h2_go_eligible 不是浏览器审批或执行。"
        aside={
          <StateBadge
            state={loop.value.h1_current ? "pass" : "blocked"}
            label={loop.value.h1_current ? "H1 current" : "H1 required"}
          />
        }
      />
      {loop.value.blockers.length > 0 && (
        <Alert variant="destructive">
          <IconAlertTriangle aria-hidden="true" />
          <AlertTitle>当前循环 fail closed</AlertTitle>
          <AlertDescription>{loop.value.blockers.join(" · ")}</AlertDescription>
        </Alert>
      )}
      <HumanDecisionPanel hitl={hitl} onDecision={onDecision} />
      {rows.length === 0 ? (
        <NoResults />
      ) : (
        <>
          <LaneCards rows={rows} />
          <div className="hidden border border-border bg-surface-raised md:block">
            <Table className="density-table">
              <TableCaption className="px-4 pb-3 text-left">
                当前 HITL lane、证据包完整性与 H2 eligibility。
              </TableCaption>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">lane / model</TableHead>
                  <TableHead scope="col">stage</TableHead>
                  <TableHead scope="col">attempt</TableHead>
                  <TableHead scope="col">conclusion</TableHead>
                  <TableHead scope="col">packet / H2</TableHead>
                  <TableHead scope="col">状态</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((lane) => (
                  <TableRow key={lane.lane_id}>
                    <TableCell>
                      <p className="font-medium">{lane.model_id}</p>
                      <Raw>{lane.lane_id}</Raw>
                    </TableCell>
                    <TableCell>
                      <Raw>{lane.stage}</Raw>
                    </TableCell>
                    <TableCell>
                      <Raw>{lane.attempt_status}</Raw>
                    </TableCell>
                    <TableCell>
                      <Raw>{lane.conclusion}</Raw>
                    </TableCell>
                    <TableCell>
                      <div className="space-y-1 text-xs">
                        <p>
                          packet · <Raw>{String(lane.packet_complete)}</Raw>
                        </p>
                        <p>
                          eligible · <Raw>{String(lane.h2_go_eligible)}</Raw>
                        </p>
                        <p>
                          action · <Raw>{lane.h2_action ?? "null"}</Raw>
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <StateBadge state={laneState(lane)} />
                      {lane.blockers.length > 0 && (
                        <p className="mt-2 max-w-xs text-xs whitespace-normal text-destructive">
                          {lane.blockers.join(" · ")}
                        </p>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </>
      )}
    </div>
  )
}

function Authority({
  status,
  view,
}: {
  status: ProjectStatus
  view: ViewState
}) {
  const authorities = status.authorities.filter((item) =>
    matchesQuery([item.authority_id, item.sha256], view.query)
  )
  return (
    <div className="space-y-5">
      <SectionHeading
        eyebrow="CONTENT ADDRESSED"
        title="权威摘要"
        description="权威文件摘要与项目快照共同确定可审计身份；SHA 保留完整原值。"
        aside={
          <Badge variant="outline">
            {authorities.length} / {status.authorities.length}
          </Badge>
        }
      />
      <ConditionAlert status={status} />
      <section className="border border-border bg-surface-raised">
        <div className="grid gap-px bg-border sm:grid-cols-2 xl:grid-cols-4">
          {authorities.map((item) => (
            <div key={item.authority_id} className="min-w-0 bg-background p-4">
              <IconFingerprint
                className="mb-3 text-primary"
                aria-hidden="true"
              />
              <h3 className="font-mono text-sm font-semibold">
                {item.authority_id}
              </h3>
              <p className="mt-2">
                <Raw title={item.sha256}>{shortSha(item.sha256)}</Raw>
              </p>
            </div>
          ))}
        </div>
        {authorities.length === 0 && <NoResults />}
      </section>
      <section className="border border-border bg-surface-raised p-4">
        <div className="flex items-center gap-2">
          <IconBracketsContain className="text-primary" aria-hidden="true" />
          <h3 className="text-sm font-semibold">项目快照</h3>
        </div>
        <dl className="mt-4 grid gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-xs text-muted-foreground">project_id</dt>
            <dd className="mt-1">
              <Raw>{status.project_id}</Raw>
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">snapshot_sha256</dt>
            <dd className="mt-1">
              <Raw>{status.snapshot_sha256}</Raw>
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">review_state</dt>
            <dd className="mt-1">
              <Raw>{status.payload.review_state}</Raw>
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">
              discovery_eligible
            </dt>
            <dd className="mt-1">
              <Raw>{String(status.payload.discovery_eligible)}</Raw>
            </dd>
          </div>
        </dl>
      </section>
    </div>
  )
}

export function ResearchConsole({
  harness,
  loop,
  hitl,
  view,
  action,
  onRequest,
  onRetry,
  onHitlDecision,
}: {
  harness: HarnessState
  loop: LoopState
  hitl: HitlControlState
  view: ViewState
  action: ActionState
  onRequest: () => void
  onRetry: () => void
  onHitlDecision: (
    path: "/api/h1" | "/api/h2",
    payload: Record<string, unknown>
  ) => void
}) {
  return (
    <main
      id="main-content"
      className="flex-1 overflow-y-auto p-4 lg:p-6"
      data-density={view.density}
      tabIndex={-1}
    >
      {view.section === "overview" && (
        <Overview
          harness={harness}
          loop={loop}
          action={action}
          onRequest={onRequest}
          onRetry={onRetry}
        />
      )}
      {view.section === "candidates" && (
        <Candidates status={harness.status} view={view} />
      )}
      {view.section === "lineage" && (
        <Lineage status={harness.status} view={view} />
      )}
      {view.section === "hitl" && (
        <Hitl loop={loop} hitl={hitl} view={view} onDecision={onHitlDecision} />
      )}
      {view.section === "authority" && (
        <Authority status={harness.status} view={view} />
      )}
      <p className="sr-only" aria-live="assertive">
        {action.phase === "blocked" ||
        action.phase === "malformed" ||
        action.phase === "transport"
          ? "动作请求未生成"
          : ""}
      </p>
    </main>
  )
}
