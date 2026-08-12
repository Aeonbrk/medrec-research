import * as React from "react"
import { IconChevronDown, IconExternalLink } from "@tabler/icons-react"

import { Button } from "@/components/ui/button"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import type { Evidence } from "@/lib/domain"

const approvedHosts = new Set([
  "aclanthology.org",
  "arxiv.org",
  "dl.acm.org",
  "doi.org",
  "github.com",
  "ieeexplore.ieee.org",
  "openreview.net",
  "proceedings.mlr.press",
  "pubmed.ncbi.nlm.nih.gov",
  "raw.githubusercontent.com",
])

const credentialKeys = new Set([
  "access_token",
  "api_key",
  "apikey",
  "auth",
  "authorization",
  "credential",
  "key",
  "password",
  "passwd",
  "secret",
  "sig",
  "signature",
  "token",
])

export function safeEvidenceUrl(value: string) {
  try {
    const decoded = decodeURIComponent(value)
    if (
      [...decoded].some(
        (character) =>
          character.charCodeAt(0) < 32 || character.charCodeAt(0) === 127
      )
    ) {
      return null
    }
    const authority = value.match(/^https:\/\/([^/?#]+)/i)?.[1] ?? ""
    const parsed = new URL(value)
    if (
      parsed.protocol !== "https:" ||
      parsed.username ||
      parsed.password ||
      authority.includes(":") ||
      parsed.port ||
      parsed.hash ||
      !approvedHosts.has(parsed.hostname)
    ) {
      return null
    }
    for (const key of parsed.searchParams.keys()) {
      if (credentialKeys.has(key.toLocaleLowerCase("en"))) return null
    }
    return parsed.href
  } catch {
    return null
  }
}

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
      <CollapsibleTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          aria-label={`${open ? "收起" : "展开"}${label}`}
        >
          {evidence.length} 项
          <IconChevronDown
            data-icon="inline-end"
            className={
              open ? "rotate-180 transition-transform" : "transition-transform"
            }
            aria-hidden="true"
          />
        </Button>
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
