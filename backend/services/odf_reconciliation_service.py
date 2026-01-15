"""
Servicio de Reconciliación de ODFs con Sale Orders
===================================================

RESPONSABILIDAD:
- Leer x_studio_po_asociada (ej: "S00843, S00912")
- Parsear las SOs asociadas
- Reconciliar subproductos de ODF con productos de SOs
- Calcular KG Totales, Consumidos y Disponibles
- ESCRIBIR de vuelta a Odoo

ALGORITMO:
1. Parsear campo x_studio_po_asociada
2. Leer sale.order.line de cada SO
3. Leer subproductos (stock.move con location_dest=internal)
4. Match productos: subproducto.product_id == so_line.product_id
5. Prorrateo: qty_done / qty_ordered
6. Escribir campos x_studio_kg_*
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re


class ODFReconciliationService:
    """
    Servicio para reconciliar ODFs con sus Sale Orders asociadas.
    Calcula y actualiza campos de seguimiento en Odoo.
    """
    
    def __init__(self, odoo_client):
        """
        Args:
            odoo_client: Cliente configurado de Odoo (shared.odoo_client)
        """
        self.odoo = odoo_client
    
    # ========================================
    # PARSEO DE SALE ORDERS ASOCIADAS
    # ========================================
    
    def parse_pos_asociadas(self, po_asociada_str: Optional[str]) -> List[str]:
        """
        Parsea el campo x_studio_po_asociada que puede contener múltiples SOs.
        
        Formatos válidos:
        - "S00843"
        - "S00843, S00912"
        - "S00843,S00912,S00915"
        
        Returns:
            Lista de nombres de SO: ['S00843', 'S00912']
        """
        if not po_asociada_str:
            return []
        
        # Limpiar y separar por comas
        pos = [po.strip() for po in po_asociada_str.split(',')]
        
        # Filtrar vacíos
        return [po for po in pos if po]
    
    # ========================================
    # LECTURA DE SALE ORDERS Y SUS LÍNEAS
    # ========================================
    
    def get_so_lines(self, so_names: List[str]) -> Dict[int, Dict]:
        """
        Obtiene todas las líneas de las Sale Orders especificadas.
        
        Args:
            so_names: Lista de nombres de SO (ej: ['S00843', 'S00912'])
        
        Returns:
            Dict con estructura:
            {
                product_id: {
                    'producto_nombre': str,
                    'cantidad_total': float,  # Suma de todas las SOs
                    'so_details': [
                        {
                            'so_name': str,
                            'so_id': int,
                            'cantidad': float,
                            'entregado': float
                        }
                    ]
                }
            }
        """
        if not so_names:
            return {}
        
        # Buscar las Sale Orders
        sale_orders = self.odoo.search_read(
            'sale.order',
            [['name', 'in', so_names]],
            ['id', 'name', 'partner_id', 'state']
        )
        
        if not sale_orders:
            return {}
        
        so_ids = [so['id'] for so in sale_orders]
        so_by_id = {so['id']: so for so in sale_orders}
        
        # Leer líneas de todas las SOs
        so_lines = self.odoo.search_read(
            'sale.order.line',
            [['order_id', 'in', so_ids]],
            ['id', 'order_id', 'product_id', 'product_uom_qty', 'qty_delivered']
        )
        
        # Agrupar por producto
        productos_dict = {}
        
        for line in so_lines:
            product_id = line['product_id'][0] if line.get('product_id') else None
            product_name = line['product_id'][1] if line.get('product_id') else 'Desconocido'
            
            if not product_id:
                continue
            
            cantidad = line.get('product_uom_qty', 0)
            entregado = line.get('qty_delivered', 0)
            so_id = line['order_id'][0] if line.get('order_id') else None
            so_name = so_by_id.get(so_id, {}).get('name', 'N/A') if so_id else 'N/A'
            
            if product_id not in productos_dict:
                productos_dict[product_id] = {
                    'producto_nombre': product_name,
                    'cantidad_total': 0,
                    'so_details': []
                }
            
            productos_dict[product_id]['cantidad_total'] += cantidad
            productos_dict[product_id]['so_details'].append({
                'so_name': so_name,
                'so_id': so_id,
                'cantidad': cantidad,
                'entregado': entregado
            })
        
        return productos_dict
    
    # ========================================
    # LECTURA DE SUBPRODUCTOS DE LA ODF
    # ========================================
    
    def get_subproductos_odf(self, odf_id: int) -> Dict[int, Dict]:
        """
        Obtiene los subproductos (finished products) de una ODF.
        
        Returns:
            Dict con estructura:
            {
                product_id: {
                    'producto_nombre': str,
                    'cantidad_planeada': float,
                    'cantidad_producida': float,
                    'state': str
                }
            }
        """
        # Leer stock.move con destino a inventario (productos terminados)
        finished_moves = self.odoo.search_read(
            'stock.move',
            [
                ['production_id', '=', odf_id],
                ['location_dest_id.usage', '=', 'internal']
            ],
            ['id', 'product_id', 'product_uom_qty', 'quantity_done', 'state']
        )
        
        subproductos = {}
        
        for move in finished_moves:
            product_id = move['product_id'][0] if move.get('product_id') else None
            product_name = move['product_id'][1] if move.get('product_id') else 'Desconocido'
            
            if not product_id:
                continue
            
            planeado = move.get('product_uom_qty', 0)
            producido = move.get('quantity_done', 0)
            state = move.get('state', 'unknown')
            
            # Acumular si hay múltiples moves del mismo producto
            if product_id in subproductos:
                subproductos[product_id]['cantidad_planeada'] += planeado
                subproductos[product_id]['cantidad_producida'] += producido
            else:
                subproductos[product_id] = {
                    'producto_nombre': product_name,
                    'cantidad_planeada': planeado,
                    'cantidad_producida': producido,
                    'state': state
                }
        
        return subproductos
    
    # ========================================
    # RECONCILIACIÓN Y CÁLCULO
    # ========================================
    
    def reconciliar_odf(self, odf_id: int, dry_run: bool = False) -> Dict:
        """
        Reconcilia una ODF con sus Sale Orders asociadas.
        Calcula KG totales, consumidos y disponibles.
        
        Args:
            odf_id: ID de la ODF
            dry_run: Si True, solo calcula sin escribir a Odoo
        
        Returns:
            {
                'odf_id': int,
                'odf_name': str,
                'pos_asociadas': [...],
                'kg_totales_po': float,
                'kg_consumidos_po': float,
                'kg_disponibles_po': float,
                'desglose_productos': [...],
                'actualizado': bool
            }
        """
        # 1. Leer ODF
        odf = self.odoo.search_read(
            'mrp.production',
            [['id', '=', odf_id]],
            ['id', 'name', 'x_studio_po_asociada', 'product_id', 'state']
        )
        
        if not odf:
            raise ValueError(f"ODF {odf_id} no encontrada")
        
        odf = odf[0]
        
        # 2. Parsear POs asociadas
        po_asociada_str = odf.get('x_studio_po_asociada')
        so_names = self.parse_pos_asociadas(po_asociada_str)
        
        if not so_names:
            return {
                'odf_id': odf_id,
                'odf_name': odf.get('name'),
                'pos_asociadas': [],
                'kg_totales_po': 0,
                'kg_consumidos_po': 0,
                'kg_disponibles_po': 0,
                'desglose_productos': [],
                'actualizado': False,
                'error': 'No hay POs asociadas'
            }
        
        # 3. Leer líneas de las SOs
        productos_so = self.get_so_lines(so_names)
        
        # 4. Leer subproductos de la ODF
        subproductos = self.get_subproductos_odf(odf_id)
        
        # 5. Reconciliar: match productos
        kg_totales = 0
        kg_consumidos = 0
        desglose = []
        
        for product_id, so_info in productos_so.items():
            cantidad_so = so_info['cantidad_total']
            kg_totales += cantidad_so
            
            # Buscar si este producto está en los subproductos
            if product_id in subproductos:
                cantidad_producida = subproductos[product_id]['cantidad_producida']
                kg_consumidos += cantidad_producida
                
                desglose.append({
                    'producto_id': product_id,
                    'producto_nombre': so_info['producto_nombre'],
                    'cantidad_so': cantidad_so,
                    'cantidad_producida': cantidad_producida,
                    'porcentaje_avance': (cantidad_producida / cantidad_so * 100) if cantidad_so > 0 else 0,
                    'estado': 'coincide'
                })
            else:
                # Producto en SO pero no producido aún
                desglose.append({
                    'producto_id': product_id,
                    'producto_nombre': so_info['producto_nombre'],
                    'cantidad_so': cantidad_so,
                    'cantidad_producida': 0,
                    'porcentaje_avance': 0,
                    'estado': 'pendiente'
                })
        
        kg_disponibles = kg_totales - kg_consumidos
        
        # 6. Escribir a Odoo (si no es dry_run)
        actualizado = False
        if not dry_run:
            try:
                self.odoo.models.execute_kw(
                    self.odoo.db, self.odoo.uid, self.odoo.password,
                    'mrp.production', 'write',
                    [[odf_id], {
                        'x_studio_kg_totales_po': kg_totales,
                        'x_studio_kg_consumidos_po': kg_consumidos,
                        'x_studio_kg_disponibles_po': kg_disponibles
                    }]
                )
                actualizado = True
            except Exception as e:
                print(f"Error escribiendo a Odoo: {e}")
        
        return {
            'odf_id': odf_id,
            'odf_name': odf.get('name'),
            'pos_asociadas': so_names,
            'kg_totales_po': round(kg_totales, 2),
            'kg_consumidos_po': round(kg_consumidos, 2),
            'kg_disponibles_po': round(kg_disponibles, 2),
            'desglose_productos': desglose,
            'actualizado': actualizado,
            'timestamp': datetime.now()
        }
    
    # ========================================
    # RECONCILIACIÓN MASIVA
    # ========================================
    
    def reconciliar_odfs_por_fecha(
        self, 
        fecha_inicio: str, 
        fecha_fin: str,
        dry_run: bool = False
    ) -> Dict:
        """
        Reconcilia todas las ODFs en un rango de fechas.
        
        Args:
            fecha_inicio: Formato 'YYYY-MM-DD'
            fecha_fin: Formato 'YYYY-MM-DD'
            dry_run: Si True, solo calcula sin escribir
        
        Returns:
            {
                'total_odfs': int,
                'odfs_reconciliadas': int,
                'odfs_sin_po': int,
                'odfs_error': int,
                'resultados': [...]
            }
        """
        # Buscar ODFs en el rango de fechas
        odfs = self.odoo.search_read(
            'mrp.production',
            [
                ['date_start', '>=', fecha_inicio],
                ['date_start', '<=', fecha_fin]
            ],
            ['id', 'name', 'x_studio_po_asociada']
        )
        
        total = len(odfs)
        reconciliadas = 0
        sin_po = 0
        con_error = 0
        resultados = []
        
        for odf in odfs:
            try:
                resultado = self.reconciliar_odf(odf['id'], dry_run=dry_run)
                
                if resultado.get('actualizado'):
                    reconciliadas += 1
                elif not resultado.get('pos_asociadas'):
                    sin_po += 1
                
                resultados.append(resultado)
                
            except Exception as e:
                con_error += 1
                resultados.append({
                    'odf_id': odf['id'],
                    'odf_name': odf.get('name'),
                    'error': str(e)
                })
        
        return {
            'total_odfs': total,
            'odfs_reconciliadas': reconciliadas,
            'odfs_sin_po': sin_po,
            'odfs_error': con_error,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'resultados': resultados,
            'timestamp': datetime.now()
        }
