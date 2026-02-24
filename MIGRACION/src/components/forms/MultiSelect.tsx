import * as React from 'react'
import { Check, ChevronsUpDown, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

export interface MultiSelectOption {
  label: string
  value: string
}

interface MultiSelectProps {
  options: MultiSelectOption[]
  selected: string[]
  onChange: (values: string[]) => void
  placeholder?: string
  className?: string
  maxDisplay?: number
}

export function MultiSelect({
  options,
  selected,
  onChange,
  placeholder = 'Seleccionar...',
  className,
  maxDisplay = 3,
}: MultiSelectProps) {
  const [open, setOpen] = React.useState(false)
  const [search, setSearch] = React.useState('')

  const filtered = options.filter((o) =>
    o.label.toLowerCase().includes(search.toLowerCase()),
  )

  const toggle = (value: string) => {
    onChange(
      selected.includes(value)
        ? selected.filter((v) => v !== value)
        : [...selected, value],
    )
  }

  const removeOne = (e: React.MouseEvent, value: string) => {
    e.stopPropagation()
    onChange(selected.filter((v) => v !== value))
  }

  const clearAll = (e: React.MouseEvent) => {
    e.stopPropagation()
    onChange([])
  }

  const displayedLabels = selected
    .slice(0, maxDisplay)
    .map((v) => options.find((o) => o.value === v)?.label ?? v)

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className={cn('min-w-[160px] justify-between gap-1 h-auto py-1.5 px-3', className)}
        >
          <div className="flex flex-wrap gap-1">
            {selected.length === 0 ? (
              <span className="text-muted-foreground text-sm">{placeholder}</span>
            ) : (
              <>
                {displayedLabels.map((label, i) => (
                  <Badge
                    key={selected[i]}
                    variant="secondary"
                    className="rounded-sm px-1 font-normal text-xs"
                  >
                    {label}
                    <button
                      className="ml-1 rounded-sm opacity-70 hover:opacity-100"
                      onClick={(e) => removeOne(e, selected[i])}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
                {selected.length > maxDisplay && (
                  <Badge variant="secondary" className="rounded-sm px-1 font-normal text-xs">
                    +{selected.length - maxDisplay}
                  </Badge>
                )}
              </>
            )}
          </div>
          <div className="flex items-center gap-1 ml-1 shrink-0">
            {selected.length > 0 && (
              <button
                className="rounded-sm opacity-50 hover:opacity-100"
                onClick={clearAll}
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
            <ChevronsUpDown className="h-3.5 w-3.5 opacity-50" />
          </div>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-56 p-1" align="start">
        <div className="p-1 pb-2">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar..."
            className="w-full rounded border bg-background px-2 py-1 text-sm outline-none focus:ring-1 focus:ring-ring"
          />
        </div>
        <div className="max-h-52 overflow-y-auto">
          {filtered.length === 0 ? (
            <p className="py-2 text-center text-xs text-muted-foreground">Sin resultados</p>
          ) : (
            filtered.map((option) => (
              <button
                key={option.value}
                onClick={() => toggle(option.value)}
                className={cn(
                  'flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-accent',
                  selected.includes(option.value) && 'text-primary',
                )}
              >
                <Check
                  className={cn(
                    'h-4 w-4 shrink-0',
                    selected.includes(option.value) ? 'opacity-100' : 'opacity-0',
                  )}
                />
                {option.label}
              </button>
            ))
          )}
        </div>
        {selected.length > 0 && (
          <div className="border-t mt-1 pt-1">
            <button
              onClick={() => onChange([])}
              className="w-full rounded-sm px-2 py-1.5 text-xs text-muted-foreground hover:bg-accent text-left"
            >
              Limpiar selección ({selected.length})
            </button>
          </div>
        )}
      </PopoverContent>
    </Popover>
  )
}
