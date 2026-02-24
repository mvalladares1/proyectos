"""Smoke tests - Verificación básica de ambiente proyectos."""
import pytest
import time
from fastapi.testclient import TestClient


pytestmark = pytest.mark.smoke


class TestSmokeHealth:
    """Verificación básica que el ambiente funciona."""
    
    def test_health_endpoint_responds(self, client: TestClient):
        """El endpoint /health debe responder."""
        response = client.get("/health")
        
        assert response.status_code == 200
    
    def test_environment_is_not_production(self, client: TestClient):
        """El ambiente no debe ser producción en tests."""
        response = client.get("/health")
        data = response.json()
        
        # Verificar que no está en producción
        env = data.get("environment", data.get("env", "test"))
        assert env != "production"


class TestSmokeDocs:
    """Verificación de documentación."""
    
    def test_docs_available(self, client: TestClient):
        """Swagger docs debe estar disponible."""
        response = client.get("/docs")
        
        assert response.status_code == 200
    
    def test_openapi_schema_valid(self, client: TestClient):
        """OpenAPI schema debe ser válido."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert data["openapi"].startswith("3.")


class TestSmokePerformance:
    """Verificación básica de performance."""
    
    def test_health_responds_fast(self, client: TestClient):
        """Health debe responder en menos de 500ms."""
        start = time.time()
        response = client.get("/health")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 0.5, f"Health tardó {elapsed:.2f}s"
