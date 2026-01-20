"""
Servicio para análisis de compras de materia prima (MP/PSP)
Análisis aislado de facturas de proveedor sin comparar con ventas
"""
from typing import Optional


class AnalisisComprasService:
    """Servicio para análisis de compras de MP/PSP."""
    
    def __init__(self, odoo):
        """
        Args:
            odoo: Cliente OdooClient configurado
        """
        self.odoo = odoo
    
    def get_analisis_compras(self, fecha_desde: str, fecha_hasta: str):
        """
        Análisis completo de compras de materia prima.
        
        Args:
            fecha_desde: Fecha inicio (YYYY-MM-DD)
            fecha_hasta: Fecha fin (YYYY-MM-DD)
        
        Returns:
            dict con:
                - resumen: totales generales
                - por_tipo: desglose por tipo de fruta
                - por_proveedor: top proveedores
                - tendencia_precios: evolución de precios por mes
                - detalle: líneas individuales para tabla
        """
        # 1. Obtener líneas de compra (solo frutas - categoría PRODUCTOS/MP o PRODUCTOS/PSP)
        lineas = self.odoo.search_read(
            'account.move.line',
            [
                ['move_id.move_type', '=', 'in_invoice'],
                ['move_id.state', '=', 'posted'],
                ['product_id', '!=', False],
                ['date', '>=', fecha_desde],
                ['date', '<=', fecha_hasta],
                ['quantity', '>', 0],
                ['debit', '>', 0],
                ['account_id.code', '=like', '21%']
            ],
            ['product_id', 'quantity', 'debit', 'date', 'move_id', 'partner_id'],
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
        
        # 3. Filtrar solo productos de categoría MP o PSP
        productos_map = {}
        for prod in productos:
            categ = prod.get('categ_id')
            categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
            
            # Solo incluir si es MP o PSP
            if 'PRODUCTOS / MP' in categ_name or 'PRODUCTOS / PSP' in categ_name:
                tipo = prod.get('x_studio_sub_categora')
                tipo_str = tipo[1] if isinstance(tipo, (list, tuple)) and len(tipo) > 1 else None
                
                manejo = prod.get('x_studio_categora_tipo_de_manejo')
                manejo_str = manejo[1] if isinstance(manejo, (list, tuple)) and len(manejo) > 1 else None
                
                # Solo si tiene tipo y manejo
                if tipo_str and manejo_str:
                    productos_map[prod['id']] = {
                        'nombre': prod['name'],
                        'codigo': prod.get('default_code', ''),
                        'tipo_fruta': tipo_str,
                        'manejo': manejo_str,
                        'categoria': categ_name
                    }
        
        # 4. Obtener proveedores únicos
        partner_ids = list(set([l.get('partner_id', [None])[0] for l in lineas if l.get('partner_id')]))
        proveedores = self.odoo.search_read(
            'res.partner',
            [['id', 'in', partner_ids]],
            ['id', 'name'],
            limit=5000
        )
        proveedores_map = {p['id']: p['name'] for p in proveedores}
        
        # 5. Procesar líneas
        resumen = {'kg': 0, 'monto': 0}
        por_tipo = {}  # {tipo_fruta: {manejo: {kg, monto}}}
        por_proveedor = {}  # {proveedor: {kg, monto}}
        por_mes = {}  # {mes: {kg, monto, precios: []}}
        detalle = []
        
        for linea in lineas:
            prod_id = linea.get('product_id', [None])[0]
            if not prod_id or prod_id not in productos_map:
                continue
            
            prod = productos_map[prod_id]
            kg = linea.get('quantity', 0)
            monto = linea.get('debit', 0)
            fecha = linea.get('date', '')
            mes = fecha[:7] if fecha else ''  # YYYY-MM
            
            partner_id = linea.get('partner_id', [None])[0]
            proveedor = proveedores_map.get(partner_id, 'Sin proveedor')
            
            precio_kg = monto / kg if kg > 0 else 0
            
            # Resumen general
            resumen['kg'] += kg
            resumen['monto'] += monto
            
            # Por tipo de fruta
            tipo = prod['tipo_fruta']
            manejo = prod['manejo']
            
            if tipo not in por_tipo:
                por_tipo[tipo] = {}
            if manejo not in por_tipo[tipo]:
                por_tipo[tipo][manejo] = {'kg': 0, 'monto': 0}
            
            por_tipo[tipo][manejo]['kg'] += kg
            por_tipo[tipo][manejo]['monto'] += monto
            
            # Por proveedor
            if proveedor not in por_proveedor:
                por_proveedor[proveedor] = {'kg': 0, 'monto': 0}
            
            por_proveedor[proveedor]['kg'] += kg
            por_proveedor[proveedor]['monto'] += monto
            
            # Tendencia por mes
            if mes not in por_mes:
                por_mes[mes] = {'kg': 0, 'monto': 0, 'precios': []}
            
            por_mes[mes]['kg'] += kg
            por_mes[mes]['monto'] += monto
            por_mes[mes]['precios'].append(precio_kg)
            
            # Detalle para tabla
            detalle.append({
                'fecha': fecha,
                'proveedor': proveedor,
                'producto': prod['nombre'],
                'codigo': prod['codigo'],
                'tipo_fruta': tipo,
                'manejo': manejo,
                'kg': round(kg, 2),
                'monto': round(monto, 2),
                'precio_kg': round(precio_kg, 2)
            })
        
        # 6. Calcular precio promedio general
        resumen['precio_promedio'] = resumen['monto'] / resumen['kg'] if resumen['kg'] > 0 else 0
        
        # 7. Formatear por_tipo con precios
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
        
        # 8. Top proveedores (ordenados por monto)
        top_proveedores = [
            {
                'proveedor': prov,
                'kg': round(data['kg'], 2),
                'monto': round(data['monto'], 2),
                'precio_promedio': round(data['monto'] / data['kg'], 2) if data['kg'] > 0 else 0
            }
            for prov, data in sorted(por_proveedor.items(), key=lambda x: -x[1]['monto'])
        ]
        
        # 9. Tendencia de precios (por mes)
        tendencia = []
        for mes in sorted(por_mes.keys()):
            data = por_mes[mes]
            # Precio promedio del mes
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
            'por_tipo': tipo_detalle,
            'top_proveedores': top_proveedores[:10],  # Top 10
            'tendencia_precios': tendencia,
            'detalle': detalle
        }
    
    def _empty_response(self, fecha_desde: str, fecha_hasta: str):
        """Respuesta vacía cuando no hay datos."""
        return {
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'resumen': {'kg': 0, 'monto': 0, 'precio_promedio': 0},
            'por_tipo': [],
            'top_proveedores': [],
            'tendencia_precios': [],
            'detalle': []
        }
