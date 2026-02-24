export interface ProduccionLinea {
  id: number
  linea: string
  producto: string
  cantidad: number
  rendimiento: number
  fecha: string
  turno: string
  estado: string
}

export interface ProduccionTunel {
  id: number
  tunel: string
  producto: string
  cantidad_entrada: number
  cantidad_salida: number
  temperatura: number
  fecha: string
}

export interface FabricacionDetalle {
  id: number
  mo_name: string
  producto: string
  cantidad: number
  rendimiento_real: number
  rendimiento_teorico: number
  merma: number
  fecha: string
  linea: string
}

export interface ProduccionKPI {
  total_produccion: number
  rendimiento_promedio: number
  merma_total: number
  eficiencia: number
}

export interface ClasificacionData {
  categoria: string
  cantidad: number
  porcentaje: number
  color?: string
}
