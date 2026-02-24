import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from './client'

export interface PermisoUsuario {
  username: string
  name: string
  email: string
  dashboards: string[]
  is_admin: boolean
}

export function useUsuarios() {
  return useQuery<PermisoUsuario[]>({
    queryKey: ['permisos', 'usuarios'],
    queryFn: async () => {
      const { data } = await apiClient.get('/permissions/users')
      return data
    },
    staleTime: 2 * 60 * 1000,
  })
}

export function useActualizarPermisos() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ username, dashboards }: { username: string; dashboards: string[] }) => {
      const { data } = await apiClient.put(`/permissions/users/${username}`, { dashboards })
      return data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['permisos'] })
    },
  })
}

export function useActualizarAdmin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ username, is_admin }: { username: string; is_admin: boolean }) => {
      const { data } = await apiClient.put(`/permissions/users/${username}/admin`, { is_admin })
      return data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['permisos'] })
    },
  })
}
