"""
Componentes JavaScript y SVG para el Estado de Flujo de Efectivo
"""

ENTERPRISE_JS = """
<script src="https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.full.min.js"></script>
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
    
    if (!rows.length || !parent) return;
    
    const isExpanded = expandedConcepts.has(conceptId);
    
    rows.forEach(row => {
        row.style.display = isExpanded ? 'none' : 'table-row';
        
        // Si estamos colapsando, cerrar TODOS los niveles hijos
        if (isExpanded) {
            const classes = Array.from(row.classList);
            const cuentaClass = classes.find(c => c.startsWith('cuenta-'));
            
            if (cuentaClass) {
                const cuentaId = cuentaClass.replace('cuenta-', '');
                // Ocultar nivel 3 (categorías/etiquetas)
                const etiquetasRows = document.querySelectorAll('.etiqueta-' + cuentaId);
                etiquetasRows.forEach(etiqRow => {
                    etiqRow.style.display = 'none';
                });
                // Ocultar nivel 4 (sub-etiquetas/proveedores)
                const subEtiquetasRows = document.querySelectorAll('.sub-etiqueta-of-' + cuentaId);
                subEtiquetasRows.forEach(subRow => {
                    subRow.style.display = 'none';
                });
                // Limpiar estados expandidos
                expandedEtiquetas.delete(cuentaId);
                // Limpiar todas las categorías expandidas de esta cuenta
                expandedCategorias.forEach(key => {
                    if (key.startsWith(cuentaId + '_')) {
                        expandedCategorias.delete(key);
                    }
                });
            }
        }
    });
    
    if (isExpanded) {
        expandedConcepts.delete(conceptId);
        parent.classList.remove('expanded');
    } else {
        expandedConcepts.add(conceptId);
        parent.classList.add('expanded');
    }
}

// Estado para etiquetas expandidas
let expandedEtiquetas = new Set();

// ============ TOGGLE ETIQUETAS (Nivel 2 -> Nivel 3) ============
function toggleEtiquetas(cuentaId) {
    const rows = document.querySelectorAll('.etiqueta-' + cuentaId);
    
    if (!rows.length) return;
    
    const isExpanded = expandedEtiquetas.has(cuentaId);
    
    rows.forEach(row => {
        row.style.display = isExpanded ? 'none' : 'table-row';
    });
    
    // Si estamos colapsando nivel 2, también cerrar TODOS los proveedores (nivel 4)
    if (isExpanded) {
        const subEtiquetasRows = document.querySelectorAll('.sub-etiqueta-of-' + cuentaId);
        subEtiquetasRows.forEach(subRow => {
            subRow.style.display = 'none';
        });
        // Limpiar categorías expandidas de esta cuenta
        expandedCategorias.forEach(key => {
            if (key.startsWith(cuentaId + '_')) {
                expandedCategorias.delete(key);
            }
        });
    }
    
    if (isExpanded) {
        expandedEtiquetas.delete(cuentaId);
    } else {
        expandedEtiquetas.add(cuentaId);
    }
}

// Estado para categorías expandidas (Nivel 3 con sub_etiquetas de nivel 4)
let expandedCategorias = new Set();

// ============ TOGGLE CATEGORIA (Nivel 3 → Nivel 4) ============
function toggleCategoria(categoriaId, cuentaId) {
    // Seleccionar solo las sub-etiquetas (proveedores) de esta categoría Y esta cuenta
    const uniqueId = cuentaId + '__' + categoriaId;
    const rows = document.querySelectorAll('.sub-etiqueta-' + uniqueId);
    
    if (!rows.length) return;
    
    const key = cuentaId + '_' + categoriaId;
    const isExpanded = expandedCategorias.has(key);
    
    rows.forEach(row => {
        row.style.display = isExpanded ? 'none' : 'table-row';
    });
    
    if (isExpanded) {
        expandedCategorias.delete(key);
    } else {
        expandedCategorias.add(key);
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

// ============ EXPORT VISTA ACTUAL (XLSX) ============
function exportVisibleTableToExcel() {
    const table = document.querySelector('.excel-table');
    if (!table) return;

    const cleanText = (el) => {
        const clone = el.cloneNode(true);
        clone.querySelectorAll('.icon-expand, .tooltip-text, svg').forEach(n => n.remove());
        return (clone.textContent || '').replace(/\\s+/g, ' ').trim();
    };

    // Parsear número (quitar separadores de miles, manejar negativos con paréntesis)
    const parseNum = (s) => {
        if (!s) return s;
        let clean = s.replace(/\\s/g, '');
        let neg = false;
        if (clean.startsWith('(') && clean.endsWith(')')) {
            neg = true;
            clean = clean.slice(1, -1);
        }
        // Quitar puntos de miles y cambiar coma decimal
        clean = clean.replace(/\\./g, '').replace(',', '.');
        const n = parseFloat(clean);
        if (isNaN(n)) return s;
        return neg ? -n : n;
    };

    // Headers visibles (sin TOTAL izquierda)
    const theadRows = Array.from(table.querySelectorAll('thead tr')).filter(tr => !tr.classList.contains('toolbar-row'));
    let headerRowsForXlsx = [];
    if (theadRows.length >= 2) {
        // Semanal: dos filas de encabezado (Meses + Semanas)
        const monthRow = ['CONCEPTO'];
        const monthCells = Array.from(theadRows[0].querySelectorAll('th'));
        monthCells.forEach(th => {
            if (th.classList.contains('frozen') || th.classList.contains('frozen-total-left')) return;
            const text = cleanText(th);
            const span = parseInt(th.getAttribute('colspan') || '1', 10);
            if (!text) return;
            if (text.toUpperCase() === 'TOTAL') {
                monthRow.push('TOTAL');
            } else {
                monthRow.push(text);
                for (let i = 1; i < span; i++) monthRow.push('');
            }
        });
        const weekCells = Array.from(theadRows[1].querySelectorAll('th'));
        const weeks = weekCells.map(cleanText).filter(Boolean);
        const weekRow = ['CONCEPTO', ...weeks, 'TOTAL'];
        headerRowsForXlsx = [monthRow, weekRow];
    } else {
        // Mensual
        const ths = Array.from(table.querySelectorAll('thead tr th'));
        const raw = ths.map(cleanText).filter(Boolean);
        if (raw.length >= 3) {
            headerRowsForXlsx = [[raw[0], ...raw.slice(2)]];
        } else {
            headerRowsForXlsx = [raw];
        }
    }

    // Construir datos (array de arrays)
    const allRows = [];
    headerRowsForXlsx.forEach(row => allRows.push(row));

    // Filas visibles del body
    const bodyRows = Array.from(table.querySelectorAll('tbody tr')).filter(row => {
        const style = row.getAttribute('style') || '';
        return !style.includes('display:none');
    });

    bodyRows.forEach(row => {
        const cells = Array.from(row.querySelectorAll('td'));
        if (!cells.length) return;
        const values = cells.map(cleanText);
        let exportValues;
        if (values.length >= 3) {
            exportValues = [values[0], ...values.slice(2)];
        } else {
            exportValues = values;
        }
        // Convertir valores numéricos
        const parsed = exportValues.map((v, i) => i === 0 ? v : parseNum(v));
        allRows.push(parsed);
    });

    // Crear workbook con SheetJS
    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.aoa_to_sheet(allRows);

    // Aplicar formato de número a celdas numéricas
    const numFmt = '#,##0';
    const range = XLSX.utils.decode_range(ws['!ref'] || 'A1');
    const headerCount = headerRowsForXlsx.length;
    for (let r = headerCount; r <= range.e.r; r++) {
        for (let c = 1; c <= range.e.c; c++) {
            const cell = ws[XLSX.utils.encode_cell({r, c})];
            if (cell && typeof cell.v === 'number') {
                cell.z = numFmt;
                cell.t = 'n';
            }
        }
    }

    // Ajustar anchos de columna
    const colWidths = [];
    for (let c = 0; c <= range.e.c; c++) {
        let maxLen = 10;
        for (let r = 0; r <= Math.min(range.e.r, 100); r++) {
            const cell = ws[XLSX.utils.encode_cell({r, c})];
            if (cell) {
                const len = String(cell.v || '').length;
                if (len > maxLen) maxLen = len;
            }
        }
        colWidths.push({wch: Math.min(maxLen + 2, 30)});
    }
    ws['!cols'] = colWidths;

    XLSX.utils.book_append_sheet(wb, ws, 'Flujo de Caja');

    // Generar y descargar
    const now = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    const filename = `flujo_caja_vista_${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}.xlsx`;

    XLSX.writeFile(wb, filename);
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
    
    // Auto-ajustar altura del iframe al contenido
    updateFrameHeight();
});

// ============ AUTO-HEIGHT IFRAME ============
function updateFrameHeight() {
    // Obtener altura real del contenido
    const body = document.body;
    const html = document.documentElement;
    const height = Math.max(
        body.scrollHeight, body.offsetHeight,
        html.clientHeight, html.scrollHeight, html.offsetHeight
    );
    
    // Comunicar altura al padre de Streamlit (con padding extra)
    if (window.parent && window.parent.postMessage) {
        window.parent.postMessage({
            type: 'streamlit:setFrameHeight',
            height: height + 50
        }, '*');
    }
    
    // También intentar usar la API de Streamlit directamente si está disponible
    if (typeof Streamlit !== 'undefined' && Streamlit.setFrameHeight) {
        Streamlit.setFrameHeight(height + 50);
    }
}

// Observar cambios en el DOM para re-calcular altura cuando se expanden/contraen filas
const resizeObserver = new ResizeObserver(entries => {
    updateFrameHeight();
});

// Observar cambios en el body
if (document.body) {
    resizeObserver.observe(document.body);
}

// También actualizar altura después de cada toggle
const originalToggleConcept = toggleConcept;
toggleConcept = function(conceptId) {
    originalToggleConcept(conceptId);
    setTimeout(updateFrameHeight, 100);
};

const originalToggleEtiquetas = toggleEtiquetas;
toggleEtiquetas = function(cuentaId) {
    originalToggleEtiquetas(cuentaId);
    setTimeout(updateFrameHeight, 100);
};

const originalToggleCategoria = toggleCategoria;
toggleCategoria = function(categoriaId, cuentaId) {
    originalToggleCategoria(categoriaId, cuentaId);
    setTimeout(updateFrameHeight, 100);
};

// ============ MODAL FACTURAS ============
let facturasData = {};
let composicionData = {};

function setFacturasData(data) {
    facturasData = data;
}

function setComposicionData(data) {
    composicionData = data;
}

// Mapeo de iconos por estado de factura
const ESTADO_ICONS = {
    'Facturas Pagadas': '✅',
    'Facturas Parcialmente Pagadas': '⏳',
    'Facturas En Proceso de Pago': '🔄',
    'Facturas No Pagadas': '❌',
    'Facturas Revertidas': '↩️'
};

// Formatear fecha: 2025-10-01 -> 01-Oct-2025
function formatFecha(fechaStr) {
    if (!fechaStr || fechaStr === '-') return '-';
    try {
        const date = new Date(fechaStr + 'T00:00:00');
        const meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
        const dia = String(date.getDate()).padStart(2, '0');
        const mes = meses[date.getMonth()];
        const year = date.getFullYear();
        return `${dia}-${mes}-${year}`;
    } catch(e) {
        return fechaStr;
    }
}

// Generar link a Odoo para factura
function getOdooLink(facturaName, facturaId) {
    // URL base de Odoo Río Futuro
    if (facturaId) {
        return `https://riofuturo.server98c6e.oerpondemand.net/web#id=${facturaId}&menu_id=489&cids=1&action=232&active_id=1&model=account.move&view_type=form`;
    }
    return null;
}

function showFacturasModal(estadoNombre, periodo, cuentaCodigo) {
    const key = estadoNombre + '_' + cuentaCodigo;
    const facturas = facturasData[key] || [];
    
    // Detectar si es semana (contiene W) o mes
    const esSemana = periodo.includes('W');
    
    // Filtrar facturas por período seleccionado
    const facturasMes = facturas.filter(f => {
        if (!f.montos_por_mes) return false;
        const montoMes = f.montos_por_mes[periodo];
        return montoMes && montoMes !== 0;
    });
    
    const modal = document.getElementById('facturas-modal');
    const title = document.getElementById('modal-title');
    const body = document.getElementById('modal-body');
    
    // Formatear nombre del período - usar el período real, NO basado en fechas de facturas
    let periodoNombre;
    if (esSemana) {
        const parts = periodo.replace('-W', 'W').split('W');
        const year = parts[0];
        const week = parts[1];
        periodoNombre = `Semana ${parseInt(week)}, ${year}`;
    } else {
        // Período mensual: 2025-10 -> Octubre de 2025
        const [year, month] = periodo.split('-');
        const meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                       'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
        periodoNombre = `${meses[parseInt(month) - 1]} de ${year}`;
    }
    
    // Obtener icono del estado
    const icon = ESTADO_ICONS[estadoNombre] || '📋';
    
    title.innerHTML = `<span style="margin-right: 8px;">${icon}</span><strong>${estadoNombre}</strong> - ${periodoNombre}`;
    
    if (facturasMes.length === 0) {
        body.innerHTML = '<p style="text-align: center; color: #888; padding: 20px;">No hay facturas para este período</p>';
    } else {
        // Ordenar facturas por monto (mayor a menor en valor absoluto)
        facturasMes.sort((a, b) => Math.abs(b.montos_por_mes[periodo] || 0) - Math.abs(a.montos_por_mes[periodo] || 0));
        
        let tableHTML = `
            <table class="modal-table">
                <thead>
                    <tr>
                        <th>Factura</th>
                        <th>Fecha</th>
                        <th style="text-align: right;">Monto Período</th>
                        <th style="text-align: right;">Monto Total</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        let totalMes = 0;
        facturasMes.forEach((f, idx) => {
            const montoMes = f.montos_por_mes[periodo] || 0;
            totalMes += montoMes;
            const fmtMontoMes = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format(montoMes);
            const fmtMontoTotal = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format(f.monto);
            
            // Generar link a Odoo
            const odooLink = f.move_id ? getOdooLink(f.nombre, f.move_id) : null;
            const nombreHTML = odooLink 
                ? `<a href="${odooLink}" target="_blank" style="color: #60a5fa; text-decoration: none; font-weight: bold;" title="Abrir en Odoo">${f.nombre} 🔗</a>`
                : `<strong>${f.nombre}</strong>`;
            
            // Fila alternada
            const rowBg = idx % 2 === 0 ? '' : 'background: rgba(45, 55, 72, 0.5);';
            
            tableHTML += `
                <tr style="${rowBg}">
                    <td>${nombreHTML}</td>
                    <td>${formatFecha(f.fecha)}</td>
                    <td style="text-align: right; color: ${montoMes >= 0 ? '#00e676' : '#ff5252'};">${fmtMontoMes}</td>
                    <td style="text-align: right;">${fmtMontoTotal}</td>
                </tr>
            `;
        });
        
        const fmtTotalMes = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format(totalMes);
        tableHTML += `
                </tbody>
                <tfoot>
                    <tr style="font-weight: bold; background: linear-gradient(135deg, #2d3748 0%, #1e293b 100%);">
                        <td colspan="2">📊 Total ${facturasMes.length} factura${facturasMes.length !== 1 ? 's' : ''}</td>
                        <td style="text-align: right; color: ${totalMes >= 0 ? '#00e676' : '#ff5252'};">${fmtTotalMes}</td>
                        <td></td>
                    </tr>
                </tfoot>
            </table>
        `;
        body.innerHTML = tableHTML;
    }
    
    modal.style.display = 'flex';
}

function closeFacturasModal() {
    const modal = document.getElementById('facturas-modal');
    modal.style.display = 'none';
}

// ============ MODAL COMPOSICIÓN ============
function showComposicionModal(conceptoId, mes) {
    console.log('[Modal] Abriendo composición:', conceptoId, mes);
    console.log('[Modal] Datos disponibles:', Object.keys(composicionData));
    
    const cuentas = composicionData[conceptoId] || [];
    console.log('[Modal] Cuentas para concepto:', cuentas.length);
    
    const modal = document.getElementById('composicion-modal');
    const overlay = document.getElementById('composicion-modal-overlay');
    const title = document.getElementById('composicion-modal-title');
    const body = document.getElementById('composicion-modal-body');
    
    if (!modal || !overlay || !title || !body) {
        console.error('[Modal] Elementos no encontrados');
        return;
    }
    
    // Formatear nombre del período
    let periodoNombre;
    if (mes.includes('W')) {
        const parts = mes.replace('-W', 'W').split('W');
        const year = parts[0];
        const week = parts[1];
        periodoNombre = `Semana ${parseInt(week)}, ${year}`;
    } else {
        const [year, month] = mes.split('-');
        const meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                       'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
        periodoNombre = `${meses[parseInt(month) - 1]} de ${year}`;
    }
    
    title.innerHTML = `<strong>${conceptoId}</strong> - ${periodoNombre}`;
    
    if (cuentas.length === 0) {
        body.innerHTML = '<p style="text-align: center; color: #888; padding: 20px;">No hay cuentas para mostrar</p>';
    } else {
        // Filtrar cuentas que tienen monto en este mes
        const cuentasMes = cuentas.filter(c => {
            const montos = c.montos_por_mes || {};
            const monto = montos[mes] || 0;
            return monto !== 0;
        });
        
        if (cuentasMes.length === 0) {
            body.innerHTML = '<p style="text-align: center; color: #888; padding: 20px;">No hay movimientos en este período</p>';
        } else {
            // Ordenar por monto absoluto
            cuentasMes.sort((a, b) => {
                const montoA = Math.abs((a.montos_por_mes || {})[mes] || 0);
                const montoB = Math.abs((b.montos_por_mes || {})[mes] || 0);
                return montoB - montoA;
            });
            
            // Calcular total
            let totalMes = 0;
            cuentasMes.forEach(c => {
                totalMes += (c.montos_por_mes || {})[mes] || 0;
            });
            
            let tableHTML = `
                <table class="modal-table">
                    <thead>
                        <tr>
                            <th style="width: 120px;">Código</th>
                            <th>Nombre</th>
                            <th style="width: 140px; text-align: right;">Monto</th>
                            <th style="width: 80px; text-align: right;">% Total</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            const divisor = Math.abs(totalMes) || 1;
            
            cuentasMes.forEach((cuenta, idx) => {
                const codigo = cuenta.codigo || '';
                const nombre = cuenta.nombre || '';
                const monto = (cuenta.montos_por_mes || {})[mes] || 0;
                const pct = (Math.abs(monto) / divisor * 100).toFixed(1);
                
                const fmtMonto = new Intl.NumberFormat('es-CL', { 
                    style: 'currency', 
                    currency: 'CLP', 
                    maximumFractionDigits: 0 
                }).format(monto);
                
                const rowBg = idx % 2 === 0 ? '' : 'background: rgba(45, 55, 72, 0.5);';
                
                tableHTML += `
                    <tr style="${rowBg}">
                        <td style="font-family: monospace; color: #94a3b8;">${codigo}</td>
                        <td>${nombre}</td>
                        <td style="text-align: right; color: ${monto >= 0 ? '#00e676' : '#ff5252'};">${fmtMonto}</td>
                        <td style="text-align: right; color: #94a3b8;">${pct}%</td>
                    </tr>
                `;
            });
            
            const fmtTotal = new Intl.NumberFormat('es-CL', { 
                style: 'currency', 
                currency: 'CLP', 
                maximumFractionDigits: 0 
            }).format(totalMes);
            
            tableHTML += `
                    </tbody>
                    <tfoot>
                        <tr style="font-weight: bold; background: linear-gradient(135deg, #2d3748 0%, #1e293b 100%);">
                            <td colspan="2">📊 Total ${cuentasMes.length} cuenta${cuentasMes.length !== 1 ? 's' : ''}</td>
                            <td style="text-align: right; color: ${totalMes >= 0 ? '#00e676' : '#ff5252'};">${fmtTotal}</td>
                            <td style="text-align: right;">100%</td>
                        </tr>
                    </tfoot>
                </table>
            `;
            body.innerHTML = tableHTML;
        }
    }
    
    // Mostrar modal y overlay
    overlay.classList.add('show');
    modal.classList.add('show');
    console.log('[Modal] Modal mostrado');
}

function closeComposicionModal() {
    const modal = document.getElementById('composicion-modal');
    const overlay = document.getElementById('composicion-modal-overlay');
    
    if (modal) modal.classList.remove('show');
    if (overlay) overlay.classList.remove('show');
    
    console.log('[Modal] Modal cerrado');
}

// Cerrar modal al hacer clic fuera
document.addEventListener('click', function(e) {
    const modalFacturas = document.getElementById('facturas-modal');
    
    if (e.target === modalFacturas) {
        closeFacturasModal();
    }
});

// Cerrar modal con Escape
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeFacturasModal();
        closeComposicionModal();
    }
});
</script>
"""

# CSS adicional para el modal
MODAL_CSS = """
<style>
/* Modal de Facturas */
#facturas-modal {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.8);
    z-index: 9999;
    justify-content: center;
    align-items: center;
}

.modal-content {
    background: #1a1a2e;
    border-radius: 12px;
    max-width: 800px;
    width: 90%;
    max-height: 80vh;
    overflow: hidden;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
    border: 1px solid #333;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}

.modal-header h3 {
    margin: 0;
    font-size: 18px;
}

.modal-close {
    background: none;
    border: none;
    color: white;
    font-size: 28px;
    cursor: pointer;
    padding: 0;
    line-height: 1;
    opacity: 0.8;
    transition: opacity 0.2s;
}

.modal-close:hover {
    opacity: 1;
}

.modal-body {
    padding: 20px 24px;
    max-height: 60vh;
    overflow-y: auto;
}

/* Scrollbar celeste para el modal */
.modal-body::-webkit-scrollbar {
    width: 10px;
    background: #0a0e1a;
}

.modal-body::-webkit-scrollbar-track {
    background: #1e293b;
    border-radius: 8px;
}

.modal-body::-webkit-scrollbar-thumb {
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
    border-radius: 8px;
}

.modal-body::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%);
}

.modal-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}

.modal-table th {
    background: #2d3748;
    padding: 10px 12px;
    text-align: left;
    font-weight: 600;
    color: #a0aec0;
    border-bottom: 2px solid #4a5568;
    position: sticky;
    top: 0;
}

.modal-table td {
    padding: 10px 12px;
    border-bottom: 1px solid #2d3748;
    color: #e2e8f0;
}

.modal-table tbody tr:hover {
    background: #2d3748;
}

.modal-table tfoot td {
    border-top: 2px solid #4a5568;
}

/* Celda clickeable para mostrar modal */
.cell-clickable {
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;
}

.cell-clickable:hover {
    background: rgba(102, 126, 234, 0.4) !important;
    transform: scale(1.05);
    box-shadow: 0 0 10px rgba(102, 126, 234, 0.5);
    z-index: 10;
}

.cell-clickable:active {
    transform: scale(0.98);
}

/* Modal de composición de cuentas */
#composicion-modal {
    display: none;
    position: fixed;
    z-index: 10001;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 90%;
    max-width: 800px;
    max-height: 80vh;
}

#composicion-modal.show {
    display: block;
}

#composicion-modal-overlay {
    display: none;
    position: fixed;
    z-index: 10000;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(4px);
}

#composicion-modal-overlay.show {
    display: block;
}
</style>
"""

# HTML de los modales
MODAL_HTML = """
<div id="facturas-modal">
    <div class="modal-content">
        <div class="modal-header">
            <h3 id="modal-title">Detalle de Facturas</h3>
            <button class="modal-close" onclick="closeFacturasModal()">&times;</button>
        </div>
        <div class="modal-body" id="modal-body">
            <!-- Contenido dinámico -->
        </div>
    </div>
</div>

<div id="composicion-modal-overlay" onclick="closeComposicionModal()"></div>
<div id="composicion-modal">
    <div class="modal-content">
        <div class="modal-header">
            <h3 id="composicion-modal-title">Composición del Concepto</h3>
            <button class="modal-close" onclick="closeComposicionModal()">&times;</button>
        </div>
        <div class="modal-body" id="composicion-modal-body">
            <!-- Contenido dinámico -->
        </div>
    </div>
</div>
"""

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
