"""
Tab: Detalle - Estado de Resultados con vista desplegable jerárquica.
"""
import streamlit as st
import pandas as pd
from .shared import fmt_monto, fmt_pct


@st.fragment
def render(estructura: dict, ppto_ytd: dict):
    """
    Renderiza el tab Detalle con vista jerárquica desplegable.
    Fragment independiente para evitar re-renders al cambiar de tab.
    
    Args:
        estructura: Dict con estructura detallada de cuentas
        ppto_ytd: Dict con presupuesto YTD por categoría
    """
    st.subheader("📋 Estado de Resultados - Vista Desplegable")
    st.caption("Haz clic en cada categoría para ver el detalle de subcategorías y cuentas")
    
    # Orden de categorías para el EERR
    orden_categorias = [
        "1 - INGRESOS",
        "2 - COSTOS",
        "4 - GASTOS DIRECTOS",
        "6 - GAV",
        "8 - INTERESES",
        "10 - INGRESOS NO OPERACIONALES",
        "11 - GASTOS NO OPERACIONALES"
    ]
    
    # Calcular resultados intermedios
    ingresos = estructura.get("1 - INGRESOS", {}).get("total", 0)
    costos = estructura.get("2 - COSTOS", {}).get("total", 0)
    gastos_directos = estructura.get("4 - GASTOS DIRECTOS", {}).get("total", 0)
    gav = estructura.get("6 - GAV", {}).get("total", 0)
    intereses = estructura.get("8 - INTERESES", {}).get("total", 0)
    ing_no_op = estructura.get("10 - INGRESOS NO OPERACIONALES", {}).get("total", 0)
    gast_no_op = estructura.get("11 - GASTOS NO OPERACIONALES", {}).get("total", 0)
    
    utilidad_bruta = ingresos - costos
    margen_contribucion = utilidad_bruta - gastos_directos
    ebit = margen_contribucion - gav
    util_antes_no_op = ebit - intereses
    resultado_no_op = ing_no_op - gast_no_op
    util_antes_impuestos = util_antes_no_op + resultado_no_op
    
    # Mapeo de categorías a PPTO
    mapeo_ppto = {
        "1 - INGRESOS": "1 - INGRESOS",
        "2 - COSTOS": "2 - COSTOS",
        "4 - GASTOS DIRECTOS": "4 - GASTOS DIRECTOS",
        "6 - GAV": "6 - GAV",
        "8 - INTERESES": "8 - INTERESES",
        "10 - INGRESOS NO OPERACIONALES": "10 - INGRESOS NO OPERACIONALES",
        "11 - GASTOS NO OPERACIONALES": "11 - GASTOS NO OPERACIONALES"
    }
    
    # === MOSTRAR CADA CATEGORÍA ===
    for cat in orden_categorias:
        cat_data = estructura.get(cat, {"total": 0, "subcategorias": {}})
        real_total = cat_data.get("total", 0)
        ppto_total = ppto_ytd.get(mapeo_ppto.get(cat, cat), 0)
        dif = real_total - ppto_total
        dif_pct = (dif / ppto_total * 100) if ppto_total != 0 else 0
        
        # Header de categoría con métricas
        col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
        with col1:
            st.markdown(f"### {cat}")
        with col2:
            st.metric("Real YTD", fmt_monto(real_total))
        with col3:
            st.metric("PPTO YTD", fmt_monto(ppto_total))
        with col4:
            st.metric("Dif", fmt_monto(dif), delta=fmt_pct(dif_pct))
        
        # Subcategorías desplegables
        subcats = cat_data.get("subcategorias", {})
        if subcats:
            for subcat_nombre, subcat_data in sorted(subcats.items()):
                subcat_total = subcat_data.get("total", 0)
                with st.expander(f"↳ {subcat_nombre}: {fmt_monto(subcat_total)}"):
                    # Nivel 3: Subcategorías internas
                    nivel3 = subcat_data.get("subcategorias", {})
                    if nivel3:
                        for n3_nombre, n3_data in sorted(nivel3.items()):
                            n3_total = n3_data.get("total", 0)
                            st.markdown(f"**{n3_nombre}**: {fmt_monto(n3_total)}")
                            
                            # Cuentas individuales
                            cuentas = n3_data.get("cuentas", {})
                            if cuentas:
                                df_cuentas = pd.DataFrame([
                                    {"Cuenta": k, "Monto": v}
                                    for k, v in sorted(cuentas.items(), key=lambda x: abs(x[1]), reverse=True)
                                ])
                                st.dataframe(
                                    df_cuentas.style.format({"Monto": "${:,.0f}"}),
                                    use_container_width=True,
                                    hide_index=True,
                                    height=min(len(df_cuentas) * 35 + 38, 300)
                                )
                    else:
                        # Si no hay nivel 3, mostrar cuentas directamente
                        cuentas = subcat_data.get("cuentas", {})
                        if cuentas:
                            df_cuentas = pd.DataFrame([
                                {"Cuenta": k, "Monto": v}
                                for k, v in sorted(cuentas.items(), key=lambda x: abs(x[1]), reverse=True)
                            ])
                            st.dataframe(
                                df_cuentas.style.format({"Monto": "${:,.0f}"}),
                                use_container_width=True,
                                hide_index=True,
                                height=min(len(df_cuentas) * 35 + 38, 300)
                            )
        
        st.markdown("---")
        
        # Insertar filas calculadas después de ciertas categorías
        if cat == "2 - COSTOS":
            _render_fila_calculada("3 - UTILIDAD BRUTA", utilidad_bruta, ppto_ytd)
        elif cat == "4 - GASTOS DIRECTOS":
            _render_fila_calculada("5 - MARGEN DE CONTRIBUCIÓN", margen_contribucion, ppto_ytd)
        elif cat == "6 - GAV":
            _render_fila_calculada("7 - UTILIDAD OPERACIONAL (EBIT)", ebit, ppto_ytd)
        elif cat == "8 - INTERESES":
            _render_fila_calculada("9 - UTILIDAD ANTES DE NO OP.", util_antes_no_op, ppto_ytd)
        elif cat == "11 - GASTOS NO OPERACIONALES":
            _render_fila_calculada("12 - RESULTADO NO OPERACIONAL", resultado_no_op, ppto_ytd)
            _render_fila_calculada("13 - UTILIDAD ANTES DE IMPUESTOS", util_antes_impuestos, ppto_ytd)


def _render_fila_calculada(nombre: str, valor: float, ppto_ytd: dict):
    """Renderiza una fila calculada (subtotales)."""
    st.markdown(f"### 🟦 {nombre}")
    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
    with col2:
        st.metric("Real YTD", fmt_monto(valor))
    
    # Calcular PPTO equivalente
    ppto_valor = ppto_ytd.get(nombre, 0)
    with col3:
        st.metric("PPTO YTD", fmt_monto(ppto_valor))
    with col4:
        dif = valor - ppto_valor
        st.metric("Dif", fmt_monto(dif))
    st.markdown("---")
