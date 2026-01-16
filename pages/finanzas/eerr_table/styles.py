"""
Estilos CSS para la tabla de Estado de Resultados expandible.
Texto blanco, sin colores, alineado.
"""

EERR_CSS = """
<style>
    /* === TABLA EERR EXPANDIBLE MODERN === */
    .eerr-container {
        overflow-x: auto;
        margin: 20px 0;
        border-radius: 8px;
        background: #0f172a;
        border: 1px solid #1e293b;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    
    .eerr-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        font-size: 13px;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
        color: #f1f5f9;
    }
    
    .eerr-table th,
    .eerr-table td {
        padding: 12px 16px;
        text-align: right;
        border-bottom: 1px solid #1e293b;
        white-space: nowrap;
    }
    
    /* Números tabulares para alineación perfecta */
    .eerr-table td {
        font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
        font-variant-numeric: tabular-nums;
        letter-spacing: -0.5px;
    }
    
    /* HEADER */
    .eerr-table th {
        background: #1e293b;
        color: #94a3b8;
        font-weight: 700;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        position: sticky;
        top: 0;
        z-index: 20;
        border-bottom: 2px solid #334155;
    }
    
    /* Columna CONCEPTO (Sticky Left) */
    .eerr-table .frozen {
        position: sticky;
        left: 0;
        text-align: left;
        min-width: 300px;
        max-width: 400px;
        z-index: 10;
        border-right: 1px solid #334155;
        background: #0f172a; /* Fallback */
        font-family: 'Inter', sans-serif; /* Conceptos en sans-serif */
    }
    
    /* Concepto en header */
    .eerr-table th.frozen {
        z-index: 30;
        background: #1e293b;
    }
    
    /* === FILAS === */
    
    /* Nivel 1: Categorías Principales (Ingresos, Costos...) */
    .eerr-table .cat-row td {
        background: #111827;
        font-weight: 600;
        cursor: pointer;
        border-bottom: 1px solid #1f2937;
    }
    
    .eerr-table .cat-row:hover td {
        background: #1f2937;
    }
    
    /* Indicador visual de grupo (borde izquierdo) */
    .eerr-table .cat-row .frozen {
        border-left: 3px solid #3b82f6; /* Azul default */
    }
    
    /* Nivel 2: Subcategorías */
    .eerr-table .subcat-row td {
        background: #172231;
        font-size: 12px;
        color: #cbd5e1;
    }
    .eerr-table .subcat-row:hover td {
        background: #1e293b;
    }
    .eerr-table .level-2 {
        padding-left: 32px !important;
        border-left: 3px solid transparent;
    }
    
    /* Nivel 3: Cuentas */
    .eerr-table .cuenta-row td {
        background: #0f1a27;
        font-size: 11px;
        color: #94a3b8;
    }
    .eerr-table .cuenta-row:hover td {
        background: #172231;
    }
    .eerr-table .level-3 {
        padding-left: 54px !important;
        border-left: 3px solid transparent;
    }
    .eerr-table .level-4 {
        padding-left: 76px !important;
    }
    
    /* === TOTALES Y RESULTADOS === */
    
    /* Subtotales calculados (Utilidad Bruta, EBIT...) */
    .eerr-table .subtotal-row td {
        background: #1e293b;
        font-weight: 700;
        border-top: 1px solid #475569;
        border-bottom: 1px solid #475569;
        color: #e2e8f0;
    }
    
    .eerr-table .subtotal-row .frozen {
        border-left: 3px solid #f59e0b; /* Ambar para resultados intermedios */
    }
    
    /* Total Final (Utilidad Neta) */
    .eerr-table .total-row td {
        background: #064e3b;
        font-weight: 800;
        font-size: 13px;
        border-top: 2px solid #10b981;
        color: #ffffff;
    }
    
    .eerr-table .total-row .frozen {
        border-left: 3px solid #10b981;
    }
    
    /* Columna Total YTD */
    .eerr-table .col-total {
        font-weight: 700;
        background: rgba(30, 41, 59, 0.5); /* Semi-transparente */
        border-left: 1px solid #334155;
    }
    
    /* === UTILIDADES TEXTO === */
    .val-pos { color: #4ade80; } /* Verde suave */
    .val-neg { color: #f87171; } /* Rojo suave */
    .val-zero { color: #475569; } /* Gris oscuro */
    
    /* Ajustes específicos para filas oscuras */
    .total-row .val-pos, .total-row .val-neg { color: inherit; } 
    
    /* Icono de expansión */
    .expand-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 18px;
        height: 18px;
        margin-right: 8px;
        cursor: pointer;
        transition: transform 0.2s ease;
        color: #64748b;
        background: rgba(255,255,255,0.05);
        border-radius: 4px;
    }
    
    .expand-icon:hover {
        background: rgba(255,255,255,0.1);
        color: #cbd5e1;
    }
    
    .expand-icon.expanded {
        transform: rotate(90deg);
        background: rgba(59, 130, 246, 0.2);
        color: #60a5fa;
    }
    
    .expand-icon svg {
        width: 12px;
        height: 12px;
        fill: currentColor;
    }
    
    /* Filas ocultas */
    .hidden-row { display: none; }
    
    /* Scrollbar estilizado */
    .eerr-container::-webkit-scrollbar {
        height: 8px;
        background: #0f172a;
    }
    .eerr-container::-webkit-scrollbar-thumb {
        background: #334155;
        border-radius: 4px;
    }
    .eerr-container::-webkit-scrollbar-thumb:hover {
        background: #475569;
    }
</style>
"""

EERR_JS = """
<script>
    function toggleEerrRow(rowId) {
        const icon = document.querySelector(`[data-row-id="${rowId}"] .expand-icon`);
        const childRows = document.querySelectorAll(`.child-of-${rowId}`);
        
        if (icon) {
            icon.classList.toggle('expanded');
        }
        
        childRows.forEach(row => {
            row.classList.toggle('hidden-row');
        });
    }
</script>
"""

# SVG Icons
SVG_CHEVRON = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M9 5l7 7-7 7"></path></svg>'
