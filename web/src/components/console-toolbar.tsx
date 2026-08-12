import {
  IconArrowsSort,
  IconBrightness,
  IconMoon,
  IconSearch,
  IconSun,
} from "@tabler/icons-react"

import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Button } from "@/components/ui/button"
import type { Section, ViewState } from "@/lib/domain"

const themeIcons = {
  system: IconBrightness,
  light: IconSun,
  dark: IconMoon,
}

export function ConsoleToolbar({
  view,
  update,
}: {
  view: ViewState
  update: (patch: Partial<ViewState>) => void
}) {
  const dataSection = ["candidates", "lineage", "hitl"].includes(view.section)
  const statusSection = ["candidates", "hitl"].includes(view.section)
  return (
    <section
      aria-label="研究视图工具"
      className="flex min-w-0 flex-col gap-2 border-b bg-background px-4 py-3 lg:flex-row lg:items-center lg:px-6"
    >
      <div className="flex min-w-0 flex-1 items-center gap-2">
        <InputGroup className="max-w-xl">
          <InputGroupAddon>
            <IconSearch aria-hidden="true" />
          </InputGroupAddon>
          <InputGroupInput
            aria-label="全局搜索"
            placeholder="搜索模型 ID、状态、证据或 SHA"
            value={view.query}
            onChange={(event) => update({ query: event.target.value })}
          />
        </InputGroup>
        {view.query && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => update({ query: "" })}
          >
            清除
          </Button>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {dataSection && (
          <Select
            value={view.sort}
            onValueChange={(sort) =>
              update({ sort: sort as ViewState["sort"] })
            }
          >
            <SelectTrigger aria-label="排序字段">
              <SelectValue />
            </SelectTrigger>
            <SelectContent position="popper">
              <SelectGroup>
                <SelectItem value="identity">按标识</SelectItem>
                <SelectItem value="state">按状态</SelectItem>
              </SelectGroup>
            </SelectContent>
          </Select>
        )}
        {dataSection && (
          <Button
            variant="outline"
            size="icon"
            aria-label={
              view.order === "asc"
                ? "当前升序，切换为降序"
                : "当前降序，切换为升序"
            }
            onClick={() =>
              update({ order: view.order === "asc" ? "desc" : "asc" })
            }
          >
            <IconArrowsSort aria-hidden="true" />
          </Button>
        )}
        {statusSection && (
          <Select
            value={view.status}
            onValueChange={(status) =>
              update({ status: status as ViewState["status"] })
            }
          >
            <SelectTrigger aria-label="状态筛选">
              <SelectValue />
            </SelectTrigger>
            <SelectContent position="popper">
              <SelectGroup>
                <SelectItem value="all">全部状态</SelectItem>
                <SelectItem value="pass">通过</SelectItem>
                <SelectItem value="attention">待核验</SelectItem>
                <SelectItem value="blocked">阻塞</SelectItem>
              </SelectGroup>
            </SelectContent>
          </Select>
        )}
        <ToggleGroup
          type="single"
          value={view.density}
          onValueChange={(density) =>
            density && update({ density: density as ViewState["density"] })
          }
          variant="outline"
          size="sm"
          aria-label="信息密度"
        >
          <ToggleGroupItem value="compact">紧凑</ToggleGroupItem>
          <ToggleGroupItem value="comfortable">舒适</ToggleGroupItem>
        </ToggleGroup>
        <ToggleGroup
          type="single"
          value={view.theme}
          onValueChange={(theme) =>
            theme && update({ theme: theme as ViewState["theme"] })
          }
          variant="outline"
          size="sm"
          aria-label="主题"
        >
          {(["system", "light", "dark"] as const).map((theme) => {
            const Icon = themeIcons[theme]
            const label = { system: "跟随系统", light: "浅色", dark: "深色" }[
              theme
            ]
            return (
              <ToggleGroupItem
                key={theme}
                value={theme}
                aria-label={label}
                title={label}
              >
                <Icon aria-hidden="true" />
              </ToggleGroupItem>
            )
          })}
        </ToggleGroup>
      </div>
    </section>
  )
}

export function sectionTitle(section: Section) {
  return {
    overview: "研究总览",
    candidates: "候选基线",
    lineage: "共享谱系",
    hitl: "HITL 循环",
    authority: "权威摘要",
  }[section]
}
