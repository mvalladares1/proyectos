"""
Estilos CSS para el Estado de Flujo de Efectivo
"""

ENTERPRISE_CSS = """
<style>
/* ============ CUSTOM SCROLLBAR ============ */
.excel-container::-webkit-scrollbar {
    height: 14px;
    background: #0a0e1a;
}

.excel-container::-webkit-scrollbar-track {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    border-radius: 8px;
    border: 1px solid #1e293b;
}

.excel-container::-webkit-scrollbar-thumb {
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
    border-radius: 8px;
    border: 2px solid #1e293b;
    box-shadow: inset 0 1px 2px rgba(255,255,255,0.2);
}

.excel-container::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%);
    box-shadow: 0 0 10px rgba(59, 130, 246, 0.5);
}

/* ============ CONTAINER & TABLE BASE ============ */
.excel-container {
    width: 100%;
    overflow-x: auto;
    overflow-y: hidden;
    border: 3px solid #334155;
    border-radius: 16px;
    background: linear-gradient(145deg, #0a0e1a 0%, #1e293b 100%);
    box-shadow: 
        0 20px 60px rgba(0, 0, 0, 0.5),
        inset 0 1px 2px rgba(255,255,255,0.05);
    position: relative;
}

.excel-table {
    width: max-content;
    min-width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', 'SF Pro Display', sans-serif;
    font-size: 0.875rem;
    color: #e2e8f0;
}

.excel-table th,
.excel-table td {
    padding: 16px 24px;
    border-bottom: 1px solid #334155;
    border-right: 1px solid #2d3748;
    text-align: right;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
}

/* ============ TOOLTIPS ============ */
.tooltip-wrapper {
    position: relative;
    display: inline-block;
}

.tooltip-text {
    visibility: hidden;
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    color: #f1f5f9;
    text-align: left;
    border-radius: 8px;
    padding: 12px 16px;
    position: absolute;
    z-index: 1000;
    bottom: 125%;
    left: 50%;
    transform: translateX(-50%);
    min-width: 300px;
    max-width: 500px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.6);
    border: 2px solid #3b82f6;
    opacity: 0;
    transition: opacity 0.3s, visibility 0.3s;
    font-size: 0.875rem;
    line-height: 1.6;
    white-space: normal;
}

.tooltip-text::after {
    content: "";
    position: absolute;
    top: 100%;
    left: 50%;
    margin-left: -8px;
    border-width: 8px;
    border-style: solid;
    border-color: #3b82f6 transparent transparent transparent;
}

.tooltip-wrapper:hover .tooltip-text {
    visibility: visible;
    opacity: 1;
}

/* ============ SVG ICONS ============ */
.icon-expand {
    display: inline-block;
    width: 20px;
    height: 20px;
    margin-right: 10px;
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    vertical-align: middle;
}

.icon-expand svg {
    width: 100%;
    height: 100%;
    fill: #60a5fa;
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
}

.expanded .icon-expand {
    transform: rotate(90deg);
}

.expanded .icon-expand svg {
    fill: #3b82f6;
}

/* ============ HEADERS ============ */
.excel-table thead th {
    background: linear-gradient(180deg, #1e40af 0%, #1e3a8a 100%) !important;
    color: #ffffff;
    font-weight: 700;
    position: sticky;
    top: 0;
    z-index: 50;
    white-space: nowrap;
    border-bottom: 4px solid #3b82f6;
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 1.5px;
    padding: 18px 24px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

/* Vista Semanal: Header de Meses (fila superior) */
.excel-table thead tr.header-meses th {
    position: sticky;
    top: 0;
    z-index: 51;
}

.excel-table thead tr.header-meses th.mes-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    border-bottom: 2px solid #764ba2;
    font-size: 14px !important;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: none;
}

/* Vista Semanal: Header de Semanas (fila inferior) */
.excel-table thead tr.header-semanas th {
    position: sticky;
    top: 52px;  /* Altura de la fila de meses */
    z-index: 50;
    background: linear-gradient(180deg, #2d3748 0%, #1e293b 100%) !important;
    font-size: 11px !important;
    padding: 8px 12px !important;
    border-bottom: 3px solid #3b82f6;
    font-weight: 600;
    letter-spacing: 0;
}

.excel-table thead th.frozen {
    z-index: 150;
    background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%) !important;
    border-right: 3px solid #1e3a8a;
    text-align: left !important;
    font-size: 0.85rem;
}

/* ============ FROZEN COLUMN ============ */
.excel-table td.frozen {
    position: sticky;
    left: 0;
    z-index: 10;
    border-right: 3px solid #475569 !important;
    text-align: left !important;
    font-weight: 500;
    min-width: 480px;
    max-width: 480px;
    white-space: normal !important;
    box-shadow: 4px 0 8px rgba(0, 0, 0, 0.2);
}

.excel-table tr.activity-header td.frozen {
    background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%) !important;
    color: #ffffff !important;
    font-weight: 700;
    font-size: 1rem;
}

.excel-table tr.subtotal-interno td.frozen {
    background: linear-gradient(135deg, #1e3a5f 0%, rgba(37, 99, 235, 0.3) 100%) !important;
    color: #dbeafe !important;
}

.excel-table tr.subtotal td.frozen {
    background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%) !important;
    color: #ffffff !important;
}

.excel-table tr.grand-total td.frozen {
    background: linear-gradient(135deg, #047857 0%, #10b981 100%) !important;
    color: #ffffff !important;
}

.excel-table tr.data-row td.frozen {
    background: #1e293b !important;
    color: #cbd5e1 !important;
}

/* ============ ACTIVITY HEADERS ============ */
.excel-table tr.activity-header td {
    background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
    color: #ffffff;
    font-weight: 700;
    font-size: 1rem;
    padding: 18px 24px;
    border-top: 4px solid #60a5fa;
    border-bottom: 3px solid #3b82f6;
    text-shadow: 0 2px 6px rgba(0,0,0,0.5);
    letter-spacing: 0.8px;
}

/* ============ SUBTOTALS ============ */
.excel-table tr.subtotal-interno td {
    background: linear-gradient(135deg, #1e3a5f 0%, rgba(37, 99, 235, 0.2) 100%);
    font-weight: 600;
    border-top: 2px solid #3b82f6;
    font-style: italic;
    color: #bfdbfe;
    padding: 14px 24px;
}

.excel-table tr.subtotal td {
    background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%);
    font-weight: 700;
    border-top: 3px solid #60a5fa;
    border-bottom: 3px solid #60a5fa;
    color: #ffffff;
    padding: 16px 24px;
    box-shadow: 
        inset 0 1px 3px rgba(255,255,255,0.15),
        0 2px 8px rgba(59, 130, 246, 0.3);
}

/* ============ GRAND TOTALS ============ */
.excel-table tr.grand-total td {
    background: linear-gradient(135deg, #047857 0%, #10b981 100%);
    font-weight: 700;
    font-size: 1rem;
    border-top: 5px double #34d399;
    border-bottom: 5px double #34d399;
    color: #ffffff;
    text-shadow: 0 2px 6px rgba(0,0,0,0.5);
    padding: 18px 24px;
    box-shadow: 
        0 4px 16px rgba(16, 185, 129, 0.4), 
        inset 0 1px 3px rgba(255,255,255,0.2);
    letter-spacing: 0.8px;
}

/* ============ HEATMAP COLORS ============ */
.heatmap-very-positive {
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.25) 0%, rgba(37, 99, 235, 0.15) 100%) !important;
    box-shadow: inset 0 0 10px rgba(59, 130, 246, 0.3);
}

.heatmap-positive {
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.12) 0%, rgba(37, 99, 235, 0.08) 100%) !important;
}

.heatmap-neutral {
    background: rgba(100, 116, 139, 0.1) !important;
}

.heatmap-negative {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(220, 38, 38, 0.1) 100%) !important;
}

.heatmap-very-negative {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.3) 0%, rgba(220, 38, 38, 0.2) 100%) !important;
    box-shadow: inset 0 0 10px rgba(239, 68, 68, 0.4);
}

/* ============ AMOUNTS STYLING ============ */
.monto-positivo { 
    color: #ffffff; 
    font-weight: 700;
    text-shadow: 0 0 8px rgba(96, 165, 250, 0.5);
}
.monto-negativo { 
    color: #fca5a5; 
    font-weight: 700;
    text-shadow: 0 0 10px rgba(252, 165, 165, 0.3);
}
.monto-cero { 
    color: #94a3b8; 
    font-weight: 400;
}

/* ============ SPARKLINE ============ */
.sparkline {
    display: inline-block;
    width: 60px;
    height: 20px;
    margin-left: 10px;
    vertical-align: middle;
}

.sparkline svg {
    width: 100%;
    height: 100%;
}

/* ============ HOVER EFFECTS ============ */
.excel-table tr.data-row:hover td {
    background: rgba(59, 130, 246, 0.15) !important;
    transform: scale(1.001);
    box-shadow: inset 0 0 0 2px rgba(59, 130, 246, 0.4);
}

.excel-table tr.data-row:hover td.frozen {
    background: rgba(37, 99, 235, 0.3) !important;
}

.excel-table td.clickable {
    cursor: pointer;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.excel-table td.clickable:hover {
    background: rgba(59, 130, 246, 0.35) !important;
    transform: scale(1.05);
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.5);
    z-index: 5;
}

/* ============ INDENTATION ============ */
.indent-1 { 
    padding-left: 28px !important; 
}
.indent-2 { 
    padding-left: 56px !important;
    border-left: 4px solid rgba(59, 130, 246, 0.4);
}
.indent-3 { 
    padding-left: 84px !important;
    border-left: 3px solid rgba(100, 116, 139, 0.3);
}
.indent-4 { 
    padding-left: 112px !important;
    border-left: 2px solid rgba(100, 116, 139, 0.2);
}

/* ============ EXPANDABLE ROWS ============ */
.expandable {
    cursor: pointer;
    transition: all 0.3s ease;
}

.expandable:hover {
    background: rgba(59, 130, 246, 0.12) !important;
}

.detail-row {
    display: table-row;
    animation: slideDown 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes slideDown {
    from {
        opacity: 0;
        transform: translateY(-10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.detail-row:hover td {
    background: rgba(59, 130, 246, 0.15) !important;
}

.detail-row td {
    background: #0a0e1a !important;
    font-size: 0.8rem;
    color: #94a3b8;
    padding: 12px 24px !important;
    border-left: 4px solid #1e40af;
}

.detail-row td.frozen {
    background: #0a0e1a !important;
    padding-left: 120px !important;
    font-style: italic;
    color: #cbd5e1;
}

/* ============ TOTAL COLUMN HIGHLIGHT ============ */
.excel-table td:last-child,
.excel-table th:last-child {
    background: rgba(59, 130, 246, 0.15) !important;
    border-left: 4px solid #3b82f6;
    font-weight: 700;
    box-shadow: 
        inset 3px 0 8px rgba(0, 0, 0, 0.2),
        0 0 15px rgba(59, 130, 246, 0.2);
}

.excel-table th:last-child {
    background: linear-gradient(180deg, #1e40af 0%, #1e3a8a 100%) !important;
}

.excel-table tr.grand-total td:last-child {
    background: linear-gradient(135deg, #059669 0%, #10b981 100%) !important;
    box-shadow: 
        0 0 25px rgba(16, 185, 129, 0.5), 
        inset 3px 0 10px rgba(0, 0, 0, 0.3);
}

/* ============ ZEBRA STRIPES ============ */
.excel-table tr.data-row:nth-child(even) td {
    background: rgba(15, 23, 42, 0.6);
}

.excel-table tr.data-row:nth-child(odd) td {
    background: rgba(30, 41, 59, 0.4);
}

.excel-table tr.data-row:nth-child(even) td.frozen {
    background: #1a2332 !important;
}

.excel-table tr.data-row:nth-child(odd) td.frozen {
    background: #1e293b !important;
}

/* ============ FONTS ============ */
.excel-table td:not(.frozen) {
    font-family: 'SF Mono', 'Consolas', 'Monaco', 'Roboto Mono', monospace;
    font-size: 0.875rem;
    font-weight: 500;
}

.excel-table td.frozen {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
    line-height: 1.6;
}

/* ============ NOTES/COMMENTS ============ */
.note-indicator {
    position: absolute;
    top: 4px;
    right: 4px;
    width: 12px;
    height: 12px;
    background: #fbbf24;
    border-radius: 50%;
    border: 2px solid #1e293b;
    box-shadow: 0 0 8px rgba(251, 191, 36, 0.6);
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.2); opacity: 0.7; }
}

/* ============ SEARCH HIGHLIGHT ============ */
.search-highlight {
    background: rgba(251, 191, 36, 0.4) !important;
    box-shadow: 0 0 10px rgba(251, 191, 36, 0.6);
    animation: highlightPulse 1s;
}

@keyframes highlightPulse {
    0% { background: rgba(251, 191, 36, 0.8); }
    100% { background: rgba(251, 191, 36, 0.4); }
}

/* ============ DRAG & DROP ============ */
.draggable {
    cursor: move;
}

.dragging {
    opacity: 0.5;
    background: rgba(59, 130, 246, 0.3) !important;
}

.drop-target {
    border-top: 3px dashed #3b82f6 !important;
    background: rgba(59, 130, 246, 0.1) !important;
}

/* ============ SCROLL HINT ============ */
.scroll-hint {
    text-align: center;
    padding: 14px;
    color: #94a3b8;
    font-size: 0.75rem;
    background: linear-gradient(90deg, 
        transparent, 
        rgba(59,130,246,0.2) 20%, 
        rgba(59,130,246,0.2) 80%, 
        transparent);
    border-top: 2px solid #334155;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}
</style>
"""
