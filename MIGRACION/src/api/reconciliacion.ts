import { useQuery } from '@tanstack/react-query'
import apiClient from './client'

export interface ReconciliacionRow {
  mo: string
  producto: string
  consumo_teorico: number
  consumo_real: number
  diferencia: number
  diferencia_pct: number
  estado: 'ok' | 'alerta' | 'error'
}

export interface ReconciliacionKPI {
  total_ots: number
  sin_diferencias: number
  alertas: number
  errores: number
}

export function useReconciliacion(year: number, months: number[]) {
  return useQuery<ReconciliacionRow[]>({
    queryKey: ['reconciliacion', year, months],
    queryFn: async () => {
      const { data } = await apiClient.get('/reconciliacion/', {
        params: { year, months: months.length ? months : undefined },
      })
      return data
    },
    staleTime: 10 * 60 * 1000,
  })
}

export function useReconciliacionKPIs(year: number, months: number[]) {
  return useQuery<ReconciliacionKPI>({
    queryKey: ['reconciliacion', 'kpis', year, months],
    queryFn: async () => {
      const { data } = await apiClient.get('/reconciliacion/kpis', {
        params: { year, months: months.length ? months : undefined },
      })
      return data
    },
    staleTime: 10 * 60 * 1000,
  })
}
