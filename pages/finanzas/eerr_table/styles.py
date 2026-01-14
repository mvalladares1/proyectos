"""
Estilos CSS para la tabla de Estado de Resultados expandible.
Texto blanco, sin colores, alineado.
"""

EERR_CSS = """
<style>
    /* === TABLA EERR EXPANDIBLE === */
    .eerr-container {
        overflow-x: auto;
        margin: 20px 0;
        border-radius: 12px;
        background: #0f172a;
        border: 1px solid #1e293b;
    }
    
    .eerr-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        font-size: 13px;
        font-family: 'Inter', -apple-system, sans-serif;
        color: #e2e8f0;
    }
    
    .eerr-table th,
    .eerr-table td {
        padding: 10px 14px;
        text-align: right;
        border-bottom: 1px solid #1e293b;
        white-space: nowrap;
        color: #e2e8f0;
    }
    
    .eerr-table th {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        color: #94a3b8;
        font-weight: 600;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        position: sticky;
        top: 0;
        z-index: 10;
    }
    
    /* Columna frozen (Concepto) */
    .eerr-table .frozen {
        position: sticky;
        left: 0;
        background: #0f172a;
        text-align: left;
        min-width: 280px;
        max-width: 360px;
        z-index: 5;
        border-right: 2px solid #334155;
    }
    
    .eerr-table th.frozen {
        z-index: 15;
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    }
    
    /* Filas de categoría principal (nivel 1) */
    .eerr-table .cat-row {
        background: #1e293b;
        font-weight: 600;
        cursor: pointer;
    }
    
    .eerr-table .cat-row:hover {
        background: #334155;
    }
    
    /* Filas de subcategoría (nivel 2) */
    .eerr-table .subcat-row {
        background: #172231;
        font-size: 12px;
    }
    
    .eerr-table .level-2 {
        padding-left: 28px !important;
    }
    
    /* Filas de cuenta (nivel 3) */
    .eerr-table .cuenta-row {
        background: #0f1a27;
        font-size: 11px;
    }
    
    .eerr-table .level-3 {
        padding-left: 48px !important;
    }
    
    .eerr-table .level-4 {
        padding-left: 68px !important;
    }
    
    /* Filas de subtotal calculado */
    .eerr-table .subtotal-row {
        background: linear-gradient(90deg, #1e3a5f 0%, #1e293b 100%);
        font-weight: 700;
        border-top: 1px solid #3b82f6;
        border-bottom: 1px solid #3b82f6;
    }
    
    /* Fila de total final */
    .eerr-table .total-row {
        background: linear-gradient(90deg, #064e3b 0%, #0f172a 100%);
        font-weight: 800;
        font-size: 14px;
        border-top: 2px solid #10b981;
    }
    
    /* Icono de expansión */
    .expand-icon {
        display: inline-block;
        width: 20px;
        height: 20px;
        margin-right: 8px;
        cursor: pointer;
        transition: transform 0.2s ease;
        vertical-align: middle;
    }
    
    .expand-icon.expanded {
        transform: rotate(90deg);
    }
    
    .expand-icon svg {
        width: 16px;
        height: 16px;
        fill: #64748b;
    }
    
    /* Filas ocultas (inicialmente) */
    .eerr-table .hidden-row {
        display: none;
    }
    
    /* Columna Total/YTD */
    .eerr-table .col-total {
        background: #172231;
        font-weight: 600;
        border-left: 2px solid #334155;
    }
    
    /* Sparkline mini */
    .sparkline-mini {
        display: inline-block;
        margin-left: 8px;
        vertical-align: middle;
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .eerr-table .frozen {
            min-width: 180px;
        }
        .eerr-table th, .eerr-table td {
            padding: 8px 10px;
            font-size: 11px;
        }
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
