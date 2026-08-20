import {
  IconBug,
  IconEye,
  IconFileText,
  IconShield,
  IconTerminal,
  IconUsers,
} from "@tabler/icons-react"

import { Badge } from "@/components/ui/badge"
import type { TeamCompositionConfig } from "@/lib/domain"

const presetDisplayNames: Record<string, string> = {
  review_team: "Review Team (3 Reviewers)",
  debug_team: "Debug Team (3 Hypotheses)",
  feature_team: "Feature Team (Lead + 2 Impls)",
  fullstack_team: "Fullstack Team (4 Roles)",
  research_team: "Research Team (Literature & Matrix)",
  security_team: "Security Team (4 Hard Gates)",
  migration_team: "Migration Team (Lead + Impl + Rev)",
}

const complexityLabels: Record<string, string> = {
  simple: "简单 (1-2 agents)",
  moderate: "中等 (2-3 agents)",
  complex: "复杂 (3-4 agents)",
  very_complex: "高复杂 (4-5 agents)",
}

export function TeamCompositionConsole({
  config,
  output,
  reasonCode,
  status,
}: {
  config?: TeamCompositionConfig
  output?: string | null
  reasonCode?: string
  status?: "unavailable" | "ready" | "error"
}) {
  if (!config && !output) {
    return null
  }

  return (
    <section
      className="space-y-4 rounded-xl border border-border bg-card p-4 text-card-foreground shadow-xs"
      aria-labelledby="team-composition-heading"
    >
      <header className="flex flex-wrap items-center justify-between gap-2 border-b pb-3">
        <div className="flex items-center gap-2">
          <IconUsers className="size-5 text-primary" aria-hidden="true" />
          <div>
            <h3 id="team-composition-heading" className="text-sm font-semibold">
              Agent Team Composition Console
            </h3>
            <p className="text-xs text-muted-foreground">
              $team-composition-patterns · 动态多智能体协作中枢
            </p>
          </div>
        </div>
        {config && (
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge variant="outline" className="font-mono text-xs">
              {presetDisplayNames[config.preset] ?? config.preset}
            </Badge>
            <Badge variant="secondary" className="font-mono text-xs">
              <IconTerminal className="mr-1 size-3" />
              {config.display_mode}
            </Badge>
            <Badge variant="secondary" className="font-mono text-xs">
              {complexityLabels[config.complexity] ?? config.complexity}
            </Badge>
          </div>
        )}
      </header>

      {config && config.teammates.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground uppercase">
            Team Members ({config.teammates.length})
          </p>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {config.teammates.map((teammate) => (
              <div
                key={teammate.agent_id}
                className="flex flex-col justify-between rounded-lg border border-border/80 bg-muted/40 p-3 text-xs"
              >
                <div className="flex items-center justify-between gap-1">
                  <span className="font-mono font-semibold text-primary">
                    {teammate.agent_id}
                  </span>
                  {teammate.read_only ? (
                    <Badge variant="outline" className="text-[0.65rem]">
                      <IconEye className="mr-0.5 size-2.5" /> Read-Only
                    </Badge>
                  ) : (
                    <Badge variant="secondary" className="text-[0.65rem]">
                      Writable
                    </Badge>
                  )}
                </div>
                <div className="mt-1 font-medium text-foreground">
                  {teammate.role}
                </div>
                <p className="mt-1 text-[0.72rem] text-muted-foreground">
                  Focus: {teammate.focus_dimension}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {output && (
        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase">
            <IconFileText className="size-3.5" />
            <span>Deliberation Findings & Memo</span>
          </div>
          <div className="max-h-64 overflow-y-auto rounded-lg border border-border/80 bg-muted/30 p-3 font-mono text-xs whitespace-pre-wrap">
            {output}
          </div>
        </div>
      )}

      {status === "error" && (
        <div className="flex items-center gap-2 text-xs text-destructive">
          <IconBug className="size-4" />
          <span>Team deliberation error: {reasonCode}</span>
        </div>
      )}

      <footer className="flex items-center gap-1 text-[0.7rem] text-muted-foreground">
        <IconShield className="size-3 text-primary" />
        <span>
          Fail-closed policy active: proposals are advisory; human sign-off
          remains mandatory.
        </span>
      </footer>
    </section>
  )
}
