"""Router del portal de proveedores."""
from __future__ import annotations

from datetime import date, timedelta
import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.services.provider_portal_service import (
    ProviderPortalAuthService,
    ProviderPortalDataService,
)


router = APIRouter(prefix="/api/v1/provider-portal", tags=["provider-portal"])


class ProviderLoginRequest(BaseModel):
    rut: str
    password: str


def _get_token(authorization: Optional[str], token: Optional[str]) -> str:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    if token:
        return token
    raise HTTPException(status_code=401, detail="Sesion requerida")


def _get_session(authorization: Optional[str] = Header(None), token: Optional[str] = Query(None)):
    access_token = _get_token(authorization, token)
    session = ProviderPortalAuthService.refresh_session(access_token)
    if not session:
        raise HTTPException(status_code=401, detail="Sesion invalida o expirada")
    return access_token, session


@router.post("/login")
async def provider_login(request: ProviderLoginRequest, response: Response):
    try:
        session = ProviderPortalAuthService.login(request.rut, request.password)
        response.set_cookie(
            key="provider_portal_token",
            value=session["token"],
            max_age=12 * 60 * 60,
            httponly=True,
            samesite="lax",
            secure=False,
        )
        return {"success": True, **session}
    except Exception as exc:
        raise HTTPException(status_code=401, detail=str(exc))


@router.post("/login/dev-auto")
async def provider_login_dev_auto(
    response: Response,
    partner_id: Optional[int] = Query(None),
    rut: Optional[str] = Query(None),
    internal_session_token: Optional[str] = Query(None),
):
    if os.getenv("ENV", "production") != "development":
        raise HTTPException(status_code=404, detail="Not found")
    try:
        session = ProviderPortalAuthService.dev_auto_login(
            partner_id=partner_id,
            rut=rut,
            internal_session_token=internal_session_token or "",
        )
        response.set_cookie(
            key="provider_portal_token",
            value=session["token"],
            max_age=12 * 60 * 60,
            httponly=True,
            samesite="lax",
            secure=False,
        )
        return {"success": True, **session}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/logout")
async def provider_logout(
    response: Response,
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None),
):
    access_token = _get_token(authorization, token)
    ProviderPortalAuthService.logout(access_token)
    response.delete_cookie("provider_portal_token")
    return {"success": True}


@router.get("/me")
async def provider_me(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None),
):
    _, session = _get_session(authorization, token)
    service = ProviderPortalDataService(provider_session=session)
    partner = service.get_partner_profile(int(session["partner_id"]))
    return {"session": session, "partner": partner}


@router.get("/dashboard")
async def provider_dashboard(
    fecha_inicio: str = Query(..., description="Fecha inicio YYYY-MM-DD"),
    fecha_fin: str = Query(..., description="Fecha fin YYYY-MM-DD"),
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None),
):
    _, session = _get_session(authorization, token)
    try:
        service = ProviderPortalDataService(provider_session=session)
        return service.get_dashboard(int(session["partner_id"]), fecha_inicio, fecha_fin)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/attachments/{attachment_id}")
async def provider_attachment(
    attachment_id: int,
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None),
):
    _, session = _get_session(authorization, token)
    try:
        service = ProviderPortalDataService(provider_session=session)
        content, meta = service.get_attachment_content(int(session["partner_id"]), attachment_id)
        return StreamingResponse(
            iter([content]),
            media_type=meta["mimetype"],
            headers={"Content-Disposition": f"inline; filename={meta['name']}"},
        )
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
