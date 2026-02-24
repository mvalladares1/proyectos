import { useQuery } from '@tanstack/react-query'
import apiClient from './client'

export interface MovimientoEntrada {
  id: number
  date_order: string
  proveedor: string
  tipo_bandeja: string
  cantidad: number
  estado: string
  origen: string
  referencia?: string
}

export interface MovimientoSalida {
  id: number
  date: string
  proveedor: string
  tipo_bandeja: string
  cantidad: number
  destino: string
  referencia?: string
}

export interface StockBandeja {
  tipo_bandeja: string
  cantidad_limpia: number
  cantidad_sucia: number
  total: number
  ultima_actualizacion: string
}

interface BandejasFilters {
  fecha_desde?: string
  fecha_hasta?: string
  year?: number
  months?: number[]
  proveedor?: string
}

export function useMovimientosEntrada(filters: BandejasFilters) {
  return useQuery<MovimientoEntrada[]>({
    queryKey: ['bandejas', 'entradas', filters],
    queryFn: async () => {
      const { data } = await apiClient.get('/bandejas/movimientos-entrada', { params: filters })
      return data?.data ?? data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useMovimientosSalida(filters: BandejasFilters) {
  return useQuery<MovimientoSalida[]>({
    queryKey: ['bandejas', 'salidas', filters],
    queryFn: async () => {
      const { data } = await apiClient.get('/bandejas/movimientos-salida', { params: filters })
      return data?.data ?? data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useStockBandejas() {
  return useQuery<StockBandeja[]>({
    queryKey: ['bandejas', 'stock'],
    queryFn: async () => {
      const { data } = await apiClient.get('/bandejas/stock')
      return data?.data ?? data
    },
    staleTime: 2 * 60 * 1000,
  })
}
