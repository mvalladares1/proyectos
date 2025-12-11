"""
Rio Futuro Dashboards - Página Principal
Sistema unificado de dashboards para gestión de datos Odoo
"""
import os
import re

import httpx
import streamlit as st

from shared.auth import guardar_permisos_state


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")


def slug_from_path(path: str) -> str:
    name = os.path.splitext(os.path.basename(path))[0]
    parts = name.split("_")
    if len(parts) > 1:
        candidate = parts[-1]
    else:
        candidate = parts[0]
    slug = re.sub(r"[^A-Za-z0-9]+", "_", candidate)
    return slug.strip("_").lower()


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


def ensure_permissions(username: str) -> None:
    if not username:
        guardar_permisos_state({}, [], False)
        return
    if 'restricted_dashboards' in st.session_state:
        return
    permisos = fetch_permissions(username)
    if permisos:
        guardar_permisos_state(
            permisos.get('restricted', {}),
            permisos.get('allowed', []),
            permisos.get('is_admin', False)
        )
    else:
        guardar_permisos_state({}, [], False)


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
    div[data-testid="stVerticalBlock"] > div:has(> .dashboard-card) {
        padding: 0.25rem;
    }
    
    /* Iconos en la sidebar */
    [data-testid="stSidebarNav"] li:nth-child(1) span::before { content: "🏠 "; }
    [data-testid="stSidebarNav"] li:nth-child(2) span::before { content: "📥 "; }
    [data-testid="stSidebarNav"] li:nth-child(3) span::before { content: "🏭 "; }
    [data-testid="stSidebarNav"] li:nth-child(4) span::before { content: "📊 "; }
    [data-testid="stSidebarNav"] li:nth-child(5) span::before { content: "📦 "; }
    [data-testid="stSidebarNav"] li:nth-child(6) span::before { content: "🚢 "; }
    [data-testid="stSidebarNav"] li:nth-child(7) span::before { content: "💰 "; }
    [data-testid="stSidebarNav"] li:nth-child(8) span::before { content: "⚙️ "; }
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
                    try:
                        response = httpx.post(
                            f"{API_URL}/api/v1/auth/login",
                            json={"username": email, "password": api_token},
                            timeout=10.0
                        )
                        
                        if response.status_code == 200:
                            st.session_state['authenticated'] = True
                            st.session_state['username'] = email
                            st.session_state['password'] = api_token
                            st.session_state['user_data'] = response.json()
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

    # Definición de categorías de dashboards
    DASHBOARD_CATEGORIES = {
        "operaciones": {
            "title": "📦 Operaciones",
            "slugs": ["recepciones", "produccion", "bandejas", "stock", "containers"],
            "style": "card-operaciones"
        },
        "finanzas": {
            "title": "💰 Finanzas",
            "slugs": ["finanzas"],
            "style": "card-finanzas"
        },
        "admin": {
            "title": "⚙️ Administración",
            "slugs": ["permisos"],
            "style": "card-admin"
        }
    }

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
        meta["slug"] = slug_from_path(path)
        return meta

    pages_dir = os.path.join(os.path.dirname(__file__), "pages")
    page_files = []
    try:
        for p in os.listdir(pages_dir):
            if p.endswith('.py') and p not in ['__init__.py']:
                page_files.append(os.path.join(pages_dir, p))
    except Exception:
        page_files = []

    ensure_permissions(st.session_state.get('username', ''))
    restricted = st.session_state.get('restricted_dashboards', {})
    allowed = st.session_state.get('allowed_dashboards', [])

    def page_visible(meta: dict) -> bool:
        slug = meta.get('slug')
        if slug in restricted:
            return slug in allowed
        return True

    page_meta = [get_page_metadata(p) for p in page_files if 'Home.py' not in p]
    page_meta = [meta for meta in page_meta if page_visible(meta)]

    # Map slugs to meta
    meta_by_slug = {meta['slug']: meta for meta in page_meta}

    def render_dashboard_card(meta: dict, style_class: str):
        """Renderiza una tarjeta de dashboard con estilo"""
        icon = meta.get('icon') or '📄'
        title = meta.get('title', 'Dashboard')
        desc = meta.get('description') or 'Dashboard de Rio Futuro'
        # Limitar descripción
        if len(desc) > 100:
            desc = desc[:97] + "..."
        
        st.markdown(f"""
        <div class="dashboard-card {style_class}">
            <div class="card-title">{icon} {title}</div>
            <div class="card-desc">{desc}</div>
        </div>
        """, unsafe_allow_html=True)
        
        rel = os.path.relpath(meta['path'], os.path.join(os.path.dirname(__file__)))
        rel = rel.replace('\\', '/')
        st.page_link(rel, label=f"Ir a {title}", icon=icon or None, use_container_width=True)

    # Renderizar cada categoría
    rendered_slugs = set()
    
    for cat_key, cat_info in DASHBOARD_CATEGORIES.items():
        cat_dashboards = [meta_by_slug[s] for s in cat_info["slugs"] if s in meta_by_slug]
        if not cat_dashboards:
            continue
        
        st.markdown(f'<div class="section-header">{cat_info["title"]}</div>', unsafe_allow_html=True)
        
        # Mostrar en grid de 3 columnas
        cols = st.columns(3, gap="medium")
        for idx, meta in enumerate(cat_dashboards):
            with cols[idx % 3]:
                render_dashboard_card(meta, cat_info["style"])
                rendered_slugs.add(meta['slug'])
        
        # Añadir espacio entre categorías
        st.markdown("<br>", unsafe_allow_html=True)

    # Dashboards no categorizados (si los hay)
    other_dashboards = [meta for meta in page_meta if meta['slug'] not in rendered_slugs]
    if other_dashboards:
        st.markdown('<div class="section-header">📋 Otros Dashboards</div>', unsafe_allow_html=True)
        cols = st.columns(3, gap="medium")
        for idx, meta in enumerate(other_dashboards):
            with cols[idx % 3]:
                render_dashboard_card(meta, "")
    
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
