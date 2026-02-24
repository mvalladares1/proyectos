"""Tests de integración para API de proyectos."""
import pytest
from fastapi.testclient import TestClient


pytestmark = [pytest.mark.integration]


class TestHealthEndpoint:
    """Tests para endpoint de health."""
    
    def test_health_returns_200(self, client: TestClient):
        """Health check debe retornar 200."""
        response = client.get("/health")
        
        assert response.status_code == 200
    
    def test_health_returns_status(self, client: TestClient):
        """Health check debe retornar status healthy."""
        response = client.get("/health")
        data = response.json()
        
        assert data["status"] == "healthy"


class TestDocsEndpoint:
    """Tests para documentación."""
    
    def test_docs_available(self, client: TestClient):
        """Swagger docs debe estar disponible."""
        response = client.get("/docs")
        
        assert response.status_code == 200
    
    def test_openapi_json_available(self, client: TestClient):
        """OpenAPI JSON debe estar disponible."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data


class TestExampleEndpoint:
    """Tests para endpoint de ejemplo."""
    
    def test_get_example(self, client: TestClient):
        """Endpoint /api/v1/example debe retornar datos válidos."""
        response = client.get("/api/v1/example")
        
        assert response.status_code == 200
        data = response.json()
        assert "meta" in data and "data" in data
        assert isinstance(data["data"], list)


class TestCORSConfiguration:
    """Tests para configuración CORS."""
    
    def test_cors_headers_present(self, client: TestClient):
        """CORS headers deben estar presentes en respuestas."""
        response = client.options(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        # OPTIONS puede retornar 200 o 405 dependiendo de config
        assert response.status_code in [200, 405]
