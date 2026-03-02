import { useQuery } from '@tanstack/react-query'
import apiClient from './client'
import type {
  FlujoCajaData,
  EERRData,
  EERRYTDData,
  EERRMensualizadoData,
  CuentaContable,
  ComposicionDetalle,
  FlujoCajaMensualData,
} from '@/types/finanzas'

interface FinanzasFilters {
  year?: number
  months?: number[]
}

interface ComposicionParams {
  cuenta_id: string
  periodo: string
}

const BASE_FC = '/flujo-caja'
const BASE_ER = '/estado-resultado'

async function getFlujoCaja(filters: FinanzasFilters): Promise<FlujoCajaData> {
  const { data } = await apiClient.get(`${BASE_FC}/`, { params: filters })
  return data
}

async function getComposicion(params: ComposicionParams): Promise<ComposicionDetalle[]> {
  const { data } = await apiClient.get(`${BASE_FC}/composicion`, { params })
  return data
}

async function getEERR(filters: FinanzasFilters): Promise<EERRData> {
  const { data } = await apiClient.get(`${BASE_ER}/`, { params: filters })
  return data
}

async function getEERRComparativo(filters: FinanzasFilters): Promise<EERRData> {
  const { data } = await apiClient.get(`${BASE_ER}/comparativo`, { params: filters })
  return data
}

async function getCuentas(filters: FinanzasFilters): Promise<CuentaContable[]> {
  const { data } = await apiClient.get('/presupuesto/', { params: filters })
  return data
}

export function useFlujoCaja(filters: FinanzasFilters) {
  return useQuery({
    queryKey: ['finanzas', 'flujo-caja', filters],
    queryFn: () => getFlujoCaja(filters),
    staleTime: 10 * 60 * 1000,
  })
}

export function useComposicion(params: ComposicionParams, enabled: boolean) {
  return useQuery({
    queryKey: ['finanzas', 'composicion', params],
    queryFn: () => getComposicion(params),
    enabled,
    staleTime: 5 * 60 * 1000,
  })
}

export function useEERR(filters: FinanzasFilters) {
  return useQuery({
    queryKey: ['finanzas', 'eerr', filters],
    queryFn: () => getEERR(filters),
    staleTime: 10 * 60 * 1000,
  })
}

export function useEERRComparativo(filters: FinanzasFilters) {
  return useQuery({
    queryKey: ['finanzas', 'eerr-comparativo', filters],
    queryFn: () => getEERRComparativo(filters),
    staleTime: 10 * 60 * 1000,
  })
}

export function useCuentas(filters: FinanzasFilters) {
  return useQuery({
    queryKey: ['finanzas', 'cuentas', filters],
    queryFn: () => getCuentas(filters),
    staleTime: 10 * 60 * 1000,
  })
}

export function useEERRYTD(filters: FinanzasFilters) {
  return useQuery<EERRYTDData>({
    queryKey: ['finanzas', 'eerr-ytd', filters],
    queryFn: async () => {
      const { data } = await apiClient.get(`${BASE_ER}/ytd`, { params: filters })
      return data
    },
    staleTime: 10 * 60 * 1000,
  })
}

export function useEERRMensualizado(filters: FinanzasFilters) {
  return useQuery<EERRMensualizadoData>({
    queryKey: ['finanzas', 'eerr-mensualizado', filters],
    queryFn: async () => {
      const { data } = await apiClient.get(`${BASE_ER}/mensualizado`, { params: filters })
      return data
    },
    staleTime: 10 * 60 * 1000,
  })
}

export interface EERRAgrupadoRow {
  concepto: string
  real: number
  ppto: number
  dif: number
  dif_pct: number
  es_calculado: boolean
}

export function useEERRAgrupado(year: number, meses: number[]) {
  return useQuery<EERRAgrupadoRow[]>({
    queryKey: ['finanzas', 'eerr-agrupado', year, meses],
    queryFn: async () => {
      const { data } = await apiClient.get(`${BASE_ER}/agrupado`, {
        params: { year, meses: meses.length ? meses : undefined },
      })
      return data
    },
    enabled: meses.length > 0,
    staleTime: 10 * 60 * 1000,
  })
}

export interface EERRDetalleNivel3 {
  nombre: string
  real_ytd: number
  ppto_ytd: number
  dif: number
}

export interface EERRDetalleSubcat {
  nombre: string
  real_ytd: number
  ppto_ytd: number
  dif: number
  nivel3: EERRDetalleNivel3[]
}

export interface EERRDetalleCategoria {
  nombre: string
  real_ytd: number
  ppto_ytd: number
  dif: number
  subcategorias: EERRDetalleSubcat[]
  es_calculado?: boolean
}

export function useEERRDetalle(year: number, months: number[]) {
  return useQuery<EERRDetalleCategoria[]>({
    queryKey: ['finanzas', 'eerr-detalle', year, months],
    queryFn: async () => {
      const { data } = await apiClient.get(`${BASE_ER}/detalle`, {
        params: { year, months: months.length ? months : undefined },
      })
      return data
    },
    staleTime: 10 * 60 * 1000,
  })
}

// ─── Flujo de Caja V2 ────────────────────────────────────────────────────────

export interface FlujoCajaV2Params {
  fechaInicio: string
  fechaFin: string
  odooUser: string
  odooKey: string
  incluirProyecciones?: boolean
  enabled?: boolean
}

async function getFlujoCajaV2(
  params: FlujoCajaV2Params,
  agrupacion: 'mensual' | 'semanal',
): Promise<FlujoCajaMensualData> {
  const { data } = await apiClient.get(`${BASE_FC}/${agrupacion}`, {
    params: {
      fecha_inicio: params.fechaInicio,
      fecha_fin: params.fechaFin,
      username: params.odooUser,
      password: params.odooKey,
      incluir_proyecciones: params.incluirProyecciones ?? false,
    },
  })
  return data
}

export function useFlujoCajaMensual(params: FlujoCajaV2Params) {
  return useQuery<FlujoCajaMensualData>({
    queryKey: ['finanzas', 'flujo-caja-mensual', params],
    queryFn: () => getFlujoCajaV2(params, 'mensual'),
    enabled: (params.enabled ?? false) && !!params.odooUser && !!params.odooKey,
    staleTime: 10 * 60 * 1000,
  })
}

export function useFlujoCajaSemanal(params: FlujoCajaV2Params) {
  return useQuery<FlujoCajaMensualData>({
    queryKey: ['finanzas', 'flujo-caja-semanal', params],
    queryFn: () => getFlujoCajaV2(params, 'semanal'),
    enabled: (params.enabled ?? false) && !!params.odooUser && !!params.odooKey,
    staleTime: 10 * 60 * 1000,
  })
}
