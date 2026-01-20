"""
Servicio para análisis de producción y rendimientos
Calcula rendimiento PSP → PTT usando órdenes de fabricación
"""
from typing import Optional


class AnalisisProduccionService:
    """Servicio para análisis de rendimientos de producción."""
    
    def __init__(self, odoo):
        """
        Args:
            odoo: Cliente OdooClient configurado
        """
        self.odoo = odoo
    
    def get_analisis_produccion(self, fecha_desde: str, fecha_hasta: str):
        """
        Análisis de rendimientos de producción PSP → PTT.
        
        Args:
            fecha_desde: Fecha inicio (YYYY-MM-DD)
            fecha_hasta: Fecha fin (YYYY-MM-DD)
        
        Returns:
            dict con:
                - resumen: totales de consumo MP y producción PT
                - rendimientos: por tipo de fruta
                - ordenes: detalle de órdenes de producción
                - merma: cálculo de merma real de proceso
        """
        # 1. Obtener órdenes de producción del período
        ordenes = self.odoo.search_read(
            'mrp.production',
            [
                ['date_planned_start', '>=', fecha_desde],
                ['date_planned_start', '<=', fecha_hasta],
                ['state', 'in', ['done', 'progress']]  # Solo completadas o en proceso
            ],
            ['id', 'name', 'product_id', 'product_qty', 'date_planned_start', 
             'state', 'origin', 'lot_producing_id'],
            limit=10000
        )
        
        if not ordenes:
            return self._empty_response(fecha_desde, fecha_hasta)
        
        # 2. Obtener IDs de órdenes
        orden_ids = [o['id'] for o in ordenes]
        
        # 3. Obtener movimientos de consumo de MP (raw materials)
        consumos = self.odoo.search_read(
            'stock.move',
            [
                ['raw_material_production_id', 'in', orden_ids],
                ['state', '=', 'done']
            ],
            ['id', 'product_id', 'product_uom_qty', 'quantity_done', 
             'raw_material_production_id', 'reference'],
            limit=50000
        )
        
        # 4. Obtener movimientos de producción PT (finished products)
        producciones = self.odoo.search_read(
            'stock.move',
            [
                ['production_id', 'in', orden_ids],
                ['state', '=', 'done']
            ],
            ['id', 'product_id', 'product_uom_qty', 'quantity_done', 
             'production_id', 'reference'],
            limit=50000
        )
        
        # 5. Obtener productos únicos
        prod_ids = set()
        for mov in consumos + producciones:
            prod_id = mov.get('product_id', [None])[0]
            if prod_id:
                prod_ids.add(prod_id)
        
        # Agregar productos de las órdenes
        for orden in ordenes:
            prod_id = orden.get('product_id', [None])[0]
            if prod_id:
                prod_ids.add(prod_id)
        
        productos = self.odoo.search_read(
            'product.product',
            [['id', 'in', list(prod_ids)]],
            ['id', 'name', 'default_code', 'x_studio_sub_categora', 
             'x_studio_categora_tipo_de_manejo', 'categ_id'],
            limit=50000
        )
        
        productos_map = {}
        for prod in productos:
            categ = prod.get('categ_id')
            categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
            
            tipo = prod.get('x_studio_sub_categora')
            tipo_str = tipo[1] if isinstance(tipo, (list, tuple)) and len(tipo) > 1 else 'Sin clasificar'
            
            manejo = prod.get('x_studio_categora_tipo_de_manejo')
            manejo_str = manejo[1] if isinstance(manejo, (list, tuple)) and len(manejo) > 1 else 'Sin clasificar'
            
            productos_map[prod['id']] = {
                'nombre': prod['name'],
                'codigo': prod.get('default_code', ''),
                'tipo_fruta': tipo_str,
                'manejo': manejo_str,
                'categoria': categ_name
            }
        
        # 6. Agrupar consumos por orden
        consumos_por_orden = {}
        for consumo in consumos:
            orden_id = consumo.get('raw_material_production_id', [None])[0]
            if not orden_id:
                continue
            
            if orden_id not in consumos_por_orden:
                consumos_por_orden[orden_id] = []
            
            prod_id = consumo.get('product_id', [None])[0]
            if prod_id and prod_id in productos_map:
                consumos_por_orden[orden_id].append({
                    'producto': productos_map[prod_id]['nombre'],
                    'tipo_fruta': productos_map[prod_id]['tipo_fruta'],
                    'manejo': productos_map[prod_id]['manejo'],
                    'kg': consumo.get('quantity_done', 0)
                })
        
        # 7. Agrupar producciones por orden
        producciones_por_orden = {}
        for produccion in producciones:
            orden_id = produccion.get('production_id', [None])[0]
            if not orden_id:
                continue
            
            if orden_id not in producciones_por_orden:
                producciones_por_orden[orden_id] = []
            
            prod_id = produccion.get('product_id', [None])[0]
            if prod_id and prod_id in productos_map:
                producciones_por_orden[orden_id].append({
                    'producto': productos_map[prod_id]['nombre'],
                    'tipo_fruta': productos_map[prod_id]['tipo_fruta'],
                    'manejo': productos_map[prod_id]['manejo'],
                    'kg': produccion.get('quantity_done', 0)
                })
        
        # 8. Procesar órdenes y calcular rendimientos
        resumen = {
            'kg_consumido': 0,
            'kg_producido': 0,
            'merma_kg': 0,
            'rendimiento_pct': 0,
            'ordenes_total': len(ordenes)
        }
        
        por_tipo = {}  # {tipo_fruta: {consumo, produccion, rendimiento}}
        detalle_ordenes = []
        
        for orden in ordenes:
            orden_id = orden['id']
            nombre = orden.get('name', '')
            fecha = orden.get('date_planned_start', '')
            estado = orden.get('state', '')
            
            prod_id = orden.get('product_id', [None])[0]
            producto_final = productos_map.get(prod_id, {}).get('nombre', 'N/A') if prod_id else 'N/A'
            tipo_fruta = productos_map.get(prod_id, {}).get('tipo_fruta', 'Sin clasificar') if prod_id else 'Sin clasificar'
            
            # Sumar consumos de esta orden
            consumos_orden = consumos_por_orden.get(orden_id, [])
            kg_consumido = sum([c['kg'] for c in consumos_orden])
            
            # Sumar producciones de esta orden
            producciones_orden = producciones_por_orden.get(orden_id, [])
            kg_producido = sum([p['kg'] for p in producciones_orden])
            
            # Calcular rendimiento y merma
            rendimiento = (kg_producido / kg_consumido * 100) if kg_consumido > 0 else 0
            merma = kg_consumido - kg_producido
            merma_pct = (merma / kg_consumido * 100) if kg_consumido > 0 else 0
            
            # Actualizar resumen
            resumen['kg_consumido'] += kg_consumido
            resumen['kg_producido'] += kg_producido
            resumen['merma_kg'] += merma
            
            # Agrupar por tipo de fruta
            if tipo_fruta not in por_tipo:
                por_tipo[tipo_fruta] = {
                    'kg_consumido': 0,
                    'kg_producido': 0,
                    'merma_kg': 0
                }
            
            por_tipo[tipo_fruta]['kg_consumido'] += kg_consumido
            por_tipo[tipo_fruta]['kg_producido'] += kg_producido
            por_tipo[tipo_fruta]['merma_kg'] += merma
            
            # Detalle para tabla
            detalle_ordenes.append({
                'fecha': fecha,
                'orden': nombre,
                'producto_final': producto_final,
                'tipo_fruta': tipo_fruta,
                'estado': estado,
                'kg_consumido': round(kg_consumido, 2),
                'kg_producido': round(kg_producido, 2),
                'rendimiento_pct': round(rendimiento, 1),
                'merma_kg': round(merma, 2),
                'merma_pct': round(merma_pct, 1)
            })
        
        # 9. Calcular rendimiento general
        if resumen['kg_consumido'] > 0:
            resumen['rendimiento_pct'] = round(resumen['kg_producido'] / resumen['kg_consumido'] * 100, 1)
            resumen['merma_pct'] = round(resumen['merma_kg'] / resumen['kg_consumido'] * 100, 1)
        
        # 10. Formatear rendimientos por tipo
        rendimientos_tipo = []
        for tipo, data in sorted(por_tipo.items(), key=lambda x: -x[1]['kg_consumido']):
            rend_pct = (data['kg_producido'] / data['kg_consumido'] * 100) if data['kg_consumido'] > 0 else 0
            merma_pct = (data['merma_kg'] / data['kg_consumido'] * 100) if data['kg_consumido'] > 0 else 0
            
            rendimientos_tipo.append({
                'tipo_fruta': tipo,
                'kg_consumido': round(data['kg_consumido'], 2),
                'kg_producido': round(data['kg_producido'], 2),
                'rendimiento_pct': round(rend_pct, 1),
                'merma_kg': round(data['merma_kg'], 2),
                'merma_pct': round(merma_pct, 1)
            })
        
        return {
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'resumen': resumen,
            'rendimientos_por_tipo': rendimientos_tipo,
            'detalle_ordenes': detalle_ordenes
        }
    
    def _empty_response(self, fecha_desde: str, fecha_hasta: str):
        """Respuesta vacía cuando no hay datos."""
        return {
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'resumen': {
                'kg_consumido': 0,
                'kg_producido': 0,
                'merma_kg': 0,
                'rendimiento_pct': 0,
                'merma_pct': 0,
                'ordenes_total': 0
            },
            'rendimientos_por_tipo': [],
            'detalle_ordenes': []
        }
