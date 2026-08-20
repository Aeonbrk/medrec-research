import {
  IconAlertTriangle,
  IconCircleCheck,
  IconCircleX,
  IconClock,
} from "@tabler/icons-react"

import { Badge } from "@/components/ui/badge"
import type { RowState } from "@/lib/domain"

const labels: Record<RowState, string> = {
  pass: "通过",
  attention: "待核验",
  blocked: "阻塞",
}

export function StateBadge({
  state,
  label = labels[state],
  className,
}: {
  state: RowState
  label?: string
  className?: string
}) {
  if (state === "pass") {
    return (
      <Badge variant="success" className={className}>
        <IconCircleCheck data-icon="inline-start" />
        {label}
      </Badge>
    )
  }
  if (state === "blocked") {
    return (
      <Badge variant="destructive" className={className}>
        <IconCircleX data-icon="inline-start" />
        {label}
      </Badge>
    )
  }
  return (
    <Badge variant="warning" className={className}>
      {label === "stale" ? (
        <IconClock data-icon="inline-start" />
      ) : (
        <IconAlertTriangle data-icon="inline-start" />
      )}
      {label}
    </Badge>
  )
}
