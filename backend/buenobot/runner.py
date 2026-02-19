"""
BUENOBOT - Runner Principal

Orquestador de jobs que ejecuta los checks de forma asíncrona.
Maneja el ciclo de vida de un scan completo.
"""
import asyncio
import time
import logging
import subprocess
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable

from .models import (
    ScanType,
    ScanStatus,
    GateStatus,
    ScanReport,
    ScanReportV3,
    ScanMetadata,
    ScanProgress,
    GitInfo,
    CheckResult,
    CheckCategory,
    AIAnalysisResult
)
from .storage import get_storage
from .checks.base import CheckRegistry, BaseCheck
from .config import get_ai_config
from .evidence import EvidencePack, get_evidence_builder
from .ai import get_ai_gateway

logger = logging.getLogger(__name__)


class ScanRunner:
    """
    Ejecutor principal de scans BUENOBOT.
    
    Responsabilidades:
    - Orquestar ejecución de checks
    - Mantener estado y progreso
    - Guardar resultados
    - Calcular gate status
    """
    
    def __init__(
        self,
        working_dir: str = "/app",
        on_progress: Optional[Callable[[ScanProgress], None]] = None
    ):
        self.working_dir = working_dir
        self.storage = get_storage()
        self.on_progress = on_progress
        self._current_scan: Optional[ScanReport] = None
        self._cancelled = False
    
    def get_git_info(self) -> Optional[GitInfo]:
        """Obtiene información del repositorio Git"""
        try:
            # Commit SHA
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.working_dir,
                timeout=10
            )
            commit_sha = result.stdout.strip() if result.returncode == 0 else "unknown"
            
            # Branch
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.working_dir,
                timeout=10
            )
            branch = result.stdout.strip() if result.returncode == 0 else "unknown"
            
            # Last commit info
            result = subprocess.run(
                ["git", "log", "-1", "--format=%an|%s|%ci"],
                capture_output=True,
                text=True,
                cwd=self.working_dir,
                timeout=10
            )
            
            author = None
            commit_message = None
            commit_date = None
            
            if result.returncode == 0:
                parts = result.stdout.strip().split("|")
                if len(parts) >= 3:
                    author = parts[0]
                    commit_message = parts[1]
                    try:
                        commit_date = datetime.fromisoformat(parts[2].rsplit(" ", 1)[0])
                    except Exception:
                        pass
            
            return GitInfo(
                commit_sha=commit_sha,
                branch=branch,
                author=author,
                commit_message=commit_message,
                commit_date=commit_date
            )
            
        except Exception as e:
            logger.warning(f"Error obteniendo git info: {e}")
            return None
    
    async def run_scan(
        self,
        scan_type: ScanType,
        environment: str = "dev",
        triggered_by: Optional[str] = None,
        specific_checks: Optional[List[str]] = None
    ) -> ScanReport:
        """
        Ejecuta un scan completo.
        
        Args:
            scan_type: Tipo de scan (quick/full)
            environment: Entorno objetivo (dev/prod)
            triggered_by: Usuario que inició el scan
            specific_checks: Lista específica de checks (None = todos del tipo)
        
        Returns:
            ScanReport con resultados completos
        """
        start_time = time.time()
        
        # Crear metadata
        metadata = ScanMetadata(
            scan_type=scan_type,
            environment=environment,
            triggered_by=triggered_by,
            git_info=self.get_git_info()
        )
        
        # Inicializar reporte
        report = ScanReport(
            metadata=metadata,
            status=ScanStatus.RUNNING,
            progress=ScanProgress(
                total_checks=0,
                completed_checks=0,
                logs=[]
            )
        )
        
        # Guardar estado inicial
        self._current_scan = report
        self.storage.save_scan(report)
        
        self._log(report, f"Iniciando {scan_type.value} scan en entorno {environment}")
        self._log(report, f"Commit: {metadata.git_info.commit_sha[:8] if metadata.git_info else 'N/A'}")
        
        try:
            # Obtener checks a ejecutar
            if specific_checks:
                check_ids = specific_checks
            elif scan_type == ScanType.QUICK:
                check_ids = CheckRegistry.get_quick_checks()
            else:
                check_ids = CheckRegistry.get_full_checks()
            
            report.progress.total_checks = len(check_ids)
            report.total_checks = len(check_ids)
            
            self._log(report, f"Checks a ejecutar: {len(check_ids)}")
            
            # Determinar URL del API según entorno
            import os
            if environment == "prod":
                api_url = os.environ.get("API_URL_PROD", "http://localhost:8001")
            else:
                api_url = os.environ.get("API_URL_DEV", "http://localhost:8002")
            
            # Ejecutar checks
            for i, check_id in enumerate(check_ids):
                if self._cancelled:
                    self._log(report, "Scan cancelado por usuario")
                    report.status = ScanStatus.CANCELLED
                    break
                
                check_class = CheckRegistry.get_check(check_id)
                if not check_class:
                    self._log(report, f"Check no encontrado: {check_id}", "warning")
                    continue
                
                # Actualizar progreso
                report.progress.current_check = check_id
                self._update_progress(report)
                
                self._log(report, f"[{i+1}/{len(check_ids)}] Ejecutando: {check_class.name}")
                
                # Instanciar y ejecutar check
                try:
                    check_instance = check_class(
                        working_dir=self.working_dir,
                        environment=environment,
                        api_base_url=api_url
                    )
                    
                    result = await check_instance.execute()
                    
                    # Agregar resultado por categoría
                    category_key = result.category.value
                    if category_key not in report.results:
                        report.results[category_key] = []
                    report.results[category_key].append(result)
                    
                    # Actualizar contadores
                    if result.status == "passed":
                        report.passed_checks += 1
                    elif result.status == "failed":
                        report.failed_checks += 1
                    elif result.status in ["skipped", "error"]:
                        pass  # No cuenta como passed ni failed
                    
                    # Log resultado
                    status_emoji = "✓" if result.status == "passed" else "✗" if result.status == "failed" else "○"
                    self._log(report, f"  {status_emoji} {check_class.name}: {result.status} ({result.duration_ms}ms)")
                    
                except Exception as e:
                    logger.error(f"Error ejecutando check {check_id}: {e}")
                    self._log(report, f"  ✗ Error en {check_id}: {str(e)[:50]}", "error")
                    report.failed_checks += 1
                
                # Actualizar progreso
                report.progress.completed_checks = i + 1
                report.progress.percentage = ((i + 1) / len(check_ids)) * 100
                self._update_progress(report)
                
                # Guardar estado intermedio cada 5 checks
                if (i + 1) % 5 == 0:
                    self.storage.save_scan(report)
            
            # Calcular duración
            report.duration_seconds = time.time() - start_time
            report.metadata.completed_at = datetime.utcnow()
            
            # Calcular gate status
            report.compute_gate_status()
            
            # === v3.0 AI ANALYSIS ===
            ai_analysis = await self._run_ai_analysis(
                report=report,
                environment=environment
            )
            
            # Generar checklist
            report.checklist = self._generate_checklist(report)
            
            # Generar recomendaciones
            report.recommendations = self._generate_recommendations(report)
            
            # Generar resumen
            report.summary = {
                "total_checks": report.total_checks,
                "passed": report.passed_checks,
                "failed": report.failed_checks,
                "warnings": report.warning_checks,
                "duration_seconds": report.duration_seconds,
                "gate_status": report.gate_status.value,
                "critical_findings": len([f for f in report.top_findings if f.severity.value in ["critical", "high"]]),
                "ai_enabled": ai_analysis.enabled if ai_analysis else False,
                "ai_engine": ai_analysis.engine_used if ai_analysis else None,
                "ai_risk_score": ai_analysis.risk_score if ai_analysis and ai_analysis.enabled else None
            }
            
            # Añadir AI analysis al report si se ejecutó
            if ai_analysis and hasattr(report, 'ai_analysis'):
                report.ai_analysis = ai_analysis
            
            # Status final
            if report.status == ScanStatus.RUNNING:
                report.status = ScanStatus.DONE
            
            self._log(report, f"\nScan completado: {report.gate_status.value.upper()}")
            self._log(report, f"Duración: {report.duration_seconds:.1f}s")
            self._log(report, f"Resultados: {report.passed_checks} passed, {report.failed_checks} failed")
            
        except Exception as e:
            logger.exception(f"Error fatal en scan: {e}")
            report.status = ScanStatus.FAILED
            report.gate_status = GateStatus.FAIL
            report.gate_reason = f"Error fatal: {str(e)}"
            self._log(report, f"Error fatal: {e}", "error")
        
        # Guardar reporte final
        self.storage.save_scan(report)
        self._current_scan = None
        
        return report
    
    def _log(self, report: ScanReport, message: str, level: str = "info"):
        """Agrega mensaje al log del scan"""
        timestamp = datetime.utcnow().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        if report.progress:
            report.progress.logs.append(log_entry)
            # Limitar logs en memoria
            if len(report.progress.logs) > 500:
                report.progress.logs = report.progress.logs[-500:]
        
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)
    
    def _update_progress(self, report: ScanReport):
        """Notifica actualización de progreso"""
        if self.on_progress and report.progress:
            try:
                self.on_progress(report.progress)
            except Exception as e:
                logger.warning(f"Error en callback de progreso: {e}")
        
        # Actualizar en storage para polling
        self.storage.update_scan(report.metadata.scan_id, {
            "progress": report.progress.model_dump() if report.progress else None
        })
    
    def _generate_checklist(self, report: ScanReport) -> Dict[str, bool]:
        """Genera checklist Go/No-Go"""
        checklist = {}
        
        # Health endpoints OK
        health_results = report.results.get("api_qa", [])
        health_passed = any(r.check_name == "Health Endpoints" and r.status == "passed" for r in health_results)
        checklist["Health endpoints responden"] = health_passed
        
        # Sin vulnerabilidades críticas
        security_results = report.results.get("security", [])
        no_critical_vulns = not any(
            any(f.severity.value in ["critical", "high"] for f in r.findings)
            for r in security_results
        )
        checklist["Sin vulnerabilidades críticas"] = no_critical_vulns
        
        # Sin secretos expuestos
        secrets_passed = all(
            r.status != "failed" 
            for r in security_results 
            if "secret" in r.check_name.lower()
        )
        checklist["Sin secretos expuestos"] = secrets_passed
        
        # Autenticación funciona
        auth_results = [r for r in health_results if "auth" in r.check_name.lower()]
        auth_passed = all(r.status == "passed" for r in auth_results) if auth_results else True
        checklist["Endpoints protegidos"] = auth_passed
        
        # Permisos consistentes
        perm_results = report.results.get("permissions", [])
        perms_passed = all(r.status == "passed" for r in perm_results) if perm_results else True
        checklist["Permisos consistentes"] = perms_passed
        
        # Containers corriendo
        infra_results = report.results.get("infra", [])
        docker_passed = any(
            r.check_name == "Docker Status" and r.status == "passed" 
            for r in infra_results
        )
        checklist["Containers operativos"] = docker_passed
        
        # Odoo accesible
        odoo_results = report.results.get("odoo_integrity", [])
        odoo_passed = any(r.status == "passed" for r in odoo_results) if odoo_results else True
        checklist["Odoo conectividad"] = odoo_passed
        
        return checklist
    
    def _generate_recommendations(self, report: ScanReport) -> List[Dict[str, Any]]:
        """Genera recomendaciones accionables"""
        recommendations = []
        
        # Agrupar findings por prioridad
        p0_findings = []
        p1_findings = []
        
        for findings_list in report.results.values():
            for check in findings_list:
                for finding in check.findings:
                    priority = finding.priority or "P2"
                    if priority == "P0":
                        p0_findings.append(finding)
                    elif priority == "P1":
                        p1_findings.append(finding)
        
        # P0: Críticos
        if p0_findings:
            recommendations.append({
                "priority": "P0",
                "title": "Resolver hallazgos críticos",
                "description": f"Hay {len(p0_findings)} problemas críticos que deben resolverse antes de deploy:\n" +
                              "\n".join([f"- {f.title}" for f in p0_findings[:5]])
            })
        
        # P1: Importantes
        if p1_findings:
            recommendations.append({
                "priority": "P1",
                "title": "Revisar hallazgos importantes",
                "description": f"{len(p1_findings)} problemas importantes a revisar:\n" +
                              "\n".join([f"- {f.title}" for f in p1_findings[:5]])
            })
        
        # Recomendación de herramientas faltantes
        skipped = []
        for check_list in report.results.values():
            for check in check_list:
                if check.status == "skipped":
                    skipped.append(check.check_name)
        
        if skipped:
            recommendations.append({
                "priority": "P2",
                "title": "Instalar herramientas faltantes",
                "description": f"Los siguientes checks fueron omitidos por herramientas no instaladas: {', '.join(skipped)}"
            })
        
        return recommendations
    
    async def _run_ai_analysis(
        self,
        report: ScanReport,
        environment: str
    ) -> Optional[AIAnalysisResult]:
        """
        Ejecuta análisis de IA v3.0.
        
        Args:
            report: Reporte de scan completado
            environment: Entorno del scan
        
        Returns:
            AIAnalysisResult o None si IA está deshabilitada
        """
        config = get_ai_config()
        
        if not config.ai_enabled:
            self._log(report, "AI analysis: disabled")
            return AIAnalysisResult(
                enabled=False,
                skipped_reason="AI analysis disabled in configuration"
            )
        
        try:
            self._log(report, "AI analysis: starting...")
            start_time = time.time()
            
            # Construir EvidencePack
            builder = get_evidence_builder()
            commit_sha = report.metadata.git_info.commit_sha if report.metadata.git_info else None
            
            evidence = builder.build(
                scan_report=report,
                environment=environment,
                commit_sha=commit_sha
            )
            
            # Llamar AI Gateway
            gateway = get_ai_gateway()
            
            ai_response = await gateway.analyze(
                evidence=evidence,
                analysis_mode="basic"  # Could be configurable
            )
            
            analysis_ms = int((time.time() - start_time) * 1000)
            
            # Construir resultado
            if ai_response.get("skipped"):
                result = AIAnalysisResult(
                    enabled=True,
                    skipped_reason=ai_response.get("reason")
                )
                self._log(report, f"AI analysis: skipped - {ai_response.get('reason')}")
            elif ai_response.get("error"):
                result = AIAnalysisResult(
                    enabled=True,
                    engine_used=ai_response.get("engine_used"),
                    analysis_ms=analysis_ms,
                    error=str(ai_response.get("error"))
                )
                self._log(report, f"AI analysis: error - {ai_response.get('error')}", "warning")
            else:
                result = AIAnalysisResult.from_gateway_response({
                    **ai_response,
                    "analysis_ms": analysis_ms
                })
                engine = ai_response.get("engine_used", "unknown")
                cached = "cached" if ai_response.get("cached") else "fresh"
                self._log(report, f"AI analysis: completed ({engine}, {cached}, {analysis_ms}ms)")
            
            return result
            
        except Exception as e:
            logger.exception(f"AI analysis error: {e}")
            self._log(report, f"AI analysis: error - {str(e)[:50]}", "error")
            return AIAnalysisResult(
                enabled=True,
                error=str(e)
            )
    
    def cancel(self):
        """Cancela el scan actual"""
        self._cancelled = True
    
    def get_current_progress(self) -> Optional[ScanProgress]:
        """Obtiene el progreso del scan actual"""
        if self._current_scan and self._current_scan.progress:
            return self._current_scan.progress
        return None


# Jobs background (usando asyncio tasks)
_active_scans: Dict[str, asyncio.Task] = {}


async def start_scan_job(
    scan_type: ScanType,
    environment: str = "dev",
    triggered_by: Optional[str] = None,
    specific_checks: Optional[List[str]] = None
) -> str:
    """
    Inicia un scan en background y retorna el scan_id.
    """
    runner = ScanRunner()
    
    # Crear scan inicial para obtener ID
    from .models import ScanMetadata
    import uuid
    scan_id = str(uuid.uuid4())[:8]
    
    async def run_task():
        try:
            await runner.run_scan(
                scan_type=scan_type,
                environment=environment,
                triggered_by=triggered_by,
                specific_checks=specific_checks
            )
        except Exception as e:
            logger.exception(f"Error en scan job {scan_id}: {e}")
        finally:
            if scan_id in _active_scans:
                del _active_scans[scan_id]
    
    task = asyncio.create_task(run_task())
    _active_scans[scan_id] = task
    
    return scan_id


def get_active_scans() -> List[str]:
    """Retorna IDs de scans activos"""
    return list(_active_scans.keys())


def cancel_scan(scan_id: str) -> bool:
    """Cancela un scan activo"""
    if scan_id in _active_scans:
        _active_scans[scan_id].cancel()
        return True
    return False
