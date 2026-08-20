import { AppHeader } from "@/components/app-header"
import { AppSidebar } from "@/components/app-sidebar"
import { ConsoleToolbar } from "@/components/console-toolbar"
import { ResearchConsole } from "@/components/research-console"
import { ThemeProvider } from "@/components/theme-provider"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { Skeleton } from "@/components/ui/skeleton"
import { TooltipProvider } from "@/components/ui/tooltip"
import {
  useResearchSession,
  type ActionState,
  type ContractAIState,
  type ContractState,
  type ExecutionControlState,
  type ExecutionStreamState,
  type HitlControlState,
  type LoadFailure,
  type LoopState,
  type PacketState,
  type TransportControlState,
} from "@/hooks/use-research-session"
import { useViewState } from "@/hooks/use-view-state"
import { IconAlertTriangle, IconRefresh } from "@tabler/icons-react"

export type {
  ActionState,
  ContractAIState,
  ContractState,
  ExecutionControlState,
  ExecutionStreamState,
  HitlControlState,
  LoadFailure,
  LoopState,
  PacketState,
  TransportControlState,
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

function AppLoadingSkeleton() {
  return (
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
  )
}

export function App() {
  const [view, updateView] = useViewState()
  const {
    state,
    load,
    requestAction,
    submitHitl,
    requestContractAI,
    controlTransport,
  } = useResearchSession()

  const { harness, failure } = state

  return (
    <ThemeProvider theme={view.theme}>
      <TooltipProvider delay={180}>
        <SidebarProvider>
          <a className="skip-link" href="#main-content">
            跳到主要内容
          </a>
          <AppSidebar
            harness={harness ?? undefined}
            section={view.section}
            onSection={(section) => updateView({ section })}
          />
          <SidebarInset className="relative flex min-w-0 flex-1 flex-col overflow-hidden bg-background">
            <AppHeader
              harness={harness}
              section={view.section}
              onSectionChange={(section) => updateView({ section })}
            />
            <ConsoleToolbar view={view} update={updateView} />
            {failure ? (
              <FailurePanel kind={failure} retry={() => void load()} />
            ) : harness ? (
              <ResearchConsole
                harness={harness}
                loop={state.loop}
                hitl={state.hitl}
                contract={state.contract}
                packets={state.packets}
                execution={state.execution}
                executionStream={state.executionStream}
                transportControl={state.transportControl}
                view={view}
                action={state.action}
                onRequest={() => void requestAction()}
                onRetry={() => void load()}
                onSelect={(selected) => updateView({ selected })}
                onHitlDecision={(path, payload) =>
                  void submitHitl(path, payload)
                }
                contractAI={state.contractAI}
                onContractAI={(operation) => void requestContractAI(operation)}
                onTransportControl={(requestId, operation) =>
                  void controlTransport(requestId, operation)
                }
              />
            ) : (
              <AppLoadingSkeleton />
            )}
          </SidebarInset>
        </SidebarProvider>
      </TooltipProvider>
    </ThemeProvider>
  )
}

export default App
