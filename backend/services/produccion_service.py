"""
Servicio de Producción - Lógica de negocio para órdenes de fabricación
"""
from typing import Optional, Dict, List, Any
from datetime import datetime
import pandas as pd

from shared.odoo_client import OdooClient


class ProduccionService:
    """
    Servicio para manejar datos de producción desde Odoo.
    """
    
    def __init__(self, username: str = None, password: str = None):
        self.odoo = OdooClient(username=username, password=password)
    
    def get_ordenes_fabricacion(
        self, 
        estado: Optional[str] = None,
        fecha_desde: Optional[str] = None,
        fecha_hasta: Optional[str] = None
    ) -> List[Dict]:
        """
        Obtiene las órdenes de fabricación (mrp.production).
        """
        domain = []
        
        if estado:
            domain.append(['state', '=', estado])
        if fecha_desde:
            domain.append(['date_start', '>=', fecha_desde])
        if fecha_hasta:
            domain.append(['date_start', '<=', fecha_hasta])
        
        fields = [
            'name', 'product_id', 'product_qty', 'qty_produced',
            'state', 'date_start', 'date_finished', 'origin',
            'user_id', 'company_id'
        ]
        
        ordenes = self.odoo.search_read(
            'mrp.production',
            domain=domain,
            fields=fields,
            limit=1000,
            order='date_start desc'
        )
        
        # Procesar datos
        for orden in ordenes:
            # Convertir many2one a nombres
            if orden.get('product_id'):
                orden['product_name'] = orden['product_id'][1]
                orden['product_id'] = orden['product_id'][0]
            if orden.get('user_id'):
                orden['user_name'] = orden['user_id'][1]
                orden['user_id'] = orden['user_id'][0]
        
        return ordenes
    
    def get_kpis(self) -> Dict[str, Any]:
        """
        Calcula KPIs de producción.
        """
        # Contar por estado
        estados = ['draft', 'confirmed', 'progress', 'to_close', 'done']
        kpis = {}
        
        for estado in estados:
            count = len(self.odoo.search('mrp.production', [['state', '=', estado]]))
            kpis[f'ordenes_{estado}'] = count
        
        # Total de órdenes
        kpis['total_ordenes'] = sum(kpis.values())
        
        # Órdenes activas (confirmadas + en progreso)
        kpis['ordenes_activas'] = kpis.get('ordenes_confirmed', 0) + kpis.get('ordenes_progress', 0)
        
        return kpis
    
    def get_resumen(self) -> Dict[str, Any]:
        """
        Obtiene un resumen general de producción.
        """
        # Órdenes de hoy
        hoy = datetime.now().strftime('%Y-%m-%d')
        ordenes_hoy = self.odoo.search_read(
            'mrp.production',
            domain=[['date_start', '>=', f'{hoy} 00:00:00'], ['date_start', '<=', f'{hoy} 23:59:59']],
            fields=['name', 'state', 'product_qty']
        )
        
        return {
            'fecha': hoy,
            'ordenes_hoy': len(ordenes_hoy),
            'kpis': self.get_kpis()
        }
