from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Optional, List
from datetime import datetime, date

from backend.services.odf_reconciliation_service import ODFReconciliationService
from backend.services.trigger_so_asociada_service import TriggerSOAsociadaService
from shared.odoo_client import OdooClient

router = APIRouter(prefix="/api/v1/odf-reconciliation", tags=["ODF Reconciliation"])


def get_reconciliation_service() -> ODFReconciliationService:
    odoo = OdooClient()
    return ODFReconciliationService(odoo)


def get_trigger_service() -> TriggerSOAsociadaService:
    odoo = OdooClient()
    return TriggerSOAsociadaService(odoo)


@router.post("/odf/{odf_id}/reconciliar")
async def reconciliar_odf_single(odf_id: int, dry_run: bool = Query(False)) -> Dict:
    service = get_reconciliation_service()
    try:
        return service.reconciliar_odf(odf_id, dry_run=dry_run)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reconciliar-rango")
async def reconciliar_por_fecha(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    dry_run: bool = Query(False)
) -> Dict:
    service = get_reconciliation_service()
    try:
        return service.reconciliar_odfs_por_fecha(
            fecha_inicio=fecha_inicio.isoformat(),
            fecha_fin=fecha_fin.isoformat(),
            dry_run=dry_run
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/odf/{odf_id}/preview")
async def preview_reconciliacion(odf_id: int) -> Dict:
    service = get_reconciliation_service()
    try:
        return service.reconciliar_odf(odf_id, dry_run=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parsear-pos/{po_string}")
async def parsear_pos_string(po_string: str) -> Dict:
    service = get_reconciliation_service()
    pos = service.parse_pos_asociadas(po_string)
    return {'input': po_string, 'parsed': pos, 'count': len(pos)}


@router.get("/odfs-sin-so-asociada")
async def listar_odfs_sin_so_asociada(
    limit: Optional[int] = Query(None),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None)
) -> Dict:
    try:
        service = get_trigger_service()
        odfs_pendientes = service.get_odfs_pendientes(
            limit=limit,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        return {"success": True, "total": len(odfs_pendientes), "odfs": odfs_pendientes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-so-asociada/{odf_id}")
async def trigger_so_asociada_individual(odf_id: int, wait_seconds: float = Query(2.0)) -> Dict:
    try:
        service = get_trigger_service()
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
    odf_ids: Optional[List[int]] = Query(None),
    limit: Optional[int] = Query(None),
    wait_seconds: float = Query(2.0),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None)
) -> Dict:
    try:
        service = get_trigger_service()
        return service.trigger_bulk(
            odf_ids=odf_ids,
            limit=limit,
            wait_seconds=wait_seconds,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
