"""
Tab: CG - Análisis por Cuenta Contable.
"""
import streamlit as st
import pandas as pd
import plotly.express as px


@st.fragment
def render(estructura: dict, fecha_inicio: str, fecha_fin: str, centro_seleccionado: str):
    """
    Renderiza el tab CG con análisis detallado por cuenta contable.
    Fragment independiente para evitar re-renders al cambiar de tab.
    
    Args:
        estructura: Dict con estructura detallada de cuentas
        fecha_inicio: Fecha inicio del período
        fecha_fin: Fecha fin del período
        centro_seleccionado: Centro de costo seleccionado
    """
    st.subheader("📊 CG - Por Cuenta Contable")
    st.caption("Análisis detallado por cuenta contable | Filtros aplicables en sidebar")
    
    # Extraer todas las cuentas contables de la estructura
    cuentas_dict = {}
    
    if estructura:
        for cat_name, cat_data in estructura.items():
            if isinstance(cat_data, dict):
                subcategorias = cat_data.get("subcategorias", {})
                if isinstance(subcategorias, dict):
                    for subcat2_name, subcat2_data in subcategorias.items():
                        if isinstance(subcat2_data, dict):
                            subcats3 = subcat2_data.get("subcategorias", {})
                            if isinstance(subcats3, dict):
                                for subcat3_name, subcat3_data in subcats3.items():
                                    if isinstance(subcat3_data, dict):
                                        cuentas = subcat3_data.get("cuentas", {})
                                        if isinstance(cuentas, dict):
                                            for cuenta_name, cuenta_monto in cuentas.items():
                                                cuentas_dict[cuenta_name] = {
                                                    "monto": cuenta_monto,
                                                    "categoria": cat_name,
                                                    "subcat2": subcat2_name,
                                                    "subcat3": subcat3_name
                                                }
    
    if cuentas_dict:
        # Selector de cuenta contable
        opciones_cuentas = ["Todas"] + sorted([c for c in cuentas_dict.keys()])
        cuenta_seleccionada = st.selectbox(
            "Seleccionar Cuenta Contable",
            opciones_cuentas,
            key="finanzas_cuenta_cg"
        )
        
        if cuenta_seleccionada == "Todas":
            _render_todas_cuentas(cuentas_dict)
        else:
            _render_cuenta_especifica(cuenta_seleccionada, cuentas_dict, fecha_inicio, fecha_fin, centro_seleccionado)
    else:
        st.warning("No hay cuentas contables disponibles para el período y filtros seleccionados.")
        
        with st.expander("ℹ️ Información de debug"):
            st.write("Estructura disponible:")
            if estructura:
                st.write(f"Categorías: {list(estructura.keys())}")
                for cat_name in list(estructura.keys())[:1]:
                    st.write(f"\n{cat_name}:")
                    st.json(estructura[cat_name], expanded=False)
            else:
                st.write("Estructura vacía")


def _render_todas_cuentas(cuentas_dict: dict):
    """Renderiza vista de todas las cuentas."""
    st.write("**Todas las Cuentas Contables**")
    
    df_cuentas = []
    for cuenta_name, cuenta_info in sorted(cuentas_dict.items()):
        df_cuentas.append({
            "Cuenta": cuenta_name,
            "Categoría": cuenta_info["categoria"],
            "Subcategoría": cuenta_info.get("subcat3", cuenta_info.get("subcat2", "")),
            "Monto": cuenta_info["monto"]
        })
    
    df = pd.DataFrame(df_cuentas)
    df = df.sort_values("Monto", key=abs, ascending=False)
    
    st.dataframe(
        df.style.format({"Monto": "${:,.0f}"}),
        use_container_width=True,
        hide_index=True
    )
    
    # Gráfico de top 10
    st.divider()
    st.subheader("📈 Top 10 Cuentas por Monto")
    
    df_top = df.copy()
    df_top["Abs_Monto"] = df_top["Monto"].abs()
    df_top = df_top.nlargest(10, "Abs_Monto")
    
    fig = px.bar(
        df_top.sort_values("Monto"),
        y="Cuenta",
        x="Monto",
        orientation="h",
        title="Top 10 Cuentas Contables",
        labels={"Monto": "Monto (CLP)", "Cuenta": "Cuenta"},
        color="Monto",
        color_continuous_scale="RdYlGn"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Resumen por categoría
    st.divider()
    st.subheader("📊 Distribución por Categoría")
    
    resumen_cat = df.groupby("Categoría")["Monto"].sum().reset_index()
    resumen_cat = resumen_cat.sort_values("Monto", key=abs, ascending=False)
    
    col_tabla, col_grafico = st.columns([1, 1])
    with col_tabla:
        st.dataframe(
            resumen_cat.style.format({"Monto": "${:,.0f}"}),
            use_container_width=True,
            hide_index=True
        )
    with col_grafico:
        fig_cat = px.pie(
            resumen_cat,
            values="Monto",
            names="Categoría",
            title="Proporción por Categoría"
        )
        st.plotly_chart(fig_cat, use_container_width=True)


def _render_cuenta_especifica(cuenta_seleccionada: str, cuentas_dict: dict, 
                               fecha_inicio: str, fecha_fin: str, centro_seleccionado: str):
    """Renderiza vista de una cuenta específica."""
    cuenta_info = cuentas_dict[cuenta_seleccionada]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Monto", f"${cuenta_info['monto']:,.0f}")
    with col2:
        st.metric("Categoría", cuenta_info["categoria"])
    with col3:
        st.metric("Subcategoría", cuenta_info.get("subcat3", cuenta_info.get("subcat2", "")))
    
    st.divider()
    st.info(f"""
    **Cuenta:** {cuenta_seleccionada}
    
    **Categoría:** {cuenta_info['categoria']}
    
    **Subcategoría 2:** {cuenta_info['subcat2']}
    
    **Subcategoría 3:** {cuenta_info['subcat3']}
    
    **Período:** {fecha_inicio} a {fecha_fin}
    
    **Centro de Costo:** {centro_seleccionado}
    """)
