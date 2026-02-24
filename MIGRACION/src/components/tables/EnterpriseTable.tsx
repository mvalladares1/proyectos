import { useState, useMemo } from 'react'
import { ChevronRight, ChevronDown } from 'lucide-react'
import { cn, formatCurrency, getHeatmapColor } from '@/lib/utils'
import { MONTHS_SHORT } from '@/lib/constants'
import type { FlujoCajaRow, FlujoCajaData, HeatmapConfig } from '@/types/finanzas'

interface EnterpriseTableProps {
  data: FlujoCajaData
  heatmapConfig?: HeatmapConfig
  onCellClick?: (row: FlujoCajaRow, periodo: string, value: number) => void
  className?: string
}

// Flatten tree rows
function flattenRows(rows: FlujoCajaRow[], expanded: Set<string>): FlujoCajaRow[] {
  const result: FlujoCajaRow[] = []
  for (const row of rows) {
    result.push(row)
    if (row.children?.length && expanded.has(row.id)) {
      result.push(...flattenRows(row.children, expanded))
    }
  }
  return result
}

export function EnterpriseTable({
  data,
  heatmapConfig = { enabled: true, type: 'blue' },
  onCellClick,
  className,
}: EnterpriseTableProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  const toggleExpand = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const flatRows = useMemo(
    () => flattenRows(data.rows, expanded),
    [data.rows, expanded],
  )

  // Compute heatmap range across all values
  const allValues = useMemo(() => {
    const vals: number[] = []
    const collect = (rows: FlujoCajaRow[]) => {
      for (const row of rows) {
        vals.push(...Object.values(row.valores))
        if (row.children) collect(row.children)
      }
    }
    collect(data.rows)
    return vals
  }, [data.rows])

  const heatMin = Math.min(...allValues)
  const heatMax = Math.max(...allValues)

  const getLabelForPeriodo = (p: string) => {
    const parts = p.split('-')
    if (parts.length === 2) {
      const monthIdx = parseInt(parts[1], 10) - 1
      return `${MONTHS_SHORT[monthIdx]}\n${parts[0]}`
    }
    return p
  }

  return (
    <div className={cn('overflow-auto rounded-md border', className)}>
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="bg-muted/50 border-b">
            {/* Sticky label column */}
            <th className="sticky left-0 z-10 bg-muted/80 backdrop-blur-sm px-4 py-3 text-left font-medium text-muted-foreground min-w-[250px] border-r">
              Cuenta
            </th>
            {data.periodos.map((p) => (
              <th key={p} className="px-3 py-3 text-right font-medium text-muted-foreground whitespace-pre-line min-w-[90px]">
                {getLabelForPeriodo(p)}
              </th>
            ))}
            <th className="px-3 py-3 text-right font-medium text-muted-foreground min-w-[110px] border-l bg-muted/80">
              Total
            </th>
          </tr>
        </thead>
        <tbody>
          {flatRows.map((row) => {
            const hasChildren = (row.children?.length ?? 0) > 0
            const isExpanded = expanded.has(row.id)
            const indent = row.nivel * 16

            const rowBg =
              row.nivel === 0
                ? 'bg-muted/30 font-semibold'
                : row.nivel === 1
                ? 'bg-muted/10 font-medium'
                : ''

            return (
              <tr key={row.id} className={cn('border-b hover:bg-muted/20 transition-colors group', rowBg)}>
                {/* Sticky label */}
                <td
                  className={cn(
                    'sticky left-0 z-10 border-r px-4 py-2.5 backdrop-blur-sm',
                    row.nivel === 0 ? 'bg-muted/50' : row.nivel === 1 ? 'bg-muted/20' : 'bg-background/90',
                  )}
                >
                  <div className="flex items-center gap-1" style={{ paddingLeft: indent }}>
                    {hasChildren ? (
                      <button
                        onClick={() => toggleExpand(row.id)}
                        className="rounded p-0.5 hover:bg-muted text-muted-foreground"
                      >
                        {isExpanded ? (
                          <ChevronDown className="h-3.5 w-3.5" />
                        ) : (
                          <ChevronRight className="h-3.5 w-3.5" />
                        )}
                      </button>
                    ) : (
                      <span className="w-5" />
                    )}
                    <span className={cn('truncate', row.nivel === 0 && 'text-foreground')}>
                      {row.cuenta}
                    </span>
                  </div>
                </td>

                {/* Value cells */}
                {data.periodos.map((p) => {
                  const val = row.valores[p] ?? 0
                  const bg =
                    heatmapConfig.enabled
                      ? getHeatmapColor(val, heatMin, heatMax, heatmapConfig.type)
                      : 'transparent'

                  return (
                    <td
                      key={p}
                      className="px-3 py-2.5 text-right tabular-nums cursor-pointer transition-all"
                      style={{ backgroundColor: bg }}
                      onClick={() => onCellClick?.(row, p, val)}
                      title={`${row.cuenta} / ${getLabelForPeriodo(p)}: ${formatCurrency(val)}`}
                    >
                      {val === 0 ? (
                        <span className="text-muted-foreground/40">—</span>
                      ) : (
                        <span className={cn(val < 0 && 'text-red-400')}>
                          {formatCurrency(val)}
                        </span>
                      )}
                    </td>
                  )
                })}

                {/* Total */}
                <td
                  className={cn(
                    'px-3 py-2.5 text-right tabular-nums border-l font-medium',
                    row.nivel === 0 ? 'bg-muted/30' : 'bg-muted/10',
                    row.total < 0 ? 'text-red-400' : 'text-green-400',
                  )}
                >
                  {formatCurrency(row.total)}
                </td>
              </tr>
            )
          })}
        </tbody>

        {/* Footer totals */}
        {Object.keys(data.totales).length > 0 && (
          <tfoot>
            <tr className="border-t-2 bg-muted/50 font-bold">
              <td className="sticky left-0 z-10 bg-muted/80 px-4 py-3 border-r">TOTAL</td>
              {data.periodos.map((p) => (
                <td key={p} className="px-3 py-3 text-right tabular-nums">
                  {formatCurrency(data.totales[p] ?? 0)}
                </td>
              ))}
              <td className="px-3 py-3 text-right tabular-nums border-l bg-muted/80">
                {formatCurrency(Object.values(data.totales).reduce((a, b) => a + b, 0))}
              </td>
            </tr>
          </tfoot>
        )}
      </table>
    </div>
  )
}
