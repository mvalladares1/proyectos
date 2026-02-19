"""
BUENOBOT - FastAPI Router

Endpoints para el sistema de QA y seguridad BUENOBOT.

Endpoints:
    POST /buenobot/scan          - Iniciar nuevo scan
    GET  /buenobot/scan/{id}     - Obtener resultado de scan
    GET  /buenobot/scan/{id}/logs - Obtener logs de scan
    GET  /buenobot/scan/{id}/report - Obtener reporte en formato especificado
    GET  /buenobot/scans         - Listar historial de scans
    GET  /buenobot/checks        - Listar checks disponibles
    POST /buenobot/scan/{id}/cancel - Cancelar scan activo
    GET  /buenobot/compare       - Comparar dos scans
"""
import asyncio
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel, Field

from backend.buenobot.models import (
    ScanType,
    ScanStatus,
    ScanRequest,
    ScanResponse,
    ScanListItem,
    GateStatus
)
from backend.buenobot.storage import get_storage
from backend.buenobot.runner import ScanRunner, start_scan_job, get_active_scans, cancel_scan
from backend.buenobot.checks.base import CheckRegistry

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/buenobot",
    tags=["BUENOBOT - QA & Security"]
)


# === Request/Response Models ===

class StartScanRequest(BaseModel):
    """Request para iniciar un scan"""
    environment: str = Field(default="dev", description="Entorno: dev o prod")
    scan_type: str = Field(default="quick", description="Tipo: quick o full")
    checks: Optional[List[str]] = Field(default=None, description="Checks específicos (null=todos)")
    triggered_by: Optional[str] = Field(default=None, description="Usuario que inicia")


class ScanStatusResponse(BaseModel):
    """Response con estado de un scan"""
    scan_id: str
    status: str
    gate_status: str
    gate_reason: str
    progress: Optional[dict] = None
    summary: Optional[dict] = None
    duration_seconds: Optional[float] = None
    created_at: str
    completed_at: Optional[str] = None


class CheckInfo(BaseModel):
    """Información de un check"""
    id: str
    name: str
    category: str
    description: str
    in_quick: bool
    in_full: bool


# === Endpoints ===

@router.post("/scan", response_model=ScanResponse)
async def start_scan(
    request: StartScanRequest,
    background_tasks: BackgroundTasks
):
    """
    Inicia un nuevo scan de QA/Security.
    
    El scan se ejecuta en background y retorna inmediatamente con el scan_id.
    Usar GET /buenobot/scan/{scan_id} para obtener resultados.
    """
    logger.info(f"Iniciando scan: type={request.scan_type}, env={request.environment}")
    
    # Validar tipo
    try:
        scan_type = ScanType(request.scan_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de scan inválido: {request.scan_type}. Use 'quick' o 'full'"
        )
    
    # Validar ambiente
    if request.environment not in ["dev", "prod"]:
        raise HTTPException(
            status_code=400,
            detail="Entorno inválido. Use 'dev' o 'prod'"
        )
    
    # Verificar que no haya muchos scans activos
    active = get_active_scans()
    if len(active) >= 3:
        raise HTTPException(
            status_code=429,
            detail=f"Demasiados scans activos ({len(active)}). Espere a que terminen."
        )
    
    # Crear runner y ejecutar en background
    runner = ScanRunner()
    
    # Ejecutar directamente con asyncio (el runner maneja la persistencia)
    async def run_scan_task():
        try:
            await runner.run_scan(
                scan_type=scan_type,
                environment=request.environment,
                triggered_by=request.triggered_by,
                specific_checks=request.checks
            )
        except Exception as e:
            logger.exception(f"Error en scan: {e}")
    
    # Iniciar scan en background
    background_tasks.add_task(asyncio.create_task, run_scan_task())
    
    # Obtener el scan recién creado (el runner lo guarda inmediatamente)
    storage = get_storage()
    scans = storage.list_scans(limit=1)
    
    if scans:
        latest = scans[0]
        return ScanResponse(
            scan_id=latest.scan_id,
            status=ScanStatus.RUNNING,
            message=f"Scan iniciado. Use GET /buenobot/scan/{latest.scan_id} para resultados.",
            created_at=latest.created_at
        )
    
    # Fallback si no se encontró
    return ScanResponse(
        scan_id="pending",
        status=ScanStatus.QUEUED,
        message="Scan en cola. Intente nuevamente en unos segundos.",
        created_at=datetime.utcnow()
    )


@router.get("/scan/{scan_id}")
async def get_scan(scan_id: str):
    """
    Obtiene el estado y resultados de un scan.
    """
    storage = get_storage()
    scan_data = storage.get_scan_raw(scan_id)
    
    if not scan_data:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} no encontrado")
    
    return scan_data


@router.get("/scan/{scan_id}/status", response_model=ScanStatusResponse)
async def get_scan_status(scan_id: str):
    """
    Obtiene solo el estado resumido de un scan (polling ligero).
    """
    storage = get_storage()
    scan_data = storage.get_scan_raw(scan_id)
    
    if not scan_data:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} no encontrado")
    
    metadata = scan_data.get("metadata", {})
    
    return ScanStatusResponse(
        scan_id=scan_id,
        status=scan_data.get("status", "unknown"),
        gate_status=scan_data.get("gate_status", "unknown"),
        gate_reason=scan_data.get("gate_reason", ""),
        progress=scan_data.get("progress"),
        summary=scan_data.get("summary"),
        duration_seconds=scan_data.get("duration_seconds"),
        created_at=metadata.get("created_at", ""),
        completed_at=metadata.get("completed_at")
    )


@router.get("/scan/{scan_id}/logs")
async def get_scan_logs(
    scan_id: str,
    tail: int = Query(default=100, le=500)
):
    """
    Obtiene los logs de un scan.
    """
    storage = get_storage()
    scan_data = storage.get_scan_raw(scan_id)
    
    if not scan_data:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} no encontrado")
    
    progress = scan_data.get("progress", {})
    logs = progress.get("logs", [])
    
    return {
        "scan_id": scan_id,
        "logs": logs[-tail:],
        "total": len(logs)
    }


@router.get("/scan/{scan_id}/report")
async def get_scan_report(
    scan_id: str,
    format: str = Query(default="json", description="Formato: json o markdown")
):
    """
    Obtiene el reporte completo de un scan.
    """
    storage = get_storage()
    
    if format == "markdown":
        report_md = storage.export_report_markdown(scan_id)
        if not report_md:
            raise HTTPException(status_code=404, detail=f"Scan {scan_id} no encontrado")
        return PlainTextResponse(content=report_md, media_type="text/markdown")
    
    # Default: JSON
    scan_data = storage.get_scan_raw(scan_id)
    if not scan_data:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} no encontrado")
    
    return scan_data


@router.get("/scans", response_model=List[ScanListItem])
async def list_scans(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    environment: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None)
):
    """
    Lista el historial de scans.
    """
    storage = get_storage()
    scans = storage.list_scans(
        limit=limit,
        offset=offset,
        environment=environment,
        status=status
    )
    return scans


@router.post("/scan/{scan_id}/cancel")
async def cancel_scan_endpoint(scan_id: str):
    """
    Cancela un scan activo.
    """
    success = cancel_scan(scan_id)
    
    if success:
        return {"message": f"Scan {scan_id} cancelado"}
    
    # Verificar si existe pero ya terminó
    storage = get_storage()
    scan_data = storage.get_scan_raw(scan_id)
    
    if scan_data:
        status = scan_data.get("status", "")
        if status in ["done", "failed", "cancelled"]:
            return {"message": f"Scan {scan_id} ya terminó (status: {status})"}
    
    raise HTTPException(status_code=404, detail=f"Scan activo {scan_id} no encontrado")


@router.get("/checks", response_model=List[CheckInfo])
async def list_checks():
    """
    Lista todos los checks disponibles.
    """
    checks = CheckRegistry.list_checks()
    return [CheckInfo(**c) for c in checks]


@router.get("/compare")
async def compare_scans(
    scan_id_1: str = Query(..., description="ID del primer scan"),
    scan_id_2: str = Query(..., description="ID del segundo scan")
):
    """
    Compara dos scans y muestra diferencias.
    """
    storage = get_storage()
    
    scan1 = storage.get_scan_raw(scan_id_1)
    scan2 = storage.get_scan_raw(scan_id_2)
    
    if not scan1:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id_1} no encontrado")
    if not scan2:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id_2} no encontrado")
    
    # Comparar resultados
    comparison = {
        "scan_1": {
            "id": scan_id_1,
            "gate_status": scan1.get("gate_status"),
            "passed": scan1.get("passed_checks", 0),
            "failed": scan1.get("failed_checks", 0),
            "findings": len(scan1.get("top_findings", []))
        },
        "scan_2": {
            "id": scan_id_2,
            "gate_status": scan2.get("gate_status"),
            "passed": scan2.get("passed_checks", 0),
            "failed": scan2.get("failed_checks", 0),
            "findings": len(scan2.get("top_findings", []))
        },
        "diff": {
            "gate_status_changed": scan1.get("gate_status") != scan2.get("gate_status"),
            "passed_diff": scan2.get("passed_checks", 0) - scan1.get("passed_checks", 0),
            "failed_diff": scan2.get("failed_checks", 0) - scan1.get("failed_checks", 0),
            "improved": scan2.get("gate_status") == "pass" and scan1.get("gate_status") != "pass"
        }
    }
    
    return comparison


@router.post("/rerun-failed/{scan_id}")
async def rerun_failed_checks(
    scan_id: str,
    background_tasks: BackgroundTasks
):
    """
    Re-ejecuta solo los checks que fallaron en un scan anterior.
    """
    storage = get_storage()
    scan_data = storage.get_scan_raw(scan_id)
    
    if not scan_data:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} no encontrado")
    
    # Encontrar checks fallidos
    failed_checks = []
    for category, checks in scan_data.get("results", {}).items():
        for check in checks:
            if check.get("status") == "failed":
                failed_checks.append(check.get("check_id"))
    
    if not failed_checks:
        return {"message": "No hay checks fallidos para re-ejecutar"}
    
    # Crear nuevo scan con solo los checks fallidos
    metadata = scan_data.get("metadata", {})
    environment = metadata.get("environment", "dev")
    scan_type = metadata.get("scan_type", "quick")
    
    runner = ScanRunner()
    
    async def run_recheck():
        try:
            await runner.run_scan(
                scan_type=ScanType(scan_type),
                environment=environment,
                triggered_by=f"rerun-{scan_id}",
                specific_checks=failed_checks
            )
        except Exception as e:
            logger.exception(f"Error en rerun: {e}")
    
    background_tasks.add_task(asyncio.create_task, run_recheck())
    
    return {
        "message": f"Re-ejecutando {len(failed_checks)} checks fallidos",
        "checks": failed_checks
    }


@router.get("/health")
async def buenobot_health():
    """
    Health check del servicio BUENOBOT.
    """
    storage = get_storage()
    
    try:
        # Verificar storage accesible
        scans = storage.list_scans(limit=1)
        
        return {
            "status": "healthy",
            "storage": "ok",
            "active_scans": len(get_active_scans()),
            "total_scans": len(storage.list_scans(limit=1000)),
            "checks_available": len(CheckRegistry.list_checks())
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e)
        }


# === v3.0 AI ENDPOINTS ===

@router.get("/scan/{scan_id}/ai")
async def get_scan_ai_analysis(scan_id: str):
    """
    Obtiene el análisis de IA de un scan.
    
    v3.0: Motor híbrido Local/OpenAI con cache por commit.
    Incluye: summary, root_causes, recommendations, risk_score.
    """
    storage = get_storage()
    scan_data = storage.get_scan_raw(scan_id)
    
    if not scan_data:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} no encontrado")
    
    # Obtener AI analysis del scan
    ai_analysis = scan_data.get("ai_analysis")
    summary = scan_data.get("summary", {})
    
    if ai_analysis:
        return {
            "scan_id": scan_id,
            "ai_enabled": ai_analysis.get("enabled", False),
            "engine_used": ai_analysis.get("engine_used"),
            "engine_reason": ai_analysis.get("engine_reason"),
            "cached": ai_analysis.get("cached", False),
            "analysis_ms": ai_analysis.get("analysis_ms", 0),
            "summary": ai_analysis.get("summary"),
            "root_causes": ai_analysis.get("root_causes", []),
            "recommendations": ai_analysis.get("recommendations", []),
            "risk_score": ai_analysis.get("risk_score", 0),
            "confidence": ai_analysis.get("confidence", 0.0),
            "suggested_next_checks": ai_analysis.get("suggested_next_checks", []),
            "notable_anomalies": ai_analysis.get("notable_anomalies", []),
            "error": ai_analysis.get("error"),
            "skipped_reason": ai_analysis.get("skipped_reason")
        }
    
    # Si no hay AI analysis, retornar info del summary
    return {
        "scan_id": scan_id,
        "ai_enabled": summary.get("ai_enabled", False),
        "engine_used": summary.get("ai_engine"),
        "risk_score": summary.get("ai_risk_score"),
        "message": "AI analysis not available for this scan"
    }


@router.post("/scan/{scan_id}/ai/reanalyze")
async def reanalyze_with_ai(
    scan_id: str,
    mode: str = Query(default="basic", description="Modo: basic o deep"),
    force: bool = Query(default=False, description="Forzar re-análisis ignorando cache")
):
    """
    Re-analiza un scan existente con IA.
    
    Útil cuando:
    - El scan se hizo sin IA habilitada
    - Se quiere análisis 'deep' con OpenAI
    - Se quiere invalidar cache
    """
    from backend.buenobot.config import get_ai_config
    from backend.buenobot.evidence import get_evidence_builder
    from backend.buenobot.ai import get_ai_gateway
    from backend.buenobot.cache_ai import get_ai_cache
    from backend.buenobot.models import ScanReport, ScanMetadata, ScanType, ScanStatus, GateStatus
    import time
    
    storage = get_storage()
    scan_data = storage.get_scan_raw(scan_id)
    
    if not scan_data:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} no encontrado")
    
    config = get_ai_config()
    
    if not config.ai_enabled:
        raise HTTPException(status_code=400, detail="AI analysis is disabled")
    
    # Si force, invalidar cache para este scan
    if force:
        cache = get_ai_cache()
        metadata = scan_data.get("metadata", {})
        git_info = metadata.get("git_info", {})
        commit_sha = git_info.get("commit_sha")
        if commit_sha:
            cache.invalidate(commit_sha=commit_sha)
    
    try:
        start_time = time.time()
        
        # Reconstruir ScanReport desde datos
        # (simplificado - usamos los datos raw directamente)
        metadata = scan_data.get("metadata", {})
        
        # Construir EvidencePack desde datos raw
        builder = get_evidence_builder()
        
        # Crear objeto minimal para builder
        class MockScanReport:
            def __init__(self, data):
                self.scan_id = metadata.get("scan_id", scan_id)
                self.gate_status = data.get("gate_status", "unknown")
                self.findings = []
                self.results = data.get("results", {})
                
                # Extraer findings de results
                from backend.buenobot.models import Finding, CheckSeverity
                for category_results in self.results.values():
                    for check in category_results:
                        for f in check.get("findings", []):
                            finding = type('Finding', (), {
                                'title': f.get('title', ''),
                                'description': f.get('description', ''),
                                'severity': CheckSeverity(f.get('severity', 'info').lower()),
                                'location': f.get('location'),
                                'evidence': f.get('evidence'),
                                'recommendation': f.get('recommendation'),
                                'priority': f.get('priority'),
                                'check_name': check.get('check_name', ''),
                                'is_gate_breaker': f.get('severity', '').lower() in ['critical', 'high'],
                                'rule_id': f.get('rule_id', ''),
                                'code': f.get('code', '')
                            })()
                            self.findings.append(finding)
                
                self.total_findings = len(self.findings)
                self.findings_by_severity = data.get("findings_by_severity", {})
            
            def dict(self):
                return {"scan_id": self.scan_id}
        
        mock_report = MockScanReport(scan_data)
        
        git_info = metadata.get("git_info", {})
        evidence = builder.build(
            scan_report=mock_report,
            environment=metadata.get("environment", "unknown"),
            commit_sha=git_info.get("commit_sha")
        )
        
        # Ejecutar análisis
        gateway = get_ai_gateway()
        ai_response = await gateway.analyze(
            evidence=evidence,
            analysis_mode=mode
        )
        
        analysis_ms = int((time.time() - start_time) * 1000)
        
        # Actualizar scan con nuevo AI analysis
        ai_result = {
            "enabled": True,
            "engine_used": ai_response.get("engine_used"),
            "engine_reason": ai_response.get("engine_reason"),
            "analysis_ms": analysis_ms,
            "cached": ai_response.get("cached", False),
            "summary": ai_response.get("summary"),
            "root_causes": ai_response.get("root_causes", []),
            "recommendations": ai_response.get("recommendations", []),
            "risk_score": ai_response.get("risk_score", 0),
            "confidence": ai_response.get("confidence", 0.0),
            "suggested_next_checks": ai_response.get("suggested_next_checks", []),
            "notable_anomalies": ai_response.get("notable_anomalies", [])
        }
        
        # Guardar actualización
        storage.update_scan(scan_id, {"ai_analysis": ai_result})
        
        return {
            "scan_id": scan_id,
            "status": "completed",
            "analysis_ms": analysis_ms,
            "ai_analysis": ai_result
        }
        
    except Exception as e:
        logger.exception(f"Error in AI reanalysis: {e}")
        raise HTTPException(status_code=500, detail=f"AI analysis error: {str(e)}")


@router.get("/ai/config")
async def get_ai_config_endpoint():
    """
    Obtiene la configuración actual de IA (sin secretos).
    """
    from backend.buenobot.config import get_ai_config
    
    config = get_ai_config()
    
    return {
        "ai_enabled": config.ai_enabled,
        "default_engine": config.default_engine,
        "openai_configured": bool(config.openai_api_key),
        "openai_model": config.openai_model,
        "local_engine_url": config.local_engine_url,
        "local_engine_mode": config.local_engine_mode,
        "local_engine_model": config.local_engine_model,
        "cache_enabled": config.cache_enabled,
        "cache_ttl_hours": config.cache_ttl_hours,
        "use_api_for_critical": config.use_api_for_critical,
        "use_api_for_complex": config.use_api_for_complex,
        "complexity_triggers": config.complexity_triggers,
        "max_findings_to_ai": config.max_findings_to_ai
    }


@router.get("/ai/cache/stats")
async def get_ai_cache_stats():
    """
    Obtiene estadísticas del cache de IA.
    """
    from backend.buenobot.cache_ai import get_ai_cache
    
    cache = get_ai_cache()
    return cache.get_stats()


@router.post("/ai/cache/clear")
async def clear_ai_cache():
    """
    Limpia todo el cache de IA.
    
    Útil para desarrollo o cuando se actualiza el modelo.
    """
    from backend.buenobot.cache_ai import get_ai_cache
    
    cache = get_ai_cache()
    cleared = cache.clear()
    
    return {
        "message": f"Cleared {cleared} cache entries",
        "cleared": cleared
    }
