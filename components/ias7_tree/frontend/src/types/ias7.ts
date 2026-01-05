/**
 * TypeScript interfaces for IAS 7 Cash Flow Tree Component
 * Follows NIIF IAS 7 - Método Directo structure
 */

export type NodeType = 'HEADER' | 'LINEA' | 'TOTAL' | 'DATA';
export type ViewMode = 'real' | 'proyectado' | 'consolidado';
export type ActivityKey = 'OPERACION' | 'INVERSION' | 'FINANCIAMIENTO' | 'CONCILIACION';

/**
 * Individual account composing a line item
 */
export interface IAS7Account {
    codigo: string;
    nombre: string;
    monto: number;
    porcentaje?: number;
}

/**
 * Projected document (draft invoice)
 */
export interface IAS7Document {
    documento: string;
    partner: string;
    fecha_venc: string;
    estado: string;
    monto: number;
    etiquetas?: string[];
    sin_etiqueta?: boolean;
}

/**
 * Single node in the IAS 7 tree (header, line, or total)
 */
export interface IAS7Node {
    id: string;
    nombre: string;
    tipo: NodeType;
    nivel: number;
    monto_real: number;
    monto_proyectado: number;
    monto_display: number;
    signo?: number;
    order?: number;
    cuentas?: IAS7Account[];
    documentos?: IAS7Document[];
    children?: IAS7Node[];
}

/**
 * Activity section (Operation, Investment, Financing)
 */
export interface IAS7Activity {
    key: ActivityKey;
    nombre: string;
    subtotal: number;
    subtotal_nombre: string;
    conceptos: IAS7Node[];
    color: string;
}

/**
 * Main props for IAS7 Tree component
 */
export interface IAS7TreeProps {
    actividades: IAS7Activity[];
    conciliacion?: IAS7Node[];
    modo: ViewMode;
    efectivo_inicial: number;
    efectivo_final: number;
    variacion_neta: number;
    cuentas_sin_clasificar?: number;
    theme?: 'dark' | 'light';
}

/**
 * Activity colors configuration
 */
export const ACTIVITY_COLORS: Record<ActivityKey, string> = {
    OPERACION: '#2ecc71',
    INVERSION: '#3498db',
    FINANCIAMIENTO: '#9b59b6',
    CONCILIACION: '#f39c12',
};
