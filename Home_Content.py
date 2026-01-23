"""
Página principal del dashboard - Selección de dashboards disponibles
"""
import os
import httpx
import streamlit as st

from shared.auth import guardar_permisos_state


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")


def fetch_permissions(username: str) -> dict | None:
    try:
        resp = httpx.get(
            f"{API_URL}/api/v1/permissions/user",
            params={"username": username},
            timeout=10.0
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError:
        return None


# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .section-header {
        font-size: 1.3rem;
        font-weight: 600;
        color: #4a4a4a;
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e0e0e0;
    }
    .dashboard-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        color: white;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .dashboard-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }
    .card-operaciones {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    }
    .card-finanzas {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .card-admin {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }
    .card-title {
        font-size: 1.2rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .card-desc {
        font-size: 0.9rem;
        opacity: 0.9;
        min-height: 40px;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Header principal
st.markdown('<p class="main-header">🏭 Rio Futuro Dashboards</p>', unsafe_allow_html=True)

# === AUTENTICACIÓN ===
from shared.auth import verificar_autenticacion, iniciar_sesion, cerrar_sesion, obtener_info_sesion
from shared.cookies import save_session_multi_method, clear_session_multi_method

# Verificar si hay sesión activa (revisa session_state y query params)
is_authenticated = verificar_autenticacion()

if not is_authenticated:
    st.markdown("---")
    st.subheader("🔐 Iniciar Sesión")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            email = st.text_input("📧 Correo Electrónico", placeholder="usuario@riofuturo.cl")
            api_token = st.text_input("🔑 Token API Odoo", type="password", placeholder="Tu API Key de Odoo")
            submit_button = st.form_submit_button("Ingresar", use_container_width=True)
            
            if submit_button:
                if email and api_token:
                    try:
                        response = httpx.post(
                            f"{API_URL}/api/v1/auth/login",
                            json={"username": email, "password": api_token},
                            timeout=15.0
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            token = data.get("token")
                            uid = data.get("uid")
                            
                            if token:
                                # Guardar token en TODOS los métodos (Query Params + LocalStorage + Cookies)
                                save_session_multi_method(token)
                                
                                # Iniciar sesión en session_state
                                iniciar_sesion(token, email, uid)
                                
                                # Cargar permisos
                                permisos = fetch_permissions(email)
                                if permisos:
                                    guardar_permisos_state(
                                        permisos.get('restricted', {}),
                                        permisos.get('allowed', []),
                                        permisos.get('is_admin', False)
                                    )
                                else:
                                    guardar_permisos_state({}, [], False)
                                
                                st.success("✅ Login exitoso!")
                                st.rerun()
                            else:
                                st.error("❌ Error: No se recibió token de sesión")
                        else:
                            st.error(f"❌ Error de autenticación: {response.json().get('detail', 'Credenciales inválidas')}")
                    except httpx.ConnectError:
                        st.error("❌ No se puede conectar al servidor API.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                else:
                    st.warning("⚠️ Por favor ingresa tu correo y token API")
    
    st.markdown("---")
    st.info("💡 **Nota:** Necesitas un Token API de Odoo para acceder. La sesión expira después de 8 horas o 30 minutos de inactividad.")

else:
    # Usuario autenticado
    username = st.session_state.get('username', 'Usuario')
    
    # Sidebar con info de sesión
    st.sidebar.success(f"👤 {username}")
    
    # Mostrar tiempo restante de sesión
    session_info = obtener_info_sesion()
    if session_info:
        time_remaining = session_info.get('time_remaining_formatted', '')
        if time_remaining:
            st.sidebar.caption(f"⏱️ Sesión: {time_remaining}")
    
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
        # Limpiar TODOS los métodos de almacenamiento
        clear_session_multi_method()
        cerrar_sesion()
        st.rerun()
    
    st.markdown("---")
    st.subheader("📊 Selecciona un Dashboard")
    st.info("👈 Usa el menú lateral para navegar a los diferentes dashboards, o haz clic en las tarjetas de abajo.")
    
    # Tarjetas informativas con navegación
    st.markdown('<div class="section-header">📦 Operaciones</div>', unsafe_allow_html=True)
    
    cols = st.columns(3)
    dashboards_op = [
        ("📥", "Recepciones", "KPIs de Kg, costos y calidad por productor", "pages/1_Recepciones.py"),
        ("🏭", "Producción", "Órdenes de fabricación y rendimientos", "pages/2_Produccion.py"),
        ("�", "Reconciliación", "Gestión de SO Asociada y Campos KG en ODFs", "pages/12_Reconciliacion_Produccion.py"),
        ("📊", "Bandejas", "Control de bandejas por proveedor", "pages/3_Bandejas.py"),
        ("📦", "Stock", "Inventario en cámaras y pallets", "pages/4_Stock.py"),
        ("🚢", "Pedidos de Venta", "Pedidos y avance de producción", "pages/5_Pedidos_Venta.py"),
        ("🔍", "Trazabilidad", "Trazabilidad inversa PT → MP y generación de diagramas", "pages/7_Rendimiento.py"),
        ("🤝", "Relación Comercial", "Análisis comercial y relaciones con clientes", "pages/11_Relacion_Comercial.py"),
        ("🦾", "Automatizaciones", "Túneles Estáticos - Creación de MO", "pages/10_Automatizaciones.py"),
    ]
    
    for i, (icon, title, desc, page) in enumerate(dashboards_op):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="dashboard-card card-operaciones">
                <div class="card-title">{icon} {title}</div>
                <div class="card-desc">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Abrir {title}", key=f"btn_{title}", use_container_width=True):
                st.switch_page(page)
    
    st.markdown('<div class="section-header">💰 Finanzas</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="dashboard-card card-finanzas">
            <div class="card-title">💰 Finanzas</div>
            <div class="card-desc">Estado de Resultado vs Presupuesto</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Abrir Finanzas", key="btn_finanzas", use_container_width=True):
            st.switch_page("pages/6_Finanzas.py")
    
    with col2:
        st.markdown("""
        <div class="dashboard-card card-finanzas">
            <div class="card-title">🛒 Compras</div>
            <div class="card-desc">OC, Aprobaciones y Líneas de Crédito</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Abrir Compras", key="btn_compras", use_container_width=True):
            st.switch_page("pages/8_Compras.py")
    
    st.markdown('<div class="section-header">⚙️ Administración</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="dashboard-card card-admin">
            <div class="card-title">⚙️ Permisos</div>
            <div class="card-desc">Gestión de accesos por usuario</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Abrir Permisos", key="btn_permisos", use_container_width=True):
            st.switch_page("pages/9_Permisos.py")
    
    # Información del sistema
    st.markdown("---")
    with st.expander("ℹ️ Información del Sistema"):
        st.markdown("""
        **Rio Futuro Dashboards v1.0**
        
        - **Backend:** FastAPI
        - **Frontend:** Streamlit
        - **Base de Datos:** Odoo ERP
        """)
