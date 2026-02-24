import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import apiClient from './client'
import type {
  PermissionCheckRequest,
  PermissionCheckResponse,
  DashboardPermissions,
} from '@/types/auth'

async function checkAccess(req: PermissionCheckRequest): Promise<PermissionCheckResponse> {
  const { data } = await apiClient.post<PermissionCheckResponse>('/permissions/check', req)
  return data
}

async function getDashboards(username: string): Promise<DashboardPermissions> {
  const { data } = await apiClient.get<DashboardPermissions>(
    `/permissions/dashboards/${username}`,
  )
  return data
}

export function useCheckAccess() {
  return useMutation({
    mutationFn: checkAccess,
  })
}

export function useDashboardPermissions(username: string | undefined) {
  return useQuery({
    queryKey: ['permissions', 'dashboards', username],
    queryFn: () => getDashboards(username!),
    enabled: !!username,
    staleTime: 2 * 60 * 1000,
  })
}

export interface ModuloPermisos {
  modulo: string
  nombre: string
  emails: string[]
  es_publico: boolean
}

export interface PaginaPermiso {
  slug: string
  name: string
  emails: string[]
  es_publico: boolean
}

export interface OverrideOrigen {
  picking_name: string
  origen_original: string
  origen_override: string
  created_at?: string
}

export interface MaintenanceConfig {
  modo_mantenimiento: boolean
  mensaje: string
  usuarios_excluidos: string[]
}

export function useModulosPermisos() {
  return useQuery<ModuloPermisos[]>({
    queryKey: ['permissions', 'modulos'],
    queryFn: async () => {
      const { data } = await apiClient.get('/permissions/modules')
      return data
    },
    staleTime: 2 * 60 * 1000,
  })
}

export function usePaginasPermisos(modulo: string, enabled = true) {
  return useQuery<PaginaPermiso[]>({
    queryKey: ['permissions', 'paginas', modulo],
    queryFn: async () => {
      const { data } = await apiClient.get('/permissions/pages', { params: { modulo } })
      return data
    },
    enabled: enabled && !!modulo,
    staleTime: 2 * 60 * 1000,
  })
}

export function useOverridesOrigen() {
  return useQuery<OverrideOrigen[]>({
    queryKey: ['permissions', 'overrides-origen'],
    queryFn: async () => {
      const { data } = await apiClient.get('/permissions/overrides/origen/list')
      return data
    },
    staleTime: 2 * 60 * 1000,
  })
}

export function useMaintenanceConfig() {
  return useQuery<MaintenanceConfig>({
    queryKey: ['permissions', 'maintenance'],
    queryFn: async () => {
      const { data } = await apiClient.get('/permissions/maintenance')
      return data
    },
    staleTime: 60 * 1000,
  })
}

export function useUpdateModuloPermiso() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ accion, modulo, email }: { accion: 'assign' | 'remove'; modulo: string; email: string }) => {
      await apiClient.post('/permissions/modules/update', { accion, modulo, email })
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['permissions', 'modulos'] }),
  })
}

export function useUpdatePaginaPermiso() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ accion, modulo, slug, email }: { accion: 'assign' | 'remove'; modulo: string; slug: string; email: string }) => {
      await apiClient.post('/permissions/pages/update', { accion, modulo, slug, email })
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['permissions', 'paginas'] }),
  })
}

export function useAddOverrideOrigen() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { picking_name: string; origen_override: string }) => {
      await apiClient.post('/permissions/overrides/origen', payload)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['permissions', 'overrides-origen'] }),
  })
}

export function useUpdateMaintenanceConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (config: Partial<MaintenanceConfig>) => {
      await apiClient.put('/permissions/maintenance', config)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['permissions', 'maintenance'] }),
  })
}
