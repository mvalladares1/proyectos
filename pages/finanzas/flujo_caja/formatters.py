"""
Funciones de formateo y utilidades para Flujo de Caja
"""

def generate_sparkline(values: list) -> str:
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


def get_heatmap_class(value: float, max_abs: float) -> str:
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


def fmt_monto_html(valor: float, include_class: bool = True) -> str:
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


def nombre_mes_corto(mes_str: str) -> str:
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
