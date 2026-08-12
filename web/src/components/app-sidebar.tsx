import { Badge } from "@/components/ui/badge"
import {
  IconFingerprint,
  IconGitBranch,
  IconLayoutDashboard,
  IconStack2,
  IconUserCheck,
} from "@tabler/icons-react"

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
import type { Section } from "@/lib/domain"

const navigation = [
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

function Navigation({
  section,
  onSection,
}: {
  section: Section
  onSection: (section: Section) => void
}) {
  const { setOpenMobile } = useSidebar()
  return (
    <SidebarGroup>
      <SidebarGroupLabel>研究控制台</SidebarGroupLabel>
      <SidebarGroupContent>
        <SidebarMenu>
          {navigation.map(({ id, label, icon: Icon }) => (
            <SidebarMenuItem key={id}>
              <SidebarMenuButton
                isActive={section === id}
                tooltip={label}
                onClick={() => {
                  onSection(id)
                  setOpenMobile(false)
                }}
              >
                <Icon aria-hidden="true" />
                <span>{label}</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  )
}

export function AppSidebar({
  section,
  onSection,
}: {
  section: Section
  onSection: (section: Section) => void
}) {
  return (
    <Sidebar collapsible="icon" role="navigation" aria-label="研究控制台导航">
      <SidebarHeader className="border-b border-sidebar-border p-3">
        <div className="flex min-h-10 items-center gap-2 group-data-[collapsible=icon]:justify-center">
          <div className="grid size-8 shrink-0 place-items-center rounded-lg bg-sidebar-primary font-mono text-xs font-semibold text-sidebar-primary-foreground">
            MR
          </div>
          <div className="min-w-0 group-data-[collapsible=icon]:hidden">
            <p className="truncate text-sm font-semibold">MedRec Research</p>
            <p className="truncate text-xs text-sidebar-foreground/65">
              本机受控 HITL 投影
            </p>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <Navigation section={section} onSection={onSection} />
      </SidebarContent>
      <SidebarFooter className="border-t border-sidebar-border p-3 group-data-[collapsible=icon]:hidden">
        <Badge
          variant="outline"
          className="border-sidebar-border text-sidebar-foreground group-data-[collapsible=icon]:hidden"
        >
          Python production
        </Badge>
        <p className="text-xs text-sidebar-foreground/65">
          H1/H2 有界写入，无直接执行面
        </p>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
