/**
 * Formatting utilities for IAS7 Tree Component
 */

/**
 * Format number as CLP currency with sign
 */
export function formatMonto(valor: number): string {
    if (valor > 0) {
        return `+$${valor.toLocaleString('es-CL', { maximumFractionDigits: 0 })}`;
    } else if (valor < 0) {
        return `-$${Math.abs(valor).toLocaleString('es-CL', { maximumFractionDigits: 0 })}`;
    }
    return `$${valor.toLocaleString('es-CL', { maximumFractionDigits: 0 })}`;
}

/**
 * Format percentage
 */
export function formatPct(valor: number): string {
    return `${valor.toFixed(1)}%`;
}

/**
 * Get CSS color class based on amount sign
 */
export function getMontoColor(valor: number): string {
    if (valor > 0) return '#2ecc71';  // Green
    if (valor < 0) return '#e74c3c';  // Red
    return '#718096';                  // Gray
}

/**
 * Get indentation in pixels based on node level
 */
export function getIndent(nivel: number): number {
    return (nivel - 1) * 25;
}
