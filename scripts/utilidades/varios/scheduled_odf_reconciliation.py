"""
Scheduled Job: Reconciliación Diaria de ODFs
=============================================

Este script debe ejecutarse diariamente (ej: 18:00 hrs) para
reconciliar automáticamente las ODFs del día.

Uso:
    python scripts/scheduled_odf_reconciliation.py

Variables de entorno requeridas:
    ODOO_USERNAME
    ODOO_PASSWORD
"""

import sys
import os
from datetime import datetime, timedelta
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.odf_reconciliation_service import ODFReconciliationService
from shared.odoo_client import OdooClient

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/odf_reconciliation.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def reconciliar_odfs_diario():
    """
    Reconcilia ODFs del día actual.
    """
    logger.info("=" * 80)
    logger.info("INICIO: Reconciliación Diaria de ODFs")
    logger.info("=" * 80)
    
    # Obtener credenciales
    username = os.getenv('ODOO_USERNAME')
    password = os.getenv('ODOO_PASSWORD')
    
    if not username or not password:
        logger.error("Faltan credenciales: ODOO_USERNAME y/o ODOO_PASSWORD")
        return
    
    # Conectar a Odoo
    logger.info(f"Conectando a Odoo con usuario: {username}")
    odoo = OdooClient()
    
    try:
        odoo.authenticate(username, password)
        logger.info(f"Conectado exitosamente (UID: {odoo.uid})")
    except Exception as e:
        logger.error(f"Error de conexión: {e}")
        return
    
    # Crear servicio
    service = ODFReconciliationService(odoo)
    
    # Calcular rango de fechas (últimos 7 días para cubrir rezagos)
    hoy = datetime.now().date()
    hace_7_dias = hoy - timedelta(days=7)
    
    fecha_inicio = hace_7_dias.isoformat()
    fecha_fin = hoy.isoformat()
    
    logger.info(f"Rango de fechas: {fecha_inicio} a {fecha_fin}")
    
    # Ejecutar reconciliación
    try:
        resultado = service.reconciliar_odfs_por_fecha(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            dry_run=False  # Escribir a Odoo
        )
        
        logger.info("=" * 80)
        logger.info("RESULTADOS:")
        logger.info("=" * 80)
        logger.info(f"Total ODFs encontradas: {resultado['total_odfs']}")
        logger.info(f"ODFs reconciliadas: {resultado['odfs_reconciliadas']}")
        logger.info(f"ODFs sin PO: {resultado['odfs_sin_po']}")
        logger.info(f"ODFs con error: {resultado['odfs_error']}")
        
        # Log detallado de errores
        if resultado['odfs_error'] > 0:
            logger.warning("\nODFs con errores:")
            for res in resultado['resultados']:
                if res.get('error'):
                    logger.warning(f"  - {res.get('odf_name', 'N/A')} (ID: {res.get('odf_id')}): {res['error']}")
        
        # Log de ODFs sin PO
        if resultado['odfs_sin_po'] > 0:
            logger.info("\nODFs sin PO asociada:")
            for res in resultado['resultados']:
                if not res.get('pos_asociadas'):
                    logger.info(f"  - {res.get('odf_name', 'N/A')} (ID: {res.get('odf_id')})")
        
        logger.info("=" * 80)
        logger.info("FIN: Reconciliación completada exitosamente")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Error durante reconciliación: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    # Crear directorio de logs si no existe
    os.makedirs('logs', exist_ok=True)
    
    reconciliar_odfs_diario()
