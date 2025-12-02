"""
Router de autenticación
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from shared.odoo_client import OdooClient

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    uid: Optional[int] = None
    username: str
    message: str


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Autentica un usuario contra Odoo.
    """
    try:
        client = OdooClient(username=request.username, password=request.password)
        return LoginResponse(
            success=True,
            uid=client.uid,
            username=request.username,
            message="Login exitoso"
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/validate")
async def validate_token(request: LoginRequest):
    """
    Valida las credenciales sin crear sesión.
    """
    try:
        client = OdooClient(username=request.username, password=request.password)
        return {"valid": True, "uid": client.uid}
    except Exception:
        return {"valid": False, "uid": None}
