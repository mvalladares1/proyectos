"""
Tab: Agrupado - Estado de Resultados agrupado por meses seleccionados.
"""
import streamlit as st
import pandas as pd


def render(datos_mensuales: dict, ppto_mensual: dict, meses_seleccionados: list, 
           meses_opciones: dict, año_seleccionado: int):
    """
    Renderiza el tab Agrupado con Estado de Resultados sumando meses seleccionados.
    
    Args:
        datos_mensuales: Dict con datos reales mensuales {YYYY-MM: {categoria: valor}}
        ppto_mensual: Dict con presupuesto mensual {YYYY-MM: {categoria: valor}}
        meses_seleccionados: Lista de nombres de meses seleccionados
        meses_opciones: Dict {nombre_mes: numero_mes}
        año_seleccionado: Año actual
    """
    st.subheader("Estado de Resultados - Agrupado por Meses Seleccionados")
    
    # Filtrar datos mensuales por meses seleccionados
    meses_filtro = [f"{año_seleccionado}-{meses_opciones[m]}" for m in meses_seleccionados]
    
    # Función helper para sumar valores de meses
    def sumar_meses(cat_nombre):
        real = sum(datos_mensuales.get(m, {}).get(cat_nombre, 0) for m in meses_filtro if m in datos_mensuales)
        ppto = sum(ppto_mensual.get(m, {}).get(cat_nombre, 0) for m in meses_filtro if m in ppto_mensual)
        return real, ppto
    
    # Crear DataFrame con estructura jerárquica
    eerr_mensual = []
    
    def agregar_fila(concepto, real, ppto, es_calculado=False):
        dif = real - ppto
        dif_pct = (dif / ppto * 100) if ppto != 0 else 0
        eerr_mensual.append({
            "Concepto": concepto,
            "Real Mes": real,
            "PPTO Mes": ppto,
            "Dif Mes": dif,
            "Dif %": dif_pct,
            "es_calculado": es_calculado
        })
    
    # 1 - INGRESOS
    ing_real, ing_ppto = sumar_meses("1 - INGRESOS")
    agregar_fila("1 - INGRESOS", ing_real, ing_ppto)
    
    # 2 - COSTOS
    cost_real, cost_ppto = sumar_meses("2 - COSTOS")
    agregar_fila("2 - COSTOS", cost_real, cost_ppto)
    
    # 3 - UTILIDAD BRUTA = 1 - 2
    ub_real = ing_real - cost_real
    ub_ppto = ing_ppto - cost_ppto
    agregar_fila("3 - UTILIDAD BRUTA", ub_real, ub_ppto, es_calculado=True)
    
    # 4 - GASTOS DIRECTOS
    gd_real, gd_ppto = sumar_meses("4 - GASTOS DIRECTOS")
    agregar_fila("4 - GASTOS DIRECTOS", gd_real, gd_ppto)
    
    # 5 - MARGEN DE CONTRIBUCIÓN = 3 - 4
    mc_real = ub_real - gd_real
    mc_ppto = ub_ppto - gd_ppto
    agregar_fila("5 - MARGEN DE CONTRIBUCIÓN", mc_real, mc_ppto, es_calculado=True)
    
    # 6 - GAV
    gav_real, gav_ppto = sumar_meses("6 - GAV")
    agregar_fila("6 - GAV", gav_real, gav_ppto)
    
    # 7 - UTILIDAD OPERACIONAL (EBIT) = 5 - 6
    ebit_real = mc_real - gav_real
    ebit_ppto = mc_ppto - gav_ppto
    agregar_fila("7 - UTILIDAD OPERACIONAL (EBIT)", ebit_real, ebit_ppto, es_calculado=True)
    
    # 8 - INTERESES
    int_real, int_ppto = sumar_meses("8 - INTERESES")
    agregar_fila("8 - INTERESES", int_real, int_ppto)
    
    # 9 - UTILIDAD ANTES DE NO OP = 7 - 8
    uano_real = ebit_real - int_real
    uano_ppto = ebit_ppto - int_ppto
    agregar_fila("9 - UTILIDAD ANTES DE NO OP.", uano_real, uano_ppto, es_calculado=True)
    
    # 10 - INGRESOS NO OPERACIONALES
    ino_real, ino_ppto = sumar_meses("10 - INGRESOS NO OPERACIONALES")
    agregar_fila("10 - INGRESOS NO OPERACIONALES", ino_real, ino_ppto)
    
    # 11 - GASTOS NO OPERACIONALES
    gno_real, gno_ppto = sumar_meses("11 - GASTOS NO OPERACIONALES")
    agregar_fila("11 - GASTOS NO OPERACIONALES", gno_real, gno_ppto)
    
    # 12 - RESULTADO NO OPERACIONAL = 10 - 11
    rno_real = ino_real - gno_real
    rno_ppto = ino_ppto - gno_ppto
    agregar_fila("12 - RESULTADO NO OPERACIONAL", rno_real, rno_ppto, es_calculado=True)
    
    # 13 - UTILIDAD ANTES DE IMPUESTOS = 9 + 12
    uai_real = uano_real + rno_real
    uai_ppto = uano_ppto + rno_ppto
    agregar_fila("13 - UTILIDAD ANTES DE IMPUESTOS", uai_real, uai_ppto, es_calculado=True)
    
    df_mensual = pd.DataFrame(eerr_mensual)
    cols_mostrar = ["Concepto", "Real Mes", "PPTO Mes", "Dif Mes", "Dif %"]
    df_display = df_mensual[cols_mostrar].copy()
    
    def resaltar_calculados(row):
        idx = row.name
        if df_mensual.iloc[idx].get("es_calculado", False):
            return ["background-color: #2d3748; font-weight: bold"] * len(cols_mostrar)
        return [""] * len(cols_mostrar)
    
    st.dataframe(
        df_display.style
        .format({
            "Real Mes": "${:,.0f}",
            "PPTO Mes": "${:,.0f}",
            "Dif Mes": "${:,.0f}",
            "Dif %": "{:.1f}%"
        })
        .apply(resaltar_calculados, axis=1),
        use_container_width=True,
        hide_index=True
    )
