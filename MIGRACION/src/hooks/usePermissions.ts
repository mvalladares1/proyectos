import { useCallback } from 'react'
import { useAuthContext } from '@/providers/AuthProvider'
import { useDashboardPermissions, useCheckAccess } from '@/api/permissions'

export function usePermissions() {
  const { user } = useAuthContext()
  const { data: permissions, isLoading } = useDashboardPermissions(user?.username)
  const checkAccessMutation = useCheckAccess()

  const canAccess = useCallback(
    (dashboard: string) => {
      if (!user) return false
      if (user.is_admin) return true
      return permissions?.dashboards.includes(dashboard) ?? false
    },
    [user, permissions],
  )

  const canAccessPage = useCallback(
    (dashboard: string, page: string) => {
      if (!user) return false
      if (user.is_admin) return true
      const pages = permissions?.pages[dashboard] ?? []
      return pages.includes(page)
    },
    [user, permissions],
  )

  const checkAccess = useCallback(
    async (dashboard: string, page?: string) => {
      if (!user) return false
      if (user.is_admin) return true
      const result = await checkAccessMutation.mutateAsync({
        username: user.username,
        dashboard,
        page,
      })
      return result.allowed
    },
    [user, checkAccessMutation],
  )

  return {
    permissions,
    isLoading,
    canAccess,
    canAccessPage,
    checkAccess,
    allowedDashboards: permissions?.dashboards ?? [],
  }
}
