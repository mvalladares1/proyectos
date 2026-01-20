"""
Servicio para análisis de inventario y rotación de stock
Calcula stock actual, rotación, días de inventario
"""
from typing import Optional
from datetime import datetime, timedelta


class AnalisisInventarioService:
    """Servicio para análisis de inventario y rotación."""
    
    def __init__(self, odoo):
        """
        Args:
            odoo: Cliente OdooClient configurado
        """
        self.odoo = odoo
    
    def get_analisis_inventario(self, fecha_desde: str, fecha_hasta: str):
        """
        Análisis de inventario y rotación de stock.
        
        Args:
            fecha_desde: Fecha inicio (YYYY-MM-DD) - para calcular movimientos
            fecha_hasta: Fecha fin (YYYY-MM-DD)
        
        Returns:
            dict con:
                - resumen: totales de stock actual y valorización
                - por_producto: detalle por producto con rotación
                - por_ubicacion: stock por ubicación
                - alertas: productos con stock bajo o sin movimiento
        """
        # 1. Obtener stock actual (solo ubicaciones internas, no de clientes/proveedores)
        stock_actual = self.odoo.search_read(
            'stock.quant',
            [
                ['quantity', '>', 0],
                ['location_id.usage', '=', 'internal']  # Solo ubicaciones internas
            ],
            ['product_id', 'quantity', 'location_id', 'inventory_quantity'],
            limit=50000
        )
        
        if not stock_actual:
            return self._empty_response(fecha_desde, fecha_hasta)
        
        # 2. Obtener productos únicos
        prod_ids = list(set([s.get('product_id', [None])[0] for s in stock_actual if s.get('product_id')]))
        
        productos = self.odoo.search_read(
            'product.product',
            [['id', 'in', prod_ids]],
            ['id', 'name', 'default_code', 'x_studio_sub_categora', 
             'x_studio_categora_tipo_de_manejo', 'categ_id', 'standard_price', 'lst_price'],
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
                'categoria': categ_name,
                'costo_unitario': prod.get('standard_price', 0),
                'precio_venta': prod.get('lst_price', 0)
            }
        
        # 3. Obtener ubicaciones
        loc_ids = list(set([s.get('location_id', [None])[0] for s in stock_actual if s.get('location_id')]))
        ubicaciones = self.odoo.search_read(
            'stock.location',
            [['id', 'in', loc_ids]],
            ['id', 'name', 'complete_name'],
            limit=5000
        )
        ubicaciones_map = {u['id']: u.get('complete_name', u['name']) for u in ubicaciones}
        
        # 4. Obtener movimientos del período para calcular rotación
        movimientos = self.odoo.search_read(
            'stock.move',
            [
                ['product_id', 'in', prod_ids],
                ['state', '=', 'done'],
                ['date', '>=', fecha_desde],
                ['date', '<=', fecha_hasta],
                ['location_dest_id.usage', '=', 'customer']  # Solo salidas a clientes
            ],
            ['product_id', 'product_uom_qty', 'quantity_done', 'date'],
            limit=50000
        )
        
        # 5. Calcular salidas por producto (para rotación)
        salidas_por_producto = {}
        for mov in movimientos:
            prod_id = mov.get('product_id', [None])[0]
            if not prod_id:
                continue
            
            qty = mov.get('quantity_done', 0)
            
            if prod_id not in salidas_por_producto:
                salidas_por_producto[prod_id] = 0
            
            salidas_por_producto[prod_id] += qty
        
        # 6. Calcular días del período
        fecha_inicio = datetime.strptime(fecha_desde, '%Y-%m-%d')
        fecha_fin = datetime.strptime(fecha_hasta, '%Y-%m-%d')
        dias_periodo = (fecha_fin - fecha_inicio).days + 1
        
        # 7. Procesar stock por producto
        stock_por_producto = {}
        stock_por_ubicacion = {}
        
        for sq in stock_actual:
            prod_id = sq.get('product_id', [None])[0]
            if not prod_id or prod_id not in productos_map:
                continue
            
            qty = sq.get('quantity', 0)
            loc_id = sq.get('location_id', [None])[0]
            ubicacion = ubicaciones_map.get(loc_id, 'Sin ubicación')
            
            # Por producto
            if prod_id not in stock_por_producto:
                stock_por_producto[prod_id] = 0
            stock_por_producto[prod_id] += qty
            
            # Por ubicación
            if ubicacion not in stock_por_ubicacion:
                stock_por_ubicacion[ubicacion] = {'kg': 0, 'valor': 0}
            
            costo = productos_map[prod_id]['costo_unitario']
            stock_por_ubicacion[ubicacion]['kg'] += qty
            stock_por_ubicacion[ubicacion]['valor'] += qty * costo
        
        # 8. Calcular métricas de inventario
        resumen = {
            'stock_total_kg': 0,
            'valor_total': 0,
            'productos_con_stock': len(stock_por_producto),
            'ubicaciones': len(stock_por_ubicacion)
        }
        
        detalle_productos = []
        alertas = []
        
        for prod_id, stock_kg in stock_por_producto.items():
            prod = productos_map[prod_id]
            costo = prod['costo_unitario']
            precio = prod['precio_venta']
            
            valor_stock = stock_kg * costo
            
            # Calcular rotación
            salidas = salidas_por_producto.get(prod_id, 0)
            
            # Rotación = salidas del período / stock promedio
            # Asumimos stock constante (simplificación)
            rotacion = (salidas / stock_kg) if stock_kg > 0 else 0
            
            # Días de inventario = stock / (salidas / días)
            salida_diaria = salidas / dias_periodo if dias_periodo > 0 else 0
            dias_inventario = (stock_kg / salida_diaria) if salida_diaria > 0 else 999
            
            # Actualizar resumen
            resumen['stock_total_kg'] += stock_kg
            resumen['valor_total'] += valor_stock
            
            # Detalle
            item = {
                'producto': prod['nombre'],
                'codigo': prod['codigo'],
                'tipo_fruta': prod['tipo_fruta'],
                'manejo': prod['manejo'],
                'categoria': prod['categoria'].split(' / ')[-1] if ' / ' in prod['categoria'] else prod['categoria'],
                'stock_kg': round(stock_kg, 2),
                'costo_unitario': round(costo, 2),
                'valor_stock': round(valor_stock, 2),
                'salidas_periodo': round(salidas, 2),
                'rotacion': round(rotacion, 2),
                'dias_inventario': round(dias_inventario, 0) if dias_inventario < 999 else 999
            }
            
            detalle_productos.append(item)
            
            # Generar alertas
            if dias_inventario > 90:
                alertas.append({
                    'tipo': 'stock_lento',
                    'producto': prod['nombre'],
                    'mensaje': f'Stock de {dias_inventario:.0f} días (lenta rotación)',
                    'stock_kg': round(stock_kg, 2),
                    'dias': round(dias_inventario, 0)
                })
            
            if salidas == 0 and stock_kg > 10:  # Sin movimiento
                alertas.append({
                    'tipo': 'sin_movimiento',
                    'producto': prod['nombre'],
                    'mensaje': f'Sin salidas en período ({stock_kg:.0f} kg en stock)',
                    'stock_kg': round(stock_kg, 2),
                    'dias': 0
                })
        
        # 9. Formatear stock por ubicación
        ubicaciones_detalle = [
            {
                'ubicacion': ubi,
                'kg': round(data['kg'], 2),
                'valor': round(data['valor'], 2),
                'porcentaje': round(data['kg'] / resumen['stock_total_kg'] * 100, 1) if resumen['stock_total_kg'] > 0 else 0
            }
            for ubi, data in sorted(stock_por_ubicacion.items(), key=lambda x: -x[1]['kg'])
        ]
        
        # Ordenar productos por valor de stock (mayor a menor)
        detalle_productos.sort(key=lambda x: -x['valor_stock'])
        
        # Limitar alertas a las más importantes
        alertas.sort(key=lambda x: (-x.get('stock_kg', 0), -x.get('dias', 0)))
        
        return {
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'dias_periodo': dias_periodo,
            'resumen': {
                'stock_total_kg': round(resumen['stock_total_kg'], 2),
                'valor_total': round(resumen['valor_total'], 2),
                'productos_con_stock': resumen['productos_con_stock'],
                'ubicaciones': resumen['ubicaciones']
            },
            'por_producto': detalle_productos,
            'por_ubicacion': ubicaciones_detalle,
            'alertas': alertas[:20]  # Top 20 alertas
        }
    
    def _empty_response(self, fecha_desde: str, fecha_hasta: str):
        """Respuesta vacía cuando no hay datos."""
        return {
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'dias_periodo': 0,
            'resumen': {
                'stock_total_kg': 0,
                'valor_total': 0,
                'productos_con_stock': 0,
                'ubicaciones': 0
            },
            'por_producto': [],
            'por_ubicacion': [],
            'alertas': []
        }
