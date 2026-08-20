import type { Section } from "@/lib/domain"

export function sectionTitle(section: Section): string {
  return {
    pending: "待决工作台",
    overview: "研究总览",
    candidates: "候选基线",
    lineage: "共享谱系",
    hitl: "HITL 循环",
    authority: "权威摘要",
  }[section]
}
