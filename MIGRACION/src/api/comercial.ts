import { useQuery } from '@tanstack/react-query'
import apiClient from './client'

export interface ClienteData {
  cliente: string
  ventas: number
  margen: number
  pedidos: number
  tendencia: number
}

export interface ComercialKPI {
  clientes_activos: number
  ventas_totales: number
  margen_promedio: number
  cliente_top: string
}

export function useClientes(year: number, months: number[]) {
  return useQuery<ClienteData[]>({
    queryKey: ['comercial', 'clientes', year, months],
    queryFn: async () => {
      const { data } = await apiClient.get('/comercial/clientes', {
        params: { year, months: months.length ? months : undefined },
      })
      return data
    },
    staleTime: 10 * 60 * 1000,
  })
}

export function useComercialKPIs(year: number, months: number[]) {
  return useQuery<ComercialKPI>({
    queryKey: ['comercial', 'kpis', year, months],
    queryFn: async () => {
      const { data } = await apiClient.get('/comercial/kpis', {
        params: { year, months: months.length ? months : undefined },
      })
      return data
    },
    staleTime: 10 * 60 * 1000,
  })
}

export function useVentasMensuales(year: number) {
  return useQuery({
    queryKey: ['comercial', 'ventas-mensuales', year],
    queryFn: async () => {
      const { data } = await apiClient.get('/comercial/ventas-mensuales', {
        params: { year },
      })
      return data
    },
    staleTime: 10 * 60 * 1000,
  })
}
