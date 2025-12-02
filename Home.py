"""
Rio Futuro Dashboards - Página Principal
Sistema unificado de dashboards para gestión de datos Odoo
"""
import streamlit as st

st.set_page_config(
    page_title="Rio Futuro Dashboards",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .dashboard-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        margin: 10px;
        text-align: center;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Header principal
st.markdown('<p class="main-header">🏭 Rio Futuro Dashboards</p>', unsafe_allow_html=True)

# Estado de autenticación
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
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
                    # Validar credenciales con el backend
                    import httpx
                    import os
                    
                    api_url = os.getenv("API_URL", "http://127.0.0.1:8000")
                    
                    try:
                        response = httpx.post(
                            f"{api_url}/api/v1/auth/login",
                            json={"username": email, "password": api_token},
                            timeout=10.0
                        )
                        
                        if response.status_code == 200:
                            st.session_state['authenticated'] = True
                            st.session_state['username'] = email
                            st.session_state['password'] = api_token
                            st.session_state['user_data'] = response.json()
                            st.success("✅ Login exitoso!")
                            st.rerun()
                        else:
                            st.error(f"❌ Error de autenticación: {response.json().get('detail', 'Credenciales inválidas')}")
                    except httpx.ConnectError:
                        st.error("❌ No se puede conectar al servidor API. Verificar que el backend esté corriendo.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                else:
                    st.warning("⚠️ Por favor ingresa tu correo y token API")
    
    st.markdown("---")
    st.info("💡 **Nota:** Necesitas un Token API de Odoo para acceder. Puedes generarlo en tu perfil de Odoo > Preferencias > Claves API.")

else:
    # Usuario autenticado - Mostrar menú de dashboards
    st.sidebar.success(f"👤 {st.session_state.get('username', 'Usuario')}")
    
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    st.markdown("---")
    st.subheader("📊 Selecciona un Dashboard")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 📦 Producción
        Dashboard de órdenes de fabricación, seguimiento de producción y KPIs de manufactura.
        
        **Funcionalidades:**
        - Órdenes de fabricación activas
        - Métricas de producción
        - Análisis de eficiencia
        """)
        st.page_link("pages/1_📦_Produccion.py", label="Ir a Producción", icon="📦")
    
    with col2:
        st.markdown("""
        ### 📊 Bandejas
        Control de recepción y despacho de bandejas a productores.
        
        **Funcionalidades:**
        - Movimientos de entrada/salida
        - Stock actual por tipo
        - Balance por productor
        """)
        st.page_link("pages/2_📊_Bandejas.py", label="Ir a Bandejas", icon="📊")
    
    st.markdown("---")
    
    # Información del sistema
    with st.expander("ℹ️ Información del Sistema"):
        st.markdown("""
        **Rio Futuro Dashboards v1.0**
        
        Sistema unificado de dashboards para la gestión de datos de Odoo ERP.
        
        - **Backend:** FastAPI (REST API)
        - **Frontend:** Streamlit
        - **Base de Datos:** Odoo ERP
        
        Para soporte técnico, contactar al administrador del sistema.
        """)
