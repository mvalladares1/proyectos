import type { ReactNode } from 'react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn, formatNumber, formatCurrency, formatPercent } from '@/lib/utils'
import type { KPIMetric } from '@/types/api'

interface KPICardProps extends Partial<KPIMetric> {
  icon?: ReactNode
  trend?: number[]
  loading?: boolean
  className?: string
}

export function KPICard({
  label,
  value,
  unit,
  change,
  change_type,
  format = 'number',
  icon,
  loading = false,
  className,
}: KPICardProps) {
  if (loading) {
    return (
      <Card className={className}>
        <CardHeader className="pb-2">
          <Skeleton className="h-4 w-32" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-8 w-24 mb-2" />
          <Skeleton className="h-3 w-20" />
        </CardContent>
      </Card>
    )
  }

  const formatValue = (val: number | string | undefined) => {
    if (val === undefined || val === null) return '—'
    if (typeof val === 'string') return val
    switch (format) {
      case 'currency':
        return formatCurrency(val)
      case 'percent':
        return formatPercent(val)
      default:
        return formatNumber(val)
    }
  }

  const isPositive = change_type === 'increase'
  const isNegative = change_type === 'decrease'

  return (
    <Card className={cn('transition-shadow hover:shadow-md', className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <p className="text-sm font-medium text-muted-foreground">{label}</p>
        {icon && (
          <div className="text-muted-foreground">{icon}</div>
        )}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">
          {formatValue(value)}
          {unit && <span className="ml-1 text-sm font-normal text-muted-foreground">{unit}</span>}
        </div>
        {change !== undefined && (
          <p
            className={cn('mt-1 flex items-center gap-1 text-xs', {
              'text-green-500': isPositive,
              'text-red-500': isNegative,
              'text-muted-foreground': !isPositive && !isNegative,
            })}
          >
            {isPositive && <TrendingUp className="h-3 w-3" />}
            {isNegative && <TrendingDown className="h-3 w-3" />}
            {!isPositive && !isNegative && <Minus className="h-3 w-3" />}
            {Math.abs(change)}% vs período anterior
          </p>
        )}
      </CardContent>
    </Card>
  )
}
