"""
Tab: Flujo de Caja - Excel-Style Design
Estado de Flujo de Efectivo NIIF IAS 7 con layout mensualizado tipo Excel.
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
from datetime import datetime, timedelta
from calendar import monthrange
import io

from .shared import (
    FLUJO_CAJA_URL, fmt_flujo, fmt_numero, build_ias7_categories_dropdown,
    sugerir_categoria, guardar_mapeo_cuenta
)

# CSS para diseño profesional corporativo de alta gama
EXCEL_STYLE_CSS = """
<style>
/* Custom Scrollbar - Oscura y elegante */
.excel-container::-webkit-scrollbar {
    height: 12px;
    background: #0f172a;
}

.excel-container::-webkit-scrollbar-track {
    background: #1e293b;
    border-radius: 6px;
}

.excel-container::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, #475569 0%, #334155 100%);
    border-radius: 6px;
    border: 2px solid #1e293b;
}

.excel-container::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, #64748b 0%, #475569 100%);
}

/* Contenedor principal con scroll horizontal */
.excel-container {
    width: 100%;
    overflow-x: auto;
    overflow-y: visible;
    border: 2px solid #334155;
    border-radius: 12px;
    background: linear-gradient(145deg, #0f172a 0%, #1e293b 100%);
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
}

/* Tabla principal */
.excel-table {
    width: max-content;
    min-width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', 'SF Pro Display', sans-serif;
    font-size: 0.875rem;
    color: #e2e8f0;
}

/* Celdas base */
.excel-table th,
.excel-table td {
    padding: 14px 20px;
    border-bottom: 1px solid #334155;
    border-right: 1px solid #334155;
    white-space: nowrap;
    text-align: right;
    transition: all 0.2s ease;
}

/* Headers - Estilo corporativo premium */
.excel-table thead th {
    background: linear-gradient(180deg, #1e3a8a 0%, #1e40af 100%) !important;
    color: #ffffff;
    font-weight: 600;
    position: sticky;
    top: 0;
    z-index: 50;
    white-space: nowrap;
    border-bottom: 3px solid #3b82f6;
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 1.2px;
    padding: 16px 20px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.excel-table thead th.frozen {
    z-index: 150;
    background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%) !important;
    color: #ffffff !important;
    border-right: 2px solid #1e3a8a;
    text-align: left !important;
    font-size: 0.8rem;
    letter-spacing: 0.8px;
}

/* Columna frozen (Concepto) - Mejorada */
.excel-table td.frozen {
    position: sticky;
    left: 0;
    z-index: 10;
    border-right: 2px solid #475569 !important;
    text-align: left !important;
    font-weight: 500;
    min-width: 420px;
    max-width: 420px;
    white-space: normal !important;
    overflow: visible;
    text-overflow: clip;
}

/* Ensure frozen cells in special rows have solid backgrounds */
.excel-table tr.activity-header td.frozen {
    background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%) !important;
    color: #ffffff !important;
    font-weight: 700;
    font-size: 0.95rem;
}

.excel-table tr.subtotal-interno td.frozen {
    background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 60%) !important;
    color: #dbeafe !important;- Corporativo */
.excel-table tr.activity-header td {
    background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
    color: #ffffff;
    font-weight: 700;
    font-size: 0.95rem;
    padding: 16px 20px;
    border-top: 3px solid #60a5fa;
    border-bottom: 2px solid #3b82f6;
    text-shadow: 0 2px 4px rgba(0,0,0,0.4);
    letter-spacing: 0.5px
.excel-table tr.grand-total td.frozen {
    background: linear-gradient(135deg, #047857 0%, #10b981 100%) !important;
    color: #ffffff !important;
    font-weight: 700;
    font-size: 0.95rem;
}

.excel-table tr.data-row td.frozen {
    background: #1e293b !important;
    color: #cbd5e1 !important;
}

/* Filas de actividad (headers grandes) */
.excel-table tr.activity-header td {
    background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
    color: #ffffff;
    font-weight: 700;
    font-size: 0.95rem;
    padding: 12px 16px;
    border-top: 3px solid #3b82f6;
    border-bottom: 2px solid #1e40af;
    text-shadow: 0 1px 2px rgba(0,0,0,0.3);
}
- Elegante */
.excel-table tr.subtotal-interno td {
    background: linear-gradient(135deg, #1e3a5f 0%, rgba(37, 99, 235, 0.2) 100%);
    font-weight: 600;
    border-top: 2px solid #3b82f6;
    font-style: italic;
    color: #bfdbfe;
    padding: 12px 20px;
}

/* Subtotales de actividad - Más destacado */
.excel-table tr.subtotal td {
    background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%);
    font-weight: 700;
    border-top: 3px solid #60a5fa;
    border-bottom: 3px solid #60a5fa;
    color: #ffffff;
    padding: 14px 20px;
    box-shadow: inset 0 1px 3px rgba(255,255,255,0.1) 2px solid #3b82f6;
    color: #dbeafe;- Premium */
.excel-table tr.grand-total td {
    background: linear-gradient(135deg, #047857 0%, #10b981 100%);
    font-weight: 700;
    font-size: 0.95rem;
    border-top: 4px double #34d399;
    border-bottom: 4px double #34d399;
    color: #ffffff;
    text-shadow: 0 2px 4px rgba(0,0,0,0.4);
    padding: 16px 20px;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2), inset 0 1px 3px rgba(255,255,255,0.15);
    letter-spacing: - Más visibles y elegantes */
.monto-positivo { 
    color: #34d399; 
    font-weight: 600;
}
.monto-negativo { 
    color: #fca5a5; 
    font-weight: 600;
}- Suave y corporativo */
.excel-table tr.data-row:hover td {
    background: rgba(59, 130, 246, 0.12) !important;
    transition: all 0.2s ease;
    box-shadow: inset 0 0 0 1px rgba(59, 130, 246, 0.3);
}
- Feedback visual mejorado */
.excel-table td.clickable {
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;
}

.excel-table td.clickable:hover {
    background: rgba(59, 130, 246, 0.25) !important;
    transform: scale(1.02);
    box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3)
.monto-negativo { color: #fc8181; }
.monto-cero { color: #718096; }
- Más espacio y visual */
.indent-1 { 
    padding-left: 24px !important; 
}
.indent-2 { 
    padding-left: 48px !important;
    border-left: - Moderno y limpio */
.tipo-badge {
    display: inline-block;
    font-size: 0.7rem;
    padding: 4px 10px;
    border-radius: 6px;
    margin-right: 10px;
    font-weight: 600;
    letter-spacing: 0.5px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.tipo-op { 
    background: linear-gradient(135deg, #059669 0%, #10b981 100%); 
    color: #ffffff; 
}
.tipo-inv { 
    background: linear-gradient(135deg, #0284c7 0%, #0ea5e9 100%); 
    color: #ffffff; 
}
.tipo-fin { 
    background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%); 
    color: #ffffff; - Más elegante */
.scroll-hint {
    text-align: center;
    padding: 12px;
    color: #94a3b8;
    font-size: 0.75rem;
    background: linear-gradient(90deg, transparent, rgba(59,130,246,0.15), transparent);
    border-top: 1px solid #334155;
    font-weight: 500;
    letter-spacing:- Más suave */
.expandable {
    cursor: pointer;
    transition: all 0.2s ease;
}

.expandable:hover {
    background: rgba(59, 130, 246, 0.08) !important;
}

.expandable .expand-icon {
    display: inline-block;
    width: 20px;
    margin-right: 8px;
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    color: #60a5fa;
    font-weight: bold;
}

.expandable.expanded .expand-icon {
    transform: rotate(90deg);
    color: #3b82fElegante y legible */
.detail-row {
    display: table-row;
    animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

.detail-row:hover td {
    background: rgba(59, 130, 246, 0.1) !important;
}

.detail-row td {
    background: #0f172a !important;
    font-size: 0.8rem;
    color: #94a3b8;
    padding: 10px 20px !important;
    border-left: 3px solid #1e40af;
}
- Premium */
.excel-table td:last-child,
.excel-table th:last-child {
    background: rgba(59, 130, 246, 0.12) !important;
    border-left: 3px solid #475569;
    font-weight: 700;
    box-shadow: inset 2px 0 6px rgba(0, 0, 0, 0.15);
}

.excel-table th:last-child {
    background: linear-gradient(180deg, #1e40af 0%, #1e3a8a 100%) !important;
}

.excel-table tr.grand-total td:last-child {
    background: linear-gradient(135d- Sutil y elegante */
.excel-table tr.data-row:nth-child(even) td {
    background: rgba(15, 23, 42, 0.5);
}

.excel-table tr.data-row:nth-child(odd) td {
    background: rgba(30, 41, 59, 0.3);
}

.excel-table tr.data-row:nth-ch- Más legible */
.excel-table td:not(.frozen) {
    font-family: 'SF Mono', 'Consolas', 'Monaco', 'Roboto Mono', monospace;
    font-size: 0.875rem;
    font-weight: 500;
}

/* Mejorar legibilidad de texto en frozen */
.excel-table td.frozen {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
    line-height: 1.5

.excel-table tr.data-row:nth-child(odd) td.frozen {
    background: #1e293b
.expandable .expand-icon {
    display: inline-block;
    width: 16px;
    margin-right: 4px;
    transition: transform 0.2s;
}

.expandable.expanded .expand-icon {
    transform: rotate(90deg);
}

/* Detail rows - VISIBLES para ver composición de cuentas */
.detail-row {
    display: table-row;
}

.detail-row:hover td {
    background: #1a1a30 !important;
}

.detail-row td {
    background: #151525 !important;
    font-size: 0.75rem;
    color: #a0aec0;
    padding: 4px 12px !important;
}

.detail-row td.frozen {
    background: #151525 !important;
    padding-left: 50px !important;
    font-style: italic;
}

/* Columna Total destacada */
.excel-table td:last-child,
.excel-table th:last-child {
    background: rgba(99, 179, 237, 0.08) !important;
    border-left: 2px solid #4a5568;
}

.excel-table tr.grand-total td:last-child {
    background: rgba(72, 187, 120, 0.25) !important;
}

/* Zebra stripes para mejor lectura */
.excel-table tr.data-row:nth-child(even) td {
    background: rgba(59, 130, 246, 0.03);
}

.excel-table tr.data-row:nth-child(even) td.frozen {
    background: #1a1f2e !important;
}

/* Font monospace para números */
.excel-table td:not(.frozen) {
    font-family: 'Consolas', 'Monaco', monospace;
}

/* CSS-only expandable using checkbox hack */
.toggle-checkbox {
    display: none;
}

.toggle-label {
    cursor: pointer;
    display: inline-block;
}

.toggle-icon {
    display: inline-block;
    width: 16px;
    transition: transform 0.2s;
}

.toggle-checkbox:checked + tr .toggle-icon {
    transform: rotate(90deg);
}

/* Detail rows hidden by default, shown when checkbox checked */
.detail-group {
    display: none;
}

.toggle-checkbox:checked ~ .detail-group {
    display: table-row;
}
</style>
"""


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


def _generar_meses(fecha_inicio: datetime, fecha_fin: datetime) -> list:
    """Genera lista de meses entre dos fechas."""
    meses = []
    current = fecha_inicio.replace(day=1)
    while current <= fecha_fin:
        meses.append(current.strftime("%Y-%m"))
        # Siguiente mes
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    return meses


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
    Renderiza el tab Flujo de Caja con diseño Excel-style.
    - Categorías fijas a la izquierda
    - Columnas mensualizadas con scroll horizontal
    - Drill-down por celda
    """
    # Inyectar CSS
    st.markdown(EXCEL_STYLE_CSS, unsafe_allow_html=True)
    
    st.subheader("💵 Estado de Flujo de Efectivo")
    st.caption("Método Directo - NIIF IAS 7 • Vista Mensualizada")
    
    # === SELECTORES COMPACTOS ===
    col_año, col_meses, col_btn, col_export = st.columns([1, 2, 1, 1])
    
    with col_año:
        años_disponibles = list(range(datetime.now().year - 2, datetime.now().year + 2))
        año_sel = st.selectbox("Año", años_disponibles, 
                               index=años_disponibles.index(datetime.now().year),
                               key="flujo_año")
    
    with col_meses:
        meses_opciones = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", 
                         "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        # Multiselect para rango de meses
        meses_default = meses_opciones[:datetime.now().month] if año_sel == datetime.now().year else meses_opciones
        meses_sel = st.multiselect("Meses", meses_opciones, default=meses_default[:6],
                                   key="flujo_meses")
    
    # Calcular fecha inicio/fin
    if meses_sel:
        mes_inicio_idx = meses_opciones.index(meses_sel[0]) + 1
        mes_fin_idx = meses_opciones.index(meses_sel[-1]) + 1
        
        fecha_inicio = datetime(año_sel, mes_inicio_idx, 1)
        ultimo_dia = monthrange(año_sel, mes_fin_idx)[1]
        fecha_fin = datetime(año_sel, mes_fin_idx, ultimo_dia)
        
        fecha_inicio_str = fecha_inicio.strftime("%Y-%m-%d")
        fecha_fin_str = fecha_fin.strftime("%Y-%m-%d")
    else:
        st.warning("Selecciona al menos un mes")
        return
    
    with col_btn:
        btn_generar = st.button("🔄 Generar", type="primary", use_container_width=True,
                               key="flujo_btn_generar")
    
    with col_export:
        # Placeholder para export (se activa después de cargar datos)
        export_placeholder = st.empty()
    
    st.markdown("---")
    
    # === CARGAR DATOS ===
    cache_key = f"flujo_excel_{fecha_inicio_str}_{fecha_fin_str}"
    
    if btn_generar:
        # Limpiar caché anterior
        if cache_key in st.session_state:
            del st.session_state[cache_key]
        st.session_state["flujo_should_load"] = True
    
    if st.session_state.get("flujo_should_load") or cache_key in st.session_state:
        
        if cache_key not in st.session_state:
            with st.spinner("📊 Cargando datos mensualizados desde Odoo..."):
                try:
                    # Usar nuevo endpoint /mensual para datos por mes
                    resp = requests.get(
                        f"{FLUJO_CAJA_URL}/mensual",
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
                        st.toast("✅ Datos mensualizados cargados", icon="✅")
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
        
        # === PROCESAR DATOS MENSUALIZADOS ===
        actividades = flujo_data.get("actividades", {})
        conciliacion = flujo_data.get("conciliacion", {})
        meses_lista = flujo_data.get("meses", [])
        efectivo_por_mes = flujo_data.get("efectivo_por_mes", {})
        cuentas_nc = flujo_data.get("cuentas_sin_clasificar", [])
        
        # KPIs compactos (totales)
        op = actividades.get("OPERACION", {}).get("subtotal", 0)
        inv = actividades.get("INVERSION", {}).get("subtotal", 0)
        fin = actividades.get("FINANCIAMIENTO", {}).get("subtotal", 0)
        ef_ini = conciliacion.get("efectivo_inicial", 0)
        ef_fin = conciliacion.get("efectivo_final", 0)
        
        # KPIs en línea compacta
        kpi_cols = st.columns(5)
        kpi_cols[0].metric("🟢 Operación", fmt_flujo(op))
        kpi_cols[3].metric("💰 Ef. Inicial", fmt_flujo(ef_ini))
        kpi_cols[4].metric("💵 Ef. Final", fmt_flujo(ef_fin), delta=fmt_flujo(op + inv + fin))
        
        st.markdown("")
        
        # === GENERAR TABLA EXCEL-STYLE CON DATOS REALES POR MES ===
        # Construir HTML de la tabla
        html_parts = ['<div class="excel-container">']
        html_parts.append('<table class="excel-table">')
        
        # HEADER
        html_parts.append('<thead><tr>')
        html_parts.append('<th class="frozen">Concepto</th>')
        for mes in meses_lista:
            html_parts.append(f'<th>{_nombre_mes_corto(mes)}</th>')
        html_parts.append('<th><strong>Total</strong></th>')
        html_parts.append('</tr></thead>')
        
        # BODY
        html_parts.append('<tbody>')
        
        act_config = {
            "OPERACION": {"emoji": "🟢", "class": "tipo-op", "color": "#48bb78"},
            "INVERSION": {"emoji": "🔵", "class": "tipo-inv", "color": "#4299e1"},
            "FINANCIAMIENTO": {"emoji": "🟣", "class": "tipo-fin", "color": "#9f7aea"}
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
            
            # Fila de actividad (header)
            html_parts.append(f'<tr class="activity-header">')
            html_parts.append(f'<td class="frozen">{config["emoji"]} {act_nombre}</td>')
            for _ in meses_lista:
                html_parts.append('<td></td>')
            html_parts.append('<td></td>')
            html_parts.append('</tr>')
            
            # Filas de conceptos CON DATOS REALES POR MES
            for concepto in sorted(conceptos, key=lambda x: x.get("order", x.get("id", ""))):
                c_id = concepto.get("id") or concepto.get("codigo")
                c_nombre = concepto.get("nombre", "")
                c_tipo = concepto.get("tipo", "LINEA")
                c_nivel = concepto.get("nivel", 3)
                c_total = concepto.get("total", 0)
                montos_mes = concepto.get("montos_por_mes", {})  # Datos REALES del backend
                cuentas = concepto.get("cuentas", [])  # Cuentas que componen este concepto
                
                if c_tipo == "HEADER":
                    continue  # Skip headers, already have activity header
                
                # MOSTRAR TODAS LAS CATEGORÍAS (incluso vacías)
                
                indent_class = f"indent-{min(c_nivel, 4)}"
                # Clasificar el tipo de fila
                if c_tipo == "SUBTOTAL":
                    row_class = "subtotal-interno"
                elif c_tipo == "TOTAL":
                    row_class = "subtotal"
                else:
                    row_class = "data-row"
                
                # Si tiene cuentas, hacerlo expandible
                c_id_safe = c_id.replace(".", "_")
                has_details = len(cuentas) > 0
                expandable_class = f"expandable parent-{c_id_safe}" if has_details else ""
                onclick = f'onclick="toggleConcept(\'{c_id_safe}\')"' if has_details else ""
                expand_icon = '<span class="expand-icon">▶</span>' if has_details else '<span style="width:20px;display:inline-block;"></span>'
                
                html_parts.append(f'<tr class="{row_class} {expandable_class}" {onclick}>')
                html_parts.append(f'<td class="frozen {indent_class}">{expand_icon}{c_id} - {c_nombre[:45]}</td>')
                
                # DATOS REALES por mes
                for mes in meses_lista:
                    monto_mes = montos_mes.get(mes, 0)
                    html_parts.append(f'<td class="clickable">{_fmt_monto_html(monto_mes)}</td>')
                
                html_parts.append(f'<td><strong>{_fmt_monto_html(c_total)}</strong></td>')
                html_parts.append('</tr>')
                
                # Sub-filas de detalle (cuentas) - Ocultas por defecto via style="display:none"
                # Se muestran al hacer click en el padre (via JS toggleConcept)
                if cuentas:
                    for cuenta in cuentas[:15]:  # Máximo 15 cuentas
                        cuenta_codigo = cuenta.get("codigo", "")
                        cuenta_nombre = cuenta.get("nombre", "")[:35]
                        cuenta_monto = cuenta.get("monto", 0)
                        cu_montos_mes = cuenta.get("montos_por_mes", {})
                        
                        html_parts.append(f'<tr class="detail-row detail-{c_id_safe}" style="display:none;">')
                        html_parts.append(f'<td class="frozen">📄 {cuenta_codigo} - {cuenta_nombre}</td>')
                        
                        # Datos mensuales de la cuenta
                        for mes in meses_lista:
                            m_acc = cu_montos_mes.get(mes, 0)
                            html_parts.append(f'<td>{_fmt_monto_html(m_acc)}</td>')
                        
                        html_parts.append(f'<td>{_fmt_monto_html(cuenta_monto)}</td>')
                        html_parts.append('</tr>')
            
            # Subtotal de actividad CON DATOS REALES
            html_parts.append(f'<tr class="subtotal">')
            html_parts.append(f'<td class="frozen"><strong>Subtotal {act_key}</strong></td>')
            for mes in meses_lista:
                monto_mes_sub = act_subtotal_por_mes.get(mes, 0)
                html_parts.append(f'<td>{_fmt_monto_html(monto_mes_sub)}</td>')
            html_parts.append(f'<td><strong>{_fmt_monto_html(act_subtotal)}</strong></td>')
            html_parts.append('</tr>')
        
        # TOTAL GENERAL - VARIACIÓN POR MES
        total_variacion = op + inv + fin
        html_parts.append(f'<tr class="grand-total">')
        html_parts.append(f'<td class="frozen"><strong>VARIACIÓN NETA DEL EFECTIVO</strong></td>')
        for mes in meses_lista:
            variacion_mes = efectivo_por_mes.get(mes, {}).get("variacion", 0)
            html_parts.append(f'<td>{_fmt_monto_html(variacion_mes)}</td>')
        html_parts.append(f'<td><strong>{_fmt_monto_html(total_variacion)}</strong></td>')
        html_parts.append('</tr>')
        
        # Efectivo inicial POR MES
        html_parts.append(f'<tr class="data-row">')
        html_parts.append(f'<td class="frozen">Efectivo al inicio del período</td>')
        for mes in meses_lista:
            ef_ini_mes = efectivo_por_mes.get(mes, {}).get("inicial", ef_ini)
            html_parts.append(f'<td>{_fmt_monto_html(ef_ini_mes)}</td>')
        html_parts.append(f'<td><strong>{_fmt_monto_html(ef_ini)}</strong></td>')
        html_parts.append('</tr>')
        
        # Efectivo final POR MES
        html_parts.append(f'<tr class="grand-total">')
        html_parts.append(f'<td class="frozen"><strong>EFECTIVO AL FINAL DEL PERÍODO</strong></td>')
        for mes in meses_lista:
            ef_fin_mes = efectivo_por_mes.get(mes, {}).get("final", ef_fin)
            html_parts.append(f'<td>{_fmt_monto_html(ef_fin_mes)}</td>')
        html_parts.append(f'<td><strong>{_fmt_monto_html(ef_fin)}</strong></td>')
        html_parts.append('</tr>')
        
        html_parts.append('</tbody>')
        html_parts.append('</table>')
        
        # Hint de scroll
        if len(meses_lista) > 3:
            html_parts.append('<div class="scroll-hint">← Desliza horizontalmente para ver más meses →</div>')
        
        html_parts.append('</div>')
        
        # Script para toggle individual de conceptos
        html_parts.append('''
        <script>
        function toggleConcept(conceptId) {
            const rows = document.querySelectorAll('.detail-' + conceptId);
            const parent = document.querySelector('.parent-' + conceptId);
            const icon = parent.querySelector('.expand-icon');
            const isExpanded = parent.classList.contains('expanded');
            
            rows.forEach(row => {
                row.style.display = isExpanded ? 'none' : 'table-row';
            });
            parent.classList.toggle('expanded');
            if (icon) {
                icon.textContent = isExpanded ? '▶' : '▼';
            }
        }
        </script>
        ''')
        
        # Renderizar tabla con JavaScript habilitado
        full_html = EXCEL_STYLE_CSS + "".join(html_parts)
        components.html(full_html, height=800, scrolling=True)
        
        # === EXPORT A EXCEL ===
        with export_placeholder:
            # Crear DataFrame para export
            rows = []
            for act_key in ["OPERACION", "INVERSION", "FINANCIAMIENTO"]:
                act_data = actividades.get(act_key, {})
                if not act_data:
                    continue
                
                rows.append({"Concepto": act_data.get("nombre", act_key), "Monto": ""})
                
                for concepto in act_data.get("conceptos", []):
                    c_id = concepto.get("id") or concepto.get("codigo")
                    c_nombre = concepto.get("nombre", "")
                    c_monto = concepto.get("monto", 0)
                    rows.append({
                        "Concepto": f"  {c_id} - {c_nombre}",
                        "Monto": c_monto
                    })
                
                rows.append({
                    "Concepto": f"Subtotal {act_key}",
                    "Monto": act_data.get("subtotal", 0)
                })
            
            rows.append({"Concepto": "VARIACIÓN NETA", "Monto": total_variacion})
            rows.append({"Concepto": "Efectivo Inicial", "Monto": ef_ini})
            rows.append({"Concepto": "Efectivo Final", "Monto": ef_fin})
            
            df_export = pd.DataFrame(rows)
            
            # Botón de descarga
            csv = df_export.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Excel",
                csv,
                f"flujo_caja_{fecha_inicio_str}_{fecha_fin_str}.csv",
                "text/csv",
                use_container_width=True
            )
        
        # === CUENTAS SIN CLASIFICAR ===
        if cuentas_nc and len(cuentas_nc) > 0:
            st.markdown("---")
            with st.expander(f"⚠️ {len(cuentas_nc)} cuentas sin clasificar", expanded=False):
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
                                    st.toast(f"✅ {codigo}")
                                    if cache_key in st.session_state:
                                        del st.session_state[cache_key]
                                else:
                                    st.error(err)
    else:
        st.info("👆 Selecciona el período y haz clic en 'Generar' para cargar el flujo de caja")
