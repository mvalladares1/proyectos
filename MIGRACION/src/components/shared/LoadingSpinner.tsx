import { cn } from '@/lib/utils'

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  fullScreen?: boolean
  label?: string
  className?: string
}

export function LoadingSpinner({
  size = 'md',
  fullScreen = false,
  label,
  className,
}: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'h-4 w-4 border-2',
    md: 'h-8 w-8 border-2',
    lg: 'h-12 w-12 border-[3px]',
  }

  const spinner = (
    <div className="flex flex-col items-center justify-center gap-3">
      <div
        className={cn(
          'animate-spin rounded-full border-primary border-t-transparent',
          sizeClasses[size],
          className,
        )}
      />
      {label && <p className="text-sm text-muted-foreground">{label}</p>}
    </div>
  )

  if (fullScreen) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm z-50">
        {spinner}
      </div>
    )
  }

  return (
    <div className="flex h-full min-h-[200px] items-center justify-center">
      {spinner}
    </div>
  )
}
