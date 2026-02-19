"""
BUENOBOT - Storage

Persistencia de scans y reportes en disco (JSON).
Diseñado para ser simple y sin dependencias externas.
"""
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from filelock import FileLock

from .models import (
    ScanReport, 
    ScanListItem, 
    ScanStatus, 
    GateStatus,
    ScanMetadata,
    ScanType
)

logger = logging.getLogger(__name__)


class BuenoBotStorage:
    """
    Almacenamiento persistente para scans de BUENOBOT.
    
    Estructura de archivos:
    /app/data/buenobot/
        scans/
            {scan_id}.json          # Reporte completo
        index.json                   # Índice de scans (para listado rápido)
        config.json                  # Configuración
    """
    
    def __init__(self, base_path: str = "/app/data/buenobot"):
        self.base_path = Path(base_path)
        self.scans_path = self.base_path / "scans"
        self.index_path = self.base_path / "index.json"
        self.config_path = self.base_path / "config.json"
        self.lock_path = self.base_path / ".lock"
        
        # Crear directorios si no existen
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Crea la estructura de directorios"""
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.scans_path.mkdir(exist_ok=True)
        
        # Crear index si no existe
        if not self.index_path.exists():
            self._write_json(self.index_path, {"scans": []})
        
        # Crear config si no existe
        if not self.config_path.exists():
            self._write_json(self.config_path, {
                "max_scans_history": 100,
                "created_at": datetime.utcnow().isoformat()
            })
    
    def _write_json(self, path: Path, data: Dict[str, Any]):
        """Escribe JSON de forma segura con lock"""
        with FileLock(str(self.lock_path)):
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
    
    def _read_json(self, path: Path) -> Dict[str, Any]:
        """Lee JSON de forma segura"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON: {path}")
            return {}
    
    def save_scan(self, report: ScanReport) -> str:
        """
        Guarda un reporte de scan completo.
        
        Returns:
            scan_id del reporte guardado
        """
        scan_id = report.metadata.scan_id
        scan_path = self.scans_path / f"{scan_id}.json"
        
        # Guardar reporte completo
        self._write_json(scan_path, report.model_dump())
        
        # Actualizar índice
        self._update_index(report)
        
        logger.info(f"Scan {scan_id} guardado en {scan_path}")
        return scan_id
    
    def _update_index(self, report: ScanReport):
        """Actualiza el índice de scans"""
        with FileLock(str(self.lock_path)):
            index = self._read_json(self.index_path)
            scans = index.get("scans", [])
            
            # Crear entrada de índice
            entry = {
                "scan_id": report.metadata.scan_id,
                "scan_type": report.metadata.scan_type.value if isinstance(report.metadata.scan_type, ScanType) else report.metadata.scan_type,
                "environment": report.metadata.environment,
                "status": report.status.value if isinstance(report.status, ScanStatus) else report.status,
                "gate_status": report.gate_status.value if isinstance(report.gate_status, GateStatus) else report.gate_status,
                "created_at": report.metadata.created_at.isoformat() if isinstance(report.metadata.created_at, datetime) else report.metadata.created_at,
                "completed_at": report.metadata.completed_at.isoformat() if report.metadata.completed_at else None,
                "duration_seconds": report.duration_seconds,
                "commit_sha": report.metadata.git_info.commit_sha if report.metadata.git_info else None,
                "triggered_by": report.metadata.triggered_by,
                "summary": f"{report.passed_checks}/{report.total_checks} checks passed"
            }
            
            # Remover entrada anterior si existe
            scans = [s for s in scans if s.get("scan_id") != entry["scan_id"]]
            
            # Agregar nueva entrada al inicio
            scans.insert(0, entry)
            
            # Limitar historial
            config = self._read_json(self.config_path)
            max_history = config.get("max_scans_history", 100)
            scans = scans[:max_history]
            
            index["scans"] = scans
            self._write_json(self.index_path, index)
    
    def get_scan(self, scan_id: str) -> Optional[ScanReport]:
        """Obtiene un reporte de scan por ID"""
        scan_path = self.scans_path / f"{scan_id}.json"
        
        if not scan_path.exists():
            return None
        
        data = self._read_json(scan_path)
        if not data:
            return None
        
        try:
            return ScanReport.model_validate(data)
        except Exception as e:
            logger.error(f"Error parsing scan {scan_id}: {e}")
            return None
    
    def get_scan_raw(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene un reporte de scan como dict (sin validar)"""
        scan_path = self.scans_path / f"{scan_id}.json"
        
        if not scan_path.exists():
            return None
        
        return self._read_json(scan_path)
    
    def update_scan(self, scan_id: str, updates: Dict[str, Any]) -> bool:
        """
        Actualiza campos de un scan existente.
        Útil para actualizar progreso durante ejecución.
        """
        scan_path = self.scans_path / f"{scan_id}.json"
        
        if not scan_path.exists():
            return False
        
        with FileLock(str(self.lock_path)):
            data = self._read_json(scan_path)
            
            # Merge updates
            for key, value in updates.items():
                if isinstance(value, dict) and key in data and isinstance(data[key], dict):
                    data[key].update(value)
                else:
                    data[key] = value
            
            self._write_json(scan_path, data)
        
        return True
    
    def list_scans(
        self,
        limit: int = 20,
        offset: int = 0,
        environment: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[ScanListItem]:
        """Lista scans con filtros opcionales"""
        index = self._read_json(self.index_path)
        scans = index.get("scans", [])
        
        # Aplicar filtros
        if environment:
            scans = [s for s in scans if s.get("environment") == environment]
        if status:
            scans = [s for s in scans if s.get("status") == status]
        
        # Paginación
        scans = scans[offset:offset + limit]
        
        # Convertir a modelo
        result = []
        for s in scans:
            try:
                result.append(ScanListItem(
                    scan_id=s["scan_id"],
                    scan_type=ScanType(s.get("scan_type", "quick")),
                    environment=s.get("environment", "dev"),
                    status=ScanStatus(s.get("status", "done")),
                    gate_status=GateStatus(s.get("gate_status", "pass")),
                    created_at=datetime.fromisoformat(s["created_at"]) if isinstance(s.get("created_at"), str) else s.get("created_at", datetime.utcnow()),
                    completed_at=datetime.fromisoformat(s["completed_at"]) if s.get("completed_at") and isinstance(s["completed_at"], str) else None,
                    duration_seconds=s.get("duration_seconds"),
                    commit_sha=s.get("commit_sha"),
                    triggered_by=s.get("triggered_by"),
                    summary=s.get("summary", "")
                ))
            except Exception as e:
                logger.warning(f"Error parsing scan entry: {e}")
                continue
        
        return result
    
    def get_last_scan(self, environment: Optional[str] = None) -> Optional[ScanReport]:
        """Obtiene el último scan completado"""
        scans = self.list_scans(limit=1, environment=environment)
        if scans:
            return self.get_scan(scans[0].scan_id)
        return None
    
    def delete_scan(self, scan_id: str) -> bool:
        """Elimina un scan del historial"""
        scan_path = self.scans_path / f"{scan_id}.json"
        
        if scan_path.exists():
            scan_path.unlink()
        
        # Actualizar índice
        with FileLock(str(self.lock_path)):
            index = self._read_json(self.index_path)
            scans = index.get("scans", [])
            scans = [s for s in scans if s.get("scan_id") != scan_id]
            index["scans"] = scans
            self._write_json(self.index_path, index)
        
        return True
    
    def export_report_markdown(self, scan_id: str) -> Optional[str]:
        """Genera reporte en formato Markdown"""
        report = self.get_scan(scan_id)
        if not report:
            return None
        
        md = []
        md.append(f"# BUENOBOT Scan Report")
        md.append(f"")
        md.append(f"## Resumen Ejecutivo")
        md.append(f"")
        md.append(f"| Campo | Valor |")
        md.append(f"|-------|-------|")
        md.append(f"| **Scan ID** | `{report.metadata.scan_id}` |")
        md.append(f"| **Tipo** | {report.metadata.scan_type.value if hasattr(report.metadata.scan_type, 'value') else report.metadata.scan_type} |")
        md.append(f"| **Entorno** | {report.metadata.environment} |")
        md.append(f"| **Fecha** | {report.metadata.created_at} |")
        md.append(f"| **Duración** | {report.duration_seconds:.1f}s |")
        if report.metadata.git_info:
            md.append(f"| **Commit** | `{report.metadata.git_info.commit_sha[:8]}` |")
            md.append(f"| **Branch** | {report.metadata.git_info.branch} |")
        md.append(f"")
        
        # Gate Status con emoji
        gate_emoji = {"pass": "✅", "warn": "⚠️", "fail": "❌"}.get(
            report.gate_status.value if hasattr(report.gate_status, 'value') else report.gate_status, 
            "❓"
        )
        md.append(f"## Gate Status: {gate_emoji} {report.gate_status.value.upper() if hasattr(report.gate_status, 'value') else str(report.gate_status).upper()}")
        md.append(f"")
        md.append(f"**Razón:** {report.gate_reason}")
        md.append(f"")
        
        # Stats
        md.append(f"## Estadísticas")
        md.append(f"")
        md.append(f"- **Checks totales:** {report.total_checks}")
        md.append(f"- **Pasados:** {report.passed_checks}")
        md.append(f"- **Fallidos:** {report.failed_checks}")
        md.append(f"- **Warnings:** {report.warning_checks}")
        md.append(f"")
        
        # Top Findings
        if report.top_findings:
            md.append(f"## Top Hallazgos")
            md.append(f"")
            for i, finding in enumerate(report.top_findings[:5], 1):
                severity_emoji = {
                    "critical": "🔴",
                    "high": "🟠", 
                    "medium": "🟡",
                    "low": "🔵",
                    "info": "⚪"
                }.get(finding.severity.value if hasattr(finding.severity, 'value') else finding.severity, "⚪")
                md.append(f"{i}. {severity_emoji} **{finding.title}**")
                md.append(f"   - {finding.description}")
                if finding.location:
                    md.append(f"   - Ubicación: `{finding.location}`")
                if finding.recommendation:
                    md.append(f"   - Recomendación: {finding.recommendation}")
                md.append(f"")
        
        # Resultados por categoría
        md.append(f"## Resultados por Categoría")
        md.append(f"")
        
        for category, checks in report.results.items():
            md.append(f"### {category.replace('_', ' ').title()}")
            md.append(f"")
            
            for check in checks:
                status_emoji = "✅" if check.status == "passed" else "❌" if check.status == "failed" else "⚠️"
                md.append(f"#### {status_emoji} {check.check_name}")
                md.append(f"")
                md.append(f"- **Estado:** {check.status}")
                md.append(f"- **Duración:** {check.duration_ms}ms")
                
                if check.summary:
                    md.append(f"- **Resumen:** {check.summary}")
                
                if check.findings:
                    md.append(f"- **Hallazgos:** {len(check.findings)}")
                    for finding in check.findings[:3]:  # Limitar a 3 por check
                        md.append(f"  - {finding.title}: {finding.description}")
                
                md.append(f"")
        
        # Checklist Go/No-Go
        if report.checklist:
            md.append(f"## Checklist Go/No-Go")
            md.append(f"")
            for item, passed in report.checklist.items():
                emoji = "✅" if passed else "❌"
                md.append(f"- {emoji} {item}")
            md.append(f"")
        
        # Recomendaciones
        if report.recommendations:
            md.append(f"## Recomendaciones")
            md.append(f"")
            for rec in report.recommendations:
                priority = rec.get("priority", "P2")
                md.append(f"### [{priority}] {rec.get('title', 'Sin título')}")
                md.append(f"")
                md.append(rec.get("description", ""))
                md.append(f"")
        
        md.append(f"---")
        md.append(f"*Generado por BUENOBOT v1.0.0*")
        
        return "\n".join(md)


# Singleton
_storage_instance: Optional[BuenoBotStorage] = None


def get_storage() -> BuenoBotStorage:
    """Obtiene instancia singleton del storage"""
    global _storage_instance
    if _storage_instance is None:
        # Determinar base path según entorno
        import os
        base_path = os.environ.get("BUENOBOT_DATA_PATH", "/app/data/buenobot")
        _storage_instance = BuenoBotStorage(base_path)
    return _storage_instance
