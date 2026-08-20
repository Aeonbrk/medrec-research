import {
  IconActivity,
  IconGitBranch,
  IconRefresh,
  IconServer,
  IconShieldCheck,
} from "@tabler/icons-react"

import type { ExecutionStreamState } from "@/hooks/use-research-session"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import type { HarnessState } from "@/lib/domain"

function shortSha(value: string) {
  return `${value.slice(0, 8)}...${value.slice(-6)}`
}

export function EnvironmentHealthBar({
  executionStream,
  harness,
  onRefresh,
}: {
  executionStream: ExecutionStreamState
  harness: HarnessState
  onRefresh?: () => void
}) {
  const isDirty = harness.status.blockers.some((b) => b.reason_code === "local-worktree-dirty")
  const hasActionContext = harness.action_context.enabled

  return (
    <header
      className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/80 bg-card/80 p-3 backdrop-blur-md shadow-xs"
      aria-label="环境与预检健康状态"
    >
      <div className="flex flex-wrap items-center gap-2">
        {/* Git Workspace Status */}
        <Tooltip>
          <TooltipTrigger render={<div className="inline-flex cursor-default items-center" />}>
            <Badge
              variant={isDirty ? "secondary" : "outline"}
              className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium ${
                isDirty
                  ? "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400"
                  : "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
              }`}
            >
              <IconGitBranch className="size-3.5" />
              <span>{isDirty ? "工作区有未提交更改" : "Git 工作区就绪"}</span>
            </Badge>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="max-w-xs text-xs">
            {isDirty
              ? "检测到未提交代码改动。本地拟定与测试不受影响，但建议在下发生产 319 前完成提交以确保绝对可复现性。"
              : "当前 Git 工作区干净，符合生产级科研复现与内容可寻址标准。"}
          </TooltipContent>
        </Tooltip>

        {/* 319 Compute Cluster Status */}
        <Tooltip>
          <TooltipTrigger render={<div className="inline-flex cursor-default items-center" />}>
            <Badge
              variant="outline"
              className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium ${
                hasActionContext
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                  : "border-sky-500/30 bg-sky-500/10 text-sky-600 dark:text-sky-400"
              }`}
            >
              <IconServer className="size-3.5" />
              <span>{hasActionContext ? "319 算力集群就绪 (GPU Ready)" : "319 预检待刷新"}</span>
            </Badge>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="max-w-xs text-xs">
            {hasActionContext
              ? "319 远程集群 GPU 环境预检通过，已接入 MIMIC-III 数据集并就绪。"
              : "远程 319 集群处于待命状态，点击右侧刷新可重新探测算力连通性。"}
          </TooltipContent>
        </Tooltip>

        {/* Real-time SSE Stream */}
        <Tooltip>
          <TooltipTrigger render={<div className="inline-flex cursor-default items-center" />}>
            <Badge
              variant="outline"
              className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium ${
                executionStream === "live"
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                  : "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400"
              }`}
            >
              <IconActivity className="size-3.5" />
              <span>{executionStream === "live" ? "实时同步在线" : "流式连接恢复中"}</span>
            </Badge>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="max-w-xs text-xs">
            {executionStream === "live"
              ? "本地与 319 执行流持久化 SSE 管道正常，实时接收实验进度。"
              : "正在尝试重新建立 SSE 管道..."}
          </TooltipContent>
        </Tooltip>

        {/* Scientific Safety & Action Gate */}
        <Tooltip>
          <TooltipTrigger render={<div className="inline-flex cursor-default items-center" />}>
            <Badge
              variant="outline"
              className="flex items-center gap-1.5 border-primary/20 bg-primary/5 px-2.5 py-1 text-xs font-medium text-primary"
            >
              <IconShieldCheck className="size-3.5" />
              <span>Fail-Closed 科学防护</span>
            </Badge>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="max-w-xs text-xs">
            严格锁定隐私边界与数据切分，零患者数据外泄，仅支持确定性白名单科研指令。
          </TooltipContent>
        </Tooltip>
      </div>

      <div className="flex items-center gap-2">
        <div className="hidden font-mono text-[0.7rem] text-muted-foreground sm:inline-block">
          快照: <span className="font-semibold text-foreground">{shortSha(harness.status.snapshot_sha256)}</span>
        </div>
        {onRefresh && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onRefresh}
            className="h-7 gap-1 px-2 text-xs text-muted-foreground hover:text-foreground"
          >
            <IconRefresh className="size-3.5" />
            <span className="hidden sm:inline">刷新状态</span>
          </Button>
        )}
      </div>
    </header>
  )
}
