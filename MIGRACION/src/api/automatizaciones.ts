import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from './client'

export interface AutomatizacionMonitor {
  id: string
  nombre: string
  descripcion: string
  estado: 'activo' | 'inactivo' | 'error' | 'ejecutando'
  ultimo_run?: string
  proximo_run?: string
  resultado?: string
}

export function useAutomatizaciones() {
  return useQuery<AutomatizacionMonitor[]>({
    queryKey: ['automatizaciones', 'monitor'],
    queryFn: async () => {
      const { data } = await apiClient.get('/automatizaciones/monitor')
      return data
    },
    refetchInterval: 30_000,
  })
}

export function useEjecutarAutomatizacion() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await apiClient.post('/automatizaciones/ejecutar', { id })
      return data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['automatizaciones'] })
    },
  })
}

export function useAutomatizacionLogs(id: string | null) {
  return useQuery<string[]>({
    queryKey: ['automatizaciones', 'logs', id],
    queryFn: async () => {
      const { data } = await apiClient.get(`/automatizaciones/logs/${id}`)
      return data
    },
    enabled: id !== null,
    staleTime: 30 * 1000,
  })
}

export interface Tunel {
  codigo: string
  nombre: string
  sucursal: string
}

export interface OrdenFabricacion {
  id: number
  mo_name: string
  tunel: string
  producto_nombre: string
  estado: string
  tiene_pendientes: boolean
  kg_total: number
  pallets_count: number
  componentes_count: number
  subproductos_count: number
  fecha_creacion: string
  electricidad_costo?: number
}

export interface MovimientoStock {
  id: number
  referencia: string
  producto: string
  origen: string
  destino: string
  cantidad: number
  fecha: string
  estado: string
  tipo: string
}

export interface ProcesoAutomatizacion {
  id: string
  nombre: string
  descripcion: string
  activo: boolean
  intervalo_minutos: number
  ultimo_run?: string
  proximo_run?: string
  estado: string
}

export function useTuneles(enabled = true) {
  return useQuery<Tunel[]>({
    queryKey: ['automatizaciones', 'tuneles'],
    queryFn: async () => {
      const { data } = await apiClient.get('/automatizaciones/tuneles')
      return data
    },
    enabled,
    staleTime: 10 * 60 * 1000,
  })
}

export function useOrdenesMonitor(tunel?: string, estado?: string) {
  return useQuery<OrdenFabricacion[]>({
    queryKey: ['automatizaciones', 'ordenes', tunel, estado],
    queryFn: async () => {
      const { data } = await apiClient.get('/automatizaciones/ordenes', {
        params: { tunel, estado },
      })
      return data
    },
    staleTime: 60 * 1000,
  })
}

export function useMovimientosStock(fechaInicio: string, fechaFin: string, enabled = true) {
  return useQuery<MovimientoStock[]>({
    queryKey: ['automatizaciones', 'movimientos', fechaInicio, fechaFin],
    queryFn: async () => {
      const { data } = await apiClient.get('/automatizaciones/movimientos', {
        params: { fecha_inicio: fechaInicio, fecha_fin: fechaFin },
      })
      return data
    },
    enabled,
    staleTime: 2 * 60 * 1000,
  })
}

export function useProcesosAutomatizacion() {
  return useQuery<ProcesoAutomatizacion[]>({
    queryKey: ['automatizaciones', 'procesos'],
    queryFn: async () => {
      const { data } = await apiClient.get('/automatizaciones/procesos')
      return data
    },
    staleTime: 30 * 1000,
  })
}

export function useCrearOrdenFabricacion() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { tunel: string; pallets: string[]; buscar_ubicacion_auto?: boolean }) => {
      const { data } = await apiClient.post('/automatizaciones/crear-orden', payload)
      return data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['automatizaciones', 'ordenes'] })
    },
  })
}

export function useToggleProcesoActivo() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, activo }: { id: string; activo: boolean }) => {
      const { data } = await apiClient.put(`/automatizaciones/procesos/${id}`, { activo })
      return data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['automatizaciones', 'procesos'] })
    },
  })
}

// ─── Revertir Consumo ODF ─────────────────────────────────────────────────────

export interface ComponentePreview {
  paquete: string
  producto: string
  lote: string
  cantidad: number
  ubicacion: string
}

export interface SubproductoPreview {
  producto: string
  cantidad_actual: number
  ubicacion: string
}

export interface RevertirPreviewResult {
  success: boolean
  message: string
  componentes_preview: ComponentePreview[]
  subproductos_preview: SubproductoPreview[]
  errores?: string[]
}

export interface ComponenteRevertido {
  paquete: string
  producto: string
  lote: string
  cantidad: number
  ubicacion: string
}

export interface RevertirConsumoResult {
  success: boolean
  message: string
  componentes_revertidos: ComponenteRevertido[]
  subproductos_eliminados: SubproductoPreview[]
  transferencias_creadas: Array<{ name: string; id: number }>
  errores?: string[]
}

export function usePreviewRevertirConsumo() {
  return useMutation({
    mutationFn: async ({ odfName, odooUser, odooKey }: { odfName: string; odooUser: string; odooKey: string }) => {
      const { data } = await apiClient.post<RevertirPreviewResult>(
        '/automatizaciones/revertir-consumo-odf/preview',
        { odf_name: odfName },
        { params: { username: odooUser, password: odooKey } },
      )
      return data
    },
  })
}

export function useRevertirConsumo() {
  return useMutation({
    mutationFn: async ({ odfName, odooUser, odooKey }: { odfName: string; odooUser: string; odooKey: string }) => {
      const { data } = await apiClient.post<RevertirConsumoResult>(
        '/automatizaciones/revertir-consumo-odf',
        { odf_name: odfName },
        { params: { username: odooUser, password: odooKey } },
      )
      return data
    },
  })
}
