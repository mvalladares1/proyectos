"""
Módulo de Flujo de Caja - Estado de Flujo de Efectivo NIIF IAS 7

Estructura modular:
- styles.py: CSS y estilos visuales
- components.py: Componentes HTML/JS (tooltips, iconos, etc.)
- formatters.py: Funciones de formateo y utilidades
- render.py: Lógica principal de renderizado
"""
from .styles import ENTERPRISE_CSS
from .components import ENTERPRISE_JS, SVG_ICONS, MODAL_CSS, MODAL_HTML
from .formatters import (
    generate_sparkline,
    get_heatmap_class,
    fmt_monto_html,
    nombre_mes_corto,
    es_vista_semanal,
    agrupar_semanas_por_mes,
    nombre_semana_corto
)

__all__ = [
    'ENTERPRISE_CSS',
    'ENTERPRISE_JS',
    'SVG_ICONS',
    'MODAL_CSS',
    'MODAL_HTML',
    'generate_sparkline',
    'get_heatmap_class',
    'fmt_monto_html',
    'nombre_mes_corto',
    'es_vista_semanal',
    'agrupar_semanas_por_mes',
    'nombre_semana_corto'
]
