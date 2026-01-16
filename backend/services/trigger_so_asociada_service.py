"""
Servicio para triggear la automatización de Odoo que carga SO Asociada.

Cuando un ODF tiene x_studio_po_cliente_1 lleno pero no tiene x_studio_po_asociada,
este servicio borra y reescribe el campo PO Cliente para activar la automatización.
"""

from typing import List, Dict, Any, Optional
import time
import logging

logger = logging.getLogger(__name__)


class TriggerSOAsociadaService:
    """Servicio para triggear automatización de SO Asociada en ODFs."""
    
    def __init__(self, odoo_client):
        """
        Inicializa el servicio.
        
        Args:
            odoo_client: Cliente de Odoo ya autenticado
        """
        self.odoo = odoo_client
    
    def get_todas_odfs(
        self,
        limit: Optional[int] = None,
        estados: List[str] = None,
        fecha_inicio: Optional[str] = None,
        fecha_fin: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene TODAS las ODFs del periodo (con o sin SO Asociada).
        
        Args:
            limit: Límite de registros (None = sin límite)
            estados: Lista de estados a filtrar (default: ['confirmed', 'progress', 'to_close'])
            fecha_inicio: Fecha inicio filtro (YYYY-MM-DD)
            fecha_fin: Fecha fin filtro (YYYY-MM-DD)
            
        Returns:
            Lista de diccionarios con información de todas las ODFs
        """
        if estados is None:
            estados = ['confirmed', 'progress', 'to_close']
        
        # Buscar TODAS las ODFs que tengan PO Cliente (con o sin SO Asociada)
        domain = [
            ('x_studio_po_cliente_1', '!=', False),
            ('x_studio_po_cliente_1', '!=', ''),
            ('state', 'in', estados)
        ]
        
        # Agregar filtro de fechas si se especifica
        if fecha_inicio:
            domain.append(('date_planned_start', '>=', f'{fecha_inicio} 00:00:00'))
        if fecha_fin:
            domain.append(('date_planned_start', '<=', f'{fecha_fin} 23:59:59'))
        
        fields = [
            'name',
            'product_id',
            'x_studio_po_cliente_1',
            'x_studio_po_asociada',
            'state',
            'date_planned_start'
        ]
        
        # Buscar IDs primero
        odf_ids = self.odoo.search(
            'mrp.production',
            domain,
            limit=limit,
            order='date_planned_start desc'
        )
        
        if not odf_ids:
            logger.info("No se encontraron ODFs en el periodo")
            return []
        
        # Leer los datos
        odfs = self.odoo.read('mrp.production', odf_ids, fields)
        
        logger.info(f"Se encontraron {len(odfs)} ODFs en el periodo")
        
        return odfs
    
    def get_odfs_pendientes(
        self, 
        limit: Optional[int] = None,
        estados: List[str] = None,
        fecha_inicio: Optional[str] = None,
        fecha_fin: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene ODFs que tienen PO Cliente pero no SO Asociada.
        
        Args:
            limit: Límite de registros (None = sin límite)
            estados: Lista de estados a filtrar (default: ['confirmed', 'progress', 'to_close'])
            fecha_inicio: Fecha inicio filtro (YYYY-MM-DD)
            fecha_fin: Fecha fin filtro (YYYY-MM-DD)
            
        Returns:
            Lista de diccionarios con información de ODFs pendientes
        """
        if estados is None:
            estados = ['confirmed', 'progress', 'to_close']
        
        # Buscar ODFs con PO Cliente lleno pero SO Asociada vacía
        domain = [
            ('x_studio_po_cliente_1', '!=', False),
            ('x_studio_po_cliente_1', '!=', ''),
            '|',
            ('x_studio_po_asociada', '=', False),
            ('x_studio_po_asociada', '=', ''),
            ('state', 'in', estados)
        ]
        
        # Agregar filtro de fechas si se especifica
        if fecha_inicio:
            domain.append(('date_planned_start', '>=', f'{fecha_inicio} 00:00:00'))
        if fecha_fin:
            domain.append(('date_planned_start', '<=', f'{fecha_fin} 23:59:59'))
        
        fields = [
            'name',
            'product_id',
            'x_studio_po_cliente_1',
            'x_studio_po_asociada',
            'state',
            'date_planned_start'
        ]
        
        # Buscar IDs primero
        odf_ids = self.odoo.search(
            'mrp.production',
            domain,
            limit=limit,
            order='date_planned_start desc'
        )
        
        if not odf_ids:
            logger.info("No se encontraron ODFs pendientes de cargar SO Asociada")
            return []
        
        # Leer los datos
        odfs = self.odoo.read('mrp.production', odf_ids, fields)
        
        logger.info(f"Se encontraron {len(odfs)} ODFs pendientes de cargar SO Asociada")
        
        return odfs
    
    def trigger_so_asociada(
        self, 
        odf_id: int,
        wait_seconds: float = 2.0
    ) -> Dict[str, Any]:
        """
        Triggea la automatización de SO Asociada para un ODF.
        
        Proceso:
        1. Lee el valor actual de PO Cliente
        2. Borra el campo (escribe False)
        3. Espera para que Odoo procese
        4. Reescribe el valor original
        5. Espera nuevamente
        6. Verifica que SO Asociada se haya cargado
        
        Args:
            odf_id: ID del ODF (mrp.production)
            wait_seconds: Segundos a esperar entre operaciones
            
        Returns:
            Diccionario con resultado de la operación
        """
        try:
            # 1. Leer valor actual de PO Cliente
            odf = self.odoo.read(
                'mrp.production',
                [odf_id],
                ['name', 'x_studio_po_cliente_1', 'x_studio_po_asociada']
            )
            
            if not odf:
                return {
                    'success': False,
                    'odf_id': odf_id,
                    'error': 'ODF no encontrado'
                }
            
            odf = odf[0]
            po_cliente = odf.get('x_studio_po_cliente_1')
            
            if not po_cliente:
                return {
                    'success': False,
                    'odf_id': odf_id,
                    'odf_name': odf.get('name'),
                    'error': 'ODF no tiene PO Cliente'
                }
            
            logger.info(f"Procesando ODF {odf.get('name')} - PO Cliente: {po_cliente}")
            
            # 2. Borrar el campo PO Cliente
            self.odoo.write(
                'mrp.production',
                [odf_id],
                {'x_studio_po_cliente_1': False}
            )
            logger.info(f"  → Campo PO Cliente borrado")
            
            # 3. Esperar para que Odoo procese
            time.sleep(wait_seconds)
            
            # 4. Reescribir el valor original
            self.odoo.write(
                'mrp.production',
                [odf_id],
                {'x_studio_po_cliente_1': po_cliente}
            )
            logger.info(f"  → Campo PO Cliente reescrito: {po_cliente}")
            
            # 5. Esperar para que la automatización corra
            time.sleep(wait_seconds)
            
            # 6. Verificar que SO Asociada se haya cargado
            odf_updated = self.odoo.read(
                'mrp.production',
                [odf_id],
                ['x_studio_po_asociada']
            )[0]
            
            so_asociada = odf_updated.get('x_studio_po_asociada')
            
            if so_asociada:
                logger.info(f"  ✓ SO Asociada cargada exitosamente: {so_asociada}")
                return {
                    'success': True,
                    'odf_id': odf_id,
                    'odf_name': odf.get('name'),
                    'po_cliente': po_cliente,
                    'so_asociada': so_asociada
                }
            else:
                logger.warning(f"  ✗ SO Asociada no se cargó automáticamente")
                return {
                    'success': False,
                    'odf_id': odf_id,
                    'odf_name': odf.get('name'),
                    'po_cliente': po_cliente,
                    'error': 'La automatización no cargó SO Asociada (posiblemente no existe SO con ese origen)'
                }
                
        except Exception as e:
            logger.error(f"Error procesando ODF {odf_id}: {str(e)}")
            return {
                'success': False,
                'odf_id': odf_id,
                'error': str(e)
            }
    
    def trigger_bulk(
        self,
        odf_ids: Optional[List[int]] = None,
        limit: Optional[int] = None,
        wait_seconds: float = 2.0,
        fecha_inicio: Optional[str] = None,
        fecha_fin: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Triggea la automatización para múltiples ODFs.
        
        Args:
            odf_ids: Lista de IDs de ODFs (si None, usa get_odfs_pendientes)
            limit: Límite de registros a procesar
            wait_seconds: Segundos a esperar entre operaciones por ODF
            fecha_inicio: Fecha inicio filtro (YYYY-MM-DD)
            fecha_fin: Fecha fin filtro (YYYY-MM-DD)
            
        Returns:
            Diccionario con resumen de la operación
        """
        # Si no se especifican IDs, buscar ODFs pendientes
        if odf_ids is None:
            odfs_pendientes = self.get_odfs_pendientes(
                limit=limit,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin
            )
            odf_ids = [odf['id'] for odf in odfs_pendientes]
        
        if not odf_ids:
            return {
                'total': 0,
                'exitosos': 0,
                'fallidos': 0,
                'resultados': []
            }
        
        logger.info(f"Iniciando procesamiento bulk de {len(odf_ids)} ODFs")
        
        resultados = []
        exitosos = 0
        fallidos = 0
        
        for odf_id in odf_ids:
            resultado = self.trigger_so_asociada(odf_id, wait_seconds)
            resultados.append(resultado)
            
            if resultado['success']:
                exitosos += 1
            else:
                fallidos += 1
        
        resumen = {
            'total': len(odf_ids),
            'exitosos': exitosos,
            'fallidos': fallidos,
            'resultados': resultados
        }
        
        logger.info(f"Procesamiento bulk completado: {exitosos} exitosos, {fallidos} fallidos")
        
        return resumen
