import { useMutation, useQuery } from '@tanstack/react-query'
import apiClient from './client'
import type {
  ProduccionLinea,
  ProduccionTunel,
  FabricacionDetalle,
  ProduccionKPI,
  ClasificacionData,
} from '@/types/produccion'

interface ProduccionFilters {
  year?: number
  months?: number[]
  linea?: string
  start_date?: string
  end_date?: string
}

const BASE = '/produccion'

async function getLineas(filters: ProduccionFilters): Promise<ProduccionLinea[]> {
  const { data } = await apiClient.get(`${BASE}/lineas`, { params: filters })
  return data
}

async function getTuneles(filters: ProduccionFilters): Promise<ProduccionTunel[]> {
  const { data } = await apiClient.get(`${BASE}/tuneles`, { params: filters })
  return data
}

async function getFabricaciones(filters: ProduccionFilters): Promise<FabricacionDetalle[]> {
  const { data } = await apiClient.get(`${BASE}/fabricaciones`, { params: filters })
  return data
}

async function getKPIs(filters: ProduccionFilters): Promise<ProduccionKPI> {
  const { data } = await apiClient.get(`${BASE}/kpis`, { params: filters })
  return data
}

async function getClasificacion(filters: ProduccionFilters): Promise<ClasificacionData[]> {
  const { data } = await apiClient.get(`${BASE}/clasificacion`, { params: filters })
  return data
}

export function useProduccionLineas(filters: ProduccionFilters) {
  return useQuery({
    queryKey: ['produccion', 'lineas', filters],
    queryFn: () => getLineas(filters),
    staleTime: 5 * 60 * 1000,
  })
}

export function useProduccionTuneles(filters: ProduccionFilters) {
  return useQuery({
    queryKey: ['produccion', 'tuneles', filters],
    queryFn: () => getTuneles(filters),
    staleTime: 5 * 60 * 1000,
  })
}

export function useFabricaciones(filters: ProduccionFilters) {
  return useQuery({
    queryKey: ['produccion', 'fabricaciones', filters],
    queryFn: () => getFabricaciones(filters),
    staleTime: 5 * 60 * 1000,
  })
}

export function useProduccionKPIs(filters: ProduccionFilters) {
  return useQuery({
    queryKey: ['produccion', 'kpis', filters],
    queryFn: () => getKPIs(filters),
    staleTime: 5 * 60 * 1000,
  })
}

export function useClasificacion(filters: ProduccionFilters) {
  return useQuery({
    queryKey: ['produccion', 'clasificacion', filters],
    queryFn: () => getClasificacion(filters),
    staleTime: 5 * 60 * 1000,
  })
}

export function useMonitorDiario(fecha: string) {
  return useQuery({
    queryKey: ['produccion', 'monitor-diario', fecha],
    queryFn: async () => {
      const { data } = await apiClient.get(`${BASE}/monitor-diario`, { params: { fecha } })
      return data as Array<{
        mo_name: string; producto: string; linea: string; estado: string
        cantidad_planificada: number; cantidad_real: number; avance_pct: number; operario: string
      }>
    },
    staleTime: 2 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  })
}

export function useKgPorLinea(filters: ProduccionFilters) {
  return useQuery({
    queryKey: ['produccion', 'kg-por-linea', filters],
    queryFn: async () => {
      const { data } = await apiClient.get(`${BASE}/kg-por-linea`, { params: filters })
      return data as Array<{ linea: string; periodo: string; kg_entrada: number; kg_salida: number; rendimiento: number }>
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function usePalletsProduccion(filters: ProduccionFilters) {
  return useQuery({
    queryKey: ['produccion', 'pallets', filters],
    queryFn: async () => {
      const { data } = await apiClient.get(`${BASE}/pallets`, { params: filters })
      return data as Array<{
        sala: string; producto: string; cantidad_pallets: number
        kg_total: number; temperatura: number; fecha: string
      }>
    },
    staleTime: 5 * 60 * 1000,
  })
}

// ─── Etiquetas ────────────────────────────────────────────────────────────────

export interface OrdenEtiqueta {
  id: number
  name: string
  producto: string
  estado: string
  qty_production?: number
}

export interface PalletOrden {
  package_id: number
  numero_pallet: number
  producto: string
  lote: string
  kg: number
  ubicacion?: string
}

export function useBuscarOrdenesEtiquetas(
  termino: string,
  odooUser: string,
  odooKey: string,
  enabled = true,
) {
  return useQuery<OrdenEtiqueta[]>({
    queryKey: ['etiquetas', 'ordenes', termino, odooUser],
    queryFn: async () => {
      const { data } = await apiClient.get('/etiquetas/buscar_ordenes', {
        params: { termino, username: odooUser, password: odooKey },
      })
      return data
    },
    enabled: enabled && !!termino && !!odooUser && !!odooKey,
    staleTime: 2 * 60 * 1000,
  })
}

export function usePalletsOrden(
  ordenName: string,
  odooUser: string,
  odooKey: string,
  enabled = true,
) {
  return useQuery<PalletOrden[]>({
    queryKey: ['etiquetas', 'pallets', ordenName, odooUser],
    queryFn: async () => {
      const { data } = await apiClient.get('/etiquetas/pallets_orden', {
        params: { orden_name: ordenName, username: odooUser, password: odooKey },
      })
      return data
    },
    enabled: enabled && !!ordenName && !!odooUser && !!odooKey,
    staleTime: 2 * 60 * 1000,
  })
}

export function useGenerarEtiquetasPDF() {
  return useMutation({
    mutationFn: async ({
      packageIds,
      fechaElaboracion,
      cliente,
      odooUser,
      odooKey,
    }: {
      packageIds: number[]
      fechaElaboracion: string
      cliente: string
      odooUser: string
      odooKey: string
    }) => {
      const infos = await Promise.all(
        packageIds.map(id =>
          apiClient
            .get(`/etiquetas/info_etiqueta/${id}`, {
              params: { cliente, username: odooUser, password: odooKey },
            })
            .then(r => ({ ...r.data, fecha_elaboracion: fechaElaboracion })),
        ),
      )
      const response = await apiClient.post(
        '/etiquetas/generar_etiquetas_multiples_pdf',
        infos,
        { responseType: 'blob' },
      )
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
      const link = document.createElement('a')
      link.href = url
      link.download = 'etiquetas_pallets.pdf'
      link.click()
      window.URL.revokeObjectURL(url)
    },
  })
}

// ─── Automatización OF ───────────────────────────────────────────────────────

export interface OrdenProceso {
  id: number
  nombre: string
  estado: string
  producto: string
  cantidad: number
  es_picking?: boolean
}

export interface PalletValidadoProceso {
  pallet: string
  ok: boolean
  kg: number
  lote: string
  producto: string
  package_id?: number
  error?: string
  ya_en_orden?: boolean
}

export function useBuscarOrdenProcesos(
  orden: string,
  odooUser: string,
  odooKey: string,
  enabled = true,
) {
  return useQuery<OrdenProceso>({
    queryKey: ['procesos', 'orden', orden, odooUser],
    queryFn: async () => {
      const { data } = await apiClient.get('/automatizaciones/procesos/buscar-orden', {
        params: { orden, username: odooUser, password: odooKey },
      })
      return data
    },
    enabled: enabled && !!orden && !!odooUser && !!odooKey,
    staleTime: 0,
    retry: false,
  })
}

export function useValidarPalletsProcesos() {
  return useMutation({
    mutationFn: ({
      pallets,
      tipo,
      ordenId,
      odooUser,
      odooKey,
    }: {
      pallets: string[]
      tipo: string
      ordenId: number
      odooUser: string
      odooKey: string
    }) =>
      apiClient
        .post(
          '/automatizaciones/procesos/validar-pallets',
          { pallets, tipo, orden_id: ordenId },
          { params: { username: odooUser, password: odooKey } },
        )
        .then(r => r.data as PalletValidadoProceso[]),
  })
}

export function useAgregarPalletsProcesos() {
  return useMutation({
    mutationFn: ({
      ordenId,
      tipo,
      pallets,
      modelo = 'mrp.production',
      odooUser,
      odooKey,
    }: {
      ordenId: number
      tipo: string
      pallets: object[]
      modelo?: string
      odooUser: string
      odooKey: string
    }) =>
      apiClient
        .post(
          '/automatizaciones/procesos/agregar-pallets',
          { orden_id: ordenId, tipo, pallets, modelo },
          { params: { username: odooUser, password: odooKey } },
        )
        .then(r => r.data as { success: boolean; pallets_agregados: number; kg_total: number; errores: string[]; mensaje?: string }),
  })
}
