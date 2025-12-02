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

    import os, re

    def get_page_metadata(path: str) -> dict:
        meta = {"title": None, "icon": None, "description": None, "path": path}
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read(2048)
        except Exception:
            return meta

        # docstring (triple quotes)
        m = re.search(r"^\s*(?:\'\'\'|\"\"\")(.+?)(?:\'\'\'|\"\"\")", text, re.S | re.M)
        if m:
            meta["description"] = m.group(1).strip()

        # page_title and page_icon from st.set_page_config
        m2 = re.search(r"st\.set_page_config\(([^)]*)\)", text)
        if m2:
            inside = m2.group(1)
            title_m = re.search(r"page_title\s*=\s*['\"]([^'\"]+)['\"]", inside)
            icon_m = re.search(r"page_icon\s*=\s*['\"]([^'\"]+)['\"]", inside)
            if title_m:
                meta["title"] = title_m.group(1)
            if icon_m:
                meta["icon"] = icon_m.group(1)

        if not meta["title"]:
            meta["title"] = os.path.splitext(os.path.basename(path))[0]
        return meta

    pages_dir = os.path.join(os.path.dirname(__file__), "pages")
    page_files = []
    try:
        for p in os.listdir(pages_dir):
            if p.endswith('.py') and p not in ['__init__.py']:
                page_files.append(os.path.join(pages_dir, p))
    except Exception:
        page_files = []

    page_meta = [get_page_metadata(p) for p in page_files if 'Home.py' not in p]

    # Render cards dynamically (2 per row)
    for i in range(0, len(page_meta), 2):
        cols = st.columns(2)
        for j, meta in enumerate(page_meta[i:i+2]):
            with cols[j]:
                icon = meta.get('icon') or ''
                title = meta.get('title')
                desc = meta.get('description') or ''
                st.markdown(f"### {icon} {title}")
                if desc:
                    st.markdown(desc)
                rel = os.path.relpath(meta['path'], os.path.join(os.path.dirname(__file__)))
                rel = rel.replace('\\\\', '/')
                st.page_link(rel, label=f"Ir a {title}", icon=icon or None)
    
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
