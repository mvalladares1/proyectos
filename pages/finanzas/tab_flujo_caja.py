"""
Tab: Flujo de Caja
Flujo de caja NIIF IAS 7 con funcionalidades avanzadas.

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

# ==================== IMPORTAR MÓDULOS ====================
from .flujo_caja import (
    ENTERPRISE_CSS,
    ENTERPRISE_JS,
    SVG_ICONS,
    generate_sparkline,
    get_heatmap_class,
    fmt_monto_html,
    nombre_mes_corto,
    es_vista_semanal,
    agrupar_semanas_por_mes,
    nombre_semana_corto
)


@st.fragment
def render(username: str, password: str):
    """
    Renderiza el tab Flujo de Caja con diseño Enterprise.
    """
    st.markdown("# Flujo de Caja")
    
    # ========== CONTROLES SUPERIORES ==========
    col_search, col_filters, col_actions = st.columns([2, 3, 2])
    
    # Obtener categorías disponibles de datos cacheados
    categorias_disponibles = sorted(st.session_state.get("flujo_categorias_lista", []))
    
    with col_search:
        categorias_seleccionadas = st.multiselect(
            "📁 Filtrar por Categoría de Contacto",
            options=categorias_disponibles,
            default=[],
            key="filtro_categorias_flujo",
            placeholder="Seleccionar categorías (afecta 1.1.1 y 1.2.1)..."
        )
    
    with col_filters:
        st.write("**Filtrar por actividad:**")
        f_cols = st.columns(3)
        filter_op = f_cols[0].checkbox("🟢 Operación", value=True, key="filter_op")
        filter_inv = f_cols[1].checkbox("🔵 Inversión", value=True, key="filter_inv")
        filter_fin = f_cols[2].checkbox("🟣 Financiamiento", value=True, key="filter_fin")
    
    with col_actions:
        solo_pendiente = st.checkbox("📌 Solo pendiente", value=False, key="solo_pendiente_parciales",
                                     help="Excluir todo lo ya pagado/cobrado de Operación. Muestra solo lo que falta por llegar o pagar.")
        incluir_proyecciones = st.checkbox("🔮 Incluir Facturas Proyectadas", value=False, key="incluir_proyecciones",
                                          help="Incluir presupuestos de venta (estado draft/sent) como Facturas Proyectadas en CxC.")
    
    st.markdown("---")
    
    # ========== SELECTORES DE PERÍODO ==========
    col_desde, col_hasta, col_agrupacion, col_btn, col_export = st.columns([2, 2, 2, 1, 1])
    
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
    
    st.markdown("---")
    
    # ========== CARGAR DATOS ==========
    cache_key = f"flujo_excel_{tipo_periodo}_{fecha_inicio_str}_{fecha_fin_str}_proy_{incluir_proyecciones}"
    
    if btn_generar:
        if cache_key in st.session_state:
            del st.session_state[cache_key]
        st.session_state["flujo_should_load"] = True
    
    if st.session_state.get("flujo_should_load") or cache_key in st.session_state:
        
        if cache_key not in st.session_state:
            with st.spinner("🚀 Cargando datos con procesamiento avanzado..."):
                try:
                    # Determinar endpoint según agrupación seleccionada
                    endpoint = "semanal" if tipo_periodo == "Semanal" else "mensual"
                    url_completa = f"{FLUJO_CAJA_URL}/{endpoint}"
                    resp = requests.get(
                        url_completa,
                        params={
                            "fecha_inicio": fecha_inicio_str,
                            "fecha_fin": fecha_fin_str,
                            "username": username,
                            "password": password,
                            "incluir_proyecciones": incluir_proyecciones
                        },
                        timeout=120
                    )
                    
                    if resp.status_code == 200:
                        st.session_state[cache_key] = resp.json()
                        st.session_state["flujo_should_load"] = False
                        st.toast("✅ Datos cargados con éxito", icon="✅")
                    elif resp.status_code == 401 or "autenticación" in resp.text.lower():
                        st.error("🔐 **Error de Autenticación**")
                        st.warning("""
                        Tu sesión ha expirado o las credenciales de Odoo no son válidas.
                        
                        **Por favor:**
                        1. Cierra sesión usando el botón en la barra lateral
                        2. Vuelve a iniciar sesión con tus credenciales
                        
                        Si el problema persiste, contacta al administrador del sistema.
                        """)
                        return
                    else:
                        try:
                            error_detail = resp.json().get("detail", resp.text)
                        except:
                            error_detail = resp.text
                        st.error(f"❌ Error {resp.status_code}: {error_detail}")
                        return
                except Exception as e:
                    st.error(f"Error de conexión: {e}")
                    return
        
        flujo_data = st.session_state.get(cache_key, {})
        
        if "error" in flujo_data:
            error_msg = flujo_data['error']
            if "cuentas de efectivo" in error_msg.lower():
                st.warning("⚙️ **Configuración Pendiente**")
                st.info(f"📋 {error_msg}")
                st.markdown("""
                **¿Qué significa esto?**
                - El sistema necesita que se configuren las cuentas contables que representan efectivo
                - Estas cuentas se utilizan para calcular el flujo de caja
                
                **¿Qué hacer?**
                - Contacta al administrador para configurar las cuentas de efectivo en el archivo de configuración
                - Una vez configuradas, podrás ver el flujo de caja completo
                """)
            else:
                st.error(f"❌ Error: {error_msg}")
            return
        
        # ========== PROCESAR DATOS ==========
        actividades = flujo_data.get("actividades", {})
        conciliacion = flujo_data.get("conciliacion", {})
        meses_lista = flujo_data.get("meses", [])
        efectivo_por_mes = flujo_data.get("efectivo_por_mes", {})
        cuentas_nc = flujo_data.get("cuentas_sin_clasificar", [])
        
        # ========== EXTRAER CATEGORÍAS DISPONIBLES PARA EL FILTRO ==========
        categorias_set = set()
        for act_data_tmp in actividades.values():
            if not isinstance(act_data_tmp, dict):
                continue
            for concepto_tmp in act_data_tmp.get("conceptos", []):
                c_id_tmp = concepto_tmp.get("id", "")
                if c_id_tmp not in ("1.1.1", "1.2.1"):
                    continue
                for cuenta_tmp in concepto_tmp.get("cuentas", []):
                    for etiqueta_tmp in cuenta_tmp.get("etiquetas", []):
                        if etiqueta_tmp.get("tipo") == "categoria":
                            # CxP categorías (📁 NombreCat)
                            cat_name = etiqueta_tmp.get("nombre", "").replace("📁 ", "")
                            if cat_name:
                                categorias_set.add(cat_name)
                        elif etiqueta_tmp.get("categoria"):
                            # CxC partners con categoría (etiqueta-level)
                            categorias_set.add(etiqueta_tmp["categoria"])
                        # CxC facturas dentro de estados (Pagadas, Parciales, etc.)
                        for fact_tmp in etiqueta_tmp.get("facturas", []):
                            if fact_tmp.get("categoria"):
                                categorias_set.add(fact_tmp["categoria"])
                        # CxC sub_etiquetas (partners dentro de categorías proyectadas)
                        for sub_tmp in etiqueta_tmp.get("sub_etiquetas", []):
                            if sub_tmp.get("tipo") == "categoria":
                                cat_name = sub_tmp.get("nombre", "").replace("📁 ", "")
                                if cat_name:
                                    categorias_set.add(cat_name)
        nuevas_categorias = sorted(categorias_set)
        old_categorias = st.session_state.get("flujo_categorias_lista", [])
        st.session_state["flujo_categorias_lista"] = nuevas_categorias
        
        # Si las categorías cambiaron (primera carga), refrescar para que el multiselect las muestre
        if nuevas_categorias and nuevas_categorias != old_categorias:
            st.rerun()
        
        # ========== FILTRO POR CATEGORÍA DE CONTACTO (1.1.1 y 1.2.1) ==========
        if categorias_seleccionadas:
            import copy
            actividades = copy.deepcopy(actividades)
            for act_name, act_data_filt in actividades.items():
                if not isinstance(act_data_filt, dict):
                    continue
                for concepto in act_data_filt.get("conceptos", []):
                    c_id_filt = concepto.get("id", "")
                    if c_id_filt not in ("1.1.1", "1.2.1"):
                        continue
                    
                    tiene_cxp = any(c.get("es_cuenta_cxp") for c in concepto.get("cuentas", []))
                    tiene_cxc = any(c.get("es_cuenta_cxc") for c in concepto.get("cuentas", []))
                    
                    for cuenta_filt in concepto.get("cuentas", []):
                        # Guardar montos originales antes del filtro
                        old_cuenta_monto = cuenta_filt.get("monto", 0)
                        old_cuenta_montos_mes = dict(cuenta_filt.get("montos_por_mes", {}))
                        
                        if tiene_cxp and cuenta_filt.get("es_cuenta_cxp"):
                            # CxP: Filtrar etiquetas (categorías nivel 3)
                            etiquetas_filtradas = []
                            for etq in cuenta_filt.get("etiquetas", []):
                                if etq.get("tipo") == "categoria":
                                    cat_name = etq.get("nombre", "").replace("📁 ", "")
                                    if cat_name in categorias_seleccionadas:
                                        etiquetas_filtradas.append(etq)
                                else:
                                    etiquetas_filtradas.append(etq)
                            
                            # Recalcular monto de la cuenta basado en las etiquetas filtradas
                            nuevo_monto = sum(e.get("monto", 0) for e in etiquetas_filtradas)
                            
                            nuevos_montos_mes = {}
                            for e in etiquetas_filtradas:
                                for m, v in e.get("montos_por_mes", {}).items():
                                    nuevos_montos_mes[m] = nuevos_montos_mes.get(m, 0) + v
                            
                            cuenta_filt["etiquetas"] = etiquetas_filtradas
                            cuenta_filt["monto"] = nuevo_monto
                            cuenta_filt["montos_por_mes"] = nuevos_montos_mes
                        
                        elif tiene_cxc and cuenta_filt.get("es_cuenta_cxc"):
                            # CxC: Las etiquetas de cada estado pueden ser:
                            # A) Categorías (tipo="categoria", nombre="📁 Cliente") con sub_etiquetas de partners
                            # B) Partners directos con campo "categoria"
                            # C) Facturas agrupadas por partner con campo "categoria"
                            etiquetas_filtradas = []
                            for etq in cuenta_filt.get("etiquetas", []):
                                if etq.get("tipo") == "categoria":
                                    # Es una categoría (📁 Cliente, 📁 Empleado, etc.)
                                    cat_name = etq.get("nombre", "").replace("📁 ", "")
                                    if cat_name in categorias_seleccionadas:
                                        etiquetas_filtradas.append(etq)
                                elif etq.get("facturas"):
                                    # Partners con facturas detalladas → filtrar por categoría
                                    facturas_ok = [f for f in etq["facturas"] if f.get("categoria", "") in categorias_seleccionadas]
                                    if facturas_ok:
                                        etq_copy = dict(etq)
                                        etq_copy["facturas"] = facturas_ok
                                        etq_copy["monto"] = sum(f.get("monto", 0) for f in facturas_ok)
                                        etq_copy["montos_por_mes"] = {}
                                        for f in facturas_ok:
                                            for m, v in f.get("montos_por_mes", {}).items():
                                                etq_copy["montos_por_mes"][m] = etq_copy["montos_por_mes"].get(m, 0) + v
                                        etiquetas_filtradas.append(etq_copy)
                                elif etq.get("categoria"):
                                    # Partner directo con categoría
                                    if etq["categoria"] in categorias_seleccionadas:
                                        etiquetas_filtradas.append(etq)
                                else:
                                    # Etiqueta sin categoría ni facturas → mantener
                                    etiquetas_filtradas.append(etq)
                            
                            nuevo_monto = sum(e.get("monto", 0) for e in etiquetas_filtradas)
                            
                            nuevos_montos_mes = {}
                            for e in etiquetas_filtradas:
                                for m, v in e.get("montos_por_mes", {}).items():
                                    nuevos_montos_mes[m] = nuevos_montos_mes.get(m, 0) + v
                            
                            cuenta_filt["etiquetas"] = etiquetas_filtradas
                            cuenta_filt["monto"] = nuevo_monto
                            cuenta_filt["montos_por_mes"] = nuevos_montos_mes
                        else:
                            continue  # No es CxP ni CxC, no filtrar
                        
                        # Ajustar totales del concepto padre con la diferencia
                        diff_monto = old_cuenta_monto - cuenta_filt["monto"]
                        if diff_monto != 0:
                            concepto["total"] = concepto.get("total", 0) - diff_monto
                            for m, old_v in old_cuenta_montos_mes.items():
                                new_v = cuenta_filt["montos_por_mes"].get(m, 0)
                                diff_m = old_v - new_v
                                if diff_m != 0 and m in concepto.get("montos_por_mes", {}):
                                    concepto["montos_por_mes"][m] -= diff_m
                            # Subtotales de actividad se recalculan automáticamente después de los filtros
        
        # ========== FILTRO: Solo pendiente (excluir todo lo ya pagado/cobrado) ==========
        if solo_pendiente:
            import copy
            actividades = copy.deepcopy(actividades)
            act_data = actividades.get("OPERACION", {})
            if act_data:
                for concepto in act_data.get("conceptos", []):
                    cuentas = concepto.get("cuentas", [])
                    # Solo procesar conceptos con estructura CxP/CxC (tienen estados pagadas/parciales)
                    tiene_cxp = any(c.get("es_cuenta_cxp") for c in cuentas)
                    tiene_cxc = any(c.get("es_cuenta_cxc") for c in cuentas)
                    if not tiene_cxp and not tiene_cxc:
                        continue
                    
                    if tiene_cxp:
                        # === CxP (1.2.1): Estados son cuentas con codigo ===
                        for cuenta in cuentas:
                            if cuenta.get("codigo") == "pagadas":
                                # PAGADAS: Excluir completamente
                                monto_pagadas = cuenta.get("monto", 0)
                                concepto["total"] = concepto.get("total", 0) - monto_pagadas
                                for mes, val in cuenta.get("montos_por_mes", {}).items():
                                    concepto["montos_por_mes"][mes] = concepto.get("montos_por_mes", {}).get(mes, 0) - val
                                cuenta["monto"] = 0
                                cuenta["montos_por_mes"] = {}
                                for etiqueta in cuenta.get("etiquetas", []):
                                    etiqueta["monto"] = 0
                                    etiqueta["montos_por_mes"] = {}
                                    for sub in etiqueta.get("sub_etiquetas", []):
                                        sub["monto"] = 0
                                        sub["montos_por_mes"] = {}
                            
                            elif cuenta.get("codigo") == "parciales":
                                # PARCIALES: ya solo contiene el residual
                                # (la parte pagada fue movida a PAGADAS en el backend)
                                pass
                    
                    elif tiene_cxc:
                        # === CxC (1.1.1): Estados son cuentas con codigo (igual que CxP) ===
                        for cuenta in cuentas:
                            if not cuenta.get("es_cuenta_cxc"):
                                continue
                            
                            cuenta_codigo = cuenta.get("codigo", "")
                            
                            # Si la cuenta tiene codigo "estado_paid" → Facturas Pagadas → excluir
                            if cuenta_codigo == "estado_paid":
                                cuenta_monto = cuenta.get("monto", 0)
                                
                                # Restar de concepto
                                concepto["total"] = concepto.get("total", 0) - cuenta_monto
                                for mes, val in cuenta.get("montos_por_mes", {}).items():
                                    concepto["montos_por_mes"][mes] = concepto.get("montos_por_mes", {}).get(mes, 0) - val
                                
                                # Poner cuenta en 0
                                cuenta["monto"] = 0
                                cuenta["montos_por_mes"] = {}
                                
                                # Poner todas las etiquetas (clientes) en 0
                                for etiqueta in cuenta.get("etiquetas", []):
                                    etiqueta["monto"] = 0
                                    etiqueta["montos_por_mes"] = {}
        
        # ========== RECALCULAR SUBTOTALES DINÁMICAMENTE ==========
        # Recalcular subtotales de cada actividad a partir de los conceptos (filtrados o no)
        # Esto garantiza que los subtotales reflejen fielmente lo que muestra la tabla,
        # independientemente de filtros de categoría, solo pendiente, o proyecciones.
        # Deepcopy si no se hizo antes (para no alterar datos cacheados)
        if not categorias_seleccionadas and not solo_pendiente:
            import copy
            actividades = copy.deepcopy(actividades)
        for _act_key in ["OPERACION", "INVERSION", "FINANCIAMIENTO"]:
            _act = actividades.get(_act_key, {})
            if not isinstance(_act, dict):
                continue
            _new_sub = 0
            _new_sub_mes = {}
            for _concepto in _act.get("conceptos", []):
                _c_tipo = _concepto.get("tipo", "LINEA")
                if _c_tipo in ("SUBTOTAL", "TOTAL", "HEADER"):
                    continue
                _new_sub += _concepto.get("total", 0)
                for _m, _v in _concepto.get("montos_por_mes", {}).items():
                    _new_sub_mes[_m] = _new_sub_mes.get(_m, 0) + _v
            _act["subtotal"] = _new_sub
            _act["subtotal_por_mes"] = _new_sub_mes
        
        op = actividades.get("OPERACION", {}).get("subtotal", 0)
        inv = actividades.get("INVERSION", {}).get("subtotal", 0)
        fin = actividades.get("FINANCIAMIENTO", {}).get("subtotal", 0)
        ef_ini = conciliacion.get("efectivo_inicial", 0)
        variacion = op + inv + fin
        ef_fin = ef_ini + variacion
        
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
            <div class="kpi-label">💎 EFECTIVO Final</div>
            <div class="kpi-value {'kpi-positive' if variacion > 0 else 'kpi-negative'}">${ef_fin:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        

        
        # ========== DETECTAR VISTA SEMANAL ==========
        vista_semanal = es_vista_semanal(meses_lista)
        semanas_por_mes = {}
        meses_ordenados = []
        
        if vista_semanal:
            # Pasar fechas de filtro para excluir semanas fuera del rango
            semanas_por_mes = agrupar_semanas_por_mes(meses_lista, fecha_inicio_str, fecha_fin_str)
            meses_ordenados = list(semanas_por_mes.keys())
        
        # ========== GENERAR TABLA HTML ==========
        html_parts = [ENTERPRISE_CSS, '<div class="excel-container">']
        html_parts.append('<table class="excel-table">')
        
        # HEADER
        if vista_semanal and semanas_por_mes:
            # Vista semanal: Header de tres filas (toolbar + meses + semanas)
            num_weeks_total = sum(len(s) for s in semanas_por_mes.values())
            html_parts.append('<thead>')
            # Toolbar row
            html_parts.append('<tr class="toolbar-row">')
            html_parts.append('<th class="toolbar-btn-cell" colspan="2"><button class="excel-export-btn" onclick="exportVisibleTableToExcel()">📥 Exportar Excel (Vista actual)</button></th>')
            html_parts.append(f'<th class="toolbar-spacer" colspan="{num_weeks_total + 1}"></th>')
            html_parts.append('</tr>')
            # Fila 1: Meses con colspan
            html_parts.append('<tr class="header-meses">')
            html_parts.append('<th class="frozen" rowspan="2">CONCEPTO</th>')
            html_parts.append('<th class="frozen-total-left" rowspan="2"><strong>TOTAL</strong></th>')
            
            for mes in meses_ordenados:
                num_semanas = len(semanas_por_mes[mes])
                html_parts.append(f'<th colspan="{num_semanas}" class="mes-header" style="text-align: center; font-size: 14px; font-weight: 700; border-bottom: none;">{mes}</th>')
            
            html_parts.append('<th rowspan="2"><strong>TOTAL</strong></th>')
            html_parts.append('</tr>')
            
            # Fila 2: Semanas (número real de semana del año)
            html_parts.append('<tr class="header-semanas">')
            for mes in meses_ordenados:
                for semana in semanas_por_mes[mes]:
                    # Extraer número de semana del formato 2026-W05
                    num_semana = semana.split('-W')[1] if '-W' in semana else semana
                    html_parts.append(f'<th style="font-size: 11px; padding: 4px 8px;">S{int(num_semana)}</th>')
            html_parts.append('</tr>')
            html_parts.append('</thead>')
        else:
            # Vista mensual: Header con toolbar
            html_parts.append('<thead>')
            # Toolbar row
            html_parts.append('<tr class="toolbar-row">')
            html_parts.append('<th class="toolbar-btn-cell" colspan="2"><button class="excel-export-btn" onclick="exportVisibleTableToExcel()">📥 Exportar Excel (Vista actual)</button></th>')
            html_parts.append(f'<th class="toolbar-spacer" colspan="{len(meses_lista) + 1}"></th>')
            html_parts.append('</tr>')
            html_parts.append('<tr>')
            html_parts.append('<th class="frozen">CONCEPTO</th>')
            html_parts.append('<th class="frozen-total-left"><strong>TOTAL</strong></th>')
            for mes in meses_lista:
                html_parts.append(f'<th>{nombre_mes_corto(mes)}</th>')
            html_parts.append('<th><strong>TOTAL</strong></th>')
            html_parts.append('</tr>')
            html_parts.append('</thead>')
        
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
            html_parts.append('<td class="frozen-total-left"></td>')
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
                row_classes = [row_class]
                if has_details:
                    row_classes.extend(["expandable", f"parent-{c_id_safe}"])

                attrs = []
                if has_details:
                    attrs.append(f'onclick="toggleConcept(\'{c_id_safe}\')"')

                row_class_attr = " ".join(row_classes)
                extra_attrs = " ".join(attrs)
                
                # SVG Icon
                icon_svg = f'<span class="icon-expand">{SVG_ICONS["chevron"]}</span>' if has_details else '<span style="width:24px;display:inline-block;"></span>'
                
                # Tooltip
                tooltip_text = f"{c_id} - {c_nombre}"
                if cuentas:
                    tooltip_text += f"<br><br><strong>{len(cuentas)} cuentas:</strong><br>"
                    tooltip_text += "<br>".join([f"• {c.get('codigo', '')} - {c.get('nombre', '')}" for c in cuentas[:5]])
                    if len(cuentas) > 5:
                        tooltip_text += f"<br>... y {len(cuentas)-5} más"
                
                tooltip_html = f'''
                <div class="tooltip-wrapper">
                    <span>{c_nombre}</span>
                    <div class="tooltip-text">{tooltip_text}</div>
                </div>
                '''
                
                html_parts.append(f'<tr class="{row_class_attr}" {extra_attrs}>')
                html_parts.append(f'<td class="frozen {indent_class}">{icon_svg}{c_id} - {tooltip_html}</td>')
                html_parts.append(f'<td class="frozen-total-left"><strong>{fmt_monto_html(c_total)}</strong></td>')
                
                # Valores mensuales con HEATMAP y click para composición
                valores_lista = []
                for mes in meses_lista:
                    monto_mes = montos_mes.get(mes, 0)
                    valores_lista.append(monto_mes)
                    heatmap_class = get_heatmap_class(monto_mes, max_abs)
                    cell_id = f"cell_{c_id_safe}_{mes}"
                    # NO onclick para composición (removed per user request)
                    
                    html_parts.append(f'<td class="clickable {heatmap_class}" id="{cell_id}" oncontextmenu="addNote(\'{c_id}\', \'{cell_id}\'); return false;">{fmt_monto_html(monto_mes)}</td>')
                
                # Total con SPARKLINE
                sparkline = generate_sparkline(valores_lista)
                html_parts.append(f'<td><strong>{fmt_monto_html(c_total)}</strong>{sparkline}</td>')
                html_parts.append('</tr>')
                
                # Detail rows (Nivel 2: Cuentas)
                if cuentas:
                    for idx_cu, cuenta in enumerate(cuentas[:15]):
                        cuenta_codigo = cuenta.get("codigo", "")
                        cuenta_nombre = cuenta.get("nombre", "")  # Sin truncamiento para nombres completos
                        cuenta_monto = cuenta.get("monto", 0)
                        cu_montos_mes = cuenta.get("montos_por_mes", {})
                        etiquetas = cuenta.get("etiquetas", [])
                        
                        # ID único para esta cuenta (para expandir etiquetas)
                        cuenta_id_safe = f"{c_id_safe}_{cuenta_codigo.replace('.', '_')}"
                        has_etiquetas = len(etiquetas) > 0
                        
                        # Verificar si tiene facturas en alguna etiqueta
                        tiene_facturas_cuenta = any(
                            "facturas" in etiq and len(etiq.get("facturas", [])) > 0 
                            for etiq in etiquetas
                        )
                        
                        # Icono para expandir/contraer etiquetas
                        if has_etiquetas:
                            cuenta_icon = f'<span class="icon-expand" style="cursor:pointer;" onclick="toggleEtiquetas(\'{cuenta_id_safe}\')">{SVG_ICONS["chevron"]}</span>'
                        else:
                            cuenta_icon = '<span style="width:24px;display:inline-block;"></span>'
                        
                        # Agregar clase cuenta-{cuenta_id_safe} para identificar esta cuenta al colapsar
                        html_parts.append(f'<tr class="detail-row detail-{c_id_safe} cuenta-{cuenta_id_safe}" style="display:none;">')
                        
                        # Si es estructura especial (CxP, CxC, IVA), el nombre ya contiene todo formateado
                        es_estructura_especial = cuenta.get("es_cuenta_cxp", False) or cuenta.get("es_cuenta_cxc", False) or cuenta.get("es_cuenta_iva", False)
                        if es_estructura_especial:
                            # Solo mostrar el nombre (ya tiene emoji e info)
                            html_parts.append(f'<td class="frozen">{cuenta_icon}{cuenta_nombre}</td>')
                        else:
                            # Mostrar código + nombre normal
                            html_parts.append(f'<td class="frozen">{cuenta_icon}📄 {cuenta_codigo} - {cuenta_nombre}</td>')
                        html_parts.append(f'<td class="frozen-total-left">{fmt_monto_html(cuenta_monto)}</td>')
                        
                        # Celdas mensuales del nivel 2
                        for mes in meses_lista:
                            m_acc = cu_montos_mes.get(mes, 0)
                            html_parts.append(f'<td>{fmt_monto_html(m_acc)}</td>')
                        
                        html_parts.append(f'<td>{fmt_monto_html(cuenta_monto)}</td>')
                        html_parts.append('</tr>')
                        
                        # NIVEL 3: Etiquetas (sub-detalle de cada cuenta)
                        # Detectar si es cuenta CxC para habilitar modal
                        es_cuenta_cxc = cuenta.get("es_cuenta_cxc", False)
                        
                        # Mapeo de iconos por estado de pago
                        ESTADO_ICONS = {
                            'Facturas Pagadas': '✅',
                            'Facturas Parcialmente Pagadas': '⏳',
                            'En Proceso de Pago': '🔄',
                            'Facturas No Pagadas': '❌'
                            # 'Facturas Revertidas' se excluye completamente
                        }
                        
                        if has_etiquetas:
                            # Renderizar etiquetas con estructura anidada de 4 niveles
                            # Nivel 3: CATEGORÍAS (expandibles)
                            # Nivel 4: PROVEEDORES (sub_etiquetas anidadas bajo categoría)
                            for etiqueta in etiquetas:
                                et_nombre = etiqueta.get("nombre", "")
                                et_monto = etiqueta.get("monto", 0)
                                et_montos_mes = etiqueta.get("montos_por_mes", {})
                                et_nivel = etiqueta.get("nivel", 4)
                                et_tipo = etiqueta.get("tipo", "proveedor")
                                sub_etiquetas = etiqueta.get("sub_etiquetas", [])
                                tiene_facturas = "facturas" in etiqueta and len(etiqueta.get("facturas", [])) > 0
                                total_facturas = etiqueta.get("total_facturas", 0)
                                
                                if et_nivel == 3:  # CATEGORÍA (expandible con sub_etiquetas)
                                    categoria_id_safe = et_nombre.replace(" ", "_").replace("📁", "").strip().replace(".", "_")
                                    # ID ÚNICO por cuenta+categoría para evitar conflictos entre estados
                                    unique_cat_id = f"{cuenta_id_safe}__{categoria_id_safe}"
                                    has_proveedores = len(sub_etiquetas) > 0
                                    
                                    # Icono para expandir/contraer proveedores
                                    if has_proveedores:
                                        categoria_icon = f'<span class="icon-expand" style="cursor:pointer;" onclick="toggleCategoria(\'{categoria_id_safe}\', \'{cuenta_id_safe}\')">{SVG_ICONS["chevron"]}</span>'
                                    else:
                                        categoria_icon = '<span style="width:24px;display:inline-block;"></span>'
                                    
                                    # Fila de CATEGORÍA (nivel 3) - indentación 140px
                                    html_parts.append(f'<tr class="etiqueta-row etiqueta-{cuenta_id_safe}" style="display:none; background-color: #1a1a2e;">')
                                    html_parts.append(f'<td class="frozen" style="padding-left: 140px; font-size: 13px; font-weight: bold; color: #e0e0e0; background-color: #1a1a2e; border-left: 3px solid #667eea;">{categoria_icon}{et_nombre}</td>')
                                    html_parts.append(f'<td class="frozen-total-left" style="background-color: #1a1a2e; font-size: 13px; font-weight: bold;">{fmt_monto_html(et_monto)}</td>')
                                    
                                    # Montos por mes de la categoría
                                    for mes in meses_lista:
                                        et_mes_monto = et_montos_mes.get(mes, 0)
                                        html_parts.append(f'<td style="font-size: 12px; color: #aaa; background-color: #1a1a2e;">{fmt_monto_html(et_mes_monto)}</td>')
                                    
                                    html_parts.append(f'<td style="font-size: 13px; font-weight: bold; background-color: #1a1a2e;">{fmt_monto_html(et_monto)}</td>')
                                    html_parts.append('</tr>')
                                    
                                    # NIVEL 4: PROVEEDORES (sub_etiquetas anidadas bajo categoría)
                                    for sub_etiqueta in sub_etiquetas:
                                        sub_nombre = sub_etiqueta.get("nombre", "")
                                        sub_monto = sub_etiqueta.get("monto", 0)
                                        sub_montos_mes = sub_etiqueta.get("montos_por_mes", {})
                                        sub_tiene_facturas = "facturas" in sub_etiqueta and len(sub_etiqueta.get("facturas", [])) > 0
                                        sub_total_facturas = sub_etiqueta.get("total_facturas", 0)
                                        
                                        # Fila de PROVEEDOR (nivel 4) - ID único por cuenta+categoría
                                        html_parts.append(f'<tr class="sub-etiqueta-row sub-etiqueta-{unique_cat_id} sub-etiqueta-of-{cuenta_id_safe}" style="display:none; background-color: #1a1a2e;">')
                                        html_parts.append(f'<td class="frozen" style="padding-left: 180px; font-size: 12px; font-weight: normal; color: #ccc; background-color: #1a1a2e; border-left: 3px solid #4a5568;">{sub_nombre}</td>')
                                        html_parts.append(f'<td class="frozen-total-left" style="background-color: #1a1a2e; font-size: 12px;">{fmt_monto_html(sub_monto)}</td>')
                                        
                                        # Montos por mes del proveedor
                                        for mes in meses_lista:
                                            sub_mes_monto = sub_montos_mes.get(mes, 0)
                                            html_parts.append(f'<td style="font-size: 11px; color: #aaa; background-color: #1a1a2e;">{fmt_monto_html(sub_mes_monto)}</td>')
                                        
                                        html_parts.append(f'<td style="font-size: 12px; background-color: #1a1a2e;">{fmt_monto_html(sub_monto)}</td>')
                                        html_parts.append('</tr>')
                                
                                else:
                                    # Etiquetas sin estructura anidada (otros casos como CxC)
                                    # Obtener icono según estado de pago (si es CxC)
                                    if es_cuenta_cxc:
                                        icono = ESTADO_ICONS.get(et_nombre, '🏷️')
                                        nombre_display = et_nombre
                                        padding_left_etiqueta = 140
                                    else:
                                        nombre_display = et_nombre
                                        padding_left_etiqueta = 80
                                    
                                    # Indicador de facturas si es CxC
                                    if es_cuenta_cxc and tiene_facturas:
                                        nombre_display += f' <span style="color: #667eea; font-size: 10px;">({total_facturas})</span>'
                                    
                                    html_parts.append(f'<tr class="etiqueta-row etiqueta-{cuenta_id_safe}" style="display:none; background-color: #1a1a2e;">')
                                    html_parts.append(f'<td class="frozen" style="padding-left: {padding_left_etiqueta}px; font-size: 12px; color: #ccc; background-color: #1a1a2e; border-left: 3px solid #4a5568;">{nombre_display}</td>')
                                    html_parts.append(f'<td class="frozen-total-left" style="background-color: #1a1a2e; font-size: 12px;">{fmt_monto_html(et_monto)}</td>')
                                    
                                    # Montos por mes
                                    for mes in meses_lista:
                                        et_mes_monto = et_montos_mes.get(mes, 0)
                                        html_parts.append(f'<td style="font-size: 11px; color: #aaa; background-color: #1a1a2e;">{fmt_monto_html(et_mes_monto)}</td>')
                                    
                                    html_parts.append(f'<td style="font-size: 12px; background-color: #1a1a2e;">{fmt_monto_html(et_monto)}</td>')
                                    html_parts.append('</tr>')


            
            # Subtotal de actividad
            html_parts.append(f'<tr class="subtotal">')
            html_parts.append(f'<td class="frozen"><strong>Subtotal {act_key}</strong></td>')
            html_parts.append(f'<td class="frozen-total-left"><strong>{fmt_monto_html(act_subtotal)}</strong></td>')
            for mes in meses_lista:
                monto_mes_sub = act_subtotal_por_mes.get(mes, 0)
                html_parts.append(f'<td>{fmt_monto_html(monto_mes_sub)}</td>')
            html_parts.append(f'<td><strong>{fmt_monto_html(act_subtotal)}</strong></td>')
            html_parts.append('</tr>')
        
        # Grand Totals
        html_parts.append(f'<tr class="grand-total">')
        html_parts.append(f'<td class="frozen"><strong>VARIACIÓN NETA DEL EFECTIVO</strong></td>')
        html_parts.append(f'<td class="frozen-total-left"><strong>{fmt_monto_html(variacion)}</strong></td>')
        for mes in meses_lista:
            variacion_mes = sum(
                actividades.get(ak, {}).get("subtotal_por_mes", {}).get(mes, 0)
                for ak in ["OPERACION", "INVERSION", "FINANCIAMIENTO"]
            )
            html_parts.append(f'<td>{fmt_monto_html(variacion_mes)}</td>')
        html_parts.append(f'<td><strong>{fmt_monto_html(variacion)}</strong></td>')
        html_parts.append('</tr>')
        
        html_parts.append(f'<tr class="data-row">')
        html_parts.append(f'<td class="frozen">EFECTIVO al inicio del período</td>')
        html_parts.append(f'<td class="frozen-total-left"><strong>{fmt_monto_html(ef_ini)}</strong></td>')
        _ef_acum = ef_ini
        for mes in meses_lista:
            html_parts.append(f'<td>{fmt_monto_html(_ef_acum)}</td>')
            _var_mes = sum(
                actividades.get(ak, {}).get("subtotal_por_mes", {}).get(mes, 0)
                for ak in ["OPERACION", "INVERSION", "FINANCIAMIENTO"]
            )
            _ef_acum += _var_mes
        html_parts.append(f'<td><strong>{fmt_monto_html(ef_ini)}</strong></td>')
        html_parts.append('</tr>')
        
        html_parts.append(f'<tr class="grand-total">')
        html_parts.append('<td class="frozen"><strong>EFECTIVO AL FINAL DEL PERÍODO</strong></td>')
        html_parts.append(f'<td class="frozen-total-left"><strong>{fmt_monto_html(ef_fin)}</strong></td>')
        _ef_acum2 = ef_ini
        for mes in meses_lista:
            _var_mes2 = sum(
                actividades.get(ak, {}).get("subtotal_por_mes", {}).get(mes, 0)
                for ak in ["OPERACION", "INVERSION", "FINANCIAMIENTO"]
            )
            _ef_acum2 += _var_mes2
            html_parts.append(f'<td>{fmt_monto_html(_ef_acum2)}</td>')
        html_parts.append(f'<td><strong>{fmt_monto_html(ef_fin)}</strong></td>')
        html_parts.append('</tr>')
        
        html_parts.append('</tbody>')
        html_parts.append('</table>')
        
        if len(meses_lista) > 3:
            html_parts.append('<div class="scroll-hint">← Desliza horizontalmente para ver más meses →</div>')
        
        html_parts.append('</div>')
        
        # Agregar JavaScript principal
        html_parts.append(ENTERPRISE_JS)
        
        # Renderizar con components.html con altura dinámica
        full_html = "".join(html_parts)
        # Calcular altura dinámica basada en el contenido visible
        num_conceptos = sum(len(act.get("conceptos", [])) for act in actividades.values())
        num_cuentas_total = sum(
            sum(len(concepto.get("cuentas", [])) for concepto in act.get("conceptos", []))
            for act in actividades.values()
        )
        num_etiquetas_total = sum(
            sum(
                sum(len(cuenta.get("etiquetas", [])) for cuenta in concepto.get("cuentas", []))
                for concepto in act.get("conceptos", [])
            )
            for act in actividades.values()
        )
        
        # Altura base: filas visibles + headers + totales
        # Solo contamos conceptos visibles (no expandidos)
        altura_visible = 200 + (num_conceptos * 50) + 150  # Headers + conceptos + totales
        # Altura máxima si todo está expandido
        altura_expandida = altura_visible + (num_cuentas_total * 40) + (num_etiquetas_total * 25)
        # Usar altura expandida como máximo, con scroll si se necesita
        altura_final = min(max(altura_expandida, 800), 3000)  # Mínimo 800, máximo 3000
        
        components.html(full_html, height=altura_final, scrolling=True)  # scrolling=True permite scroll interno
        
        # Export dinámico se realiza desde el botón dentro de la tabla HTML
        with export_placeholder:
            st.caption("ℹ️ Usa 'Exportar Excel (Vista actual)' dentro de la tabla para descargar según niveles abiertos.")
        
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
        
        # Sección informativa del mapeo de cuentas
        st.divider()
        with st.expander("ℹ️ **Configuración de Mapeo de Cuentas - Información para Encargados**", expanded=False):
            st.markdown("""
            ### 📋 Cómo se organizaron las cuentas contables para el Flujo de Caja
            
            Este mapeo fue generado mediante **análisis forense automático** de la contabilidad en Odoo (Enero 2026).
            Se analizaron **746 cuentas contables** y se identificó la estructura real del plan de cuentas.
            
            ---
            
            #### 💵 **CUENTAS DE EFECTIVO** (14 cuentas identificadas)
            
            Solo se consideran cuentas de tipo `asset_cash` (cajas y bancos):
            
            **Cajas:**
            - `11010101` - CAJA $
            - `11010102` - CAJA US$
            - `10000000` - Remuneraciones Cuenta Transitoria
            - `10000001` - BANCOS CUENTA TRANSITORIA
            
            **Bancos:**
            - `1101001` - BANCO SCOTIABANK CC CLP
            - `1101002` - BANCO SCOTIABANK CC USD
            - `1101003` - BANCO ITAU CC CLP
            - `1101004` - BANCO ITAU CC USD
            - `11010201` - BANCO SANTANDER CC CLP
            - `11010202` - BANCO SANTANDER US$
            - `11010203` - BANCO BICE CC CLP
            - `11010204` - BANCO BICE US$
            - `11010205` - BANCO BCI CC CLP
            - `11010206` - BANCO BCI US$
            
            ---
            
            #### 🔄 **ACTIVIDADES DE OPERACIÓN**
            
            **OP01 - Cobros por ventas:**
            - Prefijo `41` → Todas las cuentas de ingresos (Ej: 41010101 INGRESOS POR VENTAS DE PRODUCTOS)
            
            **OP02 - Pagos a proveedores:**
            - Prefijo `51` → Costo de ventas
            - Prefijo `52` → Gastos directos de producción
            - Prefijo `53` → Sobrecostos logísticos
            
            **OP03 - Pagos a empleados:**
            - Prefijo `61` → Sueldos y remuneraciones
            - Prefijo `62` → Bonos, gratificaciones, cargas sociales
            
            **OP04 - Intereses pagados:**
            - Prefijo `65` → Gastos financieros
            
            **OP05 - Intereses recibidos:**
            - Prefijo `42` → Ingresos financieros
            - Prefijo `77` → Otras ganancias
            
            **OP06 - Impuestos pagados:**
            - Prefijo `91` → Impuesto a la renta y diferidos
            
            **OP07 - Otros gastos operacionales:**
            - Prefijos `63`, `64`, `66`, `67`, `68`, `69` → Gastos de administración, ventas, otros
            
            ---
            
            #### 🏗️ **ACTIVIDADES DE INVERSIÓN**
            
            **IN01 - Adquisición de inversiones:**
            - Prefijo `13` → Activos intangibles, concesiones, marcas
            
            **IN02 - Compra de activos fijos:**
            - Prefijo `12` → Propiedades, planta y equipo (terrenos, edificios, maquinaria)
            
            **IN03 - Venta de activos:**
            - Prefijo `71` → Ingresos por venta de activos fijos
            
            **IN04 - Costo de venta de activos:**
            - Prefijo `81` → Costo asociado a venta de activos
            
            ---
            
            #### 💰 **ACTIVIDADES DE FINANCIAMIENTO**
            
            **FI01 - Préstamos (corto y largo plazo):**
            - Prefijo `21` → Pasivos corrientes (préstamos CP, obligaciones)
            
            **FI02 - Préstamos largo plazo:**
            - Prefijo `22` → Pasivos no corrientes
            
            **FI03 - Aportes de capital:**
            - Prefijo `31` → Patrimonio (capital, acciones, reservas)
            
            **FI04 - Distribuciones:**
            - Prefijo `32` → Dividendos, retiros, utilidades distribuidas
            
            ---
            
            ### 🔧 **¿Necesitas ajustar algo?**
            
            Si encuentras que:
            - Falta alguna cuenta de efectivo
            - Alguna categoría no está clasificada correctamente
            - Se necesitan prefijos adicionales
            
            **Contacta al equipo técnico** para ajustar el archivo:
            `backend/data/mapeo_flujo_caja.json`
            
            El script de análisis forense está disponible en:
            `scripts/debug_flujo_caja_forense.py`
            
            ---
            
            📅 **Última actualización:** Enero 2026 (Análisis automático de 746 cuentas)
            """)
            
    else:
        st.info("👆 Configura el período y haz clic en 'Generar' para cargar el dashboard enterprise")
