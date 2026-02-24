import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface EmptyStateProps {
  icon?: ReactNode
  title?: string
  description?: string
  action?: ReactNode
  className?: string
}

export function EmptyState({
  icon,
  title = 'Sin datos',
  description = 'No hay información disponible para mostrar.',
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex min-h-[300px] flex-col items-center justify-center gap-4 rounded-lg border border-dashed p-8 text-center',
        className,
      )}
    >
      {icon && (
        <div className="rounded-full bg-muted p-4 text-muted-foreground">
          {icon}
        </div>
      )}
      <div className="space-y-1">
        <h3 className="text-lg font-semibold">{title}</h3>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      {action}
    </div>
  )
}
