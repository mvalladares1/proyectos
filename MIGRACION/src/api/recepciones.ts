import { useMutation, useQuery } from '@tanstack/react-query'
import apiClient from './client'
import type { KPIMetric } from '@/types/api'
import type { CurvaAbastecimientoData } from '@/types/finanzas'

export interface CurvaFilters {
  fecha_inicio?: string
  fecha_fin?: string
  plantas?: string[]
  especies?: string[]
  semana_desde?: number
  semana_hasta?: number
  solo_hechas?: boolean
}

interface RecepcionesFilters {
  year?: number
  months?: number[]
  start_date?: string
  end_date?: string
  estado?: string
  proveedor?: string
}

export interface Recepcion {
  id: number
  nombre: string
  proveedor: string
  producto: string
  cantidad_kg: number
  fecha: string
  estado: string
  flete_aprobado: boolean
  calidad: string
  numero_oc?: string
}

export interface AprobacionFlete {
  id: number
  recepcion_id: number
  proveedor: string
  monto: number
  estado: 'pendiente' | 'aprobado' | 'rechazado'
  fecha: string
}

export interface PalletSeguimiento {
  id: string
  producto: string
  ubicacion: string
  cantidad: number
  estado: string
  fecha_ingreso: string
}

const BASE = '/recepciones'

async function getRecepciones(filters: RecepcionesFilters): Promise<Recepcion[]> {
  const { data } = await apiClient.get(`${BASE}/`, { params: filters })
  return data
}

async function getKPIs(filters: RecepcionesFilters): Promise<KPIMetric[]> {
  const { data } = await apiClient.get(`${BASE}/kpis`, { params: filters })
  return data
}

async function getAprobaciones(filters: RecepcionesFilters): Promise<Recepcion[]> {
  const { data } = await apiClient.get(`${BASE}/aprobaciones`, { params: filters })
  return data
}

async function getFletes(filters: RecepcionesFilters): Promise<AprobacionFlete[]> {
  const { data } = await apiClient.get(`${BASE}/fletes`, { params: filters })
  return data
}

async function getPallets(filters: RecepcionesFilters): Promise<PalletSeguimiento[]> {
  const { data } = await apiClient.get(`${BASE}/pallets`, { params: filters })
  return data
}

async function aprobarFlete(id: number): Promise<void> {
  await apiClient.post(`${BASE}/fletes/${id}/aprobar`)
}

async function rechazarFlete(id: number, motivo: string): Promise<void> {
  await apiClient.post(`${BASE}/fletes/${id}/rechazar`, { motivo })
}

export function useRecepciones(filters: RecepcionesFilters) {
  return useQuery({
    queryKey: ['recepciones', filters],
    queryFn: () => getRecepciones(filters),
    staleTime: 3 * 60 * 1000,
  })
}

export function useRecepcionesKPIs(filters: RecepcionesFilters) {
  return useQuery({
    queryKey: ['recepciones', 'kpis', filters],
    queryFn: () => getKPIs(filters),
    staleTime: 5 * 60 * 1000,
  })
}

export function useAprobaciones(filters: RecepcionesFilters) {
  return useQuery({
    queryKey: ['recepciones', 'aprobaciones', filters],
    queryFn: () => getAprobaciones(filters),
    staleTime: 2 * 60 * 1000,
  })
}

export function useFletes(filters: RecepcionesFilters) {
  return useQuery({
    queryKey: ['recepciones', 'fletes', filters],
    queryFn: () => getFletes(filters),
    staleTime: 2 * 60 * 1000,
  })
}

export function usePallets(filters: RecepcionesFilters) {
  return useQuery({
    queryKey: ['recepciones', 'pallets', filters],
    queryFn: () => getPallets(filters),
    staleTime: 5 * 60 * 1000,
  })
}

export function useCurvaAbastecimiento(filters: CurvaFilters, enabled = true) {
  return useQuery<CurvaAbastecimientoData>({
    queryKey: ['recepciones', 'curva', filters],
    queryFn: async () => {
      const { data } = await apiClient.get('/recepciones-mp/abastecimiento/curva', { params: filters })
      return data
    },
    enabled,
    staleTime: 5 * 60 * 1000,
  })
}

export function useEspeciesDisponibles() {
  return useQuery<string[]>({
    queryKey: ['recepciones', 'especies'],
    queryFn: async () => {
      const { data } = await apiClient.get('/recepciones-mp/abastecimiento/especies')
      return data
    },
    staleTime: 30 * 60 * 1000,
  })
}

export function useAprobarFlete() {
  return useMutation({ mutationFn: aprobarFlete })
}

export function useRechazarFlete() {
  return useMutation({
    mutationFn: ({ id, motivo }: { id: number; motivo: string }) =>
      rechazarFlete(id, motivo),
  })
}

export interface KgLineaSala {
  sala: string
  kg_pt: number
  kg_por_hora: number
  rendimiento: number
  hh_total: number
  num_mos: number
}

export interface KgLineaData {
  total_kg: number
  prom_kg_hora: number
  salas_activas: number
  salas: KgLineaSala[]
}

export function useKgLineaProductividad(fechaInicio: string, fechaFin: string, enabled = true) {
  return useQuery<KgLineaData>({
    queryKey: ['recepciones', 'kg-linea', fechaInicio, fechaFin],
    queryFn: async () => {
      const { data } = await apiClient.get('/rendimiento/dashboard', {
        params: { fecha_inicio: fechaInicio, fecha_fin: fechaFin, solo_terminadas: true },
      })
      return data
    },
    enabled,
    staleTime: 5 * 60 * 1000,
  })
}

// ─── Proforma Consolidada ───────────────────────────────────────────────────

export interface RutaLogistica {
  id: number
  nombre: string
  transportista: string
  kms: number
  oc_ids: number[]
  oc_nombres: string[]
  kg_total: number
  costo_total: number
  num_ocs: number
}

export interface MaestroCosto {
  transportista: string
  ruta: string
  costo_km: number
  costo_fijo: number
}

export function useRutasLogistica(fechaDesde: string, fechaHasta: string, enabled = true) {
  return useQuery<RutaLogistica[]>({
    queryKey: ['aprobaciones-fletes', 'rutas-logistica', fechaDesde, fechaHasta],
    queryFn: async () => {
      const { data } = await apiClient.get('/aprobaciones-fletes/rutas-logistica', {
        params: { fecha_desde: fechaDesde, fecha_hasta: fechaHasta },
      })
      return data
    },
    enabled,
    staleTime: 5 * 60 * 1000,
  })
}

export function useMaestroCostos() {
  return useQuery<MaestroCosto[]>({
    queryKey: ['aprobaciones-fletes', 'maestro-costos'],
    queryFn: async () => {
      const { data } = await apiClient.get('/aprobaciones-fletes/maestro-costos')
      return data
    },
    staleTime: 15 * 60 * 1000,
  })
}

// ─── Ajuste Proformas ───────────────────────────────────────────────────────

export interface ProformaProveedor {
  id: number
  nombre: string
  rut: string
}

export interface ProformaLinea {
  id: number
  descripcion: string
  cantidad: number
  precio_usd: number
  precio_clp: number
  subtotal_usd: number
  subtotal_clp: number
}

export interface ProformaBorrador {
  id: number
  nombre: string
  proveedor_nombre: string
  proveedor_email: string
  moneda: string
  es_usd: boolean
  enviada: boolean
  fecha_creacion: string
  total_usd: number
  total_clp: number
  base_usd: number
  iva_usd: number
  lineas: ProformaLinea[]
}

export interface BorradoresParams {
  proveedor_id?: number | null
  fecha_desde?: string
  fecha_hasta?: string
  moneda_filtro?: string | null
  solo_enviadas?: boolean | null
}

export function useProformasProveedores() {
  return useQuery<ProformaProveedor[]>({
    queryKey: ['proformas', 'proveedores'],
    queryFn: async () => {
      const { data } = await apiClient.get('/proformas/proveedores')
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useProformasBorradores(params: BorradoresParams, enabled = true) {
  return useQuery<ProformaBorrador[]>({
    queryKey: ['proformas', 'borradores', params],
    queryFn: async () => {
      const { data } = await apiClient.get('/proformas/borradores', { params })
      return data
    },
    enabled,
    staleTime: 2 * 60 * 1000,
  })
}

export function useCambiarMonedaProforma() {
  return useMutation({
    mutationFn: ({ facturaId, monedaDestino = 'CLP' }: { facturaId: number; monedaDestino?: string }) =>
      apiClient.post(`/proformas/cambiar_moneda/${facturaId}`, null, {
        params: { moneda_destino: monedaDestino },
      }),
  })
}

export function useEliminarLineaProforma() {
  return useMutation({
    mutationFn: (lineaId: number) => apiClient.delete(`/proformas/linea/${lineaId}`),
  })
}
