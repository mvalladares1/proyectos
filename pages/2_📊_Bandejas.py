"""
Página de Dashboard de Bandejas
Muestra métricas, tablas y gráficos de movimientos de bandejas
"""
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import sys
import os

# Agregar el directorio raíz al path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.auth import verificar_autenticacion, proteger_pagina, tiene_acceso_dashboard


# ==================== FUNCIONES DE DATOS ====================
def cargar_movimientos_entrada(year: int = None, month: int = None, temporada: str = None):
    """Carga movimientos de entrada desde el backend"""
    import requests
    try:
        params = {}
        if year:
            params['year'] = year
        if month:
            params['month'] = month
        if temporada:
            params['temporada'] = temporada
            
        response = requests.get(
            "http://localhost:8000/api/v1/bandejas/entradas",
            params=params,
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            return pd.DataFrame(data.get('data', []))
    except Exception as e:
        st.error(f"Error cargando entradas: {e}")
    return pd.DataFrame()


def cargar_movimientos_salida(year: int = None, month: int = None, temporada: str = None):
    """Carga movimientos de salida desde el backend"""
    import requests
    try:
        params = {}
        if year:
            params['year'] = year
        if month:
            params['month'] = month
        if temporada:
            params['temporada'] = temporada
            
        response = requests.get(
            "http://localhost:8000/api/v1/bandejas/salidas",
            params=params,
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            return pd.DataFrame(data.get('data', []))
    except Exception as e:
        st.error(f"Error cargando salidas: {e}")
    return pd.DataFrame()


def cargar_stock(year: int = None, month: int = None, temporada: str = None):
    """Carga stock de bandejas desde el backend"""
    import requests
    try:
        params = {}
        if year:
            params['year'] = year
        if month:
            params['month'] = month
        if temporada:
            params['temporada'] = temporada
            
        response = requests.get(
            "http://localhost:8000/api/v1/bandejas/stock",
            params=params,
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            return pd.DataFrame(data.get('data', []))
    except Exception as e:
        st.error(f"Error cargando stock: {e}")
    return pd.DataFrame()


def get_years_disponibles():
    """Obtiene años disponibles en los datos"""
    return [2023, 2024, 2025]


def get_meses():
    """Retorna lista de meses"""
    return {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }


def get_temporadas():
    """Retorna temporadas disponibles"""
    return ["2023-2024", "2024-2025", "2025-2026"]


# ==================== FUNCIONES DE ESTILO ====================
def style_table_with_total(df: pd.DataFrame, total_column: str = None) -> str:
    """Aplica estilo a una tabla con fila TOTAL amarilla"""
    if df.empty:
        return df.to_html(index=False, classes="table table-striped")
    
    def highlight_total(row):
        if total_column and row.name == len(df) - 1:
            return ['background-color: #ffc107; font-weight: bold; color: black'] * len(row)
        elif 'TOTAL' in str(row.values):
            return ['background-color: #ffc107; font-weight: bold; color: black'] * len(row)
        return [''] * len(row)
    
    styled = df.style.apply(highlight_total, axis=1)
    styled = styled.set_properties(**{
        'text-align': 'center',
        'border': '1px solid #ddd'
    })
    styled = styled.set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', '#343a40'),
            ('color', 'white'),
            ('text-align', 'center'),
            ('padding', '10px'),
            ('border', '1px solid #ddd')
        ]},
        {'selector': 'td', 'props': [
            ('padding', '8px'),
            ('border', '1px solid #ddd')
        ]}
    ])
    return styled.to_html()


# ==================== PÁGINA PRINCIPAL ====================
st.set_page_config(page_title="Bandejas", page_icon="📊", layout="wide")

# Verificar autenticación
if not proteger_pagina():
    st.stop()

# Verificar permisos de acceso al dashboard
if not tiene_acceso_dashboard("bandejas"):
    st.error("No tiene permisos para ver esta página")
    st.stop()

st.title("📊 Dashboard de Bandejas")
st.markdown("---")

# ==================== FILTROS ====================
with st.expander("🔍 Filtros", expanded=True):
    filter_type = st.radio(
        "Tipo de filtro:",
        ["Por Temporada", "Por Año/Mes"],
        horizontal=True,
        key="filter_type_bandejas"
    )
    
    col_f1, col_f2, col_f3 = st.columns(3)
    
    year_filter = None
    month_filter = None
    temporada_filter = None
    
    if filter_type == "Por Temporada":
        with col_f1:
            temporadas = get_temporadas()
            temporada_filter = st.selectbox(
                "Temporada:",
                temporadas,
                index=len(temporadas) - 1,
                key="temporada_bandejas"
            )
    else:
        with col_f1:
            years = get_years_disponibles()
            year_filter = st.selectbox(
                "Año:",
                years,
                index=len(years) - 1,
                key="year_bandejas"
            )
        with col_f2:
            meses = get_meses()
            current_month = datetime.now().month
            month_filter = st.selectbox(
                "Mes:",
                list(meses.keys()),
                format_func=lambda x: meses[x],
                index=current_month - 1,
                key="month_bandejas"
            )

# ==================== CARGAR DATOS ====================
with st.spinner("Cargando datos..."):
    df_entradas = cargar_movimientos_entrada(year_filter, month_filter, temporada_filter)
    df_salidas = cargar_movimientos_salida(year_filter, month_filter, temporada_filter)
    df_stock = cargar_stock(year_filter, month_filter, temporada_filter)

# ==================== MÉTRICAS ====================
st.subheader("📈 Métricas Principales")

col1, col2, col3, col4 = st.columns(4)

# Calcular métricas
total_entradas = df_entradas['cantidad'].sum() if not df_entradas.empty and 'cantidad' in df_entradas.columns else 0
total_salidas = df_salidas['cantidad'].sum() if not df_salidas.empty and 'cantidad' in df_salidas.columns else 0
stock_actual = df_stock['cantidad'].sum() if not df_stock.empty and 'cantidad' in df_stock.columns else 0
balance = total_entradas - total_salidas

with col1:
    st.metric("📥 Total Entradas", f"{total_entradas:,.0f}")
with col2:
    st.metric("📤 Total Salidas", f"{total_salidas:,.0f}")
with col3:
    st.metric("📦 Stock Actual", f"{stock_actual:,.0f}")
with col4:
    delta_color = "normal" if balance >= 0 else "inverse"
    st.metric("⚖️ Balance", f"{balance:,.0f}", delta=f"{balance:,.0f}", delta_color=delta_color)

st.markdown("---")

# ==================== TABLAS ====================
st.subheader("📋 Detalle de Stock y Productores")

col_tabla1, col_tabla2 = st.columns(2)

# Tabla de Stock por Ubicación
with col_tabla1:
    st.markdown("#### 📦 Stock por Ubicación")
    
    if not df_stock.empty:
        # Agrupar por ubicación
        if 'ubicacion' in df_stock.columns and 'cantidad' in df_stock.columns:
            stock_ubicacion = df_stock.groupby('ubicacion')['cantidad'].sum().reset_index()
            stock_ubicacion.columns = ['Ubicación', 'Cantidad']
            
            # Agregar fila TOTAL
            total_row = pd.DataFrame([{
                'Ubicación': 'TOTAL',
                'Cantidad': stock_ubicacion['Cantidad'].sum()
            }])
            stock_ubicacion = pd.concat([stock_ubicacion, total_row], ignore_index=True)
            
            # Formatear números
            stock_ubicacion['Cantidad'] = stock_ubicacion['Cantidad'].apply(lambda x: f"{x:,.0f}")
            
            # Mostrar tabla con estilo
            st.markdown(style_table_with_total(stock_ubicacion), unsafe_allow_html=True)
        else:
            st.info("No hay datos de stock por ubicación")
    else:
        st.info("No hay datos de stock disponibles")

# Tabla de Entradas por Productor
with col_tabla2:
    st.markdown("#### 👨‍🌾 Entradas por Productor")
    
    if not df_entradas.empty:
        # Agrupar por productor
        if 'productor' in df_entradas.columns and 'cantidad' in df_entradas.columns:
            entradas_productor = df_entradas.groupby('productor')['cantidad'].sum().reset_index()
            entradas_productor.columns = ['Productor', 'Cantidad']
            entradas_productor = entradas_productor.sort_values('Cantidad', ascending=False)
            
            # Agregar fila TOTAL
            total_row = pd.DataFrame([{
                'Productor': 'TOTAL',
                'Cantidad': entradas_productor['Cantidad'].sum()
            }])
            entradas_productor = pd.concat([entradas_productor, total_row], ignore_index=True)
            
            # Formatear números
            entradas_productor['Cantidad'] = entradas_productor['Cantidad'].apply(lambda x: f"{x:,.0f}")
            
            # Mostrar tabla con estilo
            st.markdown(style_table_with_total(entradas_productor), unsafe_allow_html=True)
        else:
            st.info("No hay datos de entradas por productor")
    else:
        st.info("No hay datos de entradas disponibles")

st.markdown("---")

# ==================== GRÁFICOS ====================
st.subheader("📊 Análisis Visual")

col_chart1, col_chart2 = st.columns(2)

# Gráfico de Composición de Bandejas
with col_chart1:
    st.markdown("#### 🥧 Composición de Bandejas")
    
    if not df_stock.empty and 'estado' in df_stock.columns and 'cantidad' in df_stock.columns:
        stock_estado = df_stock.groupby('estado')['cantidad'].sum().reset_index()
        stock_estado.columns = ['Estado', 'Cantidad']
        
        # Colores según el estado: Sucia=rojo, Limpia=verde, Proyectada=naranja
        color_scale = alt.Scale(
            domain=['Sucia', 'Limpia', 'Proyectada'],
            range=['#dc3545', '#28a745', '#ff7f0e']
        )
        
        chart = alt.Chart(stock_estado).mark_arc(innerRadius=50).encode(
            theta=alt.Theta(field="Cantidad", type="quantitative"),
            color=alt.Color(
                field="Estado", 
                type="nominal",
                scale=color_scale,
                legend=alt.Legend(title="Estado")
            ),
            tooltip=['Estado', 'Cantidad']
        ).properties(
            width=300,
            height=300
        )
        
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No hay datos para el gráfico de composición")

# Gráfico de Evolución Temporal
with col_chart2:
    st.markdown("#### 📈 Evolución de Movimientos")
    
    if not df_entradas.empty and 'fecha' in df_entradas.columns:
        # Preparar datos de entradas
        df_entradas_temp = df_entradas.copy()
        df_entradas_temp['fecha'] = pd.to_datetime(df_entradas_temp['fecha'])
        df_entradas_temp['tipo'] = 'Entradas'
        
        # Preparar datos de salidas si existen
        if not df_salidas.empty and 'fecha' in df_salidas.columns:
            df_salidas_temp = df_salidas.copy()
            df_salidas_temp['fecha'] = pd.to_datetime(df_salidas_temp['fecha'])
            df_salidas_temp['tipo'] = 'Salidas'
            
            # Combinar
            df_combined = pd.concat([df_entradas_temp, df_salidas_temp])
        else:
            df_combined = df_entradas_temp
        
        # Agrupar por fecha y tipo
        if 'cantidad' in df_combined.columns:
            evolucion = df_combined.groupby([df_combined['fecha'].dt.date, 'tipo'])['cantidad'].sum().reset_index()
            evolucion.columns = ['Fecha', 'Tipo', 'Cantidad']
            
            chart = alt.Chart(evolucion).mark_line(point=True).encode(
                x=alt.X('Fecha:T', title='Fecha'),
                y=alt.Y('Cantidad:Q', title='Cantidad'),
                color=alt.Color(
                    'Tipo:N',
                    scale=alt.Scale(
                        domain=['Entradas', 'Salidas'],
                        range=['#28a745', '#dc3545']
                    ),
                    legend=alt.Legend(title="Tipo")
                ),
                tooltip=['Fecha', 'Tipo', 'Cantidad']
            ).properties(
                width=300,
                height=300
            )
            
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No hay datos de cantidad para graficar")
    else:
        st.info("No hay datos para el gráfico de evolución")

st.markdown("---")

# ==================== BOTÓN DE ACTUALIZACIÓN ====================
col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
with col_btn2:
    if st.button("🔄 Actualizar Datos", key="refresh_bandejas", use_container_width=True):
        st.rerun()

# Footer
st.markdown("---")
st.caption(f"Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
