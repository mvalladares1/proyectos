"""
Router de autenticación con tokens de sesión
"""
from fastapi import APIRouter, HTTPException, Response, Cookie
from pydantic import BaseModel
from typing import Optional

from shared.odoo_client import OdooClient
from backend.services.session_service import SessionService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    uid: Optional[int] = None
    username: str
    message: str
    expires_in_hours: int = 8


class TokenValidateRequest(BaseModel):
    token: str


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, response: Response):
    """
    Autentica un usuario contra Odoo y genera un token de sesión.
    El token se retorna en el body y también se establece como cookie.
    """
    try:
        # Validar contra Odoo
        client = OdooClient(username=request.username, password=request.password)
        
        # Generar token de sesión
        token = SessionService.create_session(
            username=request.username,
            uid=client.uid,
            odoo_password=request.password
        )
        
        # Establecer cookie (8 horas, httponly para seguridad)
        response.set_cookie(
            key="session_token",
            value=token,
            max_age=8 * 60 * 60,  # 8 horas en segundos
            httponly=True,
            samesite="lax",
            secure=False  # Cambiar a True en producción con HTTPS
        )
        
        return LoginResponse(
            success=True,
            token=token,
            uid=client.uid,
            username=request.username,
            message="Login exitoso",
            expires_in_hours=8
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/validate")
async def validate_token(request: TokenValidateRequest):
    """
    Valida un token de sesión.
    Retorna los datos de sesión si es válido, o error si no.
    """
    session = SessionService.validate_session(request.token)
    if session:
        # Actualizar actividad
        SessionService.refresh_activity(request.token)
        return {
            "valid": True,
            **session
        }
    return {"valid": False, "message": "Sesión inválida o expirada"}


@router.post("/refresh")
async def refresh_session(request: TokenValidateRequest):
    """
    Refresca la actividad de una sesión.
    Debe llamarse periódicamente para evitar timeout por inactividad.
    """
    success = SessionService.refresh_activity(request.token)
    if success:
        info = SessionService.get_session_info(request.token)
        return {
            "success": True,
            "session_info": info
        }
    raise HTTPException(status_code=401, detail="Sesión inválida")


@router.post("/logout")
async def logout(request: TokenValidateRequest, response: Response):
    """
    Cierra la sesión e invalida el token.
    """
    SessionService.invalidate_session(request.token)
    
    # Eliminar cookie
    response.delete_cookie(key="session_token")
    
    return {"success": True, "message": "Sesión cerrada"}


@router.get("/session-info")
async def get_session_info(token: str):
    """
    Obtiene información de la sesión actual incluyendo tiempo restante.
    """
    info = SessionService.get_session_info(token)
    if info:
        return info
    raise HTTPException(status_code=401, detail="Sesión inválida")


@router.post("/cleanup")
async def cleanup_sessions():
    """
    Limpia sesiones expiradas (uso administrativo).
    """
    count = SessionService.cleanup_expired_sessions()
    return {"cleaned": count, "message": f"Se limpiaron {count} sesiones expiradas"}


@router.get("/credentials")
async def get_credentials(token: str):
    """
    Obtiene las credenciales de Odoo para una sesión válida.
    Uso interno para llamadas a la API.
    """
    creds = SessionService.get_odoo_credentials(token)
    if creds:
        return {"username": creds[0], "password": creds[1]}
    raise HTTPException(status_code=401, detail="Sesión inválida")
