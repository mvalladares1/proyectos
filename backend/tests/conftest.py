"""
Fixtures y configuración global de pytest para proyectos.
"""
import os
import sys
import pytest
from typing import Generator
from unittest.mock import AsyncMock, patch

# Asegurar que el path incluye backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Configurar ambiente de test ANTES de importar la app
os.environ["ENV"] = "test"
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-only-for-testing"
os.environ["ODOO_URL"] = "http://localhost:8069"
os.environ["ODOO_DB"] = "test_db"
os.environ["ODOO_API_USER"] = "test@test.com"
os.environ["ODOO_API_KEY"] = "test_api_key"

from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
import pytest_asyncio

# Imports de la aplicación (después de configurar env)
from backend.main import app


# ============================================
# Fixtures de Cliente HTTP
# ============================================

@pytest.fixture(scope="function")
def client() -> Generator:
    """Cliente de test síncrono."""
    with TestClient(app) as test_client:
        yield test_client


@pytest_asyncio.fixture(scope="function")
async def async_client():
    """Cliente de test asíncrono."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


# ============================================
# Fixtures de Autenticación
# ============================================

@pytest.fixture
def auth_headers() -> dict:
    """Headers con token JWT válido para tests."""
    # Proyectos puede usar diferentes auth
    return {"Authorization": "Bearer test_token"}


# ============================================
# Mocks de Servicios Externos
# ============================================

@pytest.fixture
def mock_odoo_service():
    """Mock del servicio de Odoo."""
    with patch("backend.services.odoo_client.OdooClient") as mock:
        instance = mock.return_value
        instance.execute_kw = AsyncMock(return_value=[])
        yield instance


# ============================================
# Configuración
# ============================================

@pytest.fixture(autouse=True)
def reset_app_state():
    """Limpiar estado de la app entre tests."""
    yield
    app.dependency_overrides.clear()
