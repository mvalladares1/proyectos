"""
Inventario en cámaras de frío: ubicaciones, pallets, lotes y trazabilidad de producto terminado.
"""
import streamlit as st
import pandas as pd
import httpx
from datetime import datetime, timedelta
from typing import Dict, List

from shared.auth import proteger_modulo, tiene_acceso_dashboard, get_credenciales, tiene_acceso_pagina

# ==================== FUNCIONES DE FORMATO CHILENO ====================
def fmt_fecha(fecha):
    """Formatea fecha a DD/MM/AAAA"""
    if not fecha:
        return ""
    if isinstance(fecha, str):
        try:
            fecha = datetime.fromisoformat(fecha.replace('Z', '+00:00'))
        except:
            return fecha
    return fecha.strftime("%d/%m/%Y")

def fmt_numero(valor, decimales=0):
    """Formatea número con punto de miles y coma decimal (chileno)"""
    try:
        v = float(valor)
        if decimales == 0 and v == int(v):
            return f"{int(v):,}".replace(",", ".")
        return f"{v:,.{decimales}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(valor)

# Configuración de la página
st.set_page_config(
    page_title="Stock",
    page_icon="📦",
    layout="wide"
)

# Proteger la página
if not proteger_modulo("stock"):
    st.stop()

if not tiene_acceso_dashboard("stock"):
    st.error("No tienes permisos para ver este dashboard.")
    st.stop()

# Título
st.title("📦 Stock y Cámaras")
st.markdown("Gestión de inventario, ubicaciones y trazabilidad de pallets")

# Filtros de fecha
st.markdown("### 📅 Filtros de Fecha")
col_fecha1, col_fecha2 = st.columns(2)
with col_fecha1:
    fecha_desde_stock = st.date_input(
        "Fecha desde",
        datetime(2025, 11, 24),
        format="DD/MM/YYYY",
        key="stock_fecha_desde"
    )
with col_fecha2:
    fecha_hasta_stock = st.date_input(
        "Fecha hasta", 
        datetime.now(),
        format="DD/MM/YYYY",
        key="stock_fecha_hasta"
    )

# Panel de configuración de capacidades
with st.expander("⚙️ Configurar Capacidades", expanded=False):
    st.markdown("Modifica la capacidad de pallets de cada ubicación:")
    
    # Inicializar capacidades en session_state si no existen
    if "capacidades_config" not in st.session_state:
        st.session_state.capacidades_config = {
            "RF/Stock/Camara 0°C REAL": 200,
            "VLK/Camara 0°": 200,
            "RF/Stock/Inventario Real": 500,
            "VLK/Stock": 500
        }
    
    cap_cols = st.columns(2)
    ubicaciones = list(st.session_state.capacidades_config.keys())
    
    for i, ubicacion in enumerate(ubicaciones):
        with cap_cols[i % 2]:
            nueva_cap = st.number_input(
                f"📦 {ubicacion}",
                min_value=0,
                max_value=2000,
                value=st.session_state.capacidades_config[ubicacion],
                step=10,
                key=f"cap_{ubicacion.replace('/', '_').replace(' ', '_').replace('°', '')}"
            )
            st.session_state.capacidades_config[ubicacion] = nueva_cap
    
    st.caption("💡 Los cambios se aplican automáticamente al recargar los datos.")

st.markdown("---")

# Obtener credenciales
username, password = get_credenciales()

if not (username and password):
    st.error("No se encontraron credenciales válidas en la sesión.")
    st.stop()
API_URL = st.secrets.get("API_URL", "http://localhost:8000")

# Funciones de API
def fetch_camaras(fecha_desde=None, fecha_hasta=None) -> List[Dict]:
    """Obtiene datos de cámaras desde la API, opcionalmente filtrado por fecha de ingreso"""
    try:
        params = {
            "username": username,
            "password": password
        }
        # Agregar filtros de fecha si están definidos
        if fecha_desde:
            params["fecha_desde"] = fecha_desde.strftime("%Y-%m-%d")
        if fecha_hasta:
            params["fecha_hasta"] = fecha_hasta.strftime("%Y-%m-%d")
            
        response = httpx.get(
            f"{API_URL}/api/v1/stock/camaras",
            params=params,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error al obtener datos de cámaras: {str(e)}")
        return []


def fetch_pallets(location_id: int, category: str = None) -> List[Dict]:
    """Obtiene pallets de una ubicación"""
    try:
        params = {
            "username": username,
            "password": password,
            "location_id": location_id
        }
        if category:
            params["category"] = category
            
        response = httpx.get(
            f"{API_URL}/api/v1/stock/pallets",
            params=params,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error al obtener pallets: {str(e)}")
        return []


def fetch_lotes(category: str, location_ids: List[int] = None) -> List[Dict]:
    """Obtiene lotes por categoría"""
    try:
        params = {
            "username": username,
            "password": password,
            "category": category
        }
        if location_ids:
            params["location_ids"] = ",".join(map(str, location_ids))
            
        response = httpx.get(
            f"{API_URL}/api/v1/stock/lotes",
            params=params,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error al obtener lotes: {str(e)}")
        return []


# ==================== CONFIGURACIÓN DE CÁMARAS PRINCIPALES ====================
# Definir las ubicaciones a mostrar por defecto (4 ubicaciones específicas)
CAMARAS_CONFIG = {
    "RF/Stock/Camara 0°C REAL": {"capacidad": 200, "patron": ["Camara 0°C REAL"], "id": 5452},
    "VLK/Camara 0°": {"capacidad": 200, "patron": ["VLK/Camara 0", "VLK", "Camara 0°"], "id": 8528},
    "RF/Stock/Inventario Real": {"capacidad": 500, "patron": ["Inventario Real"], "id": 8474},
    "VLK/Stock": {"capacidad": 500, "patron": ["VLK/Stock"], "id": 8497},
}

def filtrar_camaras_principales(camaras_data):
    """Filtra solo las ubicaciones específicas configuradas"""
    camaras_filtradas = []
    usados = set()
    
    # Obtener capacidades del session_state o usar por defecto
    capacidades = st.session_state.get("capacidades_config", {
        "RF/Stock/Camara 0°C REAL": 200,
        "VLK/Camara 0°": 200,
        "RF/Stock/Inventario Real": 500,
        "VLK/Stock": 500
    })
    
    for camara in camaras_data:
        camara_id = camara.get("id")
        nombre = camara.get("name", "")
        full_name = camara.get("full_name", "")
        
        for config_name, config in CAMARAS_CONFIG.items():
            if config_name in usados:
                continue
            
            # Primero intentar match por ID (más preciso)
            if config.get("id") and camara_id == config["id"]:
                camara_copy = camara.copy()
                # Usar capacidad del session_state si existe, sino usar la del config
                camara_copy["capacity_pallets"] = capacidades.get(config_name, config["capacidad"])
                camara_copy["config_name"] = config_name
                camaras_filtradas.append(camara_copy)
                usados.add(config_name)
                break
            
            # Si no hay match por ID, usar patrones
            patrones = config.get("patron", [])
            coincide = any(
                p.lower() in nombre.lower() or p.lower() in full_name.lower() 
                for p in patrones
            )
            
            if coincide:
                camara_copy = camara.copy()
                # Usar capacidad del session_state si existe, sino usar la del config
                camara_copy["capacity_pallets"] = capacidades.get(config_name, config["capacidad"])
                camara_copy["config_name"] = config_name
                camaras_filtradas.append(camara_copy)
                usados.add(config_name)
                break
    
    return camaras_filtradas


# ==================== CARGA GLOBAL DE CÁMARAS ====================
with st.spinner("Cargando datos de cámaras..."):
    # Pasar los filtros de fecha a la API
    camaras_data_all = fetch_camaras(fecha_desde_stock, fecha_hasta_stock)

# Determinar si mostrar todas o solo principales (se sincroniza con checkbox en tab1)
if "mostrar_todas_camaras" not in st.session_state:
    st.session_state.mostrar_todas_camaras = False

if st.session_state.mostrar_todas_camaras:
    camaras_data = camaras_data_all
else:
    # Aplicar filtro para mostrar solo las 4 ubicaciones específicas
    camaras_data = filtrar_camaras_principales(camaras_data_all) if camaras_data_all else []

# Tabs principales
# Pre-calcular permisos de página
_perm_camaras = tiene_acceso_pagina("stock", "camaras")
_perm_pallets = tiene_acceso_pagina("stock", "pallets")
_perm_trazabilidad = tiene_acceso_pagina("stock", "trazabilidad")

tab_movimientos, tab1, tab2, tab3 = st.tabs(["📲 Movimientos", "🏢 Cámaras", "📦 Pallets", "🏷️ Trazabilidad"])

# ========== TAB 0: MOVIMIENTOS ==========
with tab_movimientos:
    st.markdown("### 📲 Gestión de Movimientos")
    st.info(
        "💡 **Dual Logic**: Si el pallet está en inventario, crea una transferencia interna. "
        "Si pertenece a una recepción abierta (asignada), actualiza su destino en la recepción."
    )
    
    col_scan, col_dest = st.columns(2)
    
    with col_scan:
        st.markdown("##### 1. Escanear Pallet")
        # Text input conc focus automático idealmente
        pallet_code = st.text_input("Código de Tarja / Pallet", placeholder="Escanea aquí...", key="move_pallet_code")
        
    with col_dest:
        st.markdown("##### 2. Destino")
        # Filtrar solo cámaras 'útiles' para destino (internal)
        # Usamos camaras_data_all si está disponible
        opts_dest = {}
        if camaras_data_all:
             opts_dest = {c["id"]: c["name"] for c in camaras_data_all}
             
        dest_id = st.selectbox(
            "Seleccionar Cámara Destino", 
            options=opts_dest.keys(), 
            format_func=lambda x: opts_dest.get(x, str(x)), 
            key="move_dest_id"
        )

    btn_mover = st.button("✅ Confirmar Movimiento", type="primary", use_container_width=True)
    
    if btn_mover:
        if not pallet_code:
            st.error("⚠️ Debes ingresar un código de pallet.")
        elif not dest_id:
            st.error("⚠️ Debes seleccionar un destino.")
        else:
            with st.spinner(f"Procesando movimiento de {pallet_code}..."):
                try:
                    payload = {
                        "pallet_code": pallet_code.strip(),
                        "target_location_id": dest_id,
                        "username": username,
                        "password": password
                    }
                    
                    # Llamada a la nueva API /move
                    resp_move = httpx.post(
                        f"{API_URL}/api/v1/stock/move",
                        json=payload, 
                        timeout=30.0
                    )
                    
                    if resp_move.status_code == 200:
                        res_json = resp_move.json()
                        if res_json.get("success"):
                            msg = res_json.get("message", "Movimiento exitoso")
                            tipo = res_json.get("type", "unknown")
                            
                            if tipo == "realloc":
                                st.success(f"📋 {msg}")
                                st.caption("Reasignación pre-validación exitosa.")
                            else:
                                st.success(f"🚚 {msg}")
                                st.caption("Transferencia de stock creada y validada.")
                            
                            # Mostrar resumen visual del movimiento
                            st.divider()
                            c1, c2, c3 = st.columns(3)
                            c1.metric("Pallet", pallet_code)
                            c2.metric("Destino", opts_dest.get(dest_id, "Desconocido"))
                            c3.metric("Tipo", "Recepción" if tipo=="realloc" else "Transferencia")
                            
                        else:
                            st.error(f"❌ {res_json.get('message')}")
                    else:
                        st.error(f"Error HTTP: {resp_move.status_code} - {resp_move.text}")
                        
                except Exception as e:
                    st.error(f"Error de conexión: {str(e)}")

# ========== TAB 1: CÁMARAS ==========
with tab1:
    if not _perm_camaras:
        st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'Cámaras'. Contacta al administrador.")
    st.header("Stock por Cámaras")
    
    if camaras_data_all:
        # Opción para ver todas o solo las principales
        mostrar_todas = st.checkbox("Mostrar todas las ubicaciones", value=False, key="mostrar_todas_camaras")
        
        if mostrar_todas:
            camaras_data_tab = camaras_data_all
        else:
            # Aplicar filtro para mostrar solo las 4 ubicaciones específicas
            camaras_data_tab = filtrar_camaras_principales(camaras_data_all)
        
        # Métricas generales (solo de las cámaras mostradas)
        total_camaras = len(camaras_data_tab)
        total_capacity = sum(c.get("capacity_pallets", 0) for c in camaras_data_tab)
        total_occupied = sum(c.get("occupied_pallets", 0) for c in camaras_data_tab)
        ocupacion_pct = (total_occupied / total_capacity * 100) if total_capacity > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Cámaras", fmt_numero(total_camaras))
        col2.metric("Capacidad Total", f"{fmt_numero(total_capacity)} pallets")
        col3.metric("Posiciones Ocupadas", f"{fmt_numero(total_occupied)} pallets")
        col4.metric("Ocupación", f"{fmt_numero(ocupacion_pct, 1)}%")
        
        st.divider()
        
        # Tabla de cámaras con stock
        st.subheader("Detalle por Cámara")
        
        camaras_list = []
        for camara in camaras_data_tab:
            # Calcular stock total
            total_kg = sum(camara["stock_data"].values())
            ocupacion = (camara["occupied_pallets"] / camara["capacity_pallets"] * 100) if camara["capacity_pallets"] > 0 else 0
            
            camaras_list.append({
                "Cámara": camara["name"],
                "Ubicación Completa": camara["full_name"],
                "Padre": camara["parent_name"],
                "Capacidad": camara["capacity_pallets"],
                "Ocupado": camara["occupied_pallets"],
                "Disponible": camara["capacity_pallets"] - camara["occupied_pallets"],
                "Ocupación %": round(ocupacion, 1),
                "Stock (kg)": round(total_kg, 0),
                "Tipos": len(camara["stock_data"])
            })
        
        df_camaras = pd.DataFrame(camaras_list)
        
        # Filtros
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            min_ocupacion = st.slider("Ocupación mínima (%)", 0, 100, 0)
        with col_f2:
            buscar_camara = st.text_input("Buscar cámara", "")
        
        # Aplicar filtros sobre datos originales
        mask = df_camaras["Ocupación %"] >= min_ocupacion
        if buscar_camara:
            mask = mask & (
                df_camaras["Cámara"].str.contains(buscar_camara, case=False, na=False) |
                df_camaras["Ubicación Completa"].str.contains(buscar_camara, case=False, na=False)
            )
        
        # Crear df formateado con filtro aplicado
        df_filtered = df_camaras[mask].copy()
        df_filtered["Capacidad"] = df_filtered["Capacidad"].apply(lambda x: fmt_numero(x))
        df_filtered["Ocupado"] = df_filtered["Ocupado"].apply(lambda x: fmt_numero(x))
        df_filtered["Disponible"] = df_filtered["Disponible"].apply(lambda x: fmt_numero(x))
        df_filtered["Ocupación %"] = df_filtered["Ocupación %"].apply(lambda x: fmt_numero(x, 1))
        df_filtered["Stock (kg)"] = df_filtered["Stock (kg)"].apply(lambda x: fmt_numero(x))

        st.dataframe(
            df_filtered,
            use_container_width=True,
            height=300,
            hide_index=True
        )
        
        # Detalle de stock por Tipo Fruta / Manejo
        st.subheader("Stock por Tipo Fruta / Manejo")
        
        # Seleccionar cámara
        camara_names = [c["name"] for c in camaras_data_tab]
        selected_camara = st.selectbox("Seleccionar cámara", camara_names)
        
        if selected_camara:
            camara_detail = next((c for c in camaras_data_tab if c["name"] == selected_camara), None)
            if camara_detail and camara_detail["stock_data"]:
                stock_items = [
                    {"Tipo Fruta - Manejo": k, "Stock (kg)": round(v, 2)}
                    for k, v in camara_detail["stock_data"].items()
                ]
                df_stock = pd.DataFrame(stock_items).sort_values("Stock (kg)", ascending=False)
                
                # Gráfico ancho con colores por manejo (azul convencional, verde orgánico)
                import plotly.express as px
                
                # Asignar color según manejo
                def get_color(tipo_manejo):
                    if "Orgánico" in tipo_manejo:
                        return "#28a745"  # Verde para orgánico
                    else:
                        return "#007bff"  # Azul para convencional
                
                df_stock["Color"] = df_stock["Tipo Fruta - Manejo"].apply(get_color)
                
                fig = px.bar(
                    df_stock,
                    x="Tipo Fruta - Manejo",
                    y="Stock (kg)",
                    color="Tipo Fruta - Manejo",
                    color_discrete_map={k: get_color(k) for k in df_stock["Tipo Fruta - Manejo"].unique()}
                )
                fig.update_layout(
                    showlegend=False,
                    height=400,
                    xaxis_title="",
                    yaxis_title="Stock (kg)",
                    xaxis_tickangle=-45
                )
                # Formato chileno en tooltip
                fig.update_traces(
                    hovertemplate="<b>%{x}</b><br>Stock: %{y:,.2f} kg<extra></extra>"
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Tabla debajo del gráfico con formato chileno
                df_stock_display = df_stock[["Tipo Fruta - Manejo", "Stock (kg)"]].copy()
                df_stock_display["Stock (kg)"] = df_stock_display["Stock (kg)"].apply(lambda x: fmt_numero(x, 2))
                st.dataframe(df_stock_display, use_container_width=True, height=300, hide_index=True)
    else:
        st.info("No hay datos de cámaras disponibles")


# ========== TAB 2: PALLETS ==========
with tab2:
    if not _perm_pallets:
        st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'Pallets'. Contacta al administrador.")
    st.header("Consulta de Pallets")
    
    if camaras_data:
        # Selección de ubicación
        col1, col2 = st.columns(2)
        
        with col1:
            camara_names_map = {c["name"]: c["id"] for c in camaras_data}
            selected_location_name = st.selectbox(
                "Seleccionar ubicación",
                list(camara_names_map.keys()),
                key="location_selector"
            )
            selected_location_id = camara_names_map[selected_location_name]
        
        with col2:
            # Obtener categorías disponibles
            selected_camara_data = next((c for c in camaras_data if c["id"] == selected_location_id), None)
            categories = list(selected_camara_data["stock_data"].keys()) if selected_camara_data else []
            
            filter_category = st.selectbox(
                "Filtrar por Tipo Fruta / Manejo",
                ["Todos"] + categories,
                key="category_filter"
            )
        
        if st.button("🔍 Buscar Pallets", type="primary"):
            category_param = None if filter_category == "Todos" else filter_category
            
            with st.spinner("Cargando pallets..."):
                pallets_data = fetch_pallets(selected_location_id, category_param)
            
            if pallets_data:
                st.success(f"Se encontraron {fmt_numero(len(pallets_data))} registros")
                
                # Métricas
                total_qty = sum(p.get("quantity", 0) for p in pallets_data)
                avg_age = sum(p.get("days_old", 0) for p in pallets_data) / len(pallets_data) if pallets_data else 0
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Registros", fmt_numero(len(pallets_data)))
                col2.metric("Stock Total (kg)", fmt_numero(total_qty, 2))
                col3.metric("Antigüedad Promedio", f"{fmt_numero(avg_age, 0)} días")
                
                st.divider()
                
                # Tabla de pallets
                df_pallets = pd.DataFrame(pallets_data)
                
                # Reordenar columnas
                column_order = ["pallet", "product", "lot", "quantity", "category", "condition", "in_date", "days_old"]
                df_pallets = df_pallets[[c for c in column_order if c in df_pallets.columns]]
                
                # Renombrar columnas
                df_pallets.columns = ["Pallet", "Producto", "Lote", "Cantidad (kg)", "Categoría", "Condición", "Fecha Ingreso", "Días"]
                
                # Formatear números
                df_pallets["Cantidad (kg)"] = df_pallets["Cantidad (kg)"].apply(lambda x: fmt_numero(x, 2))
                
                # Resaltar antigüedad
                def highlight_age(row):
                    days = row["Días"]
                    if days > 30:
                        return ['background-color: rgba(255, 153, 102, 0.3)'] * len(row)  # Naranjo suave para > 30 días
                    elif days > 15:
                        return ['background-color: rgba(255, 243, 205, 0.3)'] * len(row)  # Amarillo para > 15 días
                    return [''] * len(row)
                
                st.dataframe(
                    df_pallets.style.apply(highlight_age, axis=1),
                    use_container_width=True,
                    height=500
                )
                
                # Descargar CSV
                csv = df_pallets.to_csv(index=False)
                st.download_button(
                    "📥 Descargar CSV",
                    csv,
                    f"pallets_{selected_location_name}_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
            else:
                st.warning("No se encontraron pallets con los filtros aplicados")
    else:
        st.info("Primero carga los datos de cámaras en la pestaña anterior")


# ========== TAB 3: TRAZABILIDAD ==========
with tab3:
    if not _perm_trazabilidad:
        st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'Trazabilidad'. Contacta al administrador.")
    st.header("Trazabilidad de Lotes")
    st.markdown("Análisis FIFO y antigüedad de lotes por categoría")
    
    if camaras_data:
        # Obtener todas las categorías únicas
        all_categories = set()
        for c in camaras_data:
            all_categories.update(c["stock_data"].keys())
        
        selected_category = st.selectbox(
            "Seleccionar Tipo Fruta - Manejo",
            sorted(all_categories),
            key="category_traza"
        )
        
        # Filtro opcional de ubicaciones
        location_filter = st.multiselect(
            "Filtrar por ubicaciones (opcional)",
            [c["name"] for c in camaras_data],
            key="location_filter_traza"
        )
        
        if st.button("🔍 Consultar Lotes", type="primary"):
            location_ids = [c["id"] for c in camaras_data if c["name"] in location_filter] if location_filter else None
            
            with st.spinner("Analizando lotes..."):
                lotes_data = fetch_lotes(selected_category, location_ids)
            
            if lotes_data:
                st.success(f"Se encontraron {fmt_numero(len(lotes_data))} lotes")
                
                # Métricas
                total_qty = sum(l.get("quantity", 0) for l in lotes_data)
                total_pallets = sum(l.get("pallets", 0) for l in lotes_data)
                oldest_days = max((l.get("days_old", 0) for l in lotes_data), default=0)
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Lotes", fmt_numero(len(lotes_data)))
                col2.metric("Stock Total (kg)", fmt_numero(total_qty, 2))
                col3.metric("Pallets", fmt_numero(total_pallets))
                col4.metric("Lote Más Antiguo", f"{fmt_numero(oldest_days)} días")
                
                st.divider()
                
                # Gráfico de antigüedad
                st.subheader("Distribución de Antigüedad")
                df_lotes = pd.DataFrame(lotes_data)
                
                # Histograma
                st.bar_chart(df_lotes.set_index("lot")["days_old"])
                
                # Tabla detallada
                st.subheader("Detalle de Lotes (ordenado por antigüedad)")
                
                # Formatear tabla
                df_display = df_lotes.copy()
                df_display["locations"] = df_display["locations"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
                
                column_rename = {
                    "lot": "Lote",
                    "product": "Producto",
                    "quantity": "Cantidad (kg)",
                    "pallets": "Pallets",
                    "in_date": "Fecha Ingreso",
                    "days_old": "Días",
                    "locations": "Ubicaciones"
                }
                df_display = df_display.rename(columns=column_rename)
                
                # Formatear números
                df_display["Cantidad (kg)"] = df_display["Cantidad (kg)"].apply(lambda x: fmt_numero(x, 2))
                df_display["Pallets"] = df_display["Pallets"].apply(lambda x: fmt_numero(x))
                
                # Resaltar según antigüedad
                def color_age(val):
                    try:
                        days = int(val)
                        if days > 45:
                            return 'background-color: #dc3545; color: white'
                        elif days > 30:
                            return 'background-color: #ffc107'
                        elif days > 15:
                            return 'background-color: #28a745; color: white'
                        return ''
                    except:
                        return ''
                
                st.dataframe(
                    df_display.style.applymap(color_age, subset=["Días"]),
                    use_container_width=True,
                    height=500
                )
                
                # Análisis FIFO
                st.subheader("📊 Análisis FIFO")
                
                # Lotes críticos (> 30 días)
                critical_lots = df_display[df_display["Días"] > 30]
                if not critical_lots.empty:
                    st.warning(f"⚠️ {len(critical_lots)} lotes con más de 30 días de antigüedad")
                    st.dataframe(critical_lots, use_container_width=True)
                else:
                    st.success("✅ No hay lotes críticos por antigüedad")
                
                # Descargar
                csv = df_display.to_csv(index=False)
                st.download_button(
                    "📥 Descargar Trazabilidad",
                    csv,
                    f"trazabilidad_{selected_category.replace('/', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
            else:
                st.warning("No se encontraron lotes para la categoría seleccionada")
    else:
        st.info("Primero carga los datos de cámaras")

# Footer
st.divider()
st.caption("Rio Futuro - Sistema de Gestión de Stock y Cámaras")
