from fastapi.testclient import TestClient
from backend.main import app


def test_get_example():
    client = TestClient(app)
    resp = client.get("/api/v1/example")
    assert resp.status_code == 200
    data = resp.json()
    assert "meta" in data and "data" in data
    assert isinstance(data["data"], list)
