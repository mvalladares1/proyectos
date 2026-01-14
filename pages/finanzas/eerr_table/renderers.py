"""
Renderizadores para la tabla de Estado de Resultados expandible.
Genera HTML con filas expandibles de 3 niveles.
"""
from typing import Dict, List, Any
from .constants import ESTRUCTURA_EERR, MESES_NOMBRES, CATEGORIA_MAP, EERR_COLORS
from .styles import SVG_CHEVRON


def fmt_monto(valor: float) -> str:
    """Formatea un monto en formato chileno con color."""
    if valor == 0:
        return '<span class="val-zero">$0</span>'
    
    abs_val = abs(valor)
    if abs_val >= 1_000_000_000:
        formatted = f"${abs_val / 1_000_000_000:,.1f}B"
    elif abs_val >= 1_000_000:
        formatted = f"${abs_val / 1_000_000:,.1f}M"
    else:
        formatted = f"${abs_val:,.0f}"
    
    if valor < 0:
        return f'<span class="val-negative">-{formatted}</span>'
    else:
        return f'<span class="val-positive">{formatted}</span>'


def generate_sparkline(valores: List[float]) -> str:
    """Genera un mini sparkline SVG."""
    if not valores or all(v == 0 for v in valores):
        return ""
    
    max_val = max(abs(v) for v in valores) or 1
    width = 60
    height = 20
    points = []
    
    for i, v in enumerate(valores):
        x = (i / max(len(valores) - 1, 1)) * width
        y = height - ((v / max_val + 1) / 2 * height)
        points.append(f"{x},{y}")
    
    path = "M" + " L".join(points)
    return f'''
    <span class="sparkline-mini">
        <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">
            <path d="{path}" fill="none" stroke="#60a5fa" stroke-width="1.5"/>
        </svg>
    </span>
    '''


def render_eerr_table(
    estructura: Dict[str, Any],
    datos_mensuales: Dict[str, Dict[str, float]],
    meses_lista: List[str],
    ppto_mensual: Dict[str, Dict[str, float]] = None
) -> str:
    """
    Genera la tabla HTML del Estado de Resultados expandible.
    
    Args:
        estructura: Dict con estructura jerárquica de cuentas {categoria: {subcategorias: {...}}}
        datos_mensuales: Dict con datos reales por mes {YYYY-MM: {categoria: valor}}
        meses_lista: Lista de meses a mostrar ["2026-01", "2026-02", ...]
        ppto_mensual: Opcional, Dict con presupuesto mensual
        
    Returns:
        String HTML con la tabla completa
    """
    html_parts = []
    
    # Calcular valores acumulados para subtotales
    valores_calculados = calcular_subtotales(estructura, datos_mensuales, meses_lista)
    
    # Inicio de tabla
    html_parts.append('<div class="eerr-container">')
    html_parts.append('<table class="eerr-table">')
    
    # Header
    html_parts.append('<thead><tr>')
    html_parts.append('<th class="frozen">Concepto</th>')
    for mes in meses_lista:
        mes_num = mes.split("-")[1] if "-" in mes else mes
        mes_nombre = MESES_NOMBRES.get(mes_num, mes)
        html_parts.append(f'<th>{mes_nombre}</th>')
    html_parts.append('<th class="col-total">TOTAL YTD</th>')
    html_parts.append('</tr></thead>')
    
    # Body
    html_parts.append('<tbody>')
    
    for item in ESTRUCTURA_EERR:
        item_id = item["id"]
        item_nombre = item["nombre"]
        item_tipo = item["tipo"]
        item_icono = item.get("icono", "")
        is_calculado = item.get("calculado", False)
        
        if is_calculado:
            # Fila de subtotal calculado
            row_class = "total-row" if item_tipo == "TOTAL" else "subtotal-row"
            valores_mes, total = valores_calculados.get(item_id, ({}, 0))
            
            html_parts.append(f'<tr class="{row_class}">')
            html_parts.append(f'<td class="frozen">{item_icono} {item_id} - {item_nombre}</td>')
            
            valores_lista = []
            for mes in meses_lista:
                val = valores_mes.get(mes, 0)
                valores_lista.append(val)
                html_parts.append(f'<td>{fmt_monto(val)}</td>')
            
            sparkline = generate_sparkline(valores_lista)
            html_parts.append(f'<td class="col-total">{fmt_monto(total)}{sparkline}</td>')
            html_parts.append('</tr>')
        else:
            # Fila de categoría con expansión
            cat_key = CATEGORIA_MAP.get(item_id, f"{item_id} - {item_nombre}")
            cat_data = estructura.get(cat_key, {})
            subcats = cat_data.get("subcategorias", {})
            has_children = len(subcats) > 0
            
            # Calcular totales de la categoría
            cat_total = cat_data.get("total", 0)
            cat_totales_mes = {}
            for mes in meses_lista:
                mes_key = mes if "-" in mes else f"2026-{mes}"
                cat_totales_mes[mes] = datos_mensuales.get(mes_key, {}).get(cat_key, 0)
            
            row_id = f"cat_{item_id}"
            expand_icon = f'<span class="expand-icon" onclick="toggleEerrRow(\'{row_id}\')">{SVG_CHEVRON}</span>' if has_children else '<span style="width:28px;display:inline-block;"></span>'
            
            html_parts.append(f'<tr class="cat-row" data-row-id="{row_id}">')
            html_parts.append(f'<td class="frozen">{expand_icon}{item_icono} {item_id} - {item_nombre}</td>')
            
            valores_lista = []
            for mes in meses_lista:
                val = cat_totales_mes.get(mes, 0)
                valores_lista.append(val)
                html_parts.append(f'<td>{fmt_monto(val)}</td>')
            
            sparkline = generate_sparkline(valores_lista)
            html_parts.append(f'<td class="col-total">{fmt_monto(cat_total)}{sparkline}</td>')
            html_parts.append('</tr>')
            
            # Subcategorías (nivel 2) - inicialmente ocultas
            for subcat_nombre, subcat_data in sorted(subcats.items()):
                subcat_total = subcat_data.get("total", 0)
                subcat_subcats = subcat_data.get("subcategorias", {})
                has_level3 = len(subcat_subcats) > 0
                
                subcat_id = f"{row_id}_{subcat_nombre[:10].replace(' ', '_')}"
                expand_icon_sub = f'<span class="expand-icon" onclick="toggleEerrRow(\'{subcat_id}\')">{SVG_CHEVRON}</span>' if has_level3 else '<span style="width:28px;display:inline-block;"></span>'
                
                html_parts.append(f'<tr class="subcat-row hidden-row child-of-{row_id}" data-row-id="{subcat_id}">')
                html_parts.append(f'<td class="frozen">{expand_icon_sub}↳ {subcat_nombre[:40]}</td>')
                
                # Valores mensuales de subcategoría (simplificado - solo total)
                for mes in meses_lista:
                    html_parts.append('<td>-</td>')
                
                html_parts.append(f'<td class="col-total">{fmt_monto(subcat_total)}</td>')
                html_parts.append('</tr>')
                
                # Nivel 3: Subcategorías internas o cuentas
                if has_level3:
                    for n3_nombre, n3_data in sorted(subcat_subcats.items()):
                        n3_total = n3_data.get("total", 0)
                        
                        html_parts.append(f'<tr class="cuenta-row hidden-row child-of-{subcat_id}">')
                        html_parts.append(f'<td class="frozen">📄 {n3_nombre[:35]}</td>')
                        
                        for mes in meses_lista:
                            html_parts.append('<td>-</td>')
                        
                        html_parts.append(f'<td class="col-total">{fmt_monto(n3_total)}</td>')
                        html_parts.append('</tr>')
                else:
                    # Cuentas directas en nivel 2
                    cuentas = subcat_data.get("cuentas", {})
                    for cuenta_nombre, cuenta_monto in sorted(cuentas.items(), key=lambda x: abs(x[1]), reverse=True)[:10]:
                        html_parts.append(f'<tr class="cuenta-row hidden-row child-of-{subcat_id}">')
                        html_parts.append(f'<td class="frozen">📄 {cuenta_nombre[:35]}</td>')
                        
                        for mes in meses_lista:
                            html_parts.append('<td>-</td>')
                        
                        html_parts.append(f'<td class="col-total">{fmt_monto(cuenta_monto)}</td>')
                        html_parts.append('</tr>')
    
    html_parts.append('</tbody>')
    html_parts.append('</table>')
    html_parts.append('</div>')
    
    return "\n".join(html_parts)


def calcular_subtotales(
    estructura: Dict[str, Any],
    datos_mensuales: Dict[str, Dict[str, float]],
    meses_lista: List[str]
) -> Dict[str, tuple]:
    """
    Calcula los valores de subtotales (filas calculadas como UTILIDAD BRUTA, etc.).
    
    Returns:
        Dict {id: ({mes: valor}, total)}
    """
    resultados = {}
    
    # Obtener valores base por categoría
    def get_cat_value(cat_id: str, mes: str) -> float:
        cat_key = CATEGORIA_MAP.get(cat_id, f"{cat_id} - {ESTRUCTURA_EERR[int(cat_id)-1]['nombre']}")
        mes_key = mes if "-" in mes else f"2026-{mes}"
        return datos_mensuales.get(mes_key, {}).get(cat_key, 0)
    
    def get_cat_total(cat_id: str) -> float:
        cat_key = CATEGORIA_MAP.get(cat_id, f"{cat_id} - {ESTRUCTURA_EERR[int(cat_id)-1]['nombre']}")
        return estructura.get(cat_key, {}).get("total", 0)
    
    # 3 - UTILIDAD BRUTA = 1 - 2
    ub_mes = {mes: get_cat_value("1", mes) - get_cat_value("2", mes) for mes in meses_lista}
    ub_total = get_cat_total("1") - get_cat_total("2")
    resultados["3"] = (ub_mes, ub_total)
    
    # 5 - MARGEN DE CONTRIBUCIÓN = 3 - 4
    mc_mes = {mes: ub_mes[mes] - get_cat_value("4", mes) for mes in meses_lista}
    mc_total = ub_total - get_cat_total("4")
    resultados["5"] = (mc_mes, mc_total)
    
    # 7 - EBIT = 5 - 6
    ebit_mes = {mes: mc_mes[mes] - get_cat_value("6", mes) for mes in meses_lista}
    ebit_total = mc_total - get_cat_total("6")
    resultados["7"] = (ebit_mes, ebit_total)
    
    # 9 - UTIL ANTES NO OP = 7 - 8
    uano_mes = {mes: ebit_mes[mes] - get_cat_value("8", mes) for mes in meses_lista}
    uano_total = ebit_total - get_cat_total("8")
    resultados["9"] = (uano_mes, uano_total)
    
    # 12 - RESULTADO NO OP = 10 - 11
    rno_mes = {mes: get_cat_value("10", mes) - get_cat_value("11", mes) for mes in meses_lista}
    rno_total = get_cat_total("10") - get_cat_total("11")
    resultados["12"] = (rno_mes, rno_total)
    
    # 13 - UTIL ANTES IMPUESTOS = 9 + 12
    uai_mes = {mes: uano_mes[mes] + rno_mes[mes] for mes in meses_lista}
    uai_total = uano_total + rno_total
    resultados["13"] = (uai_mes, uai_total)
    
    return resultados
