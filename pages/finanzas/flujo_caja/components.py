"""
Componentes JavaScript y SVG para el Estado de Flujo de Efectivo
"""

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
    
    if (!rows.length || !parent) return;
    
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
