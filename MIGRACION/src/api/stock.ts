import { useQuery } from '@tanstack/react-query'
import apiClient from './client'

export interface StockItem {
  id: number
  producto: string
  ubicacion: string
  cantidad: number
  unidad: string
  valor: number
  categoria: string
}

export interface StockKPI {
  total_productos: number
  valor_total: number
  ubicaciones: number
  alertas_minimo: number
}

export function useStock(year: number) {
  return useQuery<StockItem[]>({
    queryKey: ['stock', year],
    queryFn: async () => {
      const { data } = await apiClient.get('/stock/', { params: { year } })
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useStockKPIs(year: number) {
  return useQuery<StockKPI>({
    queryKey: ['stock', 'kpis', year],
    queryFn: async () => {
      const { data } = await apiClient.get('/stock/kpis', { params: { year } })
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useStockMovimientos(year: number, months: number[]) {
  return useQuery({
    queryKey: ['stock', 'movimientos', year, months],
    queryFn: async () => {
      const { data } = await apiClient.get('/stock/movimientos', {
        params: { year, months: months.length ? months : undefined },
      })
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export interface PalletStock {
  pallet: string
  product: string
  lot: string
  quantity: number
  category: string
  condition: string
  in_date: string
  days_old: number
}

export interface Lote {
  lot: string
  product: string
  quantity: number
  pallets: number
  in_date: string
  days_old: number
  locations: string[]
}

export function usePallets(
  locationId: number | null,
  category: string | null,
  enabled = true,
) {
  return useQuery<PalletStock[]>({
    queryKey: ['stock', 'pallets', locationId, category],
    queryFn: async () => {
      const { data } = await apiClient.get('/stock/pallets', {
        params: {
          location_id: locationId,
          category: category ?? undefined,
        },
      })
      return data
    },
    enabled: enabled && locationId !== null,
    staleTime: 2 * 60 * 1000,
  })
}

export function useLotes(
  category: string,
  locationIds: number[] | null,
  enabled = true,
) {
  return useQuery<Lote[]>({
    queryKey: ['stock', 'lotes', category, locationIds],
    queryFn: async () => {
      const { data } = await apiClient.get('/stock/lotes', {
        params: {
          category,
          location_ids: locationIds ?? undefined,
        },
      })
      return data
    },
    enabled: enabled && !!category,
    staleTime: 2 * 60 * 1000,
  })
}
