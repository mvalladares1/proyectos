# Módulo Flujo de Caja - Documentación

## 📊 Descripción
Módulo modularizado del Estado de Flujo de Efectivo según NIIF IAS 7 (Método Directo)

## 📁 Estructura del Módulo

```
flujo_caja/
├── __init__.py         # Exports principales (26 líneas)
├── styles.py           # CSS Enterprise (440 líneas)
├── components.py       # JavaScript & SVG Icons (126 líneas)
├── formatters.py       # Funciones de formateo (63 líneas)
└── README.md           # Esta documentación
```

## 🎯 Uso

### Importación
```python
from .flujo_caja import (
    ENTERPRISE_CSS,
    ENTERPRISE_JS,
    SVG_ICONS,
    generate_sparkline,
    get_heatmap_class,
    fmt_monto_html,
    nombre_mes_corto
)
```

### Funciones Principales

#### `generate_sparkline(values: list) -> str`
Genera un gráfico SVG de tendencia inline
- **Parámetros**: `values` - Lista de valores numéricos
- **Retorna**: HTML string con SVG sparkline
- **Ejemplo**:
  ```python
  sparkline_html = generate_sparkline([100, 150, 120, 180])
  ```

#### `get_heatmap_class(value: float, max_abs: float) -> str`
Determina la clase CSS de heatmap según intensidad
- **Parámetros**: 
  - `value` - Valor a clasificar
  - `max_abs` - Valor máximo absoluto (para ratio)
- **Retorna**: Clase CSS ('heatmap-very-positive', 'heatmap-positive', etc.)
- **Ejemplo**:
  ```python
  heatmap_class = get_heatmap_class(250000, 1000000)  # -> 'heatmap-positive'
  ```

#### `fmt_monto_html(valor: float, include_class: bool = True) -> str`
Formatea montos con color condicional
- **Parámetros**:
  - `valor` - Monto numérico
  - `include_class` - Si incluir clases CSS (default: True)
- **Retorna**: HTML string con monto formateado
- **Ejemplo**:
  ```python
  html = fmt_monto_html(150000)  # -> '<span class="monto-positivo">$150,000</span>'
  ```

#### `nombre_mes_corto(mes_str: str) -> str`
Convierte formato de mes a abreviación
- **Parámetros**: `mes_str` - Formato '2026-01' o '2026-W01'
- **Retorna**: String abreviado ('Ene 26' o 'W01-26')
- **Ejemplo**:
  ```python
  corto = nombre_mes_corto('2026-03')  # -> 'Mar 26'
  ```

## 🎨 Componentes CSS

### Scrollbar Personalizado
- Gradiente azul (#3b82f6 → #2563eb)
- Hover effect con glow
- Diseño premium corporativo

### Tooltips
- Fondo oscuro con borde azul
- Animación suave (opacity + visibility)
- Flecha indicadora

### Heatmap (5 niveles)
- `heatmap-very-positive` - Azul intenso (ratio > 0.6)
- `heatmap-positive` - Azul moderado (ratio > 0.2)
- `heatmap-neutral` - Gris (ratio ≈ 0)
- `heatmap-negative` - Rojo moderado (ratio < -0.2)
- `heatmap-very-negative` - Rojo intenso (ratio < -0.6)

### Indentación
- `.indent-1` - 28px
- `.indent-2` - 56px + borde azul
- `.indent-3` - 84px + borde gris
- `.indent-4` - 112px + borde gris claro

## 🚀 JavaScript Features

### Funciones Globales
- `toggleConcept(conceptId)` - Expande/colapsa filas detalle
- `expandAll()` / `collapseAll()` - Expande/colapsa todos
- `searchTable(term)` - Búsqueda en tiempo real
- `toggleFilter(activity)` - Filtro por tipo de actividad
- `addNote(conceptId, cellId)` - Agregar notas a celdas

### Drag & Drop
- Eventos: dragstart, dragover, dragleave, drop, dragend
- Clases: `.draggable`, `.dragging`, `.drop-target`

## 📈 Métricas de Reducción

| Métrica | Antes | Después | Reducción |
|---------|-------|---------|-----------|
| **Líneas totales** | 1,296 | 518 | **60%** |
| **CSS** | Inline | 440 líneas | Modularizado |
| **JavaScript** | Inline | 126 líneas | Modularizado |
| **Formatters** | Inline | 63 líneas | Modularizado |

## 🔧 Mantenimiento

### Agregar nuevos estilos
Editar: `flujo_caja/styles.py`

### Agregar nuevas funciones JS
Editar: `flujo_caja/components.py`

### Agregar nuevos formatters
Editar: `flujo_caja/formatters.py`

### Exportar nuevas funciones
Editar: `flujo_caja/__init__.py` → `__all__`

## 🎯 Estándares

- **Nomenclatura**: Snake_case para funciones Python
- **Indentación**: 4 espacios
- **CSS**: BEM-like naming (`.excel-table`, `.frozen`, `.heatmap-positive`)
- **JavaScript**: camelCase (expandAll, toggleConcept)
- **Colores**: Paleta azul (#3b82f6, #2563eb) + rojo (#ef4444, #dc2626) + verde (#10b981)

## 📝 Ejemplos de Uso Completo

```python
# En tab_flujo_caja.py
from .flujo_caja import (
    ENTERPRISE_CSS,
    ENTERPRISE_JS,
    SVG_ICONS,
    generate_sparkline,
    get_heatmap_class,
    fmt_monto_html,
    nombre_mes_corto
)

# Construir tabla HTML
html = f"""
{ENTERPRISE_CSS}
{ENTERPRISE_JS}
<table class="excel-table">
    <thead>
        <th class="frozen">Concepto</th>
        <th>{nombre_mes_corto('2026-01')}</th>
    </thead>
    <tbody>
        <tr class="data-row">
            <td class="frozen">Ventas</td>
            <td class="{get_heatmap_class(250000, 1000000)}">
                {fmt_monto_html(250000)}
            </td>
        </tr>
    </tbody>
</table>
"""

# Renderizar con Streamlit
components.html(html, height=600, scrolling=False)
```

## 🏆 Best Practices

1. **Siempre importar funciones necesarias** - No importar todo (*)
2. **Usar type hints** - Para mejor IntelliSense
3. **CSS mobile-first** - Aunque este dashboard es desktop
4. **JavaScript vanilla** - Sin dependencias externas
5. **HTML semántico** - Usar tags apropiados (thead, tbody, etc.)

---

**Última actualización**: 2026-01-XX  
**Versión**: 1.0 (Modularizada)  
**Mantenedor**: Río Futuro Dashboard Team
