"""
Demo router for example usage by the Streamlit template.
This provides a simple JSON response at GET /api/v1/example for demo/test purposes.
"""
from typing import Optional
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["demo"])


@router.get("/example")
async def get_example(username: Optional[str] = None, password: Optional[str] = None):
    """Return a small JSON payload useful for the template page.

    Accepts username and password as query params (ignored) for convenience during frontend tests.
    """
    sample = {
        "meta": {
            "source": "rio-futuro-dashboards-demo",
            "count": 3,
        },
        "data": [
            {"id": 1, "name": "Item A", "value": 42, "status": "ok"},
            {"id": 2, "name": "Item B", "value": 17, "status": "ok"},
            {"id": 3, "name": "Item C", "value": 99, "status": "warning"},
        ],
    }
    return sample
