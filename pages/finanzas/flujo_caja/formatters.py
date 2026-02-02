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


def es_vista_semanal(periodos: list) -> bool:
    """Detecta si los períodos son semanas (contienen 'W' o formato semanal)."""
    if not periodos:
        return False
    # Formato semanal típico: "2025-W01" o "W01 2025" o contiene "W"
    first_period = str(periodos[0])
    return 'W' in first_period or '-W' in first_period


def agrupar_semanas_por_mes(semanas: list) -> dict:
    """
    Agrupa semanas por mes.
    Input: ['2025-W01', '2025-W02', ..., '2025-W05', '2025-W06', ...]
    Output: {
        'Ene 25': ['2025-W01', '2025-W02', '2025-W03', '2025-W04'],
        'Feb 25': ['2025-W05', '2025-W06', '2025-W07', '2025-W08'],
        ...
    }
    """
    from datetime import datetime, timedelta
    
    meses_nombres = {
        1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr",
        5: "May", 6: "Jun", 7: "Jul", 8: "Ago",
        9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
    }
    
    resultado = {}
    
    for semana in semanas:
        try:
            # Parsear semana ISO: "2025-W01" o "2025W01"
            semana_str = str(semana).replace('-W', 'W')  # Normalizar
            
            if 'W' in semana_str:
                # Formato ISO: 2025W01
                year = int(semana_str.split('W')[0].replace('-', ''))
                week = int(semana_str.split('W')[1])
                
                # Obtener fecha del primer día de esa semana
                fecha = datetime.strptime(f'{year}-W{week:02d}-1', '%G-W%V-%u')
                
                # Mes de esa semana
                mes = fecha.month
                year_short = str(fecha.year)[2:]
                mes_key = f"{meses_nombres[mes]} {year_short}"
                
                if mes_key not in resultado:
                    resultado[mes_key] = []
                resultado[mes_key].append(semana)
        except Exception as e:
            # Si no se puede parsear, ponerlo en "Otros"
            if "Otros" not in resultado:
                resultado["Otros"] = []
            resultado["Otros"].append(semana)
    
    return resultado


def nombre_semana_corto(semana_str: str) -> str:
    """Convierte '2025-W01' a 'S1'."""
    try:
        semana = str(semana_str).replace('-W', 'W')
        if 'W' in semana:
            week_num = int(semana.split('W')[1])
            # Calcular semana del mes (1-4/5)
            year = int(semana.split('W')[0].replace('-', ''))
            from datetime import datetime
            fecha = datetime.strptime(f'{year}-W{week_num:02d}-1', '%G-W%V-%u')
            # Semana del mes: ((día - 1) // 7) + 1
            week_of_month = ((fecha.day - 1) // 7) + 1
            return f"S{week_of_month}"
        return semana_str
    except:
        return semana_str
