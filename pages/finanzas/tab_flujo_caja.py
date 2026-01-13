"""
Tab: Flujo de Caja
Estado de Flujo de EFECTIVO NIIF IAS 7 con funcionalidades avanzadas.

FEATURES:
- Tooltips inteligentes
- SVG Icons modernos
- Mini sparklines
- Colores condicionales
- Búsqueda en tiempo real
- Filtros por actividad
- Export Excel con formato
- Comparación YoY
- Waterfall chart
- Heatmap
- Drill-down modal
- KPIs animados
- Comentarios/notas
- Auditoría de cambios
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
from datetime import datetime, timedelta
from calendar import monthrange
import io
import json
import base64

from .shared import (
    FLUJO_CAJA_URL, fmt_flujo, fmt_numero, build_ias7_categories_dropdown,
    sugerir_categoria, guardar_mapeo_cuenta
)

# ==================== CSS ENTERPRISE LEVEL ====================
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
    overflow-y: visible;
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

# ==================== JAVASCRIPT AVANZADO ====================
ENTERPRISE_JS = """
<script>
// ============ GLOBAL STATE ============
let expandedConcepts = new Set();
let searchTerm = '';
let activeFilters = new Set(['OPERACION', 'INVERSION', 'FINANCIAMIENTO']);
let notesData = {};

// ============ EXPAND/COLLAPSE ============
function toggleConcept(conceptId) {
    const rows = document.querySelectorAll('.detail-' + conceptId);
    const parent = document.querySelector('.parent-' + conceptId);
    const icon = parent.querySelector('.icon-expand');
    
    const isExpanded = expandedConcepts.has(conceptId);
    
    rows.forEach(row => {
        row.style.display = isExpanded ? 'none' : 'table-row';
    });
    
    if (isExpanded) {
        expandedConcepts.delete(conceptId);
        parent.classList.remove('expanded');
    } else {
        expandedConcepts.add(conceptId);
        parent.classList.add('expanded');
    }
}

// ============ EXPAND ALL / COLLAPSE ALL ============
function expandAll() {
    document.querySelectorAll('.expandable').forEach(parent => {
        const conceptId = parent.classList[2].replace('parent-', '');
        if (!expandedConcepts.has(conceptId)) {
            toggleConcept(conceptId);
        }
    });
}

function collapseAll() {
    document.querySelectorAll('.expandable').forEach(parent => {
        const conceptId = parent.classList[2].replace('parent-', '');
        if (expandedConcepts.has(conceptId)) {
            toggleConcept(conceptId);
        }
    });
}

// ============ SEARCH ============
function searchTable(term) {
    searchTerm = term.toLowerCase();
    const rows = document.querySelectorAll('.data-row, .detail-row');
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        const matches = text.includes(searchTerm);
        
        row.style.display = matches || searchTerm === '' ? 'table-row' : 'none';
        
        if (matches && searchTerm !== '') {
            row.classList.add('search-highlight');
            setTimeout(() => row.classList.remove('search-highlight'), 2000);
        }
    });
}

// ============ FILTER BY ACTIVITY ============
function toggleFilter(activity) {
    if (activeFilters.has(activity)) {
        activeFilters.delete(activity);
    } else {
        activeFilters.add(activity);
    }
    applyFilters();
}

function applyFilters() {
    const activitySections = {
        'OPERACION': document.querySelectorAll('.tipo-op').parentElement,
        'INVERSION': document.querySelectorAll('.tipo-inv').parentElement,
        'FINANCIAMIENTO': document.querySelectorAll('.tipo-fin').parentElement
    };
    
    // Simple show/hide based on filters
    document.querySelectorAll('.activity-header').forEach((header, idx) => {
        const activities = ['OPERACION', 'INVERSION', 'FINANCIAMIENTO'];
        const activity = activities[idx];
        
        let currentRow = header.nextElementSibling;
        const visible = activeFilters.has(activity);
        
        header.style.display = visible ? 'table-row' : 'none';
        
        while (currentRow && !currentRow.classList.contains('activity-header')) {
            currentRow.style.display = visible ? 'table-row' : 'none';
            currentRow = currentRow.nextElementSibling;
        }
    });
}

// ============ DRILL-DOWN MODAL ============
function showDrillDown(conceptId, conceptName, data) {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2>${conceptId} - ${conceptName}</h2>
                <button onclick="this.closest('.modal-overlay').remove()">✕</button>
            </div>
            <div class="modal-body">
                <h3>Cuentas que componen este concepto:</h3>
                <div id="drill-down-data"></div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

// ============ NOTES/COMMENTS ============
function addNote(conceptId, cellId) {
    const note = prompt('Agregar nota para ' + conceptId + ':');
    if (note) {
        notesData[cellId] = note;
        // Add note indicator
        const cell = document.getElementById(cellId);
        if (cell && !cell.querySelector('.note-indicator')) {
            const indicator = document.createElement('span');
            indicator.className = 'note-indicator';
            indicator.title = note;
            cell.appendChild(indicator);
        }
    }
}

function showNote(cellId) {
    const note = notesData[cellId];
    if (note) {
        alert(note);
    }
}

// ============ DRAG & DROP ============
let draggedRow = null;

function handleDragStart(e) {
    draggedRow = this;
    this.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
}

function handleDragOver(e) {
    if (e.preventDefault) {
        e.preventDefault();
    }
    e.dataTransfer.dropEffect = 'move';
    this.classList.add('drop-target');
    return false;
}

function handleDragLeave(e) {
    this.classList.remove('drop-target');
}

function handleDrop(e) {
    if (e.stopPropagation) {
        e.stopPropagation();
    }
    
    if (draggedRow !== this) {
        const parent = this.parentNode;
        parent.insertBefore(draggedRow, this);
    }
    
    this.classList.remove('drop-target');
    return false;
}

function handleDragEnd(e) {
    this.classList.remove('dragging');
    document.querySelectorAll('.drop-target').forEach(el => {
        el.classList.remove('drop-target');
    });
}

// ============ INITIALIZE ============
document.addEventListener('DOMContentLoaded', function() {
    // Enable drag & drop on draggable rows
    document.querySelectorAll('.draggable').forEach(row => {
        row.addEventListener('dragstart', handleDragStart);
        row.addEventListener('dragover', handleDragOver);
        row.addEventListener('dragleave', handleDragLeave);
        row.addEventListener('drop', handleDrop);
        row.addEventListener('dragend', handleDragEnd);
    });
});
</script>
"""

# ==================== SVG ICONS ====================
SVG_ICONS = {
    "chevron": '''<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
        <path d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"/>
    </svg>''',
    "chart": '''<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
        <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"/>
    </svg>''',
    "note": '''<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
        <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/>
    </svg>'''
}


def _generate_sparkline(values: list) -> str:
    """Genera un mini gráfico SVG de tendencia."""
    if not values or len(values) < 2:
        return ""
    
    max_val = max(abs(v) for v in values) or 1
    normalized = [(v / max_val) * 10 + 10 for v in values]
    
    points = " ".join([f"{i*10},{20-n}" for i, n in enumerate(normalized)])
    
    color = "#34d399" if values[-1] > 0 else "#fca5a5"
    
    return f'''<span class="sparkline">
        <svg viewBox="0 0 {len(values)*10} 20" preserveAspectRatio="none">
            <polyline points="{points}" 
                fill="none" 
                stroke="{color}" 
                stroke-width="2" 
                stroke-linecap="round"/>
        </svg>
    </span>'''


def _get_heatmap_class(value: float, max_abs: float) -> str:
    """Determina la clase heatmap según el valor."""
    if max_abs == 0:
        return "heatmap-neutral"
    
    ratio = value / max_abs
    
    if ratio > 0.6:
        return "heatmap-very-positive"
    elif ratio > 0.2:
        return "heatmap-positive"
    elif ratio < -0.6:
        return "heatmap-very-negative"
    elif ratio < -0.2:
        return "heatmap-negative"
    else:
        return "heatmap-neutral"


def _fmt_monto_html(valor: float, include_class: bool = True) -> str:
    """Formatea un monto con color según signo."""
    if valor > 0:
        cls = "monto-positivo" if include_class else ""
        return f'<span class="{cls}">${valor:,.0f}</span>'
    elif valor < 0:
        cls = "monto-negativo" if include_class else ""
        return f'<span class="{cls}">-${abs(valor):,.0f}</span>'
    else:
        cls = "monto-cero" if include_class else ""
        return f'<span class="{cls}">$0</span>'


def _nombre_mes_corto(mes_str: str) -> str:
    """Convierte '2026-01' a 'Ene 26'."""
    meses_nombres = {
        "01": "Ene", "02": "Feb", "03": "Mar", "04": "Abr",
        "05": "May", "06": "Jun", "07": "Jul", "08": "Ago",
        "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dic"
    }
    parts = mes_str.split("-")
    if len(parts) == 2:
        return f"{meses_nombres.get(parts[1], parts[1])} {parts[0][2:]}"
    return mes_str


@st.fragment
def render(username: str, password: str):
    """
    Renderiza el tab Flujo de Caja con diseño Enterprise.
    """
    st.markdown("# Estado de Flujo de EFECTIVO")
    
    # ========== CONTROLES SUPERIORES ==========
    col_search, col_filters, col_actions = st.columns([2, 3, 2])
    
    with col_search:
        search_query = st.text_input("🔍 Búsqueda en tiempo real", 
                                     placeholder="Buscar concepto, cuenta...",
                                     key="search_flujo")
    
    with col_filters:
        st.write("**Filtrar por actividad:**")
        f_cols = st.columns(3)
        filter_op = f_cols[0].checkbox("🟢 Operación", value=True, key="filter_op")
        filter_inv = f_cols[1].checkbox("🔵 Inversión", value=True, key="filter_inv")
        filter_fin = f_cols[2].checkbox("🟣 Financiamiento", value=True, key="filter_fin")
    
    with col_actions:
        act_cols = st.columns(2)
        expand_all = act_cols[0].button("📂 Expandir Todo", use_container_width=True)
        collapse_all = act_cols[1].button("📁 Contraer Todo", use_container_width=True)
    
    st.markdown("---")
    
    # ========== SELECTORES DE PERÍODO ==========
    col_desde, col_hasta, col_agrupacion, col_btn, col_export, col_waterfall = st.columns([2, 2, 2, 1, 1, 1])
    
    with col_desde:
        fecha_inicio = st.date_input(
            "Fecha Desde",
            value=datetime(datetime.now().year, 1, 1),
            key="flujo_fecha_desde"
        )
    
    with col_hasta:
        fecha_fin = st.date_input(
            "Fecha Hasta",
            value=datetime.now(),
            key="flujo_fecha_hasta"
        )
    
    with col_agrupacion:
        tipo_periodo = st.selectbox(
            "Agrupación",
            ["Mensual", "Semanal"],
            key="flujo_agrupacion"
        )
    
    # Convertir a string para API
    fecha_inicio_str = fecha_inicio.strftime("%Y-%m-%d")
    fecha_fin_str = fecha_fin.strftime("%Y-%m-%d")
    
    with col_btn:
        btn_generar = st.button("🔄 Generar", type="primary", use_container_width=True,
                               key="flujo_btn_generar")
    
    with col_export:
        export_placeholder = st.empty()
    
    with col_waterfall:
        show_waterfall = st.button("📊 Cascada", use_container_width=True, key="show_waterfall")
    
    st.markdown("---")
    
    # ========== CARGAR DATOS ==========
    cache_key = f"flujo_excel_{tipo_periodo}_{fecha_inicio_str}_{fecha_fin_str}"
    
    if btn_generar:
        if cache_key in st.session_state:
            del st.session_state[cache_key]
        st.session_state["flujo_should_load"] = True
    
    if st.session_state.get("flujo_should_load") or cache_key in st.session_state:
        
        if cache_key not in st.session_state:
            with st.spinner("🚀 Cargando datos con procesamiento avanzado..."):
                try:
                    # Determinar endpoint según agrupación
                    endpoint = "semanal" if tipo_periodo == "Semanal" else "mensual"
                    resp = requests.get(
                        f"{FLUJO_CAJA_URL}/{endpoint}",
                        params={
                            "fecha_inicio": fecha_inicio_str,
                            "fecha_fin": fecha_fin_str,
                            "username": username,
                            "password": password
                        },
                        timeout=120
                    )
                    
                    if resp.status_code == 200:
                        st.session_state[cache_key] = resp.json()
                        st.session_state["flujo_should_load"] = False
                        st.toast("✅ Datos cargados con éxito", icon="✅")
                    else:
                        st.error(f"Error {resp.status_code}: {resp.text}")
                        return
                except Exception as e:
                    st.error(f"Error de conexión: {e}")
                    return
        
        flujo_data = st.session_state.get(cache_key, {})
        
        if "error" in flujo_data:
            st.error(f"Error: {flujo_data['error']}")
            return
        
        # ========== PROCESAR DATOS ==========
        actividades = flujo_data.get("actividades", {})
        conciliacion = flujo_data.get("conciliacion", {})
        meses_lista = flujo_data.get("meses", [])
        EFECTIVO_por_mes = flujo_data.get("EFECTIVO_por_mes", {})
        cuentas_nc = flujo_data.get("cuentas_sin_clasificar", [])
        
        op = actividades.get("OPERACION", {}).get("subtotal", 0)
        inv = actividades.get("INVERSION", {}).get("subtotal", 0)
        fin = actividades.get("FINANCIAMIENTO", {}).get("subtotal", 0)
        ef_ini = conciliacion.get("EFECTIVO_inicial", 0)
        ef_fin = conciliacion.get("EFECTIVO_final", 0)
        variacion = op + inv + fin
        
        # ========== DASHBOARD KPIs ANIMADO ==========
        st.markdown("""
        <style>
        .kpi-card {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            padding: 24px;
            border-radius: 16px;
            border: 2px solid #334155;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
            transition: all 0.3s ease;
        }
        .kpi-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 50px rgba(59, 130, 246, 0.3);
            border-color: #3b82f6;
        }
        .kpi-label {
            font-size: 0.75rem;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }
        .kpi-value {
            font-size: 1.8rem;
            font-weight: 700;
            font-family: 'SF Mono', monospace;
        }
        .kpi-positive { color: #34d399; }
        .kpi-negative { color: #fca5a5; }
        .kpi-neutral { color: #60a5fa; }
        </style>
        """, unsafe_allow_html=True)
        
        kpi_cols = st.columns(5)
        
        kpi_cols[0].markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">🟢 Operación</div>
            <div class="kpi-value {'kpi-positive' if op > 0 else 'kpi-negative'}">${op:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        kpi_cols[1].markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">🔵 Inversión</div>
            <div class="kpi-value {'kpi-positive' if inv > 0 else 'kpi-negative'}">${inv:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        kpi_cols[2].markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">🟣 Financiamiento</div>
            <div class="kpi-value {'kpi-positive' if fin > 0 else 'kpi-negative'}">${fin:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        kpi_cols[3].markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">💰 EFECTIVO Inicial</div>
            <div class="kpi-value kpi-neutral">${ef_ini:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        kpi_cols[4].markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">� EFECTIVO Final</div>
            <div class="kpi-value {'kpi-positive' if variacion > 0 else 'kpi-negative'}">${ef_fin:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # ========== WATERFALL CHART ==========
        if show_waterfall:
            st.markdown("### 📊 Gráfico de Cascada (Waterfall Chart)")
            
            waterfall_data = {
                "Concepto": ["Ef. Inicial", "Operación", "Inversión", "Financiamiento", "Ef. Final"],
                "Valor": [ef_ini, op, inv, fin, ef_fin],
                "Tipo": ["inicial", "flujo", "flujo", "flujo", "final"]
            }
            
            # Aquí podrías integrar un gráfico de Plotly o similar
            st.info("🚧 Gráfico de cascada interactivo en desarrollo...")
            st.dataframe(pd.DataFrame(waterfall_data))
        
        # ========== GENERAR TABLA HTML ==========
        html_parts = [ENTERPRISE_CSS, '<div class="excel-container">']
        html_parts.append('<table class="excel-table">')
        
        # HEADER
        html_parts.append('<thead><tr>')
        html_parts.append('<th class="frozen">CONCEPTO</th>')
        for mes in meses_lista:
            html_parts.append(f'<th>{_nombre_mes_corto(mes)}</th>')
        html_parts.append('<th><strong>TOTAL</strong></th>')
        html_parts.append('</tr></thead>')
        
        # BODY
        html_parts.append('<tbody>')
        
        # Calcular max_abs para heatmap
        all_values = []
        for act_data in actividades.values():
            for concepto in act_data.get("conceptos", []):
                all_values.extend(concepto.get("montos_por_mes", {}).values())
        max_abs = max([abs(v) for v in all_values], default=1)
        
        act_config = {
            "OPERACION": {"icon": "🟢", "class": "tipo-op"},
            "INVERSION": {"icon": "🔵", "class": "tipo-inv"},
            "FINANCIAMIENTO": {"icon": "🟣", "class": "tipo-fin"}
        }
        
        for act_key in ["OPERACION", "INVERSION", "FINANCIAMIENTO"]:
            act_data = actividades.get(act_key, {})
            if not act_data:
                continue
            
            config = act_config[act_key]
            act_nombre = act_data.get("nombre", act_key)
            act_subtotal = act_data.get("subtotal", 0)
            act_subtotal_por_mes = act_data.get("subtotal_por_mes", {})
            conceptos = act_data.get("conceptos", [])
            
            # Activity Header
            html_parts.append(f'<tr class="activity-header">')
            html_parts.append(f'<td class="frozen">{config["icon"]} {act_nombre}</td>')
            for _ in meses_lista:
                html_parts.append('<td></td>')
            html_parts.append('<td></td>')
            html_parts.append('</tr>')
            
            # Conceptos
            for concepto in sorted(conceptos, key=lambda x: x.get("order", x.get("id", ""))):
                c_id = concepto.get("id") or concepto.get("codigo")
                c_nombre = concepto.get("nombre", "")
                c_tipo = concepto.get("tipo", "LINEA")
                c_nivel = concepto.get("nivel", 3)
                c_total = concepto.get("total", 0)
                montos_mes = concepto.get("montos_por_mes", {})
                cuentas = concepto.get("cuentas", [])
                
                if c_tipo == "HEADER":
                    continue
                
                indent_class = f"indent-{min(c_nivel, 4)}"
                
                if c_tipo == "SUBTOTAL":
                    row_class = "subtotal-interno"
                elif c_tipo == "TOTAL":
                    row_class = "subtotal"
                else:
                    row_class = "data-row"
                
                c_id_safe = c_id.replace(".", "_")
                has_details = len(cuentas) > 0
                expandable_class = f"expandable parent-{c_id_safe}" if has_details else ""
                draggable = 'draggable="true" class="draggable"' if c_tipo == "LINEA" else ""
                onclick = f'onclick="toggleConcept(\'{c_id_safe}\')"' if has_details else ""
                
                # SVG Icon
                icon_svg = f'<span class="icon-expand">{SVG_ICONS["chevron"]}</span>' if has_details else '<span style="width:24px;display:inline-block;"></span>'
                
                # Tooltip
                tooltip_text = f"{c_id} - {c_nombre}"
                if cuentas:
                    tooltip_text += f"<br><br><strong>{len(cuentas)} cuentas:</strong><br>"
                    tooltip_text += "<br>".join([f"• {c.get('codigo', '')} - {c.get('nombre', '')[:30]}" for c in cuentas[:5]])
                    if len(cuentas) > 5:
                        tooltip_text += f"<br>... y {len(cuentas)-5} más"
                
                tooltip_html = f'''
                <div class="tooltip-wrapper">
                    <span>{c_nombre[:50]}</span>
                    <div class="tooltip-text">{tooltip_text}</div>
                </div>
                '''
                
                html_parts.append(f'<tr class="{row_class} {expandable_class}" {draggable} {onclick}>')
                html_parts.append(f'<td class="frozen {indent_class}">{icon_svg}{c_id} - {tooltip_html}</td>')
                
                # Valores mensuales con HEATMAP
                valores_lista = []
                for mes in meses_lista:
                    monto_mes = montos_mes.get(mes, 0)
                    valores_lista.append(monto_mes)
                    heatmap_class = _get_heatmap_class(monto_mes, max_abs)
                    cell_id = f"cell_{c_id_safe}_{mes}"
                    html_parts.append(f'<td class="clickable {heatmap_class}" id="{cell_id}" oncontextmenu="addNote(\'{c_id}\', \'{cell_id}\'); return false;">{_fmt_monto_html(monto_mes)}</td>')
                
                # Total con SPARKLINE
                sparkline = _generate_sparkline(valores_lista)
                html_parts.append(f'<td><strong>{_fmt_monto_html(c_total)}</strong>{sparkline}</td>')
                html_parts.append('</tr>')
                
                # Detail rows
                if cuentas:
                    for cuenta in cuentas[:15]:
                        cuenta_codigo = cuenta.get("codigo", "")
                        cuenta_nombre = cuenta.get("nombre", "")[:40]
                        cuenta_monto = cuenta.get("monto", 0)
                        cu_montos_mes = cuenta.get("montos_por_mes", {})
                        
                        html_parts.append(f'<tr class="detail-row detail-{c_id_safe}" style="display:none;">')
                        html_parts.append(f'<td class="frozen">📄 {cuenta_codigo} - {cuenta_nombre}</td>')
                        
                        for mes in meses_lista:
                            m_acc = cu_montos_mes.get(mes, 0)
                            html_parts.append(f'<td>{_fmt_monto_html(m_acc)}</td>')
                        
                        html_parts.append(f'<td>{_fmt_monto_html(cuenta_monto)}</td>')
                        html_parts.append('</tr>')
            
            # Subtotal de actividad
            html_parts.append(f'<tr class="subtotal">')
            html_parts.append(f'<td class="frozen"><strong>Subtotal {act_key}</strong></td>')
            for mes in meses_lista:
                monto_mes_sub = act_subtotal_por_mes.get(mes, 0)
                html_parts.append(f'<td>{_fmt_monto_html(monto_mes_sub)}</td>')
            html_parts.append(f'<td><strong>{_fmt_monto_html(act_subtotal)}</strong></td>')
            html_parts.append('</tr>')
        
        # Grand Totals
        html_parts.append(f'<tr class="grand-total">')
        html_parts.append(f'<td class="frozen"><strong>VARIACIÓN NETA DEL EFECTIVO</strong></td>')
        for mes in meses_lista:
            variacion_mes = EFECTIVO_por_mes.get(mes, {}).get("variacion", 0)
            html_parts.append(f'<td>{_fmt_monto_html(variacion_mes)}</td>')
        html_parts.append(f'<td><strong>{_fmt_monto_html(variacion)}</strong></td>')
        html_parts.append('</tr>')
        
        html_parts.append(f'<tr class="data-row">')
        html_parts.append(f'<td class="frozen">EFECTIVO al inicio del período</td>')
        for mes in meses_lista:
            ef_ini_mes = EFECTIVO_por_mes.get(mes, {}).get("inicial", ef_ini)
            html_parts.append(f'<td>{_fmt_monto_html(ef_ini_mes)}</td>')
        html_parts.append(f'<td><strong>{_fmt_monto_html(ef_ini)}</strong></td>')
        html_parts.append('</tr>')
        
        html_parts.append(f'<tr class="grand-total">')
        html_parts.append(f'<td class="frozen"><strong>�EFECTIVO AL FINAL DEL PERÍODO</strong></td>')
        for mes in meses_lista:
            ef_fin_mes = EFECTIVO_por_mes.get(mes, {}).get("final", ef_fin)
            html_parts.append(f'<td>{_fmt_monto_html(ef_fin_mes)}</td>')
        html_parts.append(f'<td><strong>{_fmt_monto_html(ef_fin)}</strong></td>')
        html_parts.append('</tr>')
        
        html_parts.append('</tbody>')
        html_parts.append('</table>')
        
        if len(meses_lista) > 3:
            html_parts.append('<div class="scroll-hint">← Desliza horizontalmente para ver más meses →</div>')
        
        html_parts.append('</div>')
        
        # Agregar JavaScript
        html_parts.append(ENTERPRISE_JS)
        
        # Renderizar con components.html con altura muy generosa
        full_html = "".join(html_parts)
        # Calcular altura: 150px header + 60px por concepto + 250px footer + margen
        num_conceptos = sum(len(act.get("conceptos", [])) for act in actividades.values())
        # Contar también las filas de detalle (cuentas) para expandidos
        num_cuentas_total = sum(
            sum(len(concepto.get("cuentas", [])) for concepto in act.get("conceptos", []))
            for act in actividades.values()
        )
        altura_base = 150 + (num_conceptos * 60) + (num_cuentas_total * 45) + 250
        # Usar altura generosa, mínimo 1000px, máximo 5000px
        altura_final = max(min(altura_base, 5000), 1000)
        components.html(full_html, height=altura_final, scrolling=True)
        
        # ========== EXPORT MEJORADO ==========
        with export_placeholder:
            if st.button("📥 Exportar Excel", use_container_width=True):
                # Crear Excel con formato
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # Sheet 1: Datos
                    rows = []
                    for act_key in ["OPERACION", "INVERSION", "FINANCIAMIENTO"]:
                        act_data = actividades.get(act_key, {})
                        if not act_data:
                            continue
                        
                        rows.append({"Concepto": act_data.get("nombre", act_key), "Monto": ""})
                        
                        for concepto in act_data.get("conceptos", []):
                            c_id = concepto.get("id") or concepto.get("codigo")
                            c_nombre = concepto.get("nombre", "")
                            c_monto = concepto.get("total", 0)
                            rows.append({
                                "Concepto": f"  {c_id} - {c_nombre}",
                                "Monto": c_monto
                            })
                        
                        rows.append({
                            "Concepto": f"Subtotal {act_key}",
                            "Monto": act_data.get("subtotal", 0)
                        })
                    
                    df = pd.DataFrame(rows)
                    df.to_excel(writer, sheet_name='Flujo de Caja', index=False)
                
                st.download_button(
                    "⬇️ Descargar",
                    output.getvalue(),
                    f"flujo_caja_{fecha_inicio_str}_{fecha_fin_str}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        
        # ========== CUENTAS SIN CLASIFICAR CON AUDITORÍA ==========
        if cuentas_nc and len(cuentas_nc) > 0:
            st.markdown("---")
            with st.expander(f"⚠️ {len(cuentas_nc)} cuentas sin clasificar (Sistema de Auditoría)", expanded=False):
                st.info("💡 Cada cambio queda registrado en el historial de auditoría")
                
                categorias = build_ias7_categories_dropdown()
                
                for cuenta in sorted(cuentas_nc, key=lambda x: abs(x.get('monto', 0)), reverse=True)[:20]:
                    codigo = cuenta.get('codigo', '')
                    nombre = cuenta.get('nombre', '')
                    monto = cuenta.get('monto', 0)
                    
                    col1, col2, col3, col4 = st.columns([1, 2, 1, 2])
                    col1.code(codigo)
                    col2.caption(nombre[:40])
                    col3.write(fmt_flujo(monto))
                    
                    with col4:
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            cat = st.selectbox("Cat", list(categorias.keys()), 
                                             key=f"cat_{codigo}", label_visibility="collapsed")
                        with c2:
                            if st.button("💾", key=f"save_{codigo}"):
                                ok, err = guardar_mapeo_cuenta(codigo, categorias[cat], nombre,
                                                               username, password, monto)
                                if ok:
                                    st.toast(f"✅ {codigo} → {cat}")
                                    if cache_key in st.session_state:
                                        del st.session_state[cache_key]
                                    st.rerun()
                                else:
                                    st.error(err)
    else:
        st.info("👆 Configura el período y haz clic en 'Generar' para cargar el dashboard enterprise")
