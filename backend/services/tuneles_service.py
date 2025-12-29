"""
Servicio para automatización de órdenes de fabricación en túneles estáticos.
Maneja la lógica de creación de componentes y subproductos con sufijo -C.
"""

import os
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
        'sala_proceso': 'Tunel - Estatico 1',
        'picking_type_id': 192  # Rio Futuro: Congelar TE1 → RF/MO/CongTE1/XXXXX
    },
    'TE2': {
        'producto_proceso_id': 15985,
        'producto_proceso_nombre': '[1.2] PROCESO CONGELADO TÚNEL ESTÁTICO 2',
        'sucursal': 'RF',
        'ubicacion_origen_id': 5452,
        'ubicacion_origen_nombre': 'RF/Stock/Camara 0°C REAL',
        'ubicacion_destino_id': 8479,
        'ubicacion_destino_nombre': 'Tránsito/Salida Túneles Estáticos',
        'sala_proceso': 'Tunel - Estatico 2',
        'picking_type_id': 190  # Rio Futuro: Congelar TE2 → RF/MO/CongTE2/XXXXX
    },
    'TE3': {
        'producto_proceso_id': 15986,
        'producto_proceso_nombre': '[1.3] PROCESO CONGELADO TÚNEL ESTÁTICO 3',
        'sucursal': 'RF',
        'ubicacion_origen_id': 5452,
        'ubicacion_origen_nombre': 'RF/Stock/Camara 0°C REAL',
        'ubicacion_destino_id': 8479,
        'ubicacion_destino_nombre': 'Tránsito/Salida Túneles Estáticos',
        'sala_proceso': 'Tunel - Estatico 3',
        'picking_type_id': 191  # Rio Futuro: Congelar TE3 → RF/MO/CongTE3/XXXXX
    },
    'VLK': {
        'producto_proceso_id': 16446,
        'producto_proceso_nombre': '[1.1.1] PROCESO CONGELADO TÚNEL ESTÁTICO VLK',
        'sucursal': 'VLK',
        'ubicacion_origen_id': 8528,
        'ubicacion_origen_nombre': 'VLK/Camara 0°',
        'ubicacion_destino_id': 8532,
        'ubicacion_destino_nombre': 'Tránsito VLK/Salida Túnel Estático',
        'sala_proceso': 'Tunel - Estatico VLK',
        'picking_type_id': 219  # VILKUN: Congelar TE VLK → MO/CongTE/XXXXX
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
        Valida múltiples pallets buscando por PACKAGE (PACK000XXXX) en 2 llamadas a Odoo.
        
        Args:
            codigos_pallets: Lista de códigos de PACKAGES (ej: PACK0010337)
            buscar_ubicacion: Si True, busca la ubicación real del pallet
            
        Returns:
            Lista de dicts con validación de cada pallet
        """
        if not codigos_pallets:
            return []
        
        resultados = []
        
        # LLAMADA 1: Buscar TODOS los packages en una sola llamada
        packages = self.odoo.search_read(
            'stock.quant.package',
            [('name', 'in', codigos_pallets)],
            ['id', 'name']
        )
        
        # Crear mapa de packages por código
        packages_map = {pkg['name']: pkg for pkg in packages}
        
        # Identificar pallets no encontrados
        codigos_encontrados = set(packages_map.keys())
        codigos_no_encontrados = set(codigos_pallets) - codigos_encontrados
        
        # Agregar resultados de no encontrados
        for codigo in codigos_no_encontrados:
            # --- BÚSQUEDA EN RECEPCIONES PENDIENTES ---
            reception_info = None
            try:
                # PASO 1: Buscar el package por nombre para obtener su ID
                pkg_search = self.odoo.search_read(
                    'stock.quant.package', 
                    [('name', '=', codigo)], 
                    ['id'],
                    limit=1
                )
                
                move_lines = []
                if pkg_search:
                    pkg_id = pkg_search[0]['id']
                    
                    # PASO 2: Buscar move_lines que usen este package como destino
                    # SIN filtro de estado de move_line - buscamos todo
                    move_lines = self.odoo.search_read(
                        'stock.move.line', 
                        [
                            ('result_package_id', '=', pkg_id),
                            ('picking_id', '!=', False)
                        ], 
                        ['picking_id', 'product_id', 'qty_done', 'reserved_uom_qty'],
                        limit=5,
                        order='id desc'
                    )
                    
                    # Si no hay como destino, buscar como origen
                    if not move_lines:
                        move_lines = self.odoo.search_read(
                            'stock.move.line', 
                            [
                                ('package_id', '=', pkg_id),
                                ('picking_id', '!=', False)
                            ], 
                            ['picking_id', 'product_id', 'qty_done', 'reserved_uom_qty'],
                            limit=5,
                            order='id desc'
                        )
                
                # PASO 3: Filtrar para obtener picking que NO esté done/cancel
                for ml in move_lines:
                    picking_id = ml['picking_id'][0]
                    picking_name = ml['picking_id'][1]
                    
                    # Obtener estado del picking
                    picking = self.odoo.search_read(
                        'stock.picking', 
                        [('id', '=', picking_id)], 
                        ['state'],
                        limit=1
                    )
                    
                    if picking and picking[0]['state'] not in ['done', 'cancel']:
                        state = picking[0]['state']
                        
                        # Generar URL de Odoo (usar env var)
                        base_url = os.environ.get('ODOO_URL', 'https://riofuturo.odoo.com')
                        odoo_url = f"{base_url}/web#id={picking_id}&model=stock.picking&view_type=form"
                        
                        # Obtener Kg: usar qty_done si existe, sino reserved_uom_qty
                        kg = ml['qty_done'] if ml['qty_done'] and ml['qty_done'] > 0 else ml.get('reserved_uom_qty', 0)
                        
                        reception_info = {
                            'found_in_reception': True,
                            'picking_name': picking_name,
                            'picking_id': picking_id,
                            'state': state,
                            'odoo_url': odoo_url,
                            'product_name': ml['product_id'][1] if ml['product_id'] else 'Desconocido',
                            'kg': kg, 
                            'product_id': ml['product_id'][0] if ml['product_id'] else None
                        }
                        break  # Encontramos uno válido, salimos del loop
                        
            except Exception as e:
                print(f"Error buscando recepción para {codigo}: {e}")

            if reception_info:
                resultados.append({
                    'existe': False, # Falso en stock disponible
                    'codigo': codigo,
                    'error': f'Pallet en recepción pendiente: {reception_info["picking_name"]}',
                    'reception_info': reception_info,
                    'kg': reception_info['kg'],
                    'product_id': reception_info['product_id'],
                    'producto_nombre': reception_info['product_name']
                })
            else:
                resultados.append({
                    'existe': False,
                    'codigo': codigo,
                    'error': f'Paquete {codigo} no encontrado en Odoo',
                    'reception_info': None
                })
        
        # Si no hay packages encontrados, retornar
        if not packages:
            return resultados
        
        # LLAMADA 2: Buscar TODOS los quants asociados a esos packages
        package_ids = [pkg['id'] for pkg in packages]
        quants = self.odoo.search_read(
            'stock.quant',
            [('package_id', 'in', package_ids), ('quantity', '>', 0)],
            ['package_id', 'lot_id', 'quantity', 'location_id', 'product_id']
        )
        
        # Agrupar quants por package_id
        quants_por_package = {}
        for quant in quants:
            pkg_id = quant['package_id'][0]
            if pkg_id not in quants_por_package:
                quants_por_package[pkg_id] = []
            quants_por_package[pkg_id].append(quant)
        
        # Procesar cada package encontrado
        for codigo in codigos_encontrados:
            package = packages_map[codigo]
            pkg_quants = quants_por_package.get(package['id'], [])
            
            if not pkg_quants:
                # Package existe pero sin stock - BUSCAR EN RECEPCIONES PENDIENTES
                reception_info = None
                try:
                    move_lines = self.odoo.search_read(
                        'stock.move.line', 
                        [
                            ('result_package_id', '=', package['id']),
                            ('picking_id', '!=', False)
                        ], 
                        ['picking_id', 'product_id', 'qty_done', 'reserved_uom_qty', 'lot_id'],
                        limit=5,
                        order='id desc'
                    )
                    
                    for ml in move_lines:
                        picking_id = ml['picking_id'][0]
                        picking_name = ml['picking_id'][1]
                        
                        picking = self.odoo.search_read(
                            'stock.picking', 
                            [('id', '=', picking_id)], 
                            ['state'],
                            limit=1
                        )
                        
                        if picking and picking[0]['state'] not in ['done', 'cancel']:
                            state = picking[0]['state']
                            base_url = os.environ.get('ODOO_URL', 'https://riofuturo.odoo.com')
                            odoo_url = f"{base_url}/web#id={picking_id}&model=stock.picking&view_type=form"
                            kg = ml['qty_done'] if ml['qty_done'] and ml['qty_done'] > 0 else ml.get('reserved_uom_qty', 0)
                            
                            # Extraer info del lote
                            lot_id = ml['lot_id'][0] if ml.get('lot_id') else None
                            lot_name = ml['lot_id'][1] if ml.get('lot_id') else None
                            
                            reception_info = {
                                'found_in_reception': True,
                                'picking_name': picking_name,
                                'picking_id': picking_id,
                                'state': state,
                                'odoo_url': odoo_url,
                                'product_name': ml['product_id'][1] if ml['product_id'] else 'Desconocido',
                                'kg': kg,
                                'product_id': ml['product_id'][0] if ml['product_id'] else None,
                                'lot_id': lot_id,
                                'lot_name': lot_name
                            }
                            break
                except Exception as e:
                    print(f"Error buscando recepción para {codigo}: {e}")
                
                if reception_info:
                    resultados.append({
                        'existe': False,
                        'codigo': codigo,
                        'error': f'Pallet en recepción pendiente: {reception_info["picking_name"]}',
                        'reception_info': reception_info,
                        'kg': reception_info['kg'],
                        'product_id': reception_info['product_id'],
                        'producto_nombre': reception_info['product_name']
                    })
                else:
                    resultados.append({
                        'existe': True,
                        'codigo': codigo,
                        'kg': 0.0,
                        'ubicacion_id': None,
                        'ubicacion_nombre': None,
                        'producto_id': None,
                        'package_id': package['id'],
                        'advertencia': 'Paquete sin stock disponible'
                    })
                continue
            
            # Sumar cantidades
            kg_total = sum(q['quantity'] for q in pkg_quants)
            
            # Usar primera ubicación y producto
            ubicacion = pkg_quants[0]['location_id']
            producto_id = pkg_quants[0]['product_id'][0] if pkg_quants[0]['product_id'] else None
            lote_id = pkg_quants[0]['lot_id'][0] if pkg_quants[0].get('lot_id') else None
            
            resultados.append({
                'existe': True,
                'codigo': codigo,
                'kg': kg_total,
                'ubicacion_id': ubicacion[0] if ubicacion else None,
                'ubicacion_nombre': ubicacion[1] if ubicacion else None,
                'producto_id': producto_id,
                'producto_nombre': pkg_quants[0]['product_id'][1] if pkg_quants[0]['product_id'] else None,
                'package_id': package['id'],
                'lote_id': lote_id
            })
        
        return resultados
    
    def validar_pallet(self, codigo_pallet: str, buscar_ubicacion: bool = False) -> Dict:
        """
        Valida un solo pallet buscando por PACKAGE (wrapper sobre validar_pallets_batch).
        
        Args:
            codigo_pallet: Código del PACKAGE (ej: PACK0010337)
            buscar_ubicacion: Si True, busca la ubicación real del pallet
            
        Returns:
            Dict con: existe, kg, ubicacion_id, ubicacion_nombre, producto_id, package_id
        """
        resultados = self.validar_pallets_batch([codigo_pallet], buscar_ubicacion)
        return resultados[0] if resultados else {
            'existe': False,
            'codigo': codigo_pallet,
            'error': 'Error al validar pallet'
        }
    
    def verificar_pendientes(self, mo_id: int) -> Dict:
        """
        Verifica el estado de las recepciones pendientes de una MO.
        
        Args:
            mo_id: ID de la orden de fabricación
            
        Returns:
            Dict con: mo_name, has_pending, pickings (con estado actual), all_ready
        """
        import json
        
        try:
            # Leer la MO
            mo = self.odoo.search_read(
                'mrp.production',
                [('id', '=', mo_id)],
                ['name', 'x_studio_pending_receptions', 'state'],
                limit=1
            )
            
            if not mo:
                return {'success': False, 'error': 'MO no encontrada'}
            
            mo = mo[0]
            pending_json = mo.get('x_studio_pending_receptions')
            
            # Si no hay datos JSON o está vacío
            if not pending_json:
                return {
                    'success': True,
                    'mo_name': mo['name'],
                    'has_pending': False,
                    'all_ready': True,
                    'pickings': []
                }
            
            # Parsear JSON
            try:
                pending_data = json.loads(pending_json) if isinstance(pending_json, str) else pending_json
            except:
                return {
                    'success': True,
                    'mo_name': mo['name'],
                    'has_pending': True,
                    'all_ready': False,
                    'pickings': [],
                    'error': 'Error al parsear JSON de pendientes'
                }
            
            # Si pending es False, no hay pendientes
            if not pending_data.get('pending', True):
                return {
                    'success': True,
                    'mo_name': mo['name'],
                    'has_pending': False,
                    'all_ready': True,
                    'pickings': []
                }
            
            picking_ids = pending_data.get('picking_ids', [])
            
            # Verificar estado de cada picking
            pickings = self.odoo.search_read(
                'stock.picking',
                [('id', 'in', picking_ids)],
                ['name', 'state', 'id']
            )
            
            pickings_info = []
            all_done = True
            
            for p in pickings:
                is_done = p['state'] == 'done'
                pickings_info.append({
                    'id': p['id'],
                    'name': p['name'],
                    'state': p['state'],
                    'is_done': is_done
                })
                if not is_done:
                    all_done = False
            
            return {
                'success': True,
                'mo_id': mo_id,
                'mo_name': mo['name'],
                'mo_state': mo['state'],
                'has_pending': True,
                'all_ready': all_done,
                'pickings': pickings_info,
                'pending_count': len([p for p in pickings_info if not p['is_done']]),
                'ready_count': len([p for p in pickings_info if p['is_done']])
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def completar_pendientes(self, mo_id: int) -> Dict:
        """
        Quita el flag de pendientes cuando todas las recepciones están validadas.
        
        Args:
            mo_id: ID de la orden de fabricación
            
        Returns:
            Dict con: success, mensaje
        """
        try:
            # Primero verificar que todas estén listas
            verificacion = self.verificar_pendientes(mo_id)
            
            if not verificacion.get('success'):
                return verificacion
            
            if not verificacion.get('all_ready'):
                pending = verificacion.get('pending_count', 0)
                return {
                    'success': False,
                    'error': f'Aún hay {pending} recepciones pendientes de validar'
                }
            
            # Limpiar el JSON de pendientes (marcar como completado)
            import json
            completed_data = json.dumps({
                'pending': False,
                'completed_at': datetime.now().isoformat()
            })
            # Usar execute_kw directamente con formato correcto
            self.odoo.models.execute_kw(
                self.odoo.db, self.odoo.uid, self.odoo.password,
                'mrp.production', 'write',
                [[mo_id], {'x_studio_pending_receptions': completed_data}]
            )
            
            return {
                'success': True,
                'mo_id': mo_id,
                'mo_name': verificacion['mo_name'],
                'mensaje': 'Flag de pendientes removido. MO lista para confirmar.'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
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
        
        # 0. VALIDAR DUPLICADOS: Verificar que los pallets no estén en otras MOs activas
        codigos_pallets = [p['codigo'] for p in pallets]
        
        # Buscar packages con estos códigos
        packages = self.odoo.search_read(
            'stock.quant.package',
            [('name', 'in', codigos_pallets)],
            ['id', 'name']
        )
        package_ids = [pkg['id'] for pkg in packages]
        packages_map = {pkg['name']: pkg['id'] for pkg in packages}
        
        if package_ids:
            # Buscar en stock.move.line si estos packages están en MOs no canceladas/terminadas
            move_lines = self.odoo.search_read(
                'stock.move.line',
                [
                    ('package_id', 'in', package_ids),
                    ('production_id', '!=', False)
                ],
                ['package_id', 'production_id'],
                limit=100
            )
            
            if move_lines:
                # Verificar estado de las MOs encontradas
                mo_ids = list(set([ml['production_id'][0] for ml in move_lines]))
                mos = self.odoo.search_read(
                    'mrp.production',
                    [('id', 'in', mo_ids), ('state', 'not in', ['done', 'cancel'])],
                    ['id', 'name', 'state']
                )
                
                if mos:
                    # Mapear package_id a mo_name
                    pkg_to_mo = {}
                    for ml in move_lines:
                        pkg_id = ml['package_id'][0]
                        mo_id = ml['production_id'][0]
                        mo_match = [m for m in mos if m['id'] == mo_id]
                        if mo_match:
                            pkg_to_mo[pkg_id] = mo_match[0]['name']
                    
                    # Verificar si algún pallet de la lista está en estas MOs
                    for codigo in codigos_pallets:
                        pkg_id = packages_map.get(codigo)
                        if pkg_id and pkg_id in pkg_to_mo:
                            errores.append(f"{codigo}: Ya está en orden {pkg_to_mo[pkg_id]} (activa)")
        
        if errores:
            return {
                'success': False,
                'errores': errores,
                'error': f"Pallets ya usados en otras órdenes activas: {', '.join(codigos_pallets[:3])}"
            }
        
        # 1. Validar todos los pallets primero
        pallets_validados = []
        for pallet in pallets:
            # --- NUEVO FLUJO: Pallets que están en Recepción Pendiente ---
            if pallet.get('pendiente_recepcion'):
                # Validamos que traiga data mínima
                if not pallet.get('producto_id'):
                     errores.append(f"{pallet['codigo']}: Pallet pendiente sin producto identificado")
                     continue
                
                pallets_validados.append({
                    'codigo': pallet['codigo'],
                    'kg': float(pallet.get('kg', 0)),
                    'lote_id': pallet.get('lot_id'),  # Puede venir del frontend
                    'producto_id': int(pallet['producto_id']),
                    'ubicacion_id': config['ubicacion_origen_id'], 
                    'package_id': None,  # No asignamos package aún
                    'manual': False,
                    'pendiente_recepcion': True,  # Flag para saber que es especial
                    'picking_id': pallet.get('picking_id')  # Guardar picking_id para JSON
                })
                advertencias.append(f"Pallet {pallet['codigo']} agregado desde Recepción Pendiente (Sin reserva stock)")
                continue

            # --- MEJORA: Soporte para Pallets Manuales (Legacy/Fallback) ---
            if pallet.get('manual'):
                # Si es manual, confiamos en los datos enviados
                if not pallet.get('producto_id'):
                    errores.append(f"{pallet['codigo']}: Pallet manual debe incluir producto_id")
                    continue
                if not pallet.get('kg') or pallet['kg'] <= 0:
                    errores.append(f"{pallet['codigo']}: Pallet manual debe incluir Kg > 0")
                    continue
                
                pallets_validados.append({
                    'codigo': pallet['codigo'],
                    'kg': pallet['kg'],
                    'lote_id': None, # Sin lote en Odoo
                    'producto_id': pallet['producto_id'],
                    'ubicacion_id': config['ubicacion_origen_id'], # Usar ubicación por defecto del túnel
                    'package_id': None, # Sin package en Odoo
                    'manual': True # Marcamos como manual
                })
                advertencias.append(f"Pallet {pallet['codigo']} ingresado manualmente sin trazabilidad")
                continue
            
            # Flujo normal: Validar en Odoo
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
                'ubicacion_id': validacion.get('ubicacion_id', config['ubicacion_origen_id']),
                'package_id': validacion.get('package_id'),  # ID del paquete origen
                'manual': False
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
            # --- MEJORA: Fechas sincronizadas ---
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            mo_data = {
                'product_id': config['producto_proceso_id'],
                'product_qty': total_kg,
                'product_uom_id': 12,  # kg
                'location_src_id': config['ubicacion_origen_id'],
                'location_dest_id': config['ubicacion_destino_id'],
                'picking_type_id': config['picking_type_id'],  # Tipo de operación para correlativo
                'state': 'draft',  # Borrador
                'company_id': 1,  # RIO FUTURO PROCESOS SPA
                'date_planned_start': now,
                'date_planned_finished': now,
                'x_studio_inicio_de_proceso': now,
                'x_studio_termino_de_proceso': now,
            }
            
            if responsable_id:
                mo_data['user_id'] = responsable_id
            
            mo_id = self.odoo.execute('mrp.production', 'create', mo_data)
            
            # --- MEJORA: Limpiar componentes del BoM por defecto ---
            # Al crear la MO, Odoo inserta componentes del BoM. Debemos borrarlos.
            mo_data_read = self.odoo.read('mrp.production', [mo_id], ['move_raw_ids', 'name'])[0]
            if mo_data_read.get('move_raw_ids'):
                self.odoo.execute('stock.move', 'unlink', mo_data_read['move_raw_ids'])
            
            mo_name = mo_data_read['name']
            
            # --- NUEVO: Detectar pallets pendientes y marcar MO ---
            pallets_pendientes = [p for p in pallets_validados if p.get('pendiente_recepcion')]
            has_pending = len(pallets_pendientes) > 0
            
            if has_pending:
                # Crear estructura JSON con datos de pendientes
                pending_data = {
                    'pending': True,
                    'created_at': datetime.now().isoformat(),
                    'pallets': []
                }
                
                picking_ids_set = set()
                for p in pallets_pendientes:  # Usar pallets_validados filtrados
                    if p.get('picking_id'):
                        picking_ids_set.add(p['picking_id'])
                    pending_data['pallets'].append({
                        'codigo': p['codigo'],
                        'picking_id': p.get('picking_id'),
                        'kg': p.get('kg', 0),
                        'producto_id': p.get('producto_id')
                    })
                
                pending_data['picking_ids'] = list(picking_ids_set)
                
                # Actualizar MO con JSON de pendientes
                try:
                    import json
                    pending_json = json.dumps(pending_data)
                    print(f"DEBUG: Intentando guardar JSON en MO {mo_id}: {pending_json[:100]}...")
                    # Usar execute_kw directamente con formato correcto para write
                    write_result = self.odoo.models.execute_kw(
                        self.odoo.db, self.odoo.uid, self.odoo.password,
                        'mrp.production', 'write',
                        [[mo_id], {'x_studio_pending_receptions': pending_json}]
                    )
                    print(f"DEBUG: Resultado del write: {write_result}")
                    if write_result:
                        advertencias.append(f"MO marcada con {len(pallets_pendientes)} pallets pendientes de recepción")
                    else:
                        advertencias.append(f"Write retornó False para guardar pendientes")
                except Exception as e:
                    print(f"DEBUG: Error en write: {e}")
                    advertencias.append(f"Error al guardar pendientes: {e}")
            
            # 4. Crear componentes (move_raw_ids)
            componentes_creados = self._crear_componentes(
                mo_id, 
                mo_name, 
                productos_totales, 
                config
            )

            # NOTA: Electricidad ya se agrega en _crear_componentes

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
                'has_pending': has_pending,
                'pending_count': len(pallets_pendientes),
                'mensaje': f'Orden {mo_name} creada con {componentes_creados} componentes y {subproductos_creados} subproductos' + 
                          (f' ({len(pallets_pendientes)} pallets pendientes de recepción)' if has_pending else '')
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
                # Obtener lote_id del quant del pallet (viene de la validación)
                lote_id = pallet.get('lote_id')
                package_id = pallet.get('package_id')  # ID del package origen
                
                move_line_data = {
                    'move_id': move_id,
                    'product_id': producto_id,
                    'qty_done': pallet['kg'],
                    'reserved_uom_qty': pallet['kg'],
                    'product_uom_id': 12,  # kg
                    'location_id': pallet.get('ubicacion_id', config['ubicacion_origen_id']),
                    'location_dest_id': ubicacion_virtual,
                    'state': 'draft',
                    'reference': mo_name,
                    'company_id': 1
                }
                
                # Agregar lote si existe
                if lote_id:
                    move_line_data['lot_id'] = lote_id
                
                # Agregar package de origen si existe
                if package_id:
                    move_line_data['package_id'] = package_id
                
                self.odoo.execute('stock.move.line', 'create', move_line_data)
            
            movimientos_creados += 1
        
        # --- Agregar componente de Electricidad ---
        # Producto: Provisión Electricidad Túnel Estático ($/hr)
        # Buscamos por código 'ETE' en product.product (no template)
        try:
            total_kg = sum(data['kg'] for data in productos_totales.values())
            
            # Buscar product.product por código
            ete_products = self.odoo.models.execute_kw(
                self.odoo.db, self.odoo.uid, self.odoo.password,
                'product.product', 'search_read',
                [[('default_code', '=', 'ETE')]],
                {'fields': ['id', 'name'], 'limit': 1}
            )
            
            if ete_products:
                ete_id = ete_products[0]['id']
                print(f"DEBUG: Producto electricidad encontrado por código: ID={ete_id}")
            else:
                # Fallback: Usar ID hardcodeado
                ete_id = PRODUCTO_ELECTRICIDAD_ID
                print(f"DEBUG: Producto ETE no encontrado por código, usando ID fijo: {ete_id}")

            # Validar que tengamos un ID válido (aunque sea el fijo)
            if ete_id:
                elect_move = {
                    'name': mo_name,
                    'product_id': ete_id,
                    'product_uom_qty': total_kg,
                    'product_uom': 12,  # kg
                    'location_id': config['ubicacion_origen_id'],
                    'location_dest_id': ubicacion_virtual,
                    'state': 'draft',
                    'raw_material_production_id': mo_id,
                    'company_id': 1,
                    'reference': mo_name
                }
                self.odoo.models.execute_kw(
                    self.odoo.db, self.odoo.uid, self.odoo.password,
                    'stock.move', 'create', [elect_move]
                )
                movimientos_creados += 1
                print(f"DEBUG: Electricidad agregada correctamente")
        except Exception as e:
            print(f"Advertencia: No se pudo agregar electricidad: {e}")
        
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
            ['name', 'product_id', 'product_qty', 'state', 'create_date', 'date_planned_start', 'x_studio_pending_receptions'],
            limit=limit,
            order='create_date desc'
        )
        
        # Formatear resultados
        resultado = []
        
        # Optimización: Buscar qué órdenes tienen componentes sin lote asignado (Pendientes)
        mo_ids = [o['id'] for o in ordenes]
        if mo_ids:
            # Buscamos moves asociados a estas MOs que NO tengan lote asignado y requerían (no son consumibles/servicios)
            # Simplificación: Si tenemos move lines sin lot_id pero con qty_done/product_uom_qty > 0
            # En Odoo 16 'stock.move' tiene 'move_line_ids'. 
            # Hacemos una búsqueda directa de moves que pertenezcan a las MOs y no tengan lote, 
            # asumiendo que nuestros pallets manuales/pendientes se crearon sin lote.
            
            # Nota: Al estar en Borrador (draft), los moves existen. 
            # Buscamos moves con estado 'draft' y sin lote, pero cuidado con componentes que no usan lote.
            # Nuestros componentes de fruta SI usan lote.
            
            moves_sin_lote = self.odoo.search_read(
                'stock.move.line',
                [
                    ('reference', 'in', [o['name'] for o in ordenes]), # Referencia suele ser el nombre de la MO
                    ('lot_id', '=', False),
                    ('qty_done', '>', 0) # Tienen cantidad asignada
                ],
                ['reference']
            )
            moves_pendientes_refs = set(m['reference'] for m in moves_sin_lote)
        else:
            moves_pendientes_refs = set()

        for orden in ordenes:
            # Determinar túnel por producto_id
            tunel_codigo = None
            for codigo, config in TUNELES_CONFIG.items():
                if config['producto_proceso_id'] == orden['product_id'][0]:
                    tunel_codigo = codigo
                    break
            
            # Determinar tiene_pendientes desde el campo JSON o desde moves sin lote
            tiene_pendientes = orden['name'] in moves_pendientes_refs
            
            # Priorizar el campo JSON si existe
            pending_json = orden.get('x_studio_pending_receptions')
            if pending_json:
                try:
                    import json
                    print(f"DEBUG listar: MO {orden['name']} tiene pending_json: {str(pending_json)[:50]}...")
                    pending_data = json.loads(pending_json) if isinstance(pending_json, str) else pending_json
                    if pending_data.get('pending'):
                        tiene_pendientes = True
                        print(f"DEBUG listar: MO {orden['name']} marcada como tiene_pendientes=True")
                except Exception as e:
                    print(f"DEBUG listar: Error parseando JSON para {orden['name']}: {e}")
            
            resultado.append({
                'id': orden['id'],
                'nombre': orden['name'],
                'tunel': tunel_codigo,
                'producto': orden['product_id'][1] if orden['product_id'] else 'N/A',
                'kg_total': orden['product_qty'],
                'estado': orden['state'],
                'fecha_creacion': orden.get('create_date'),
                'fecha_planificada': orden.get('date_planned_start'),
                'tiene_pendientes': tiene_pendientes  # Nuevo Flag
            })
        
        return resultado


def get_tuneles_service(odoo: OdooClient) -> TunelesService:
    """Factory function para obtener el servicio de túneles."""
    return TunelesService(odoo)
