import { IconPlayerPlay, IconPlayerStop } from "@tabler/icons-react"

import type { TransportControlState } from "@/hooks/use-research-session"
import { Button } from "@/components/ui/button"
import {
  permittedTransportOperations,
  type ExecutionRecord,
  type TransportControlOperation,
} from "@/lib/domain"

export function TransportRecoveryCard({
  onTransportControl,
  record,
  transportControl,
}: {
  onTransportControl: (
    requestId: string,
    operation: TransportControlOperation
  ) => void
  record: ExecutionRecord
  transportControl: TransportControlState
}) {
  const operations = permittedTransportOperations(record)
  if (operations.length === 0) return null

  const controlState =
    transportControl.phase !== "idle" &&
    transportControl.requestId === record.request_id
      ? transportControl
      : null
  const submitting = controlState?.phase === "submitting"

  return (
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
  )
}
