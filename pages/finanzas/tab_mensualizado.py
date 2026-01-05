"""
"""
Tab: Mensualizado - Control Presupuestario con detalle mes a mes.
"""
import streamlit as st
import pandas as pd


@st.fragment
def render(datos_mensuales: dict, ppto_mensual: dict, meses_seleccionados: list,
           meses_opciones: dict, año_seleccionado: int):
    """
    Renderiza el tab Mensualizado con vista de Reales, PPTO y Variaciones por mes.
    Fragment independiente para evitar re-renders al cambiar de tab.
    
    Args:
        datos_mensuales: Dict con datos reales mensuales {YYYY-MM: {categoria: valor}}
        ppto_mensual: Dict con presupuesto mensual {YYYY-MM: {categoria: valor}}
        meses_seleccionados: Lista de nombres de meses seleccionados
        meses_opciones: Dict {nombre_mes: numero_mes}
        año_seleccionado: Año actual
    """
    st.subheader("💰 Control Presupuestario - Mensualizado Detalle")
    st.caption("Detalle mes a mes de los meses seleccionados")
    
    # === MESES DEL AÑO ===
    meses_nombres = {
        "01": "ENE", "02": "FEB", "03": "MAR", "04": "ABR",
        "05": "MAY", "06": "JUN", "07": "JUL", "08": "AGO",
        "09": "SEP", "10": "OCT", "11": "NOV", "12": "DIC"
    }
    
    # Mapear datos mensuales por número de mes
    meses_data = {}
    for mes_str, datos_mes in datos_mensuales.items():
        if "-" in mes_str:
            mes_num = mes_str.split("-")[1]
            if mes_num in meses_nombres:
                meses_data[mes_num] = datos_mes
    
    # Convertir meses seleccionados a números
    meses_nums_sel = [meses_opciones[m] for m in meses_seleccionados]
    
    # Definir estructura completa EERR con indicador de calculado
    estructura_eerr = [
        ("1 - INGRESOS", False),
        ("2 - COSTOS", False),
        ("3 - UTILIDAD BRUTA", True),
        ("4 - GASTOS DIRECTOS", False),
        ("5 - MARGEN DE CONTRIBUCIÓN", True),
        ("6 - GAV", False),
        ("7 - UTILIDAD OPERACIONAL (EBIT)", True),
        ("8 - INTERESES", False),
        ("9 - UTILIDAD ANTES DE NO OP.", True),
        ("10 - INGRESOS NO OPERACIONALES", False),
        ("11 - GASTOS NO OPERACIONALES", False),
        ("12 - RESULTADO NO OPERACIONAL", True),
        ("13 - UTILIDAD ANTES DE IMPUESTOS", True),
    ]
    
    def obtener_valor_mensual(mes_num, concepto, datos_mes_dict):
        """Obtiene valor para un concepto (calculando los derivados)."""
        if concepto.startswith("3 - "):
            ing = datos_mes_dict.get(mes_num, {}).get("1 - INGRESOS", 0)
            cost = datos_mes_dict.get(mes_num, {}).get("2 - COSTOS", 0)
            return ing - cost
        elif concepto.startswith("5 - "):
            ub = obtener_valor_mensual(mes_num, "3 - UTILIDAD BRUTA", datos_mes_dict)
            gd = datos_mes_dict.get(mes_num, {}).get("4 - GASTOS DIRECTOS", 0)
            return ub - gd
        elif concepto.startswith("7 - "):
            mc = obtener_valor_mensual(mes_num, "5 - MARGEN", datos_mes_dict)
            gav = datos_mes_dict.get(mes_num, {}).get("6 - GAV", 0)
            return mc - gav
        elif concepto.startswith("9 - "):
            ebit = obtener_valor_mensual(mes_num, "7 - EBIT", datos_mes_dict)
            inter = datos_mes_dict.get(mes_num, {}).get("8 - INTERESES", 0)
            return ebit - inter
        elif concepto.startswith("12 - "):
            ino = datos_mes_dict.get(mes_num, {}).get("10 - INGRESOS NO OPERACIONALES", 0)
            gno = datos_mes_dict.get(mes_num, {}).get("11 - GASTOS NO OPERACIONALES", 0)
            return ino - gno
        elif concepto.startswith("13 - "):
            uano = obtener_valor_mensual(mes_num, "9 - UTIL", datos_mes_dict)
            rno = obtener_valor_mensual(mes_num, "12 - RESULTADO", datos_mes_dict)
            return uano + rno
        else:
            return datos_mes_dict.get(mes_num, {}).get(concepto, 0)
    
    cols_meses = [meses_nombres[m] for m in meses_nums_sel]
    
    # === VISTA DE REALES MENSUALES ===
    st.write("**📊 Montos Reales (CLP)**")
    tabla_real = {"Concepto": [], "es_calculado": []}
    for concepto, es_calc in estructura_eerr:
        tabla_real["Concepto"].append(concepto)
        tabla_real["es_calculado"].append(es_calc)
    
    for mes_num in meses_nums_sel:
        tabla_real[meses_nombres[mes_num]] = []
        for concepto, _ in estructura_eerr:
            val = obtener_valor_mensual(mes_num, concepto, meses_data)
            tabla_real[meses_nombres[mes_num]].append(val)
    
    df_real = pd.DataFrame(tabla_real)
    
    def resaltar_calculados(row, df_ref):
        idx = row.name
        if df_ref.iloc[idx].get("es_calculado", False):
            return ["background-color: #2d3748; font-weight: bold"] * len(row)
        return [""] * len(row)
    
    st.dataframe(
        df_real[["Concepto"] + cols_meses].style
        .format("{:,.0f}", subset=cols_meses)
        .apply(lambda x: resaltar_calculados(x, df_real), axis=1),
        use_container_width=True,
        hide_index=True
    )
    
    # === VISTA DE PRESUPUESTO MENSUAL ===
    st.write("**💰 Presupuesto (CLP)**")
    
    meses_ppto_data = {}
    for mes_num in meses_nums_sel:
        mes_key = f"{año_seleccionado}-{mes_num}"
        meses_ppto_data[mes_num] = ppto_mensual.get(mes_key, {})
    
    tabla_ppto = {"Concepto": [], "es_calculado": []}
    for concepto, es_calc in estructura_eerr:
        tabla_ppto["Concepto"].append(concepto)
        tabla_ppto["es_calculado"].append(es_calc)
    
    for mes_num in meses_nums_sel:
        tabla_ppto[meses_nombres[mes_num]] = []
        for concepto, _ in estructura_eerr:
            val = obtener_valor_mensual(mes_num, concepto, meses_ppto_data)
            tabla_ppto[meses_nombres[mes_num]].append(val)
    
    df_ppto = pd.DataFrame(tabla_ppto)
    
    st.dataframe(
        df_ppto[["Concepto"] + cols_meses].style
        .format("{:,.0f}", subset=cols_meses)
        .apply(lambda x: resaltar_calculados(x, df_ppto), axis=1),
        use_container_width=True,
        hide_index=True
    )
    
    # === VARIACIONES ===
    st.divider()
    st.write("**📈 Variaciones (Real - PPTO)**")
    tabla_var = {"Concepto": [], "es_calculado": []}
    for concepto, es_calc in estructura_eerr:
        tabla_var["Concepto"].append(concepto)
        tabla_var["es_calculado"].append(es_calc)
    
    for mes_num in meses_nums_sel:
        tabla_var[meses_nombres[mes_num]] = []
        for concepto, _ in estructura_eerr:
            real_val = obtener_valor_mensual(mes_num, concepto, meses_data)
            ppto_val = obtener_valor_mensual(mes_num, concepto, meses_ppto_data)
            tabla_var[meses_nombres[mes_num]].append(real_val - ppto_val)
    
    df_var = pd.DataFrame(tabla_var)
    
    st.dataframe(
        df_var[["Concepto"] + cols_meses].style
        .format("{:,.0f}", subset=cols_meses)
        .apply(lambda x: resaltar_calculados(x, df_var), axis=1),
        use_container_width=True,
        hide_index=True
    )
