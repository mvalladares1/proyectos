import * as React from 'react'
import { CalendarIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { cn } from '@/lib/utils'

// Lightweight popover wrapper – full calendar via react-day-picker if needed
export interface DateRange {
  from: Date | undefined
  to: Date | undefined
}

interface DateRangePickerProps {
  value: DateRange
  onChange: (range: DateRange) => void
  className?: string
  placeholder?: string
}

function formatRange({ from, to }: DateRange): string {
  const fmt = (d: Date) =>
    d.toLocaleDateString('es-CL', { day: '2-digit', month: 'short', year: 'numeric' })
  if (from && to) return `${fmt(from)} – ${fmt(to)}`
  if (from) return fmt(from)
  return ''
}

// Inline mini calendar
function MiniCalendar({
  month,
  year,
  selected,
  onSelect,
}: {
  month: number
  year: number
  selected: Date[]
  onSelect: (d: Date) => void
}) {
  const firstDay = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const cells: (number | null)[] = [
    ...Array(firstDay).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ]
  const isSelected = (d: number) =>
    selected.some(
      (s) => s.getFullYear() === year && s.getMonth() === month && s.getDate() === d,
    )
  const isInRange = (d: number) => {
    if (selected.length < 2) return false
    const dt = new Date(year, month, d)
    return dt > selected[0] && dt < selected[1]
  }
  return (
    <div className="w-56 select-none text-sm">
      <div className="mb-2 flex justify-between text-xs text-muted-foreground font-medium px-1">
        {['Do', 'Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sa'].map((d) => (
          <span key={d} className="w-7 text-center">{d}</span>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-y-1">
        {cells.map((d, i) =>
          d === null ? (
            <span key={i} />
          ) : (
            <button
              key={i}
              onClick={() => onSelect(new Date(year, month, d))}
              className={cn(
                'h-7 w-7 rounded text-xs transition-colors hover:bg-primary/20',
                isSelected(d) && 'bg-primary text-primary-foreground',
                isInRange(d) && 'bg-primary/10',
              )}
            >
              {d}
            </button>
          ),
        )}
      </div>
    </div>
  )
}

export function DateRangePicker({
  value,
  onChange,
  className,
  placeholder = 'Seleccionar rango',
}: DateRangePickerProps) {
  const [open, setOpen] = React.useState(false)
  const today = new Date()
  const [viewMonth, setViewMonth] = React.useState(today.getMonth())
  const [viewYear, setViewYear] = React.useState(today.getFullYear())
  const [tempFrom, setTempFrom] = React.useState<Date | undefined>(value.from)
  const [tempTo, setTempTo] = React.useState<Date | undefined>(value.to)
  const [step, setStep] = React.useState<'from' | 'to'>('from')

  const selected = [tempFrom, tempTo].filter(Boolean) as Date[]

  const handleSelect = (d: Date) => {
    if (step === 'from') {
      setTempFrom(d)
      setTempTo(undefined)
      setStep('to')
    } else {
      if (tempFrom && d < tempFrom) {
        setTempTo(tempFrom)
        setTempFrom(d)
      } else {
        setTempTo(d)
      }
      setStep('from')
    }
  }

  const handleApply = () => {
    onChange({ from: tempFrom, to: tempTo })
    setOpen(false)
  }

  const handleClear = () => {
    setTempFrom(undefined)
    setTempTo(undefined)
    onChange({ from: undefined, to: undefined })
    setOpen(false)
  }

  const prevMonth = () => {
    if (viewMonth === 0) { setViewMonth(11); setViewYear(y => y - 1) }
    else setViewMonth(m => m - 1)
  }
  const nextMonth = () => {
    if (viewMonth === 11) { setViewMonth(0); setViewYear(y => y + 1) }
    else setViewMonth(m => m + 1)
  }

  const MONTHS_ES = [
    'Enero','Febrero','Marzo','Abril','Mayo','Junio',
    'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre',
  ]

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className={cn('justify-start gap-2 text-sm font-normal', !value.from && 'text-muted-foreground', className)}
        >
          <CalendarIcon className="h-4 w-4" />
          {value.from ? formatRange(value) : placeholder}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-3" align="start">
        <div className="flex items-center justify-between mb-3">
          <button onClick={prevMonth} className="rounded p-1 hover:bg-muted">&lt;</button>
          <span className="text-sm font-medium">{MONTHS_ES[viewMonth]} {viewYear}</span>
          <button onClick={nextMonth} className="rounded p-1 hover:bg-muted">&gt;</button>
        </div>
        <MiniCalendar
          month={viewMonth}
          year={viewYear}
          selected={selected}
          onSelect={handleSelect}
        />
        <p className="mt-2 text-xs text-muted-foreground">
          {step === 'from' ? 'Selecciona fecha inicio' : 'Selecciona fecha fin'}
        </p>
        <div className="mt-3 flex gap-2">
          <Button size="sm" onClick={handleApply} disabled={!tempFrom}>Aplicar</Button>
          <Button size="sm" variant="ghost" onClick={handleClear}>Limpiar</Button>
        </div>
      </PopoverContent>
    </Popover>
  )
}
