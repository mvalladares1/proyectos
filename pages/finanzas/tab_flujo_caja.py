"""
Tab: Flujo de Caja - Estado de Flujo de Efectivo NIIF IAS 7.
"""
import streamlit as st
import pandas as pd
import requests
import altair as alt
from datetime import datetime, timedelta
from calendar import monthrange

from .shared import (
    FLUJO_CAJA_URL, fmt_flujo, build_ias7_categories_dropdown,
    sugerir_categoria, render_ias7_tree_activity, guardar_mapeo_cuenta
)


def render(username: str, password: str):
    """
    Renderiza el tab Flujo de Caja con método directo NIIF IAS 7.
    
    Args:
        username: Usuario para API
        password: Contraseña para API
    """
    st.subheader("💵 Estado de Flujo de Efectivo")
    st.caption("Método Directo - NIIF IAS 7")
    
    # === SELECTORES DE PERÍODO ===
    st.markdown("#### 📅 Seleccionar Período")
    
    periodo_opciones = ["Mes actual", "Mes anterior", "Último trimestre", "Año actual", "Personalizado"]
    
    col_periodo, col_desde, col_hasta, col_modo = st.columns([1.2, 1, 1, 1.2])
    
    with col_periodo:
        periodo_sel = st.selectbox("Período", periodo_opciones, key="finanzas_flujo_periodo")
    
    hoy = datetime.now()
    
    if periodo_sel == "Mes actual":
        flujo_fecha_ini = hoy.replace(day=1)
        ultimo_dia = monthrange(hoy.year, hoy.month)[1]
        flujo_fecha_fin = hoy.replace(day=ultimo_dia)
    elif periodo_sel == "Mes anterior":
        primer_dia_actual = hoy.replace(day=1)
        ultimo_dia_anterior = primer_dia_actual - timedelta(days=1)
        flujo_fecha_ini = ultimo_dia_anterior.replace(day=1)
        flujo_fecha_fin = ultimo_dia_anterior
    elif periodo_sel == "Último trimestre":
        flujo_fecha_fin = hoy
        flujo_fecha_ini = hoy - timedelta(days=90)
    elif periodo_sel == "Año actual":
        flujo_fecha_ini = datetime(hoy.year, 1, 1)
        flujo_fecha_fin = hoy
    else:
        flujo_fecha_ini = hoy.replace(day=1)
        flujo_fecha_fin = hoy
    
    with col_desde:
        flujo_f_inicio = st.date_input(
            "Desde", value=flujo_fecha_ini, format="DD/MM/YYYY",
            key="finanzas_flujo_desde", disabled=periodo_sel != "Personalizado"
        )
    
    with col_hasta:
        flujo_f_fin = st.date_input(
            "Hasta", value=flujo_fecha_fin, format="DD/MM/YYYY",
            key="finanzas_flujo_hasta", disabled=periodo_sel != "Personalizado"
        )
    
    with col_modo:
        st.caption("Modo de Visualización")
        modo_ver = st.radio("Modo", ["Real", "Proyectado", "Consolidado"],
                           horizontal=True, label_visibility="collapsed", key="finanzas_modo_ver")
    
    if periodo_sel == "Personalizado":
        flujo_inicio_str = flujo_f_inicio.strftime("%Y-%m-%d")
        flujo_fin_str = flujo_f_fin.strftime("%Y-%m-%d")
    else:
        flujo_inicio_str = flujo_fecha_ini.strftime("%Y-%m-%d")
        flujo_fin_str = flujo_fecha_fin.strftime("%Y-%m-%d")
    
    flujo_cache_key = f"finanzas_flujo_{flujo_inicio_str}_{flujo_fin_str}"
    
    st.markdown("---")
    
    # === BOTÓN GENERAR ===
    def cargar_flujo_click():
        if flujo_cache_key in st.session_state:
            del st.session_state[flujo_cache_key]
        st.session_state['finanzas_flujo_clicked'] = True
    
    col_btn, col_info = st.columns([1, 2])
    with col_btn:
        st.button("🔄 Generar Flujo de Caja", type="primary", use_container_width=True,
                 key="finanzas_btn_flujo", on_click=cargar_flujo_click)
    with col_info:
        st.info(f"📅 Período: {flujo_inicio_str} a {flujo_fin_str}")
    
    # === CARGAR Y MOSTRAR DATOS ===
    if st.session_state.get('finanzas_flujo_clicked') or flujo_cache_key in st.session_state:
        
        if flujo_cache_key not in st.session_state:
            with st.spinner("Consultando movimientos de efectivo..."):
                try:
                    resp = requests.get(
                        f"{FLUJO_CAJA_URL}/",
                        params={
                            "fecha_inicio": flujo_inicio_str,
                            "fecha_fin": flujo_fin_str,
                            "username": username,
                            "password": password
                        },
                        timeout=120
                    )
                    if resp.status_code == 200:
                        st.session_state[flujo_cache_key] = resp.json()
                    else:
                        st.error(f"Error {resp.status_code}: {resp.text}")
                        return
                except Exception as e:
                    st.error(f"Error de conexión: {e}")
                    return
        
        flujo_data = st.session_state.get(flujo_cache_key, {})
        
        if "error" in flujo_data:
            st.error(f"Error: {flujo_data['error']}")
            return
        
        # Extraer datos
        actividades = flujo_data.get("actividades", {})
        if modo_ver == "Proyectado":
            actividades = flujo_data.get("actividades_proy", actividades)
        elif modo_ver == "Consolidado":
            actividades_real = flujo_data.get("actividades", {})
            actividades_proy = flujo_data.get("actividades_proy", {})
            for key in actividades_real:
                if key in actividades_proy:
                    actividades_real[key]["subtotal"] = (
                        actividades_real[key].get("subtotal", 0) +
                        actividades_proy[key].get("subtotal", 0)
                    )
            actividades = actividades_real
        
        conciliacion = flujo_data.get("conciliacion", {})
        cuentas_nc = flujo_data.get("cuentas_sin_clasificar", [])
        drill_down = flujo_data.get("drill_down", {})
        
        # === KPIs ===
        op = actividades.get("OPERACION", {}).get("subtotal", 0)
        inv = actividades.get("INVERSION", {}).get("subtotal", 0)
        fin = actividades.get("FINANCIAMIENTO", {}).get("subtotal", 0)
        ef_ini = conciliacion.get("efectivo_inicial", 0)
        ef_fin = conciliacion.get("efectivo_final", 0)
        otros = conciliacion.get("otros_no_clasificados", 0)
        
        # Status del flujo
        if otros == 0 and len(cuentas_nc) == 0:
            st.success("✅ Flujo completo - Todas las cuentas clasificadas")
        elif abs(otros) < abs(ef_fin - ef_ini) * 0.05:
            st.warning(f"⚠️ Flujo con {len(cuentas_nc)} cuentas pendientes: ${abs(otros):,.0f}")
        else:
            st.error(f"❌ Revisar clasificación - ${abs(otros):,.0f} sin clasificar")
        
        # Métricas
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("🟢 Operación", fmt_flujo(op))
        with col2:
            st.metric("🔵 Inversión", fmt_flujo(inv))
        with col3:
            st.metric("🟣 Financiamiento", fmt_flujo(fin))
        with col4:
            st.metric("💰 Efectivo Inicial", fmt_flujo(ef_ini))
        with col5:
            variacion = op + inv + fin
            st.metric("💵 Efectivo Final", fmt_flujo(ef_fin), delta=fmt_flujo(variacion))
        
        st.divider()
        
        # === WATERFALL CHART ===
        waterfall_data = [
            {"Concepto": "Efectivo Inicial", "Monto": ef_ini, "Tipo": "Inicial"},
            {"Concepto": "Operación", "Monto": op, "Tipo": "Actividad"},
            {"Concepto": "Inversión", "Monto": inv, "Tipo": "Actividad"},
            {"Concepto": "Financiamiento", "Monto": fin, "Tipo": "Actividad"},
        ]
        if otros != 0:
            waterfall_data.append({"Concepto": "Otros", "Monto": otros, "Tipo": "Otros"})
        waterfall_data.append({"Concepto": "Efectivo Final", "Monto": ef_fin, "Tipo": "Final"})
        
        df_waterfall = pd.DataFrame(waterfall_data)
        
        chart_waterfall = alt.Chart(df_waterfall).mark_bar().encode(
            x=alt.X("Concepto:N", sort=None, axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("Monto:Q", title="Monto (CLP)"),
            color=alt.Color("Tipo:N", scale=alt.Scale(
                domain=["Inicial", "Actividad", "Otros", "Final"],
                range=["#3498db", "#2ecc71", "#f39c12", "#9b59b6"]
            )),
            tooltip=[alt.Tooltip("Concepto:N"), alt.Tooltip("Monto:Q", title="Monto", format="$,.0f")]
        ).properties(height=300)
        
        st.altair_chart(chart_waterfall, use_container_width=True)
        
        st.divider()
        
        # === ESTADO DE FLUJO OFICIAL (React Component) ===
        st.markdown("### 📋 Estado de Flujo de Efectivo (NIIF IAS 7)")
        
        # Importar y usar el nuevo componente React
        try:
            from components.ias7_tree import ias7_tree, transform_backend_to_component
            
            # Transformar datos al formato del componente
            props = transform_backend_to_component(flujo_data, modo=modo_ver.lower())
            
            # Renderizar el componente React
            ias7_tree(**props)
        except ImportError as e:
            st.warning(f"Componente React no disponible: {e}. Usando renderizado alternativo.")
            # Fallback: usar render directo sin HTML problemático
            from .shared import render_ias7_tree_activity
            colores = {"OPERACION": "#2ecc71", "INVERSION": "#3498db", "FINANCIAMIENTO": "#9b59b6"}
            for act_key in ["OPERACION", "INVERSION", "FINANCIAMIENTO"]:
                act_data = actividades.get(act_key, {})
                if act_data:
                    render_ias7_tree_activity(
                        actividad_data=act_data,
                        cuentas_por_concepto=drill_down,
                        docs_por_concepto={},
                        actividad_key=act_key,
                        color=colores.get(act_key, "#718096")
                    )
        
        st.divider()
        
        # === CONCILIACIÓN ===
        st.markdown("### 📑 Conciliación de Efectivo")
        
        concil_data = [
            {"Concepto": "Incremento neto en efectivo", "Monto": conciliacion.get("incremento_neto", 0)},
            {"Concepto": "Efectos variación tipo cambio", "Monto": conciliacion.get("efecto_tipo_cambio", 0)},
        ]
        if otros != 0:
            concil_data.append({"Concepto": "Otros no clasificados", "Monto": otros})
        concil_data.extend([
            {"Concepto": "Efectivo al inicio", "Monto": ef_ini},
            {"Concepto": "Efectivo al cierre", "Monto": ef_fin},
        ])
        
        df_concil = pd.DataFrame(concil_data)
        st.dataframe(df_concil.style.format({"Monto": "${:,.0f}"}), use_container_width=True, hide_index=True)
        
        # === EDITOR DE MAPEO ===
        if cuentas_nc and len(cuentas_nc) > 0:
            st.divider()
            st.markdown("### ✏️ Editor de Mapeo de Cuentas")
            
            with st.expander(f"📋 {len(cuentas_nc)} cuentas sin clasificar ({fmt_flujo(abs(otros))})", expanded=True):
                st.warning(f"⚠️ {len(cuentas_nc)} cuentas generan ${abs(otros):,.0f} en 'Otros no clasificados'")
                
                categorias = build_ias7_categories_dropdown()
                codigo_to_option = {v: k for k, v in categorias.items() if v}
                
                total_nc = sum(abs(c.get('monto', 0)) for c in cuentas_nc)
                
                for cuenta in sorted(cuentas_nc, key=lambda x: abs(x.get('monto', 0)), reverse=True)[:25]:
                    codigo = cuenta.get('codigo', '')
                    nombre = cuenta.get('nombre', '')
                    monto = cuenta.get('monto', 0)
                    pct = abs(monto) / total_nc * 100 if total_nc > 0 else 0
                    
                    sugerencia, razon = sugerir_categoria(nombre, monto)
                    
                    monto_color = "#2ecc71" if monto >= 0 else "#e74c3c"
                    monto_display = f"+${monto:,.0f}" if monto >= 0 else f"-${abs(monto):,.0f}"
                    
                    col1, col2, col3, col4, col5 = st.columns([0.8, 2, 1, 0.6, 2])
                    with col1:
                        st.markdown(f"<span style='font-family:monospace;color:#718096;'>{codigo}</span>", unsafe_allow_html=True)
                    with col2:
                        st.caption(nombre[:40])
                        if sugerencia:
                            st.markdown(f"<small style='color:#3498db;'>💡 {sugerencia}</small>", unsafe_allow_html=True)
                    with col3:
                        st.markdown(f"<span style='color:{monto_color};font-weight:bold;'>{monto_display}</span>", unsafe_allow_html=True)
                    with col4:
                        st.caption(f"{pct:.1f}%")
                    with col5:
                        col_sel, col_btn = st.columns([3, 1])
                        with col_sel:
                            default_idx = 0
                            if sugerencia and sugerencia in codigo_to_option:
                                option_label = codigo_to_option[sugerencia]
                                if option_label in list(categorias.keys()):
                                    default_idx = list(categorias.keys()).index(option_label)
                            
                            cat_sel = st.selectbox("Cat", options=list(categorias.keys()),
                                                  index=default_idx, key=f"finanzas_cat_{codigo}",
                                                  label_visibility="collapsed")
                        with col_btn:
                            if categorias.get(cat_sel):
                                if st.button("💾", key=f"finanzas_save_{codigo}"):
                                    ok, err = guardar_mapeo_cuenta(
                                        codigo, categorias[cat_sel], nombre,
                                        username, password, monto
                                    )
                                    if ok:
                                        st.success(f"✓ {codigo}")
                                        if flujo_cache_key in st.session_state:
                                            del st.session_state[flujo_cache_key]
                                        st.rerun()
                                    else:
                                        st.error(err)
                
                if len(cuentas_nc) > 25:
                    st.info(f"Mostrando 25 de {len(cuentas_nc)} cuentas.")
                
                # Historial
                historial = flujo_data.get("historial_mapeo", [])
                if historial:
                    with st.expander("📋 Historial de Cambios", expanded=False):
                        df_hist = pd.DataFrame(historial).sort_values("fecha", ascending=False)
                        cols_hist = ["fecha", "usuario", "cuenta", "concepto_anterior", "concepto_nuevo"]
                        st.dataframe(df_hist[[c for c in cols_hist if c in df_hist.columns]],
                                   use_container_width=True, hide_index=True)
