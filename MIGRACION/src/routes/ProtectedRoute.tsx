import { Navigate } from 'react-router-dom'
import { useEffect, useState, type ReactNode } from 'react'
import { useAuthContext } from '@/providers/AuthProvider'
import { usePermissions } from '@/hooks/usePermissions'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'

interface ProtectedRouteProps {
  children: ReactNode
  dashboard?: string
  page?: string
}

function AccessDenied() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
      <div className="rounded-full bg-destructive/10 p-4">
        <svg className="h-8 w-8 text-destructive" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
        </svg>
      </div>
      <div>
        <h2 className="text-xl font-semibold">Acceso Denegado</h2>
        <p className="text-muted-foreground mt-1">No tienes permisos para ver esta página.</p>
      </div>
    </div>
  )
}

export function ProtectedRoute({ children, dashboard, page }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuthContext()
  const { canAccess, canAccessPage, isLoading: permLoading } = usePermissions()
  const [hasAccess, setHasAccess] = useState<boolean | null>(null)

  useEffect(() => {
    if (!isAuthenticated || isLoading || permLoading) return

    if (!dashboard) {
      setHasAccess(true)
      return
    }

    if (page) {
      setHasAccess(canAccessPage(dashboard, page))
    } else {
      setHasAccess(canAccess(dashboard))
    }
  }, [isAuthenticated, isLoading, permLoading, dashboard, page, canAccess, canAccessPage])

  if (isLoading) return <LoadingSpinner fullScreen />
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (hasAccess === null) return <LoadingSpinner fullScreen />
  if (!hasAccess) return <AccessDenied />

  return <>{children}</>
}
