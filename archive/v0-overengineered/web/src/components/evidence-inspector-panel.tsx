import { IconDatabase } from "@tabler/icons-react"

import { EvidenceDisclosure } from "@/components/evidence-disclosure"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  aggregateTableRows,
  type DecisionPacketRecord,
  type Evidence,
  type PublicJson,
} from "@/lib/domain"

function displayPublicJson(value: PublicJson) {
  return typeof value === "string" ? value : JSON.stringify(value)
}

function Definition({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 border-b py-2 last:border-b-0">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1 font-mono text-xs break-all">{value}</dd>
    </div>
  )
}

export function EvidenceInspectorPanel({
  evidence,
  packet,
  phase,
}: {
  evidence: Evidence[]
  packet?: DecisionPacketRecord
  phase: "loading" | "ready" | "unavailable" | "malformed" | "transport"
}) {
  const rawRows = packet ? aggregateTableRows(packet.raw_aggregate_table) : null
  const rawColumns = rawRows
    ? [...new Set(rawRows.flatMap((row) => Object.keys(row)))]
    : []

  return (
    <section aria-labelledby="packet-artifacts" className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 id="packet-artifacts" className="text-sm font-semibold">
          原始工件与依据
        </h3>
        {evidence.length > 0 && <EvidenceDisclosure evidence={evidence} />}
      </div>

      {packet && (
        <dl className="border-y">
          <Definition
            label="outcomes"
            value={JSON.stringify(packet.outcomes)}
          />
          <Definition
            label="uncertainty"
            value={JSON.stringify(packet.uncertainty)}
          />
          <Definition
            label="validity"
            value={`${packet.validity} · ${packet.go_eligible ? "go eligible" : "not go eligible"}`}
          />
        </dl>
      )}

      {phase !== "ready" ? (
        <Alert variant="destructive">
          <IconDatabase aria-hidden="true" />
          <AlertTitle>Decision Packet 依据不可用</AlertTitle>
          <AlertDescription>
            服务端没有返回当前 packet projection。
          </AlertDescription>
        </Alert>
      ) : rawRows ? (
        <div
          className="overflow-x-auto border-y focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          role="region"
          aria-label="Decision Packet 公开聚合数据表"
          tabIndex={0}
        >
          <Table>
            <caption className="px-2 py-2 text-left text-xs text-muted-foreground">
              服务端 receipt 提供的公开聚合数据表
            </caption>
            <TableHeader>
              <TableRow>
                {rawColumns.map((column) => (
                  <TableHead key={column}>{column}</TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {rawRows.map((row) => {
                const rowKey =
                  typeof row.id === "string" || typeof row.id === "number"
                    ? String(row.id)
                    : JSON.stringify(row)
                return (
                  <TableRow key={rowKey}>
                    {rawColumns.map((column) => (
                      <TableCell key={column} className="whitespace-normal">
                        {column in row ? displayPublicJson(row[column]) : "—"}
                      </TableCell>
                    ))}
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      ) : (
        <Alert>
          <IconDatabase aria-hidden="true" />
          <AlertTitle>聚合 outcomes 原始数据表未公开</AlertTitle>
          <AlertDescription>
            当前 API 返回 outcomes 与
            uncertainty，但没有曲线或对应原始聚合数据表；
            不能据此推断未公开的曲线结论。
          </AlertDescription>
        </Alert>
      )}
    </section>
  )
}
