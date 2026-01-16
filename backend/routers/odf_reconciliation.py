from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Optional, List
from datetime import datetime, date

from backend.services.odf_reconciliation_service import ODFReconciliationService
from backend.services.trigger_so_asociada_service import TriggerSOAsociadaService
from shared.odoo_client import OdooClient

router = APIRouter(prefix="/api/v1/odf-reconciliation", tags=["ODF Reconciliation"])


def get_reconciliation_service(username: str, password: str) -> ODFReconciliationService:
    odoo = OdooClient(username=username, password=password)
    return ODFReconciliationService(odoo)


def get_trigger_service(username: str, password: str) -> TriggerSOAsociadaService:
    odoo = OdooClient(username=username, password=password)
    return TriggerSOAsociadaService(odoo)


@router.post("/odf/{odf_id}/reconciliar")
async def reconciliar_odf_single(
    odf_id: int,
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    dry_run: bool = Query(False)
) -> Dict:
    service = get_reconciliation_service(username, password)
    try:
        return service.reconciliar_odf(odf_id, dry_run=dry_run)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reconciliar-rango")
async def reconciliar_por_fecha(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    dry_run: bool = Query(False)
) -> Dict:
    service = get_reconciliation_service(username, password)
    try:
        return service.reconciliar_odfs_por_fecha(
            fecha_inicio=fecha_inicio.isoformat(),
            fecha_fin=fecha_fin.isoformat(),
            dry_run=dry_run
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/odf/{odf_id}/preview")
async def preview_reconciliacion(
    odf_id: int,
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
) -> Dict:
    service = get_reconciliation_service(username, password)
    try:
        return service.reconciliar_odf(odf_id, dry_run=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parsear-pos/{po_string}")
async def parsear_pos_string(
    po_string: str,
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
) -> Dict:
    service = get_reconciliation_service(username, password)
    pos = service.parse_pos_asociadas(po_string)
    return {'input': po_string, 'parsed': pos, 'count': len(pos)}


@router.get("/todas-odfs")
async def listar_todas_odfs(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    limit: Optional[int] = Query(None),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None)
) -> Dict:
    """Retorna TODAS las ODFs del periodo (con o sin SO Asociada)."""
    try:
        service = get_trigger_service(username, password)
        todas_odfs = service.get_todas_odfs(
            limit=limit,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        # Separar las que tienen SO de las que no
        sin_so = [odf for odf in todas_odfs if not odf.get('x_studio_po_asociada')]
        return {
            "success": True,
            "total": len(todas_odfs),
            "total_sin_so": len(sin_so),
            "odfs": todas_odfs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/odfs-sin-so-asociada")
async def listar_odfs_sin_so_asociada(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    limit: Optional[int] = Query(None),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None)
) -> Dict:
    try:
        service = get_trigger_service(username, password)
        odfs_pendientes = service.get_odfs_pendientes(
            limit=limit,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        return {"success": True, "total": len(odfs_pendientes), "odfs": odfs_pendientes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-so-asociada/{odf_id}")
async def trigger_so_asociada_individual(
    odf_id: int,
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    wait_seconds: float = Query(2.0)
) -> Dict:
    try:
        service = get_trigger_service(username, password)
        resultado = service.trigger_so_asociada(odf_id, wait_seconds)
        if not resultado['success']:
            raise HTTPException(status_code=400, detail=resultado.get('error'))
        return resultado
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-so-asociada-bulk")
async def trigger_so_asociada_bulk(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    odf_ids: Optional[List[int]] = Query(None),
    limit: Optional[int] = Query(None),
    wait_seconds: float = Query(2.0),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None)
) -> Dict:
    try:
        service = get_trigger_service(username, password)
        return service.trigger_bulk(
            odf_ids=odf_ids,
            limit=limit,
            wait_seconds=wait_seconds,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
