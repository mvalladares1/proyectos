"""
Servicio para automatización de órdenes de fabricación en túneles estáticos.
Maneja la lógica de creación de componentes y subproductos con sufijo -C.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from shared.odoo_client import OdooClient


# Configuración de túneles y productos
TUNELES_CONFIG = {
    'TE1': {
        'producto_proceso_id': 15984,
        'producto_proceso_nombre': '[1.1] PROCESO CONGELADO TÚNEL ESTÁTICO 1',
        'sucursal': 'RF',
        'ubicacion_origen_id': 5452,
        'ubicacion_origen_nombre': 'RF/Stock/Camara 0°C REAL',
        'ubicacion_destino_id': 8479,
        'ubicacion_destino_nombre': 'Tránsito/Salida Túneles Estáticos',
        'sala_proceso': 'Tunel - Estatico 1'
    },
    'TE2': {
        'producto_proceso_id': 15985,  # TODO: Confirmar ID real
        'producto_proceso_nombre': '[1.2] PROCESO CONGELADO TÚNEL ESTÁTICO 2',
        'sucursal': 'RF',
        'ubicacion_origen_id': 5452,
        'ubicacion_origen_nombre': 'RF/Stock/Camara 0°C REAL',
        'ubicacion_destino_id': 8479,
        'ubicacion_destino_nombre': 'Tránsito/Salida Túneles Estáticos',
        'sala_proceso': 'Tunel - Estatico 2'
    },
    'TE3': {
        'producto_proceso_id': 15986,  # TODO: Confirmar ID real
        'producto_proceso_nombre': '[1.3] PROCESO CONGELADO TÚNEL ESTÁTICO 3',
        'sucursal': 'RF',
        'ubicacion_origen_id': 5452,
        'ubicacion_origen_nombre': 'RF/Stock/Camara 0°C REAL',
        'ubicacion_destino_id': 8479,
        'ubicacion_destino_nombre': 'Tránsito/Salida Túneles Estáticos',
        'sala_proceso': 'Tunel - Estatico 3'
    },
    'VLK': {
        'producto_proceso_id': 16446,
        'producto_proceso_nombre': '[1.1.1] PROCESO CONGELADO TÚNEL ESTÁTICO VLK',
        'sucursal': 'VLK',
        'ubicacion_origen_id': 8528,
        'ubicacion_origen_nombre': 'VLK/Camara 0°',
        'ubicacion_destino_id': 8532,
        'ubicacion_destino_nombre': 'Tránsito VLK/Salida Túnel Estático',
        'sala_proceso': 'Tunel - Estatico VLK'
    }
}

# Mapeo de productos: fresco → congelado
PRODUCTOS_TRANSFORMACION = {
    15999: 16183,  # [102122000] FB MK Conv. IQF en Bandeja → [202122000] FB MK Conv. IQF Congelado en Bandeja
    16016: 16182,  # [102121000] FB S/V Conv. IQF en Bandeja → [202121000] FB S/V Conv. IQF Congelado en Bandeja
}

# Provisión eléctrica
PRODUCTO_ELECTRICIDAD_ID = 15995  # [ETE] Provisión Electricidad Túnel Estático ($/hr)

# Ubicaciones virtuales
UBICACION_VIRTUAL_CONGELADO_ID = 8485  # Virtual Locations/Ubicación Congelado
UBICACION_VIRTUAL_PROCESOS_ID = 15     # Virtual Locations/Ubicación Procesos


class TunelesService:
    """Servicio para gestión de túneles estáticos."""
    
    def __init__(self, odoo: OdooClient):
        self.odoo = odoo
    
    def get_tuneles_disponibles(self) -> List[Dict]:
        """Obtiene la lista de túneles disponibles."""
        return [
            {
                'codigo': codigo,
                'nombre': config['producto_proceso_nombre'],
                'sucursal': config['sucursal']
            }
            for codigo, config in TUNELES_CONFIG.items()
        ]
    
    def validar_pallets_batch(self, codigos_pallets: List[str], buscar_ubicacion: bool = False) -> List[Dict]:
        """
        Valida múltiples pallets en 2 llamadas a Odoo (OPTIMIZADO).
        
        Args:
            codigos_pallets: Lista de códigos de pallets
            buscar_ubicacion: Si True, busca la ubicación real del pallet
            
        Returns:
            Lista de dicts con validación de cada pallet
        """
        if not codigos_pallets:
            return []
        
        resultados = []
        
        # LLAMADA 1: Buscar TODOS los lotes en una sola llamada
        lotes = self.odoo.search_read(
            'stock.lot',
            [('name', 'in', codigos_pallets)],
            ['id', 'name', 'product_id']
        )
        
        # Crear mapa de lotes por código
        lotes_map = {lote['name']: lote for lote in lotes}
        
        # Identificar pallets no encontrados
        codigos_encontrados = set(lotes_map.keys())
        codigos_no_encontrados = set(codigos_pallets) - codigos_encontrados
        
        # Agregar resultados de no encontrados
        for codigo in codigos_no_encontrados:
            resultados.append({
                'existe': False,
                'codigo': codigo,
                'error': f'Lote {codigo} no encontrado en Odoo'
            })
        
        # Si no hay lotes encontrados, retornar
        if not lotes:
            return resultados
        
        # LLAMADA 2: Buscar TODAS las cantidades en una sola llamada
        lote_ids = [lote['id'] for lote in lotes]
        quants = self.odoo.search_read(
            'stock.quant',
            [('lot_id', 'in', lote_ids), ('quantity', '>', 0)],
            ['lot_id', 'quantity', 'location_id', 'product_id']
        )
        
        # Agrupar quants por lote_id
        quants_por_lote = {}
        for quant in quants:
            lot_id = quant['lot_id'][0]
            if lot_id not in quants_por_lote:
                quants_por_lote[lot_id] = []
            quants_por_lote[lot_id].append(quant)
        
        # Procesar cada lote encontrado
        for codigo in codigos_encontrados:
            lote = lotes_map[codigo]
            lote_quants = quants_por_lote.get(lote['id'], [])
            
            if not lote_quants:
                resultados.append({
                    'existe': True,
                    'codigo': codigo,
                    'kg': 0.0,
                    'ubicacion_id': None,
                    'ubicacion_nombre': None,
                    'producto_id': lote['product_id'][0] if lote['product_id'] else None,
                    'lote_id': lote['id'],
                    'advertencia': 'Pallet sin stock disponible'
                })
                continue
            
            # Sumar cantidades
            kg_total = sum(q['quantity'] for q in lote_quants)
            
            # Usar primera ubicación
            ubicacion = lote_quants[0]['location_id']
            producto_id = lote_quants[0]['product_id'][0] if lote_quants[0]['product_id'] else None
            
            resultados.append({
                'existe': True,
                'codigo': codigo,
                'kg': kg_total,
                'ubicacion_id': ubicacion[0] if ubicacion else None,
                'ubicacion_nombre': ubicacion[1] if ubicacion else None,
                'producto_id': producto_id,
                'lote_id': lote['id']
            })
        
        return resultados
    
    def validar_pallet(self, codigo_pallet: str, buscar_ubicacion: bool = False) -> Dict:
        """
        Valida si un pallet existe y obtiene su información.
        
        Args:
            codigo_pallet: Código del pallet (ej: PAC0002683)
            buscar_ubicacion: Si True, busca la ubicación real del pallet
            
        Returns:
            Dict con: existe, kg, ubicacion_id, ubicacion_nombre, producto_id
        """
        # Buscar lote (lot) por nombre
        lotes = self.odoo.search_read(
            'stock.lot',
            [('name', '=', codigo_pallet)],
            ['id', 'name', 'product_id']
        )
        
        if not lotes:
            return {
                'existe': False,
                'codigo': codigo_pallet,
                'error': f'Lote {codigo_pallet} no encontrado en Odoo'
            }
        
        lote = lotes[0]
        
        # Buscar cantidad y ubicación en stock.quant
        quants = self.odoo.search_read(
            'stock.quant',
            [('lot_id', '=', lote['id']), ('quantity', '>', 0)],
            ['quantity', 'location_id', 'product_id']
        )
        
        if not quants:
            return {
                'existe': True,
                'codigo': codigo_pallet,
                'kg': 0.0,
                'ubicacion_id': None,
                'ubicacion_nombre': None,
                'producto_id': lote['product_id'][0] if lote['product_id'] else None,
                'advertencia': 'Pallet sin stock disponible'
            }
        
        # Sumar cantidades si hay múltiples ubicaciones
        kg_total = sum(q['quantity'] for q in quants)
        
        # Usar la primera ubicación (o buscar la correcta)
        ubicacion = quants[0]['location_id']
        producto_id = quants[0]['product_id'][0] if quants[0]['product_id'] else None
        
        return {
            'existe': True,
            'codigo': codigo_pallet,
            'kg': kg_total,
            'ubicacion_id': ubicacion[0] if ubicacion else None,
            'ubicacion_nombre': ubicacion[1] if ubicacion else None,
            'producto_id': producto_id,
            'lote_id': lote['id']
        }
    
    def crear_orden_fabricacion(
        self,
        tunel: str,
        pallets: List[Dict[str, float]],
        buscar_ubicacion_auto: bool = False,
        responsable_id: Optional[int] = None
    ) -> Dict:
        """
        Crea una orden de fabricación para un túnel estático.
        
        Args:
            tunel: Código del túnel (TE1, TE2, TE3, VLK)
            pallets: Lista de dicts con {codigo: str, kg: float}
            buscar_ubicacion_auto: Si True, busca ubicación real del pallet
            responsable_id: ID del usuario responsable
            
        Returns:
            Dict con: success, mo_id, mo_name, total_kg, errores, advertencias
        """
        if tunel not in TUNELES_CONFIG:
            return {
                'success': False,
                'error': f'Túnel {tunel} no válido. Opciones: {list(TUNELES_CONFIG.keys())}'
            }
        
        config = TUNELES_CONFIG[tunel]
        errores = []
        advertencias = []
        
        # 1. Validar todos los pallets primero
        pallets_validados = []
        for pallet in pallets:
            validacion = self.validar_pallet(pallet['codigo'], buscar_ubicacion_auto)
            
            if not validacion['existe']:
                errores.append(validacion['error'])
                continue
            
            # Si no tiene kg en Odoo, usar el ingresado manualmente
            kg = validacion['kg'] if validacion['kg'] > 0 else pallet.get('kg', 0)
            
            if kg <= 0:
                advertencias.append(f"{pallet['codigo']}: Sin stock, debe ingresar kg manualmente")
                kg = pallet.get('kg', 0)
                if kg <= 0:
                    errores.append(f"{pallet['codigo']}: Debe especificar cantidad en Kg")
                    continue
            
            pallets_validados.append({
                'codigo': pallet['codigo'],
                'kg': kg,
                'lote_id': validacion.get('lote_id'),
                'producto_id': validacion.get('producto_id'),
                'ubicacion_id': validacion.get('ubicacion_id', config['ubicacion_origen_id'])
            })
        
        if errores:
            return {
                'success': False,
                'errores': errores,
                'advertencias': advertencias
            }
        
        if not pallets_validados:
            return {
                'success': False,
                'error': 'No hay pallets válidos para procesar'
            }
        
        # 2. Calcular totales por producto
        productos_totales = {}
        for pallet in pallets_validados:
            prod_id = pallet['producto_id']
            if prod_id not in productos_totales:
                productos_totales[prod_id] = {
                    'kg': 0,
                    'pallets': []
                }
            productos_totales[prod_id]['kg'] += pallet['kg']
            productos_totales[prod_id]['pallets'].append(pallet)
        
        total_kg = sum(p['kg'] for p in pallets_validados)
        
        # 3. Crear la orden de fabricación
        try:
            mo_data = {
                'product_id': config['producto_proceso_id'],
                'product_qty': total_kg,
                'product_uom_id': 12,  # kg
                'location_src_id': config['ubicacion_origen_id'],
                'location_dest_id': config['ubicacion_destino_id'],
                'state': 'draft',  # Borrador
                'company_id': 1,  # RIO FUTURO PROCESOS SPA
            }
            
            if responsable_id:
                mo_data['user_id'] = responsable_id
            
            mo_id = self.odoo.execute('mrp.production', 'create', mo_data)
            
            # Leer el nombre generado
            mo = self.odoo.read('mrp.production', [mo_id], ['name'])[0]
            mo_name = mo['name']
            
            # 4. Crear componentes (move_raw_ids)
            componentes_creados = self._crear_componentes(
                mo_id, 
                mo_name, 
                productos_totales, 
                config
            )
            
            # 5. Crear subproductos (move_finished_ids)
            subproductos_creados = self._crear_subproductos(
                mo_id,
                mo_name,
                productos_totales,
                config
            )
            
            return {
                'success': True,
                'mo_id': mo_id,
                'mo_name': mo_name,
                'total_kg': total_kg,
                'pallets_count': len(pallets_validados),
                'componentes_count': componentes_creados,
                'subproductos_count': subproductos_creados,
                'advertencias': advertencias,
                'mensaje': f'Orden {mo_name} creada con {componentes_creados} componentes y {subproductos_creados} subproductos'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error al crear orden de fabricación: {str(e)}'
            }
    
    def _buscar_o_crear_lotes_batch(self, lotes_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Busca o crea múltiples lotes en batch (OPTIMIZADO).
        
        Args:
            lotes_data: Lista de dicts con 'codigo' y 'producto_id'
            Ejemplo: [{'codigo': 'PAC0002683-C', 'producto_id': 16183}, ...]
            
        Returns:
            Dict mapeando codigo → lote_id
        """
        if not lotes_data:
            return {}
        
        codigos = [d['codigo'] for d in lotes_data]
        
        # LLAMADA 1: Buscar todos los lotes existentes
        lotes_existentes = self.odoo.search_read(
            'stock.lot',
            [('name', 'in', codigos)],
            ['name', 'id']
        )
        
        lotes_map = {lot['name']: lot['id'] for lot in lotes_existentes}
        
        # Identificar los que faltan
        faltantes = [d for d in lotes_data if d['codigo'] not in lotes_map]
        
        # LLAMADA 2: Crear TODOS los faltantes en una sola llamada
        if faltantes:
            nuevos_ids = self.odoo.execute('stock.lot', 'create', [
                {
                    'name': d['codigo'],
                    'product_id': d['producto_id'],
                    'company_id': 1
                }
                for d in faltantes
            ])
            
            # Si es un solo registro, execute retorna int, sino lista
            if isinstance(nuevos_ids, int):
                nuevos_ids = [nuevos_ids]
            
            # Agregar nuevos al mapa
            for d, nuevo_id in zip(faltantes, nuevos_ids):
                lotes_map[d['codigo']] = nuevo_id
        
        return lotes_map
    
    def _buscar_o_crear_packages_batch(self, package_names: List[str]) -> Dict[str, int]:
        """
        Busca o crea múltiples packages en batch (OPTIMIZADO).
        
        Args:
            package_names: Lista de nombres de packages (ej: ['PACK0002683-C', ...])
            
        Returns:
            Dict mapeando package_name → package_id
        """
        if not package_names:
            return {}
        
        # LLAMADA 1: Buscar todos los packages existentes
        packages_existentes = self.odoo.search_read(
            'stock.quant.package',
            [('name', 'in', package_names)],
            ['name', 'id']
        )
        
        packages_map = {pkg['name']: pkg['id'] for pkg in packages_existentes}
        
        # Identificar los que faltan
        faltantes = [name for name in package_names if name not in packages_map]
        
        # LLAMADA 2: Crear TODOS los faltantes en una sola llamada
        if faltantes:
            nuevos_ids = self.odoo.execute('stock.quant.package', 'create', [
                {'name': name, 'company_id': 1}
                for name in faltantes
            ])
            
            # Si es un solo registro, execute retorna int, sino lista
            if isinstance(nuevos_ids, int):
                nuevos_ids = [nuevos_ids]
            
            # Agregar nuevos al mapa
            for name, nuevo_id in zip(faltantes, nuevos_ids):
                packages_map[name] = nuevo_id
        
        return packages_map
    
    def _buscar_o_crear_lote(self, codigo_lote: str, producto_id: int) -> int:
        """
        Busca un lote por nombre, si no existe lo crea.
        
        Args:
            codigo_lote: Código del lote (ej: PAC0002683 o PAC0002683-C)
            producto_id: ID del producto al que pertenece el lote
            
        Returns:
            ID del lote
        """
        # Buscar lote existente
        lotes = self.odoo.search('stock.lot', [
            ('name', '=', codigo_lote),
            ('product_id', '=', producto_id)
        ])
        
        if lotes:
            return lotes[0]
        
        # Crear nuevo lote
        lote_data = {
            'name': codigo_lote,
            'product_id': producto_id,
            'company_id': 1
        }
        
        lote_id = self.odoo.execute('stock.lot', 'create', lote_data)
        return lote_id
    
    def _crear_componentes(
        self, 
        mo_id: int, 
        mo_name: str,
        productos_totales: Dict,
        config: Dict
    ) -> int:
        """
        Crea los movimientos de componentes (move_raw_ids) para la orden.
        
        Args:
            mo_id: ID de la orden de fabricación
            mo_name: Nombre de la orden
            productos_totales: Dict con {producto_id: {kg, pallets}}
            config: Configuración del túnel
            
        Returns:
            Cantidad de movimientos creados
        """
        movimientos_creados = 0
        ubicacion_virtual = UBICACION_VIRTUAL_CONGELADO_ID if config['sucursal'] == 'RF' else UBICACION_VIRTUAL_PROCESOS_ID
        
        for producto_id, data in productos_totales.items():
            # Crear stock.move principal
            move_data = {
                'name': mo_name,
                'product_id': producto_id,
                'product_uom_qty': data['kg'],
                'product_uom': 12,  # kg
                'location_id': config['ubicacion_origen_id'],
                'location_dest_id': ubicacion_virtual,
                'state': 'draft',
                'raw_material_production_id': mo_id,  # Relación con MO
                'company_id': 1,
                'reference': mo_name
            }
            
            move_id = self.odoo.execute('stock.move', 'create', move_data)
            
            # Crear stock.move.line por cada pallet
            for pallet in data['pallets']:
                # Buscar el lote del pallet
                lote_id = pallet.get('lote_id')
                if not lote_id:
                    lote_id = self._buscar_o_crear_lote(pallet['codigo'], producto_id)
                
                move_line_data = {
                    'move_id': move_id,
                    'product_id': producto_id,
                    'lot_id': lote_id,
                    'qty_done': pallet['kg'],
                    'reserved_uom_qty': pallet['kg'],
                    'product_uom_id': 12,  # kg
                    'location_id': pallet.get('ubicacion_id', config['ubicacion_origen_id']),
                    'location_dest_id': ubicacion_virtual,
                    'state': 'draft',
                    'reference': mo_name,
                    'company_id': 1
                }
                
                self.odoo.execute('stock.move.line', 'create', move_line_data)
            
            movimientos_creados += 1
        
        return movimientos_creados
    
    def _crear_subproductos(
        self,
        mo_id: int,
        mo_name: str,
        productos_totales: Dict,
        config: Dict
    ) -> int:
        """
        Crea los movimientos de subproductos (move_finished_ids) para la orden.
        Genera lotes con sufijo -C y result_package_id.
        
        Args:
            mo_id: ID de la orden de fabricación
            mo_name: Nombre de la orden
            productos_totales: Dict con {producto_id: {kg, pallets}}
            config: Configuración del túnel
            
        Returns:
            Cantidad de movimientos creados
        """
        movimientos_creados = 0
        ubicacion_virtual = UBICACION_VIRTUAL_CONGELADO_ID if config['sucursal'] == 'RF' else UBICACION_VIRTUAL_PROCESOS_ID
        
        for producto_id_input, data in productos_totales.items():
            # Obtener producto congelado (output)
            producto_id_output = PRODUCTOS_TRANSFORMACION.get(producto_id_input)
            
            if not producto_id_output:
                # Si no hay mapeo, usar el mismo producto
                producto_id_output = producto_id_input
            
            # Crear stock.move principal
            move_data = {
                'name': mo_name,
                'product_id': producto_id_output,
                'product_uom_qty': data['kg'],
                'product_uom': 12,  # kg
                'location_id': ubicacion_virtual,
                'location_dest_id': config['ubicacion_destino_id'],
                'state': 'draft',
                'production_id': mo_id,  # Relación con MO (finished)
                'company_id': 1,
                'reference': mo_name
            }
            
            move_id = self.odoo.execute('stock.move', 'create', move_data)
            
            # ✅ OPTIMIZADO: Preparar TODOS los lotes y packages de una vez
            lotes_data = []
            package_names = []
            
            for pallet in data['pallets']:
                # Código con sufijo -C
                codigo_output = f"{pallet['codigo']}-C"
                lotes_data.append({
                    'codigo': codigo_output,
                    'producto_id': producto_id_output
                })
                
                # Nombre de package
                try:
                    numero_pallet = pallet['codigo'].replace('PAC', '').replace('PACK', '')
                    package_name = f"PACK{numero_pallet}-C"
                except:
                    package_name = f"{pallet['codigo'].replace('PAC', 'PACK')}-C"
                
                package_names.append(package_name)
            
            # ✅ Crear TODOS los lotes en batch (2 llamadas máximo)
            lotes_map = self._buscar_o_crear_lotes_batch(lotes_data)
            
            # ✅ Crear TODOS los packages en batch (2 llamadas máximo)
            packages_map = self._buscar_o_crear_packages_batch(package_names)
            
            # Ahora crear los move.lines
            for idx, pallet in enumerate(data['pallets']):
                codigo_output = f"{pallet['codigo']}-C"
                
                # Generar nombre de package
                try:
                    numero_pallet = pallet['codigo'].replace('PAC', '').replace('PACK', '')
                    package_name = f"PACK{numero_pallet}-C"
                except:
                    package_name = f"{pallet['codigo'].replace('PAC', 'PACK')}-C"
                
                # Obtener IDs del mapa (ya creados en batch)
                lote_id_output = lotes_map.get(codigo_output)
                package_id = packages_map.get(package_name)
                
                move_line_data = {
                    'move_id': move_id,
                    'product_id': producto_id_output,
                    'lot_id': lote_id_output,
                    'result_package_id': package_id,
                    'qty_done': pallet['kg'],
                    'reserved_uom_qty': 0.0,  # Los subproductos no tienen reserva
                    'product_uom_id': 12,  # kg
                    'location_id': ubicacion_virtual,
                    'location_dest_id': config['ubicacion_destino_id'],
                    'state': 'draft',
                    'reference': mo_name,
                    'company_id': 1
                }
                
                self.odoo.execute('stock.move.line', 'create', move_line_data)
            
            movimientos_creados += 1
        
        return movimientos_creados
    
    def listar_ordenes_recientes(
        self,
        tunel: Optional[str] = None,
        estado: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Lista las órdenes de fabricación recientes.
        
        Args:
            tunel: Filtrar por túnel (TE1, TE2, TE3, VLK)
            estado: Filtrar por estado (draft, confirmed, progress, done, cancel)
            limit: Límite de resultados
            
        Returns:
            Lista de órdenes con información resumida
        """
        domain = []
        
        # Filtrar por túneles estáticos
        if tunel:
            if tunel in TUNELES_CONFIG:
                domain.append(('product_id', '=', TUNELES_CONFIG[tunel]['producto_proceso_id']))
        else:
            # Todos los túneles
            producto_ids = [config['producto_proceso_id'] for config in TUNELES_CONFIG.values()]
            domain.append(('product_id', 'in', producto_ids))
        
        if estado:
            domain.append(('state', '=', estado))
        
        ordenes = self.odoo.search_read(
            'mrp.production',
            domain,
            ['name', 'product_id', 'product_qty', 'state', 'create_date', 'date_planned_start'],
            limit=limit,
            order='create_date desc'
        )
        
        # Formatear resultados
        resultado = []
        for orden in ordenes:
            # Determinar túnel por producto_id
            tunel_codigo = None
            for codigo, config in TUNELES_CONFIG.items():
                if config['producto_proceso_id'] == orden['product_id'][0]:
                    tunel_codigo = codigo
                    break
            
            resultado.append({
                'id': orden['id'],
                'nombre': orden['name'],
                'tunel': tunel_codigo,
                'producto': orden['product_id'][1] if orden['product_id'] else 'N/A',
                'kg_total': orden['product_qty'],
                'estado': orden['state'],
                'fecha_creacion': orden.get('create_date'),
                'fecha_planificada': orden.get('date_planned_start')
            })
        
        return resultado


def get_tuneles_service(odoo: OdooClient) -> TunelesService:
    """Factory function para obtener el servicio de túneles."""
    return TunelesService(odoo)
