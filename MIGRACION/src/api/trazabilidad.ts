import { useQuery } from '@tanstack/react-query'
import apiClient from './client'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface TrazabilidadLoteMP {
  lot_id: number
  lot_name: string
  product_name: string
  kg: number
  proveedor: string
  fecha_recepcion: string
}

export interface TrazabilidadInversaResult {
  lote_pt: string
  producto_pt: string
  fecha_creacion: string
  mo: { name: string; producto_pt?: string; fecha_inicio?: string } | null
  lotes_mp: TrazabilidadLoteMP[]
  error?: string
}

export interface SankeyNode {
  name: string
  [key: string]: unknown
}

export interface SankeyLink {
  source: number | string
  target: number | string
  value: number
  [key: string]: unknown
}

export interface SankeyData {
  nodes: SankeyNode[]
  links: SankeyLink[]
}

export interface SankeyProducer {
  id: number
  name: string
  [key: string]: unknown
}

// ─── Hooks ────────────────────────────────────────────────────────────────────

export function useTrazabilidadInversa(
  lotePT: string,
  odooUser: string,
  odooKey: string,
  enabled = true,
) {
  return useQuery<TrazabilidadInversaResult>({
    queryKey: ['trazabilidad', 'inversa', lotePT, odooUser],
    queryFn: async () => {
      const { data } = await apiClient.get(
        `/rendimiento/trazabilidad-inversa/${encodeURIComponent(lotePT)}`,
        { params: { username: odooUser, password: odooKey } },
      )
      return data
    },
    enabled: enabled && !!lotePT && !!odooUser && !!odooKey,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  })
}

export function useSankeyTrazabilidad(
  odooUser: string,
  odooKey: string,
  params: { startDate?: string; endDate?: string } = {},
  enabled = true,
) {
  return useQuery<SankeyData>({
    queryKey: ['trazabilidad', 'sankey', odooUser, params.startDate, params.endDate],
    queryFn: async () => {
      const { data } = await apiClient.get('/containers/traceability/sankey', {
        params: {
          username: odooUser,
          password: odooKey,
          start_date: params.startDate,
          end_date: params.endDate,
        },
      })
      return data
    },
    enabled: enabled && !!odooUser && !!odooKey,
    staleTime: 10 * 60 * 1000,
    retry: 1,
  })
}

export function useSankeyProductores(
  odooUser: string,
  odooKey: string,
  params: { startDate?: string; endDate?: string } = {},
  enabled = true,
) {
  return useQuery<SankeyProducer[]>({
    queryKey: ['trazabilidad', 'sankey-productores', odooUser, params.startDate, params.endDate],
    queryFn: async () => {
      const { data } = await apiClient.get('/containers/sankey/producers', {
        params: {
          username: odooUser,
          password: odooKey,
          start_date: params.startDate,
          end_date: params.endDate,
        },
      })
      return Array.isArray(data) ? data : data?.producers ?? []
    },
    enabled: enabled && !!odooUser && !!odooKey,
    staleTime: 10 * 60 * 1000,
    retry: 1,
  })
}
