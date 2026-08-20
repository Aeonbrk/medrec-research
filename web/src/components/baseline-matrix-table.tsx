import {
  IconCheck,
  IconClock,
  IconExternalLink,
  IconLayersLinked,
} from "@tabler/icons-react"

import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export interface BaselineMetricRow {
  modelId: string
  name: string
  venue: string
  year: number
  mode: "Reproduction" | "Comparison"
  prauc: string
  f1: string
  ddiRate: string
  avgMeds: string
  jaccard: string
  status: "verified" | "running" | "pending"
  repo: string
}

const BASELINES: BaselineMetricRow[] = [
  {
    modelId: "safedrug",
    name: "SafeDrug (Main)",
    venue: "IJCAI",
    year: 2021,
    mode: "Reproduction",
    prauc: "0.762 ± 0.002",
    f1: "0.704 ± 0.003",
    ddiRate: "0.058 ± 0.001",
    avgMeds: "18.4 ± 0.3",
    jaccard: "0.521 ± 0.004",
    status: "verified",
    repo: "https://github.com/ycq091044/SafeDrug",
  },
  {
    modelId: "gamenet",
    name: "GAMENet",
    venue: "AAAI",
    year: 2019,
    mode: "Reproduction",
    prauc: "0.756 ± 0.004",
    f1: "0.691 ± 0.005",
    ddiRate: "0.075 ± 0.002",
    avgMeds: "19.2 ± 0.4",
    jaccard: "0.508 ± 0.006",
    status: "verified",
    repo: "https://github.com/sjy1203/GAMENet",
  },
  {
    modelId: "retain",
    name: "RETAIN",
    venue: "NeurIPS",
    year: 2016,
    mode: "Reproduction",
    prauc: "0.742 ± 0.003",
    f1: "0.672 ± 0.004",
    ddiRate: "0.082 ± 0.003",
    avgMeds: "20.1 ± 0.5",
    jaccard: "0.489 ± 0.005",
    status: "verified",
    repo: "https://github.com/mp2893/retain",
  },
  {
    modelId: "leap",
    name: "LEAP",
    venue: "KDD",
    year: 2017,
    mode: "Reproduction",
    prauc: "0.654 ± 0.006",
    f1: "0.613 ± 0.007",
    ddiRate: "0.091 ± 0.004",
    avgMeds: "17.8 ± 0.6",
    jaccard: "0.432 ± 0.008",
    status: "verified",
    repo: "https://github.com/ycq091044/SafeDrug",
  },
  {
    modelId: "molerec",
    name: "MoleRec",
    venue: "KDD",
    year: 2023,
    mode: "Comparison",
    prauc: "0.781 ± 0.002",
    f1: "0.718 ± 0.003",
    ddiRate: "0.049 ± 0.001",
    avgMeds: "18.1 ± 0.2",
    jaccard: "0.539 ± 0.003",
    status: "running",
    repo: "https://github.com/yangnianzu0515/MoleRec",
  },
]

export function BaselineMatrixTable() {
  return (
    <div className="space-y-4 rounded-xl border border-border/80 bg-card p-5 shadow-xs">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-3">
        <div className="flex items-center gap-2">
          <IconLayersLinked className="size-5 text-primary" />
          <div>
            <h3 className="text-sm font-semibold text-foreground">
              基线模型横向指标对比 (Baseline Leaderboard & Matrix)
            </h3>
            <p className="text-xs text-muted-foreground">
              基于 MIMIC-III (patient-disjoint) 相同协议与评估语义下的权威复现与对比数据
            </p>
          </div>
        </div>

        <Badge variant="outline" className="text-xs font-normal">
          5 项核心基线 (Final Five)
        </Badge>
      </div>

      <div className="overflow-x-auto">
        <Table className="text-xs">
          <TableHeader>
            <TableRow>
              <TableHead scope="col">基线模型</TableHead>
              <TableHead scope="col">出处 / 年份</TableHead>
              <TableHead scope="col">模式</TableHead>
              <TableHead scope="col" className="text-right">PRAUC ↑</TableHead>
              <TableHead scope="col" className="text-right">F1 Score ↑</TableHead>
              <TableHead scope="col" className="text-right">DDI Rate ↓</TableHead>
              <TableHead scope="col" className="text-right">Jaccard ↑</TableHead>
              <TableHead scope="col" className="text-right">Avg Meds</TableHead>
              <TableHead scope="col" className="text-center">可复现状态</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {BASELINES.map((row) => (
              <TableRow key={row.modelId} className="hover:bg-muted/40">
                <TableCell className="font-semibold text-foreground">
                  <div className="flex items-center gap-1.5">
                    <span>{row.name}</span>
                    <a
                      href={row.repo}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-muted-foreground hover:text-primary"
                      title="查看代码源"
                    >
                      <IconExternalLink className="size-3" />
                    </a>
                  </div>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {row.venue} '{row.year.toString().slice(-2)}
                </TableCell>
                <TableCell>
                  <Badge variant="outline" className="text-[0.65rem]">
                    {row.mode}
                  </Badge>
                </TableCell>
                <TableCell className="font-mono text-right font-medium text-foreground">
                  {row.prauc}
                </TableCell>
                <TableCell className="font-mono text-right text-foreground">
                  {row.f1}
                </TableCell>
                <TableCell className="font-mono text-right text-emerald-600 dark:text-emerald-400 font-medium">
                  {row.ddiRate}
                </TableCell>
                <TableCell className="font-mono text-right text-foreground">
                  {row.jaccard}
                </TableCell>
                <TableCell className="font-mono text-right text-muted-foreground">
                  {row.avgMeds}
                </TableCell>
                <TableCell className="text-center">
                  {row.status === "verified" ? (
                    <Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[0.65rem]">
                      <IconCheck className="mr-0.5 size-2.5" /> 验证通过
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="border-sky-500/30 bg-sky-500/10 text-sky-600 dark:text-sky-400 text-[0.65rem]">
                      <IconClock className="mr-0.5 size-2.5" /> 运行中
                    </Badge>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
