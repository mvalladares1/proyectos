import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { X } from 'lucide-react'
import { MONTHS_ES, YEARS_RANGE, CURRENT_YEAR } from '@/lib/constants'
import { cn } from '@/lib/utils'

interface FilterBarProps {
  year?: number
  onYearChange?: (year: number) => void
  months?: number[]
  onMonthsChange?: (months: number[]) => void
  showMonths?: boolean
  showYear?: boolean
  extra?: React.ReactNode
  className?: string
}

export function FilterBar({
  year = CURRENT_YEAR,
  onYearChange,
  months = [],
  onMonthsChange,
  showMonths = true,
  showYear = true,
  extra,
  className,
}: FilterBarProps) {
  const toggleMonth = (m: number) => {
    if (!onMonthsChange) return
    if (months.includes(m)) {
      onMonthsChange(months.filter((x) => x !== m))
    } else {
      onMonthsChange([...months, m].sort((a, b) => a - b))
    }
  }

  const clearMonths = () => onMonthsChange?.([])

  return (
    <div className={cn('flex flex-wrap items-center gap-3', className)}>
      {showYear && (
        <Select value={String(year)} onValueChange={(v) => onYearChange?.(Number(v))}>
          <SelectTrigger className="h-9 w-28">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {YEARS_RANGE.map((y) => (
              <SelectItem key={y} value={String(y)}>{y}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}

      {showMonths && (
        <div className="flex flex-wrap items-center gap-1.5">
          {MONTHS_ES.map((name, i) => {
            const m = i + 1
            const active = months.includes(m)
            return (
              <button
                key={m}
                onClick={() => toggleMonth(m)}
                className={cn(
                  'h-7 rounded px-2 text-xs font-medium transition-colors border',
                  active
                    ? 'bg-primary border-primary text-primary-foreground'
                    : 'bg-background border-border text-muted-foreground hover:border-primary hover:text-foreground',
                )}
              >
                {name.slice(0, 3)}
              </button>
            )
          })}
          {months.length > 0 && (
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={clearMonths}>
              <X className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
      )}

      {extra}
    </div>
  )
}
