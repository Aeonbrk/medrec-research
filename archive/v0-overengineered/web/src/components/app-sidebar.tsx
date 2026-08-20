import {
  IconCpu,
  IconFingerprint,
  IconGitBranch,
  IconHelp,
  IconLayoutDashboard,
  IconListCheck,
  IconLock,
  IconPill,
  IconShieldLock,
  IconStack2,
  IconUserCheck,
} from "@tabler/icons-react"

import { Badge } from "@/components/ui/badge"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  useSidebar,
} from "@/components/ui/sidebar"
import type { HarnessState, Section } from "@/lib/domain"

const mainNavigation = [
  { id: "pending", label: "待决工作台", icon: IconListCheck },
  { id: "overview", label: "总览", icon: IconLayoutDashboard },
  { id: "candidates", label: "候选基线", icon: IconStack2 },
  { id: "lineage", label: "共享谱系", icon: IconGitBranch },
  { id: "hitl", label: "HITL 循环", icon: IconUserCheck },
  { id: "authority", label: "权威摘要", icon: IconFingerprint },
] satisfies Array<{
  id: Section
  label: string
  icon: typeof IconLayoutDashboard
}>

const baselineLanes = [
  { id: "safedrug", name: "SafeDrug-main", badge: "Core" },
  { id: "gamenet", name: "GAMENet", badge: "Repro" },
  { id: "retain", name: "RETAIN", badge: "Repro" },
  { id: "molerec", name: "MoleRec", badge: "Stage" },
  { id: "leap", name: "LEAP-SafeDrug", badge: "Repro" },
]

const secondaryItems = [
  {
    title: "Fail-Closed 科学约束",
    icon: IconShieldLock,
    hint: "私有数据不入 Git",
  },
  {
    title: "319 算力执行契约",
    icon: IconCpu,
    hint: "硬件探针与隔离环境",
  },
  {
    title: "第一性原理与协议",
    icon: IconHelp,
    hint: "UNIFIED_RESEARCH_PROTOCOL",
  },
]

function NavMain({
  section,
  onSection,
}: {
  section: Section
  onSection: (section: Section) => void
}) {
  const { setOpenMobile } = useSidebar()
  return (
    <SidebarGroup>
      <SidebarGroupLabel className="text-[0.68rem] font-medium tracking-wider text-muted-foreground uppercase">
        科研控制台
      </SidebarGroupLabel>
      <SidebarGroupContent>
        <SidebarMenu>
          {mainNavigation.map(({ id, label, icon: Icon }) => (
            <SidebarMenuItem key={id}>
              <SidebarMenuButton
                isActive={section === id}
                tooltip={label}
                className="transition-colors hover:bg-sidebar-accent/80 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground"
                onClick={() => {
                  onSection(id)
                  setOpenMobile(false)
                }}
              >
                <Icon aria-hidden="true" className="size-4 shrink-0" />
                <span>{label}</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  )
}

function NavLanes({ onSection }: { onSection: (section: Section) => void }) {
  const { setOpenMobile } = useSidebar()
  return (
    <SidebarGroup>
      <SidebarGroupLabel className="text-[0.68rem] font-medium tracking-wider text-muted-foreground uppercase">
        基线轨道 (Final Five)
      </SidebarGroupLabel>
      <SidebarGroupContent>
        <SidebarMenu>
          {baselineLanes.map((lane) => (
            <SidebarMenuItem key={lane.id}>
              <SidebarMenuButton
                tooltip={`${lane.name} (${lane.badge})`}
                className="text-xs text-sidebar-foreground/80 hover:bg-sidebar-accent/60"
                onClick={() => {
                  onSection("candidates")
                  setOpenMobile(false)
                }}
              >
                <IconPill className="size-3.5 shrink-0 text-muted-foreground" />
                <span className="truncate">{lane.name}</span>
                <span className="ml-auto font-mono text-[0.65rem] text-muted-foreground">
                  {lane.badge}
                </span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  )
}

function NavSecondary() {
  return (
    <SidebarGroup className="mt-auto">
      <SidebarGroupLabel className="text-[0.68rem] font-medium tracking-wider text-muted-foreground uppercase">
        依据与安全
      </SidebarGroupLabel>
      <SidebarGroupContent>
        <SidebarMenu>
          {secondaryItems.map((item) => (
            <SidebarMenuItem key={item.title}>
              <SidebarMenuButton
                tooltip={`${item.title} · ${item.hint}`}
                className="text-xs text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground"
              >
                <item.icon className="size-3.5 shrink-0 text-muted-foreground" />
                <span className="truncate">{item.title}</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  )
}

function NavHarness({ harness }: { harness?: HarnessState }) {
  const condition = harness?.status.condition ?? "current"
  const projectId = harness?.status.project_id ?? "medrec-research"
  const snapshotSha = harness?.status.snapshot_sha256
    ? `${harness.status.snapshot_sha256.slice(0, 8)}...`
    : "local"

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <div className="flex flex-col gap-2 rounded-lg border border-sidebar-border bg-sidebar-accent/30 p-2.5 text-sidebar-foreground group-data-[collapsible=icon]:p-1.5">
          <div className="flex items-center justify-between gap-1 group-data-[collapsible=icon]:justify-center">
            <div className="flex items-center gap-1.5 group-data-[collapsible=icon]:hidden">
              <span
                className={`size-2 rounded-full ${condition === "current" ? "bg-emerald-500" : "bg-amber-500"}`}
                aria-hidden="true"
              />
              <span className="truncate text-xs font-semibold">
                {projectId}
              </span>
            </div>
            <Badge
              variant="outline"
              className="h-5 border-sidebar-border px-1.5 font-mono text-[0.65rem] text-sidebar-foreground group-data-[collapsible=icon]:hidden"
            >
              {condition}
            </Badge>
          </div>
          <div className="flex items-center justify-between text-[0.68rem] text-muted-foreground group-data-[collapsible=icon]:hidden">
            <span className="font-mono">SHA: {snapshotSha}</span>
            <span className="flex items-center gap-0.5">
              <IconLock className="size-2.5" /> Fail-closed
            </span>
          </div>
        </div>
      </SidebarMenuItem>
    </SidebarMenu>
  )
}

export function AppSidebar({
  harness,
  onSection,
  section,
  ...props
}: {
  harness?: HarnessState
  onSection: (section: Section) => void
  section: Section
} & React.ComponentProps<typeof Sidebar>) {
  return (
    <Sidebar
      collapsible="icon"
      variant="inset"
      role="navigation"
      aria-label="研究控制台导航"
      {...props}
    >
      <SidebarHeader className="border-b border-sidebar-border/60 p-3">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              size="lg"
              className="h-auto p-1.5 hover:bg-sidebar-accent/50"
            >
              <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
                <IconShieldLock className="size-4" />
              </div>
              <div className="grid flex-1 text-left text-sm leading-tight group-data-[collapsible=icon]:hidden">
                <span className="truncate font-semibold tracking-tight text-sidebar-foreground">
                  MedRec Research
                </span>
                <span className="truncate text-[0.7rem] text-muted-foreground">
                  HITL Control Console
                </span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <NavMain section={section} onSection={onSection} />
        <NavLanes onSection={onSection} />
        <NavSecondary />
      </SidebarContent>
      <SidebarFooter className="border-t border-sidebar-border/60 p-2.5">
        <NavHarness harness={harness} />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
