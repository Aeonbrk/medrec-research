import * as React from "react"
import { IconChevronDown, IconExternalLink } from "@tabler/icons-react"

import { Button } from "@/components/ui/button"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { safeEvidenceUrl, type Evidence } from "@/lib/domain"

export function EvidenceDisclosure({
  evidence,
  label = "公开证据",
}: {
  evidence: Evidence[]
  label?: string
}) {
  const [open, setOpen] = React.useState(false)
  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger
        render={
          <Button
            variant="ghost"
            size="sm"
            aria-label={`${open ? "收起" : "展开"}${label}`}
          />
        }
      >
        {evidence.length} 项
        <IconChevronDown
          data-icon="inline-end"
          className={
            open ? "rotate-180 transition-transform" : "transition-transform"
          }
          aria-hidden="true"
        />
      </CollapsibleTrigger>
      <CollapsibleContent className="pt-2">
        <ul className="flex flex-col gap-1.5" aria-label={label}>
          {evidence.map((item) => {
            const url = safeEvidenceUrl(item.url)
            return (
              <li
                key={`${item.label}:${item.url}`}
                className="text-sm text-muted-foreground"
              >
                {url ? (
                  <a
                    className="inline-flex min-h-8 items-center gap-1 text-primary underline-offset-4 hover:underline focus-visible:rounded-sm"
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {item.label}
                    <IconExternalLink aria-hidden="true" />
                  </a>
                ) : (
                  <span>{item.label}（链接不可用）</span>
                )}
              </li>
            )
          })}
        </ul>
      </CollapsibleContent>
    </Collapsible>
  )
}
