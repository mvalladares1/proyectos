import * as React from 'react'
import { cn, formatNumber } from '@/lib/utils'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

export interface HeatmapCell {
  row: string
  col: string
  value: number
}

interface HeatmapProps {
  data: HeatmapCell[]
  rows: string[]
  cols: string[]
  /** If specified, use these min/max for color scale; otherwise inferred from data */
  minValue?: number
  maxValue?: number
  colorScheme?: 'blue' | 'green' | 'red' | 'diverging'
  formatValue?: (v: number) => string
  onCellClick?: (cell: HeatmapCell) => void
  className?: string
  rowLabel?: string
}

function cellColor(
  value: number,
  min: number,
  max: number,
  scheme: HeatmapProps['colorScheme'] = 'blue',
): string {
  if (max === min) return 'hsl(var(--muted))'
  const ratio = Math.max(0, Math.min(1, (value - min) / (max - min)))

  if (scheme === 'blue') {
    const l = Math.round(65 - ratio * 45) // 65% → 20%
    return `hsl(217 91% ${l}%)`
  }
  if (scheme === 'green') {
    const l = Math.round(65 - ratio * 45)
    return `hsl(142 72% ${l}%)`
  }
  if (scheme === 'red') {
    const l = Math.round(65 - ratio * 45)
    return `hsl(0 84% ${l}%)`
  }
  // diverging: green → neutral → red
  if (ratio < 0.5) {
    const r = (ratio / 0.5)
    return `hsl(142 ${Math.round(72 - r * 50)}% ${Math.round(45 + r * 20)}%)`
  }
  const r = (ratio - 0.5) / 0.5
  return `hsl(0 ${Math.round(20 + r * 64)}% ${Math.round(65 - r * 20)}%)`
}

function textColor(bgHsl: string): string {
  // Simple heuristic: dark text on light backgrounds
  const match = bgHsl.match(/(\d+)%\)$/)
  if (match && Number(match[1]) > 50) return 'text-gray-900'
  return 'text-white'
}

export function Heatmap({
  data,
  rows,
  cols,
  minValue,
  maxValue,
  colorScheme = 'blue',
  formatValue = (v) => formatNumber(v, 0),
  onCellClick,
  className,
  rowLabel = '',
}: HeatmapProps) {
  const index = React.useMemo(() => {
    const map = new Map<string, number>()
    for (const cell of data) {
      map.set(`${cell.row}|||${cell.col}`, cell.value)
    }
    return map
  }, [data])

  const values = data.map((c) => c.value)
  const min = minValue ?? Math.min(...values, 0)
  const max = maxValue ?? Math.max(...values, 1)

  const getCell = (row: string, col: string): HeatmapCell | null => {
    const value = index.get(`${row}|||${col}`)
    if (value === undefined) return null
    return { row, col, value }
  }

  return (
    <TooltipProvider delayDuration={100}>
      <div className={cn('overflow-x-auto', className)}>
        <table className="min-w-full text-xs border-collapse">
          <thead>
            <tr>
              <th className="sticky left-0 z-10 bg-background px-3 py-2 text-left text-xs font-medium text-muted-foreground w-32 min-w-[8rem]">
                {rowLabel}
              </th>
              {cols.map((col) => (
                <th
                  key={col}
                  className="px-1 py-2 text-center font-medium text-muted-foreground whitespace-nowrap min-w-[3rem]"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row} className="hover:bg-muted/10">
                <td className="sticky left-0 z-10 bg-background px-3 py-1 font-medium text-foreground truncate max-w-[8rem]">
                  {row}
                </td>
                {cols.map((col) => {
                  const cell = getCell(row, col)
                  if (!cell) {
                    return (
                      <td key={col} className="px-1 py-1 text-center">
                        <div className="h-8 w-full rounded bg-muted/20" />
                      </td>
                    )
                  }
                  const bg = cellColor(cell.value, min, max, colorScheme)
                  const tc = textColor(bg)
                  return (
                    <td key={col} className="px-1 py-1">
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <div
                            className={cn(
                              'flex h-8 min-w-[3rem] items-center justify-center rounded text-xs font-medium transition-opacity hover:opacity-80',
                              tc,
                              onCellClick && 'cursor-pointer',
                            )}
                            style={{ backgroundColor: bg }}
                            onClick={() => onCellClick?.(cell)}
                          >
                            {formatValue(cell.value)}
                          </div>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="font-semibold">{row} · {col}</p>
                          <p>{formatValue(cell.value)}</p>
                        </TooltipContent>
                      </Tooltip>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
        {/* Legend */}
        <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
          <span>{formatValue(min)}</span>
          <div
            className="h-2 flex-1 rounded"
            style={{
              background: `linear-gradient(to right, ${cellColor(min, min, max, colorScheme)}, ${cellColor(max, min, max, colorScheme)})`,
            }}
          />
          <span>{formatValue(max)}</span>
        </div>
      </div>
    </TooltipProvider>
  )
}
