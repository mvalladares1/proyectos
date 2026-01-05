"""
Tab: YTD (Acumulado) - Estado de Resultados Year-to-Date.
"""
import streamlit as st
import pandas as pd


@st.fragment
def render(resultados: dict, ppto_ytd: dict, estructura: dict):
    """
    Renderiza el tab YTD con métricas principales y tabla de Estado de Resultados.
    Fragment independiente para evitar re-renders al cambiar de tab.
    
    Args:
        resultados: Dict con resultados reales (ingresos, costos, etc.)
        ppto_ytd: Dict con presupuesto YTD por categoría
        estructura: Dict con estructura detallada de cuentas
    """
    st.subheader("Estado de Resultados - YTD (Acumulado)")
    
    # === MÉTRICAS PRINCIPALES ===
    real_ing = resultados.get('ingresos', 0)
    real_cost = resultados.get('costos', 0)
    real_gd = resultados.get('gastos_directos', 0)
    real_gav = resultados.get('gav', 0)
    
    # Cálculos jerárquicos
    ub_calc = real_ing - real_cost
    mc_calc = ub_calc - real_gd
    ebit_calc = mc_calc - real_gav
    
    ppto_ing = ppto_ytd.get('1 - INGRESOS', 0)
    ppto_cost = ppto_ytd.get('2 - COSTOS', 0)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        dif_ing = ((real_ing - ppto_ing) / ppto_ing * 100) if ppto_ing else 0
        st.metric("Ingresos", f"${real_ing:,.0f}", f"{dif_ing:.1f}% vs PPTO")
    with col2:
        dif_cost = ((real_cost - ppto_cost) / ppto_cost * 100) if ppto_cost else 0
        st.metric("Costos", f"${real_cost:,.0f}", f"{dif_cost:.1f}% vs PPTO")
    with col3:
        st.metric("Utilidad Bruta (3)", f"${ub_calc:,.0f}")
    with col4:
        st.metric("EBIT (7)", f"${ebit_calc:,.0f}")
    
    st.divider()
    
    # === TABLA ESTADO DE RESULTADOS YTD ===
    eerr_data = []
    
    def agregar_fila(concepto, real, ppto, nivel=0, es_calculado=False):
        dif = real - ppto
        dif_pct = (dif / ppto * 100) if ppto != 0 else 0
        indent = "    " * nivel
        eerr_data.append({
            "Concepto": f"{indent}{concepto}",
            "Real YTD": real,
            "PPTO YTD": ppto,
            "Dif YTD": dif,
            "Dif %": dif_pct,
            "es_calculado": es_calculado
        })
    
    # 1 - INGRESOS
    ingresos_real = resultados.get("ingresos", 0)
    ingresos_ppto = ppto_ytd.get("1 - INGRESOS", 0)
    agregar_fila("1 - INGRESOS", ingresos_real, ingresos_ppto)
    if "1 - INGRESOS" in estructura:
        for subcat, subdata in estructura["1 - INGRESOS"].get("subcategorias", {}).items():
            agregar_fila(subcat, subdata.get("total", 0), 0, 1)
    
    # 2 - COSTOS
    costos_real = resultados.get("costos", 0)
    costos_ppto = ppto_ytd.get("2 - COSTOS", 0)
    agregar_fila("2 - COSTOS", costos_real, costos_ppto)
    if "2 - COSTOS" in estructura:
        for subcat, subdata in estructura["2 - COSTOS"].get("subcategorias", {}).items():
            agregar_fila(subcat, subdata.get("total", 0), 0, 1)
    
    # 3 - UTILIDAD BRUTA = 1 - 2
    ub_real = ingresos_real - costos_real
    ub_ppto = ingresos_ppto - costos_ppto
    agregar_fila("3 - UTILIDAD BRUTA", ub_real, ub_ppto, es_calculado=True)
    
    # 4 - GASTOS DIRECTOS
    gd_real = resultados.get("gastos_directos", 0)
    gd_ppto = ppto_ytd.get("4 - GASTOS DIRECTOS", 0)
    agregar_fila("4 - GASTOS DIRECTOS", gd_real, gd_ppto)
    
    # 5 - MARGEN DE CONTRIBUCIÓN = 3 - 4
    mc_real = ub_real - gd_real
    mc_ppto = ub_ppto - gd_ppto
    agregar_fila("5 - MARGEN DE CONTRIBUCIÓN", mc_real, mc_ppto, es_calculado=True)
    
    # 6 - GAV
    gav_real = resultados.get("gav", 0)
    gav_ppto = ppto_ytd.get("6 - GAV", 0)
    agregar_fila("6 - GAV", gav_real, gav_ppto)
    
    # 7 - UTILIDAD OPERACIONAL (EBIT) = 5 - 6
    ebit_real = mc_real - gav_real
    ebit_ppto = mc_ppto - gav_ppto
    agregar_fila("7 - UTILIDAD OPERACIONAL (EBIT)", ebit_real, ebit_ppto, es_calculado=True)
    
    # 8 - INTERESES
    int_real = resultados.get("intereses", 0)
    int_ppto = ppto_ytd.get("8 - INTERESES", 0)
    agregar_fila("8 - INTERESES", int_real, int_ppto)
    
    # 9 - UTILIDAD ANTES DE NO OP = 7 - 8
    uano_real = ebit_real - int_real
    uano_ppto = ebit_ppto - int_ppto
    agregar_fila("9 - UTILIDAD ANTES DE NO OP.", uano_real, uano_ppto, es_calculado=True)
    
    # 10 - INGRESOS NO OPERACIONALES
    ino_real = resultados.get("ingresos_no_operacionales", 0)
    ino_ppto = ppto_ytd.get("10 - INGRESOS NO OPERACIONALES", 0)
    agregar_fila("10 - INGRESOS NO OPERACIONALES", ino_real, ino_ppto)
    
    # 11 - GASTOS NO OPERACIONALES
    gno_real = resultados.get("gastos_no_operacionales", 0)
    gno_ppto = ppto_ytd.get("11 - GASTOS NO OPERACIONALES", 0)
    agregar_fila("11 - GASTOS NO OPERACIONALES", gno_real, gno_ppto)
    
    # 12 - RESULTADO NO OPERACIONAL = 10 - 11
    rno_real = ino_real - gno_real
    rno_ppto = ino_ppto - gno_ppto
    agregar_fila("12 - RESULTADO NO OPERACIONAL", rno_real, rno_ppto, es_calculado=True)
    
    # 13 - UTILIDAD ANTES DE IMPUESTOS = 9 + 12
    uai_real = uano_real + rno_real
    uai_ppto = uano_ppto + rno_ppto
    agregar_fila("13 - UTILIDAD ANTES DE IMPUESTOS", uai_real, uai_ppto, es_calculado=True)
    
    df_eerr = pd.DataFrame(eerr_data)
    cols_mostrar = ["Concepto", "Real YTD", "PPTO YTD", "Dif YTD", "Dif %"]
    df_display = df_eerr[cols_mostrar].copy()
    
    def resaltar_calculados(row):
        idx = row.name
        if df_eerr.iloc[idx].get("es_calculado", False):
            return ["background-color: #2d3748; font-weight: bold"] * len(cols_mostrar)
        return [""] * len(cols_mostrar)
    
    st.dataframe(
        df_display.style
        .format({
            "Real YTD": "${:,.0f}",
            "PPTO YTD": "${:,.0f}",
            "Dif YTD": "${:,.0f}",
            "Dif %": "{:.1f}%"
        })
        .apply(resaltar_calculados, axis=1),
        use_container_width=True,
        hide_index=True
    )
