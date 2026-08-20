import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Separator } from "@/components/ui/separator"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { sectionTitle } from "@/lib/navigation"
import type { HarnessState, Section } from "@/lib/domain"

export function AppHeader({
  harness,
  onSectionChange,
  section,
}: {
  harness: HarnessState | null
  onSectionChange: (section: Section) => void
  section: Section
}) {
  return (
    <header className="sticky top-0 z-10 flex min-h-14 items-center justify-between gap-2 border-b bg-background/80 px-3 backdrop-blur-md lg:px-5">
      <div className="flex min-w-0 items-center gap-2">
        <SidebarTrigger aria-label="切换导航栏" className="-ml-1" />
        <Separator orientation="vertical" className="mr-2 h-4" />
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem className="hidden sm:inline-flex">
              <BreadcrumbLink onClick={() => onSectionChange("overview")}>
                MedRec Research
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator className="hidden sm:inline-flex" />
            <BreadcrumbItem className="hidden md:inline-flex">
              <span>HITL Control</span>
            </BreadcrumbItem>
            <BreadcrumbSeparator className="hidden md:inline-flex" />
            <BreadcrumbItem>
              <BreadcrumbPage>
                <h1
                  id="page-title"
                  className="inline text-sm font-semibold text-foreground"
                >
                  {sectionTitle(section)}
                </h1>
              </BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </div>
      <div className="flex items-center gap-2">
        {harness ? (
          <div className="flex items-center gap-1.5 font-mono text-xs text-muted-foreground">
            <span
              className={`size-2 rounded-full ${harness.status.condition === "current" ? "bg-emerald-500" : "bg-amber-500"}`}
              aria-hidden="true"
            />
            <span className="hidden sm:inline">
              {harness.status.condition}
            </span>
            <span className="hidden text-muted-foreground/60 md:inline">·</span>
            <span className="hidden md:inline">
              v{harness.schema_version}
            </span>
          </div>
        ) : null}
      </div>
    </header>
  )
}
