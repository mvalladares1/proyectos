export interface FlujoCajaRow {
  id: string
  cuenta: string
  nivel: number
  parent_id?: string
  children?: FlujoCajaRow[]
  valores: Record<string, number>  // key: 'YYYY-MM' or 'YYYY'
  total: number
  tipo: 'ingreso' | 'egreso' | 'resultado' | 'subtotal'
  expanded?: boolean
}

export interface FlujoCajaData {
  rows: FlujoCajaRow[]
  periodos: string[]  // ['2024-01', '2024-02', ...]
  totales: Record<string, number>
}

export interface ComposicionDetalle {
  cuenta: string
  descripcion: string
  monto: number
  porcentaje: number
  documento?: string
  fecha?: string
}

export interface EERRRow {
  cuenta: string
  nivel: number
  descripcion: string
  actual: number
  anterior: number
  variacion: number
  variacion_pct: number
}

export interface EERRData {
  rows: EERRRow[]
  periodo: string
  periodo_anterior: string
}

export interface CuentaContable {
  codigo: string
  nombre: string
  tipo: string
  saldo: number
  nivel: number
  parent?: string
}

export interface HeatmapConfig {
  min?: number
  max?: number
  type?: 'green' | 'blue' | 'diverging'
  enabled: boolean
}

// ─── YTD ────────────────────────────────────────────────────────────────────
export interface EERRYTDRow {
  concepto: string
  real_ytd: number
  ppto_ytd: number
  diferencia: number
  diferencia_pct: number
  es_calculado: boolean
  nivel: number
}

export interface EERRYTDData {
  rows: EERRYTDRow[]
  year: number
  meses_incluidos: number
  kpis: {
    ingresos_real: number
    ingresos_ppto: number
    costos_real: number
    costos_ppto: number
    utilidad_bruta: number
    ebit: number
  }
}

// ─── Mensualizado ───────────────────────────────────────────────────────────
export interface EERRMensualizadoRow {
  concepto: string
  nivel: number
  es_calculado: boolean
  meses: Record<string, { real: number; ppto: number; diff: number; diff_pct: number }>
}

export interface EERRMensualizadoData {
  rows: EERRMensualizadoRow[]
  meses: string[]  // ['01','02',...]
  year: number
}

// ─── Curva abastecimiento ────────────────────────────────────────────────────
export interface CurvaAbastecimientoPoint {
  semana: number
  fecha_inicio: string
  proyectado_kg: number
  recepcionado_kg: number
  cumplimiento_pct: number
}

export interface CurvaAbastecimientoData {
  puntos: CurvaAbastecimientoPoint[]
  total_proyectado: number
  total_recepcionado: number
  cumplimiento_promedio: number
  plantas: string[]
}
