"""
Servicio para análisis de ventas de productos terminados (PTT/Retail)
Análisis aislado de facturas de clientes sin comparar con compras
"""
from typing import Optional


class AnalisisVentasService:
    """Servicio para análisis de ventas de PT."""
    
    def __init__(self, odoo):
        """
        Args:
            odoo: Cliente OdooClient configurado
        """
        self.odoo = odoo
    
    def get_analisis_ventas(self, fecha_desde: str, fecha_hasta: str):
        """
        Análisis completo de ventas de productos terminados.
        
        Args:
            fecha_desde: Fecha inicio (YYYY-MM-DD)
            fecha_hasta: Fecha fin (YYYY-MM-DD)
        
        Returns:
            dict con:
                - resumen: totales generales
                - por_producto: desglose por tipo de producto
                - por_cliente: top clientes
                - tendencia_precios: evolución de precios por mes
                - detalle: líneas individuales para tabla
        """
        # 1. Obtener líneas de venta (solo PTT/Retail/Subproducto)
        lineas = self.odoo.search_read(
            'account.move.line',
            [
                ['move_id.move_type', '=', 'out_invoice'],
                ['move_id.state', '=', 'posted'],
                ['product_id', '!=', False],
                ['date', '>=', fecha_desde],
                ['date', '<=', fecha_hasta],
                ['quantity', '>', 0],
                ['credit', '>', 0],
                ['account_id.code', '=like', '41%']
            ],
            ['product_id', 'quantity', 'credit', 'date', 'move_id', 'partner_id'],
            limit=50000
        )
        
        if not lineas:
            return self._empty_response(fecha_desde, fecha_hasta)
        
        # 2. Obtener productos únicos
        prod_ids = list(set([l.get('product_id', [None])[0] for l in lineas if l.get('product_id')]))
        
        productos = self.odoo.search_read(
            'product.product',
            [['id', 'in', prod_ids]],
            ['id', 'name', 'default_code', 'x_studio_sub_categora', 
             'x_studio_categora_tipo_de_manejo', 'categ_id'],
            limit=50000
        )
        
        # 3. Filtrar solo productos PTT, Retail, Subproducto
        productos_map = {}
        for prod in productos:
            categ = prod.get('categ_id')
            categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
            
            # Solo incluir PTT, Retail, Subproducto
            if any(x in categ_name for x in ['PRODUCTOS / PTT', 'PRODUCTOS / RETAIL', 'PRODUCTOS / SUBPRODUCTO']):
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
        
        # 4. Obtener clientes únicos
        partner_ids = list(set([l.get('partner_id', [None])[0] for l in lineas if l.get('partner_id')]))
        clientes = self.odoo.search_read(
            'res.partner',
            [['id', 'in', partner_ids]],
            ['id', 'name', 'country_id'],
            limit=5000
        )
        clientes_map = {}
        for c in clientes:
            pais = c.get('country_id')
            pais_str = pais[1] if isinstance(pais, (list, tuple)) and len(pais) > 1 else 'Sin país'
            clientes_map[c['id']] = {
                'nombre': c['name'],
                'pais': pais_str
            }
        
        # 5. Procesar líneas
        resumen = {'kg': 0, 'monto': 0}
        por_categoria = {}  # {categoria: {kg, monto}}
        por_tipo = {}  # {tipo_fruta: {manejo: {kg, monto}}}
        por_cliente = {}  # {cliente: {kg, monto, pais}}
        por_mes = {}  # {mes: {kg, monto, precios: []}}
        detalle = []
        
        for linea in lineas:
            prod_id = linea.get('product_id', [None])[0]
            if not prod_id or prod_id not in productos_map:
                continue
            
            prod = productos_map[prod_id]
            kg = linea.get('quantity', 0)
            monto = linea.get('credit', 0)
            fecha = linea.get('date', '')
            mes = fecha[:7] if fecha else ''  # YYYY-MM
            
            partner_id = linea.get('partner_id', [None])[0]
            cliente_info = clientes_map.get(partner_id, {'nombre': 'Sin cliente', 'pais': 'Sin país'})
            cliente = cliente_info['nombre']
            pais = cliente_info['pais']
            
            precio_kg = monto / kg if kg > 0 else 0
            
            # Resumen general
            resumen['kg'] += kg
            resumen['monto'] += monto
            
            # Por categoría (PTT, Retail, Subproducto)
            categoria = prod['categoria'].split(' / ')[-1]  # Última parte
            if categoria not in por_categoria:
                por_categoria[categoria] = {'kg': 0, 'monto': 0}
            
            por_categoria[categoria]['kg'] += kg
            por_categoria[categoria]['monto'] += monto
            
            # Por tipo de fruta
            tipo = prod['tipo_fruta']
            manejo = prod['manejo']
            
            if tipo not in por_tipo:
                por_tipo[tipo] = {}
            if manejo not in por_tipo[tipo]:
                por_tipo[tipo][manejo] = {'kg': 0, 'monto': 0}
            
            por_tipo[tipo][manejo]['kg'] += kg
            por_tipo[tipo][manejo]['monto'] += monto
            
            # Por cliente
            if cliente not in por_cliente:
                por_cliente[cliente] = {'kg': 0, 'monto': 0, 'pais': pais}
            
            por_cliente[cliente]['kg'] += kg
            por_cliente[cliente]['monto'] += monto
            
            # Tendencia por mes
            if mes not in por_mes:
                por_mes[mes] = {'kg': 0, 'monto': 0, 'precios': []}
            
            por_mes[mes]['kg'] += kg
            por_mes[mes]['monto'] += monto
            por_mes[mes]['precios'].append(precio_kg)
            
            # Detalle para tabla
            detalle.append({
                'fecha': fecha,
                'cliente': cliente,
                'pais': pais,
                'producto': prod['nombre'],
                'codigo': prod['codigo'],
                'categoria': categoria,
                'tipo_fruta': tipo,
                'manejo': manejo,
                'kg': round(kg, 2),
                'monto': round(monto, 2),
                'precio_kg': round(precio_kg, 2)
            })
        
        # 6. Calcular precio promedio general
        resumen['precio_promedio'] = resumen['monto'] / resumen['kg'] if resumen['kg'] > 0 else 0
        
        # 7. Formatear por categoría
        categoria_detalle = [
            {
                'categoria': cat,
                'kg': round(data['kg'], 2),
                'monto': round(data['monto'], 2),
                'precio_promedio': round(data['monto'] / data['kg'], 2) if data['kg'] > 0 else 0,
                'porcentaje': round(data['monto'] / resumen['monto'] * 100, 1) if resumen['monto'] > 0 else 0
            }
            for cat, data in sorted(por_categoria.items(), key=lambda x: -x[1]['monto'])
        ]
        
        # 8. Formatear por tipo con precios
        tipo_detalle = []
        for tipo, manejos in por_tipo.items():
            for manejo, data in manejos.items():
                tipo_detalle.append({
                    'tipo_fruta': tipo,
                    'manejo': manejo,
                    'kg': round(data['kg'], 2),
                    'monto': round(data['monto'], 2),
                    'precio_promedio': round(data['monto'] / data['kg'], 2) if data['kg'] > 0 else 0
                })
        
        # 9. Top clientes (ordenados por monto)
        top_clientes = [
            {
                'cliente': cliente,
                'pais': data['pais'],
                'kg': round(data['kg'], 2),
                'monto': round(data['monto'], 2),
                'precio_promedio': round(data['monto'] / data['kg'], 2) if data['kg'] > 0 else 0
            }
            for cliente, data in sorted(por_cliente.items(), key=lambda x: -x[1]['monto'])
        ]
        
        # 10. Tendencia de precios (por mes)
        tendencia = []
        for mes in sorted(por_mes.keys()):
            data = por_mes[mes]
            precio_prom = sum(data['precios']) / len(data['precios']) if data['precios'] else 0
            
            tendencia.append({
                'mes': mes,
                'kg': round(data['kg'], 2),
                'monto': round(data['monto'], 2),
                'precio_promedio': round(precio_prom, 2)
            })
        
        return {
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'resumen': {
                'kg': round(resumen['kg'], 2),
                'monto': round(resumen['monto'], 2),
                'precio_promedio': round(resumen['precio_promedio'], 2)
            },
            'por_categoria': categoria_detalle,
            'por_tipo': tipo_detalle,
            'top_clientes': top_clientes[:10],  # Top 10
            'tendencia_precios': tendencia,
            'detalle': detalle
        }
    
    def _empty_response(self, fecha_desde: str, fecha_hasta: str):
        """Respuesta vacía cuando no hay datos."""
        return {
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'resumen': {'kg': 0, 'monto': 0, 'precio_promedio': 0},
            'por_categoria': [],
            'por_tipo': [],
            'top_clientes': [],
            'tendencia_precios': [],
            'detalle': []
        }
