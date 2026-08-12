import * as React from "react"
import { IconAlertTriangle, IconRefresh } from "@tabler/icons-react"

import { AppSidebar } from "@/components/app-sidebar"
import { ConsoleToolbar, sectionTitle } from "@/components/console-toolbar"
import { ResearchConsole } from "@/components/research-console"
import { ThemeProvider } from "@/components/theme-provider"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { Skeleton } from "@/components/ui/skeleton"
import { TooltipProvider } from "@/components/ui/tooltip"
import { useViewState } from "@/hooks/use-view-state"
import { fetchJson, TransportError } from "@/lib/api"
import {
  validateActionDecision,
  validateHarnessState,
  validateHitlControl,
  validateResearchLoop,
  type ActionDecision,
  type HarnessState,
  type HitlControl,
  type ResearchLoop,
} from "@/lib/domain"

type LoadFailure = "malformed" | "transport"
export type LoopState =
  | { phase: "loading" }
  | { phase: "ready"; value: ResearchLoop }
  | { phase: "unavailable" | LoadFailure }

export type ActionState =
  | { phase: "idle" }
  | { phase: "submitting" }
  | { phase: "allowed" | "blocked"; decision: ActionDecision }
  | { phase: LoadFailure }

export type HitlControlState =
  | { phase: "loading" }
  | { phase: "ready"; value: HitlControl }
  | { phase: "submitting" | "rejected" | LoadFailure }

function failureKind(error: unknown): LoadFailure {
  return error instanceof TransportError || error instanceof TypeError
    ? "transport"
    : "malformed"
}

function FailurePanel({
  kind,
  retry,
}: {
  kind: LoadFailure
  retry: () => void
}) {
  const malformed = kind === "malformed"
  return (
    <div className="grid flex-1 place-items-center p-6">
      <Alert variant="destructive" className="max-w-xl">
        <IconAlertTriangle aria-hidden="true" />
        <AlertTitle>
          {malformed ? "状态格式不可用" : "无法连接本机 harness"}
        </AlertTitle>
        <AlertDescription>
          {malformed
            ? "响应未通过既有 schema 校验。为避免错误投影，研究数据与动作请求均保持关闭。"
            : "production harness 没有返回可用状态。研究数据不会从本地样例或缓存补齐。"}
        </AlertDescription>
        <Button className="mt-3 w-fit" variant="outline" onClick={retry}>
          <IconRefresh data-icon="inline-start" />
          重新载入
        </Button>
      </Alert>
    </div>
  )
}

export function App() {
  const [view, updateView] = useViewState()
  const [harness, setHarness] = React.useState<HarnessState | null>(null)
  const [failure, setFailure] = React.useState<LoadFailure | null>(null)
  const [loop, setLoop] = React.useState<LoopState>({ phase: "loading" })
  const [hitl, setHitl] = React.useState<HitlControlState>({ phase: "loading" })
  const [action, setAction] = React.useState<ActionState>({ phase: "idle" })
  const inFlight = React.useRef(false)

  const load = React.useCallback(async () => {
    setHarness(null)
    setFailure(null)
    setLoop({ phase: "loading" })
    setHitl({ phase: "loading" })
    setAction({ phase: "idle" })
    inFlight.current = false
    try {
      const nextHarness = validateHarnessState(
        await fetchJson("/api/harness-state")
      )
      setHarness(nextHarness)
    } catch (error) {
      setFailure(failureKind(error))
      return
    }

    try {
      const nextLoop = validateResearchLoop(
        await fetchJson("/api/research-loop")
      )
      setLoop({ phase: "ready", value: nextLoop })
    } catch (error) {
      setLoop({
        phase:
          error instanceof TransportError && error.status === 503
            ? "unavailable"
            : failureKind(error),
      })
    }
    try {
      setHitl({
        phase: "ready",
        value: validateHitlControl(await fetchJson("/api/hitl-control")),
      })
    } catch (error) {
      setHitl({ phase: failureKind(error) })
    }
  }, [])

  React.useEffect(() => {
    void load()
  }, [load])

  const requestAction = React.useCallback(async () => {
    const context = harness?.action_context
    if (!context?.enabled || inFlight.current) return
    inFlight.current = true
    setAction({ phase: "submitting" })
    try {
      const decision = validateActionDecision(
        await fetchJson("/api/action-requests", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            kind: "action_request_input",
            request_id: context.request_id,
            schema_version: 1,
          }),
        })
      )
      setAction({ phase: decision.status, decision })
    } catch (error) {
      setAction({ phase: failureKind(error) })
    }
  }, [harness])

  const submitHitl = React.useCallback(
    async (path: "/api/h1" | "/api/h2", payload: Record<string, unknown>) => {
      setHitl({ phase: "submitting" })
      try {
        await fetchJson(path, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        })
        await load()
      } catch (error) {
        setHitl({
          phase:
            error instanceof TransportError && error.status === 409
              ? "rejected"
              : failureKind(error),
        })
      }
    },
    [load]
  )

  return (
    <ThemeProvider theme={view.theme}>
      <TooltipProvider delayDuration={180}>
        <SidebarProvider>
          <a className="skip-link" href="#main-content">
            跳到主要内容
          </a>
          <AppSidebar
            section={view.section}
            onSection={(section) => updateView({ section })}
          />
          <div className="relative flex w-full min-w-0 flex-1 flex-col overflow-hidden bg-background">
            <header className="flex min-h-14 items-center gap-2 border-b bg-background px-3 lg:px-5">
              <SidebarTrigger aria-label="切换导航栏" />
              <div className="h-5 w-px bg-border" aria-hidden="true" />
              <div className="min-w-0 flex-1">
                <h1 className="truncate text-sm font-semibold" id="page-title">
                  {sectionTitle(view.section)}
                </h1>
                <p className="truncate text-xs text-muted-foreground">
                  {harness?.status.project_id ?? "正在读取受控研究状态"}
                </p>
              </div>
              {harness && (
                <span className="font-mono text-xs text-muted-foreground">
                  schema v{harness.schema_version}
                </span>
              )}
            </header>
            <ConsoleToolbar view={view} update={updateView} />
            {failure ? (
              <FailurePanel kind={failure} retry={() => void load()} />
            ) : harness ? (
              <ResearchConsole
                harness={harness}
                loop={loop}
                hitl={hitl}
                view={view}
                action={action}
                onRequest={() => void requestAction()}
                onRetry={() => void load()}
                onHitlDecision={(path, payload) =>
                  void submitHitl(path, payload)
                }
              />
            ) : (
              <main
                id="main-content"
                aria-busy="true"
                aria-label="正在载入研究控制台"
                className="space-y-4 p-4 lg:p-6"
              >
                <Skeleton className="h-24 w-full" />
                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                  {[0, 1, 2, 3].map((item) => (
                    <Skeleton key={item} className="h-28" />
                  ))}
                </div>
                <Skeleton className="h-64 w-full" />
              </main>
            )}
          </div>
        </SidebarProvider>
      </TooltipProvider>
    </ThemeProvider>
  )
}

export default App
