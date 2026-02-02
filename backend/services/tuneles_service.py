"""
Servicio para automatización de órdenes de fabricación en túneles estáticos.
Maneja la lógica de creación de componentes y subproductos con sufijo -C.

REFACTORIZADO: Constantes y helpers extraídos a módulos separados.
"""

import os
from typing import List, Dict, Optional, Any
from datetime import datetime
from shared.odoo_client import OdooClient

# Importar desde módulos modularizados
from .tuneles.constants import (
    TUNELES_CONFIG,
    PRODUCTOS_TRANSFORMACION,
    PRODUCTO_ELECTRICIDAD_ID,
    UOM_DOLARES_KG_ID,
    UBICACION_VIRTUAL_CONGELADO_ID,
    UBICACION_VIRTUAL_PROCESOS_ID
)
from .tuneles.helpers import (
    buscar_o_crear_lotes_batch,
    buscar_o_crear_packages_batch,
    buscar_o_crear_lote
)
from .tuneles.pallet_validator import (
    validar_pallets_batch as _validar_pallets_batch,
    check_pallets_duplicados as _check_pallets_duplicados
)
from .tuneles.pendientes import (
    verificar_pendientes as _verificar_pendientes,
    obtener_detalle_pendientes as _obtener_detalle_pendientes,
    completar_pendientes as _completar_pendientes,
    reset_estado_pendientes as _reset_estado_pendientes
)


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
        """Valida múltiples pallets (delegado al módulo pallet_validator)."""
        return _validar_pallets_batch(self.odoo, codigos_pallets, buscar_ubicacion)
    
    def validar_pallet(self, codigo_pallet: str, buscar_ubicacion: bool = False) -> Dict:
        """Valida un solo pallet (wrapper sobre validar_pallets_batch)."""
        resultados = self.validar_pallets_batch([codigo_pallet], buscar_ubicacion)
        return resultados[0] if resultados else {
            'existe': False,
            'codigo': codigo_pallet,
            'error': 'Error al validar pallet'
        }
    
    def verificar_pendientes(self, mo_id: int) -> Dict:
        """Verifica el estado de recepciones pendientes (delegado al módulo pendientes)."""
        return _verificar_pendientes(self.odoo, mo_id)
    
    def completar_pendientes(self, mo_id: int) -> Dict:
        """Completa los pendientes si todos están agregados (delegado al módulo pendientes)."""
        return _completar_pendientes(self.odoo, mo_id)
    
    def reset_estado_pendientes(self, mo_id: int) -> Dict:
        """Resetea el estado de pendientes para re-validación (delegado al módulo pendientes)."""
        return _reset_estado_pendientes(self.odoo, mo_id)
    
    def obtener_detalle_pendientes(self, mo_id: int) -> Dict:
        """Obtiene detalle de pallets pendientes (delegado al módulo pendientes)."""
        return _obtener_detalle_pendientes(self.odoo, mo_id)
    
    def agregar_componentes_disponibles(self, mo_id: int) -> Dict:
        """
        Agrega como componentes los pallets que ahora están disponibles.
        
        Args:
            mo_id: ID de la orden de fabricación
            
        Returns:
            Dict con: success, agregados (cantidad), mensaje
        """
        try:
            import json
            
            # Obtener detalle actual
            detalle = self.obtener_detalle_pendientes(mo_id)
            if not detalle.get('success'):
                return detalle
            
            if not detalle.get('hay_disponibles_sin_agregar'):
                return {
                    'success': True,
                    'agregados': 0,
                    'mensaje': 'No hay pallets disponibles pendientes de agregar'
                }
            
            # Obtener config del túnel basado en la MO
            mo_data = self.odoo.read('mrp.production', [mo_id], 
                ['name', 'product_id', 'x_studio_pending_receptions'])[0]
            mo_name = mo_data['name']
            
            # Identificar túnel por producto
            config = None
            for codigo, cfg in TUNELES_CONFIG.items():
                if cfg['producto_proceso_id'] == mo_data['product_id'][0]:
                    config = cfg
                    break
            
            if not config:
                return {
                    'success': False,
                    'error': 'No se pudo identificar el túnel de esta MO'
                }
            
            ubicacion_virtual = UBICACION_VIRTUAL_CONGELADO_ID if config['sucursal'] == 'RF' else UBICACION_VIRTUAL_PROCESOS_ID
            
            # Procesar pallets disponibles
            agregados = 0
            pallets_agregados = []
            pending_json = mo_data.get('x_studio_pending_receptions')
            pending_data = json.loads(pending_json) if isinstance(pending_json, str) else pending_json
            
            for pallet in detalle['pallets']:
                if pallet['estado'] != 'disponible':
                    continue
                
                codigo = pallet['codigo']
                producto_id = pallet['producto_id']
                quant_info = pallet.get('quant_info', {})
                kg = quant_info.get('quantity', pallet['kg'])
                lote_id = quant_info.get('lot_id', [None])[0] if quant_info.get('lot_id') else None
                # FIX: Asegurar que ubicacion_id nunca sea None
                ubicacion_id_raw = quant_info.get('location_id', [None])[0] if quant_info.get('location_id') else None
                ubicacion_id = ubicacion_id_raw or config['ubicacion_origen_id']
                
                # Buscar el package_id
                package = self.odoo.search_read(
                    'stock.quant.package',
                    [('name', '=', codigo)],
                    ['id'],
                    limit=1
                )
                package_id = package[0]['id'] if package else None
                
                # --- MEJORA: Buscar stock.move existente para NO duplicar demanda ---
                # Buscamos el move_id que ya creamos al inicio (el que tiene la demanda)
                moves = self.odoo.search_read(
                    'stock.move',
                    [
                        ('raw_material_production_id', '=', mo_id),
                        ('product_id', '=', producto_id),
                        ('state', '!=', 'cancel')
                    ],
                    ['id'],
                    limit=1
                )
                
                if moves:
                    move_id = moves[0]['id']
                else:
                    # Fallback por si alguien borró la línea manual en Odoo
                    move_data = {
                        'name': mo_name,
                        'product_id': producto_id,
                        'product_uom_qty': kg,
                        'product_uom': 12,  # kg
                        'location_id': ubicacion_id,
                        'location_dest_id': ubicacion_virtual,
                        'state': 'draft',
                        'raw_material_production_id': mo_id,
                        'company_id': 1,
                        'reference': mo_name
                    }
                    move_id = self.odoo.execute('stock.move', 'create', move_data)
                
                # Crear stock.move.line con qty_done
                move_line_data = {
                    'move_id': move_id,
                    'product_id': producto_id,
                    'qty_done': kg,
                    'reserved_uom_qty': kg,
                    'product_uom_id': 12,
                    'location_id': ubicacion_id,
                    'location_dest_id': ubicacion_virtual,
                    'state': 'draft',
                    'reference': mo_name,
                    'company_id': 1
                }
                
                if lote_id:
                    move_line_data['lot_id'] = lote_id
                if package_id:
                    move_line_data['package_id'] = package_id
                
                self.odoo.execute('stock.move.line', 'create', move_line_data)

                # --- LIMPIAR LÍNEAS ANTIGUAS CON kg=0 DEL COMPONENTE ---
                # Buscar líneas del mismo move con qty_done=0 y package_id
                lineas_vacias = self.odoo.search_read(
                    'stock.move.line',
                    [
                        ('move_id', '=', move_id),
                        ('qty_done', '=', 0),
                        ('package_id', '!=', False)
                    ],
                    ['id']
                )
                if lineas_vacias:
                    ids_a_borrar = [l['id'] for l in lineas_vacias]
                    self.odoo.execute('stock.move.line', 'unlink', ids_a_borrar)

                # --- NUEVO: También crear la línea de SUBPRODUCTO (-C) ---
                # Ya que también se saltó al crear la MO
                try:
                    # Determinar producto de salida
                    # Transformar código: primer dígito 1 → 2 para variante congelada
                    producto_id_output = producto_id # Fallback
                    prod_input_data = self.odoo.read('product.product', [producto_id], ['default_code'])[0]
                    codigo_input = prod_input_data.get('default_code')
                    if codigo_input and len(codigo_input) >= 1 and codigo_input[0] == '1':
                        codigo_output = '2' + codigo_input[1:]
                        prod_output_ids = self.odoo.search('product.product', [('default_code', '=', codigo_output)])
                        if prod_output_ids:
                            producto_id_output = prod_output_ids[0]

                    # Buscar el stock.move de salida existente en la MO
                    moves_out = self.odoo.search_read(
                        'stock.move',
                        [
                            ('production_id', '=', mo_id),
                            ('product_id', '=', producto_id_output),
                            ('state', '!=', 'cancel')
                        ],
                        ['id'],
                        limit=1
                    )
                    
                    if moves_out:
                        move_out_id = moves_out[0]['id']
                        
                        # Generar nombres para lote y package -C
                        # CORRECCIÓN: Obtener el lote REAL del quant, no usar el código del pallet
                        lote_nombre_real = quant_info.get('lot_id', [None, None])[1] if quant_info.get('lot_id') else None
                        
                        if lote_nombre_real:
                            # Si el lote ya tiene -C, no duplicar
                            if lote_nombre_real.endswith('-C'):
                                lote_name_out = lote_nombre_real
                            else:
                                lote_name_out = f"{lote_nombre_real}-C"
                        else:
                            # Fallback: usar código del pallet
                            lote_name_out = f"{codigo}-C"
                        
                        # Limpiar nombre del pallet para el sufijo -C
                        clean_code = codigo[4:] if codigo.startswith('PACK') else codigo[3:] if codigo.startswith('PAC') else codigo
                        package_name_out = f"PACK{clean_code}-C"
                        
                        # Buscar/Crear Lote y Package de salida
                        lote_id_out = self._buscar_o_crear_lote(lote_name_out, producto_id_output)
                        pkgs_out = self.odoo.search('stock.quant.package', [('name', '=', package_name_out)])
                        if pkgs_out:
                            package_id_out = pkgs_out[0]
                        else:
                            package_id_out = self.odoo.execute('stock.quant.package', 'create', {'name': package_name_out, 'company_id': 1})
                        
                        # --- LIMPIAR LÍNEAS ANTIGUAS CON kg=0 DEL SUBPRODUCTO ---
                        lineas_vacias_out = self.odoo.search_read(
                            'stock.move.line',
                            [
                                ('move_id', '=', move_out_id),
                                ('qty_done', '=', 0),
                                ('result_package_id', '!=', False)
                            ],
                            ['id']
                        )
                        if lineas_vacias_out:
                            ids_a_borrar_out = [l['id'] for l in lineas_vacias_out]
                            self.odoo.execute('stock.move.line', 'unlink', ids_a_borrar_out)
                        
                        # Crear la línea de subproducto (stock.move.line)
                        subprod_line = {
                            'move_id': move_out_id,
                            'product_id': producto_id_output,
                            'qty_done': kg,
                            'product_uom_id': 12, # kg
                            'location_id': ubicacion_virtual,
                            'location_dest_id': config['ubicacion_destino_id'],
                            'lot_id': lote_id_out,
                            'result_package_id': package_id_out,
                            'state': 'draft',
                            'reference': mo_name,
                            'company_id': 1
                        }
                        self.odoo.execute('stock.move.line', 'create', subprod_line)
                except Exception as e_sub:
                    print(f"ERROR: No se pudo crear subproducto para {codigo}: {e_sub}")
                
                agregados += 1
                pallets_agregados.append(codigo)
            
            # NUEVO: Actualizar JSON con estado y historial
            for p in pending_data.get('pallets', []):
                if p.get('codigo') in pallets_agregados:
                    p['estado_ultima_revision'] = 'agregado'
                    p['timestamp_agregado'] = datetime.now().isoformat()
            
            # Agregar al historial de revisiones
            if 'historial_revisiones' not in pending_data:
                pending_data['historial_revisiones'] = []
            
            pending_data['historial_revisiones'].append({
                'timestamp': datetime.now().isoformat(),
                'accion': 'agregar_disponibles',
                'cantidad': agregados,
                'pallets': pallets_agregados
            })
            
            # Guardar JSON actualizado
            self.odoo.execute('mrp.production', 'write', [mo_id], {
                'x_studio_pending_receptions': json.dumps(pending_data)
            })
            
            return {
                'success': True,
                'agregados': agregados,
                'pallets_agregados': pallets_agregados,
                'mensaje': f'Se agregaron {agregados} pallet(s) disponible(s) a la orden'
            }
            
        except Exception as e:
            import traceback
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def listar_ordenes_recientes(
        self, 
        tunel: Optional[str] = None, 
        estado: Optional[str] = None, 
        limit: int = 50,
        solo_pendientes: bool = False
    ) -> List[Dict]:
        """
        Lista las órdenes de fabricación recientes de túneles estáticos con información extendida.
        
        Args:
            tunel: Filtrar por túnel (TE1, TE2, TE3, VLK)
            estado: Filtrar por estado de Odoo (draft, confirmed, progress, done, cancel)
            limit: Límite de resultados
            solo_pendientes: Si True, solo retorna órdenes con stock pendiente (en JSON)
            
        Returns:
            Lista de dicts con información de cada orden
        """
        try:
            import json
            
            # Construir dominio base: Solo productos de túneles
            producto_ids = [cfg['producto_proceso_id'] for cfg in TUNELES_CONFIG.values()]
            domain = [('product_id', 'in', producto_ids)]
            
            # Filtrar por túnel específico
            if tunel and tunel in TUNELES_CONFIG:
                domain = [('product_id', '=', TUNELES_CONFIG[tunel]['producto_proceso_id'])]
            
            # Filtrar por estado de Odoo
            if estado == 'pendientes':
                # 'pendientes' tradicional: estados activos
                domain.append(('state', 'in', ['draft', 'confirmed', 'progress']))
            elif estado == 'done':
                domain.append(('state', '=', 'done'))
            elif estado == 'cancel':
                domain.append(('state', '=', 'cancel'))
            elif estado and estado in ['draft', 'confirmed', 'progress']:
                domain.append(('state', '=', estado))
            
            # Filtro especial: Solo órdenes que tienen el flag de pendientes en el JSON de Studio
            if solo_pendientes:
                domain.append(('x_studio_pending_receptions', '!=', False))
            
            # Buscar órdenes
            ordenes = self.odoo.search_read(
                'mrp.production',
                domain,
                [
                    'id', 'name', 'product_id', 'product_qty', 'state',
                    'create_date', 'date_planned_start',
                    'x_studio_pending_receptions',
                    'move_raw_ids', 'move_finished_ids'
                ],
                limit=limit,
                order='create_date desc'
            )
            
            resultado = []
            
            for orden in ordenes:
                # 1. Identificar túnel
                tunel_codigo = None
                for codigo, cfg in TUNELES_CONFIG.items():
                    if orden['product_id'] and cfg['producto_proceso_id'] == orden['product_id'][0]:
                        tunel_codigo = codigo
                        break
                
                # 2. Verificar si tiene pendientes REALES en el JSON
                tiene_pendientes = False
                pending_json = orden.get('x_studio_pending_receptions')
                if pending_json:
                    try:
                        p_data = json.loads(pending_json) if isinstance(pending_json, str) else pending_json
                        tiene_pendientes = p_data.get('pending', False)
                    except:
                        pass
                
                # Si pedimos solo pendientes y esta no tiene, saltar
                if solo_pendientes and not tiene_pendientes:
                    continue
                
                # 3. Calcular electricidad y contar componentes reales (no-servicios)
                componentes_count = 0
                electricidad_costo = 0
                move_raw_ids = orden.get('move_raw_ids', [])
                
                if move_raw_ids:
                    # Contar move_lines para mayor precisión si es necesario, 
                    # pero para el listado usamos move_ids por performance a menos que sea necesario
                    # Aquí usamos el conteo de move_raw_ids como fallback rápido
                    componentes_count = len(move_raw_ids)
                    
                    # Intentar obtener costo de electricidad si ya existe el movimiento
                    # (Se calculó en la creación: Kg * $35.10 aprox)
                    # Por ahora usamos la fórmula rápida para el listado
                    electricidad_costo = orden.get('product_qty', 0) * 35.10
                
                # 4. Contar subproductos
                subproductos_count = len(orden.get('move_finished_ids', []))
                
                resultado.append({
                    'id': orden['id'],
                    'nombre': orden['name'],
                    'mo_name': orden['name'],
                    'tunel': tunel_codigo,
                    'producto': orden['product_id'][1] if orden['product_id'] else 'N/A',
                    'producto_nombre': orden['product_id'][1] if orden['product_id'] else 'N/A',
                    'kg_total': orden.get('product_qty', 0),
                    'estado': orden.get('state', 'draft'),
                    'fecha_creacion': orden.get('create_date'),
                    'fecha_planificada': orden.get('date_planned_start'),
                    'tiene_pendientes': tiene_pendientes,
                    'componentes_count': componentes_count,
                    'subproductos_count': subproductos_count,
                    'electricidad_costo': electricidad_costo,
                    'pallets_count': componentes_count
                })
            
            return resultado
            
        except Exception as e:
            print(f"Error en listar_ordenes_recientes: {e}")
            import traceback
            traceback.print_exc()
            return []
    


    def check_pallets_duplicados(self, codigos_pallets: List[str]) -> List[str]:
        """
        Verifica si los pallets ya están en uso en otras órdenes activas (no canceladas/done).
        Retorna lista de advertencias.
        """
        advertencias = []
        
        # Buscar packages con estos códigos
        packages = self.odoo.search_read(
            'stock.quant.package',
            [('name', 'in', codigos_pallets)],
            ['id', 'name']
        )
        package_ids = [pkg['id'] for pkg in packages]
        packages_map = {pkg['name']: pkg['id'] for pkg in packages}
        
        if package_ids:
            # Buscar moveline de estos packages
            # Traemos move_id para ver si es consumo de materia prima
            move_lines = self.odoo.search_read(
                'stock.move.line',
                [('package_id', 'in', package_ids)],
                ['package_id', 'production_id', 'move_id'],
                limit=100
            )
            
            if move_lines:
                mo_ids = set()
                # 1. Direct production_id (Finished Goods usually)
                for ml in move_lines:
                    if ml.get('production_id'):
                        mo_ids.add(ml['production_id'][0])
                
                # 2. Via move_id (Raw Materials usually)
                move_ids = [ml['move_id'][0] for ml in move_lines if ml.get('move_id')]
                if move_ids:
                    moves = self.odoo.search_read(
                        'stock.move',
                        [('id', 'in', move_ids)],
                        ['raw_material_production_id', 'production_id']
                    )
                    for m in moves:
                        if m.get('raw_material_production_id'):
                            mo_ids.add(m['raw_material_production_id'][0])
                        if m.get('production_id'):
                            mo_ids.add(m['production_id'][0])
                
                if mo_ids:
                    # Verificar estado de las MOs encontradas
                    mos = self.odoo.search_read(
                        'mrp.production',
                        [('id', 'in', list(mo_ids)), ('state', 'not in', ['done', 'cancel'])],
                        ['id', 'name', 'state']
                    )
                    
                    if mos:
                        # Mapear MO ID -> Name
                        mo_map = {m['id']: m['name'] for m in mos}
                        active_mo_ids = set(mo_map.keys())

                        # Re-recorrer para asociar pallet -> MO activa
                        # Esto es más complejo porque un pallet puede estar en varias lineas/moves
                        # Hacemos un mapa PalletID -> Lista de MOs activas
                        pallet_to_mos = {} # {pkg_id: set(mo_names)}
                        
                        # Cache de move -> MOs
                        move_to_mos = {} # {move_id: [mo_id1, mo_id2]}
                        if move_ids:
                             for m in moves:
                                m_mos = []
                                if m.get('raw_material_production_id'):
                                    m_mos.append(m['raw_material_production_id'][0])
                                if m.get('production_id'):
                                    m_mos.append(m['production_id'][0])
                                move_to_mos[m['id']] = m_mos

                        for ml in move_lines:
                            pkg_id = ml['package_id'][0]
                            found_mos = []
                            
                            # Direct check
                            if ml.get('production_id') and ml['production_id'][0] in active_mo_ids:
                                found_mos.append(mo_map[ml['production_id'][0]])
                            
                            # Move check
                            if ml.get('move_id'):
                                m_id = ml['move_id'][0]
                                associated_mo_ids = move_to_mos.get(m_id, [])
                                for mid in associated_mo_ids:
                                    if mid in active_mo_ids:
                                        found_mos.append(mo_map[mid])
                            
                            if found_mos:
                                if pkg_id not in pallet_to_mos:
                                    pallet_to_mos[pkg_id] = set()
                                pallet_to_mos[pkg_id].update(found_mos)
                        
                        # Generar advertencias
                        for codigo in codigos_pallets:
                            pkg_id = packages_map.get(codigo)
                            if pkg_id and pkg_id in pallet_to_mos:
                                mo_names = ", ".join(sorted(list(pallet_to_mos[pkg_id])))
                                msg = f"{codigo}: Ya está en orden {mo_names} (activa)"
                                advertencias.append(msg)
                            
        return advertencias

    def crear_orden_fabricacion(
        self,
        tunel: str,
        pallets: List[Dict[str, float]],
        buscar_ubicacion_auto: bool = False,
        responsable_id: Optional[int] = None
    ) -> Dict:
        """
        Crea una orden de fabricación para un túnel estático.
        """
        if tunel not in TUNELES_CONFIG:
            return {
                'success': False,
                'error': f'Túnel {tunel} no válido. Opciones: {list(TUNELES_CONFIG.keys())}'
            }
        
        config = TUNELES_CONFIG[tunel]
        errores = []
        advertencias = []
        validation_warnings = []  # Para registro en JSON
        validation_errors = []    # Para registro en JSON
        
        # 0. VALIDAR DUPLICADOS: Verificar que los pallets no estén en otras MOs activas
        codigos_pallets = [p['codigo'] for p in pallets]
        duplicados_adv = self.check_pallets_duplicados(codigos_pallets)
        
        if duplicados_adv:
            advertencias.extend(duplicados_adv)
            for msg in duplicados_adv:
                validation_warnings.append({
                    'tipo': 'pallet_duplicado',
                    'detalle': msg,
                    'timestamp': datetime.now().isoformat()
                })
        
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
                    'lote_nombre': pallet.get('lot_name'),  # Nombre del lote desde recepción
                    'producto_id': int(pallet['producto_id']),
                    'ubicacion_id': config['ubicacion_origen_id'], 
                    'package_id': None,  # No asignamos package aún
                    'manual': False,
                    'pendiente_recepcion': True,  # Flag para saber que es especial
                    'picking_id': pallet.get('picking_id')  # Guardar picking_id para JSON
                })
                # Log de datos del pallet pendiente
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
                # ERROR: Pallet no existe en sistema
                msg = validacion['error']
                errores.append(msg)
                validation_errors.append({
                    'tipo': 'pallet_no_existe',
                    'pallet': pallet['codigo'],
                    'detalle': msg,
                    'timestamp': datetime.now().isoformat()
                })
                continue
            
            # Si no tiene kg en Odoo, verificar si puede usar kg manual
            kg = validacion['kg'] if validacion['kg'] > 0 else pallet.get('kg', 0)
            
            if kg <= 0:
                # ERROR: Sin stock disponible - crear como pendiente
                msg = f"{pallet['codigo']}: Sin stock disponible para consumir"
                advertencias.append(msg)
                validation_errors.append({
                    'tipo': 'sin_stock',
                    'pallet': pallet['codigo'],
                    'detalle': msg,
                    'timestamp': datetime.now().isoformat()
                })
                
                # Intentar obtener producto_id de la validación
                producto_id = validacion.get('producto_id')
                if not producto_id:
                    errores.append(f"{pallet['codigo']}: Sin stock y sin producto identificado")
                    continue
                
                # Agregar como pallet pendiente (sin stock)
                pallets_validados.append({
                    'codigo': pallet['codigo'],
                    'kg': pallet.get('kg', 0),  # Usar kg esperado del frontend
                    'lote_id': validacion.get('lote_id'),
                    'lote_nombre': validacion.get('lote_nombre'),
                    'producto_id': producto_id,
                    'ubicacion_id': config['ubicacion_origen_id'],
                    'package_id': validacion.get('package_id'),
                    'manual': False,
                    'pendiente_recepcion': True,  # Marcar como pendiente por falta de stock
                    'picking_id': None
                })
                continue
            
            pallets_validados.append({
                'codigo': pallet['codigo'],
                'kg': kg,
                'lote_id': validacion.get('lote_id'),
                'lote_nombre': validacion.get('lote_nombre'),  # Nombre del lote original
                'producto_id': validacion.get('producto_id'),
                'ubicacion_id': validacion.get('ubicacion_id') or config['ubicacion_origen_id'],  # FIX: usar 'or' para manejar None explícito
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
                    'pallets': [],
                    'validation_warnings': validation_warnings,  # Agregar warnings
                    'validation_errors': validation_errors        # Agregar errors
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
                'validation_warnings': validation_warnings,  # Incluir warnings
                'validation_errors': validation_errors,      # Incluir errors
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
        
        # DEDUPLICAR entrada: evitar crear el mismo lote 2 veces en la misma llamada
        seen_keys = set()
        lotes_data_uniq = []
        for d in lotes_data:
            key = (d['codigo'], d['producto_id'])
            if key not in seen_keys:
                seen_keys.add(key)
                lotes_data_uniq.append(d)
        
        codigos = [d['codigo'] for d in lotes_data_uniq]
        producto_ids = list(set(d['producto_id'] for d in lotes_data_uniq))
        
        # LLAMADA 1: Buscar todos los lotes existentes por nombre Y producto
        lotes_existentes = self.odoo.search_read(
            'stock.lot',
            [('name', 'in', codigos), ('product_id', 'in', producto_ids)],
            ['name', 'id', 'product_id']
        )
        
        # Crear mapa con clave compuesta: (nombre, producto_id) -> lot_id
        lotes_existentes_set = {}
        for lot in lotes_existentes:
            key = (lot['name'], lot['product_id'][0] if lot['product_id'] else 0)
            lotes_existentes_set[key] = lot['id']
        
        # Mapa simple por nombre para retornar
        lotes_map = {}
        faltantes = []
        
        for d in lotes_data_uniq:
            key = (d['codigo'], d['producto_id'])
            if key in lotes_existentes_set:
                # Ya existe, reusar
                lotes_map[d['codigo']] = lotes_existentes_set[key]
            else:
                # No existe, necesita crearse
                faltantes.append(d)
        
        # LLAMADA 2: Crear SOLO los faltantes (ya deduplicados)
        if faltantes:
            print(f"DEBUG _buscar_o_crear_lotes_batch: Creando {len(faltantes)} lotes: {[(d['codigo'], d['producto_id']) for d in faltantes]}")
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
        print(f"DEBUG _crear_componentes: mo_id={mo_id}, mo_name={mo_name}, productos={len(productos_totales)}")
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
                
                # --- NUEVO: Si es pendiente de recepción, crear línea con qty=0 ---
                if pallet.get('pendiente_recepcion'):
                    print(f"DEBUG: Creando stock.move.line PENDIENTE (qty=0) para: {pallet['codigo']}")
                    
                    # Buscar o crear lote temporal con el nombre correcto
                    lote_nombre_temp = pallet.get('lote_nombre') or pallet.get('lot_name') or pallet.get('codigo')
                    if not lote_id:
                        lote_id = self._buscar_o_crear_lote(lote_nombre_temp, producto_id)
                    
                    # Buscar o crear package
                    if not package_id:
                        pkg = self.odoo.search_read(
                            'stock.quant.package',
                            [('name', '=', pallet['codigo'])],
                            ['id'],
                            limit=1
                        )
                        if pkg:
                            package_id = pkg[0]['id']
                        else:
                            package_id = self.odoo.execute('stock.quant.package', 'create', {
                                'name': pallet['codigo'],
                                'company_id': 1
                            })
                    
                    move_line_data = {
                        'move_id': move_id,
                        'product_id': producto_id,
                        'qty_done': 0.0,  # PENDIENTE: qty en 0 hasta que se confirme recepción
                        'reserved_uom_qty': 0.0,  # Sin reserva
                        'product_uom_id': 12,  # kg
                        'location_id': pallet.get('ubicacion_id') or config['ubicacion_origen_id'],  # FIX: usar 'or' para manejar None
                        'location_dest_id': ubicacion_virtual,
                        'state': 'draft',
                        'reference': f"{mo_name} [PENDIENTE: {pallet.get('kg', 0)} kg]",
                        'company_id': 1
                    }
                    
                    if lote_id:
                        move_line_data['lot_id'] = lote_id
                    if package_id:
                        move_line_data['package_id'] = package_id
                    
                    self.odoo.execute('stock.move.line', 'create', move_line_data)
                    continue  # Siguiente pallet

                # Flujo normal para pallets con stock
                move_line_data = {
                    'move_id': move_id,
                    'product_id': producto_id,
                    'qty_done': pallet['kg'],
                    'reserved_uom_qty': pallet['kg'],
                    'product_uom_id': 12,  # kg
                    'location_id': pallet.get('ubicacion_id') or config['ubicacion_origen_id'],  # FIX: usar 'or' para manejar None
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
        try:
            total_kg = sum(data['kg'] for data in productos_totales.values())
            ete_id = None
            
            # Intento 1: Buscar por código exacto 'ETE'
            ete_products = self.odoo.models.execute_kw(
                self.odoo.db, self.odoo.uid, self.odoo.password,
                'product.product', 'search_read',
                [[('default_code', '=', 'ETE')]],
                {'fields': ['id', 'name', 'uom_id'], 'limit': 1}  # También traer uom_id
            )
            
            ete_uom_id = 12  # Fallback a kg
            if ete_products:
                ete_id = ete_products[0]['id']
                if ete_products[0].get('uom_id'):
                    ete_uom_id = ete_products[0]['uom_id'][0]  # Odoo retorna [id, name]
                print(f"DEBUG: Electricidad encontrada por código ETE: ID={ete_id}, UoM={ete_uom_id}")
            else:
                # Intento 2: Buscar por nombre que contenga 'Electricidad' y 'Túnel'
                ete_products = self.odoo.models.execute_kw(
                    self.odoo.db, self.odoo.uid, self.odoo.password,
                    'product.product', 'search_read',
                    [[('name', 'ilike', 'Electricidad'), ('name', 'ilike', 'Túnel')]],
                    {'fields': ['id', 'name', 'uom_id'], 'limit': 1}
                )
                if ete_products:
                    ete_id = ete_products[0]['id']
                    if ete_products[0].get('uom_id'):
                        ete_uom_id = ete_products[0]['uom_id'][0]
                    print(f"DEBUG: Electricidad encontrada por nombre: ID={ete_id}, UoM={ete_uom_id}")
                else:
                    # Fallback: Usar ID fijo
                    ete_id = PRODUCTO_ELECTRICIDAD_ID
                    print(f"DEBUG: Usando ID fijo de electricidad: {ete_id}")

            # Crear el movimiento de electricidad
            if ete_id:
                elect_move = {
                    'name': mo_name,
                    'product_id': ete_id,
                    'product_uom_qty': total_kg,
                    'product_uom': ete_uom_id,  # Usar UoM del producto
                    'location_id': config['ubicacion_origen_id'],
                    'location_dest_id': ubicacion_virtual,
                    'state': 'draft',
                    'raw_material_production_id': mo_id,
                    'company_id': 1,
                    'reference': mo_name
                }
                elect_move_id = self.odoo.models.execute_kw(
                    self.odoo.db, self.odoo.uid, self.odoo.password,
                    'stock.move', 'create', [elect_move]
                )
                
                # Crear stock.move.line con qty_done para que aparezca en "Hecho"
                if elect_move_id:
                    elect_line = {
                        'move_id': elect_move_id,
                        'product_id': ete_id,
                        'qty_done': total_kg,
                        'reserved_uom_qty': total_kg,
                        'product_uom_id': ete_uom_id,  # Usar UoM del producto
                        'location_id': config['ubicacion_origen_id'],
                        'location_dest_id': ubicacion_virtual,
                        'state': 'draft',
                        'company_id': 1
                    }
                    self.odoo.models.execute_kw(
                        self.odoo.db, self.odoo.uid, self.odoo.password,
                        'stock.move.line', 'create', [elect_line]
                    )
                
                movimientos_creados += 1
                print(f"DEBUG: Electricidad agregada correctamente con qty_done={total_kg}")
        except Exception as e:
            import traceback
            print(f"ERROR Electricidad: {e}")
            print(f"ERROR Traceback: {traceback.format_exc()}")
        
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
        
        # DEBUG: Log TODOS los productos a procesar
        print(f"DEBUG _crear_subproductos: productos_totales keys = {list(productos_totales.keys())}")
        
        for producto_id_input, data in productos_totales.items():
            # Asegurarse que producto_id_input sea entero
            if not producto_id_input:
                continue
            
            try:
                producto_id_input_int = int(producto_id_input)
            except (ValueError, TypeError):
                print(f"WARN _crear_subproductos: producto_id invalido: {producto_id_input}")
                continue
            
            # Obtener producto congelado (output) - DINÁMICO
            # La lógica es: código 10xxxxxx → 20xxxxxx (cambiar primer dígito de 1 a 2)
            producto_id_output = None
            
            try:
                # Obtener el código del producto de entrada
                prod_input = self.odoo.search_read(
                    'product.product',
                    [('id', '=', producto_id_input_int)],
                    ['default_code', 'name'],
                    limit=1
                )
                
                if prod_input and prod_input[0].get('default_code'):
                    codigo_input = prod_input[0]['default_code']
                    
                    # Transformar código: primer dígito 1 → 2 para variante congelada
                    if codigo_input and len(codigo_input) >= 1 and codigo_input[0] == '1':
                        codigo_output = '2' + codigo_input[1:]
                        
                        # Buscar producto con el nuevo código
                        prod_output = self.odoo.search_read(
                            'product.product',
                            [('default_code', '=', codigo_output)],
                            ['id', 'name'],
                            limit=1
                        )
                        
                        if prod_output:
                            producto_id_output = prod_output[0]['id']
                            # print(f"DEBUG Transformación: {codigo_input} → {codigo_output}")
                        else:
                            print(f"WARN: Producto congelado {codigo_output} no encontrado")
                            producto_id_output = producto_id_input_int
                    else:
                        producto_id_output = producto_id_input_int
                else:
                    producto_id_output = producto_id_input_int
                    
            except Exception as e:
                print(f"ERROR buscando producto congelado: {e}")
                producto_id_output = producto_id_input_int
            
            # Garantizar que siempre tenemos un producto_id_output
            if not producto_id_output:
                producto_id_output = producto_id_input_int
            
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
                # LOTE: Usar nombre del lote original + sufijo -C
                # Prioridad: lot_name (frontend) -> lote_nombre (backend) -> codigo (fallback)
                if pallet.get('pendiente_recepcion'):
                     # MEJORA: Obtener lot_name real si existe, sino intentar construirlo o usar el del input
                     lote_origen = pallet.get('lot_name') or pallet.get('lote_nombre')
                     
                     # Si no viene en el payload, intentamos buscarlo en Odoo usando el picking_id
                     if not lote_origen and pallet.get('picking_id'):
                         try:
                             # Buscar move line en el picking para este pallet (puede ser package_id o result_package_id)
                             mls = self.odoo.search_read(
                                 'stock.move.line',
                                 [
                                     ('picking_id', '=', pallet['picking_id']),
                                     '|',
                                     ('package_id.name', '=', pallet['codigo']),
                                     ('result_package_id.name', '=', pallet['codigo'])
                                 ],
                                 ['lot_id'],
                                 limit=1
                             )
                             if mls and mls[0].get('lot_id'):
                                 lote_origen = mls[0]['lot_id'][1]
                                 print(f"✅ Recuperado lot_name desde Odoo para {pallet['codigo']}: {lote_origen}")
                         except Exception as e:
                             print(f"⚠️ Error recuperando lot_name en backend: {e}")

                     if not lote_origen:
                         lote_origen = f"{pallet.get('codigo')}" 
                else:
                    lote_origen = pallet.get('lot_name') or pallet.get('lote_nombre') or pallet.get('codigo')
                lote_output_name = f"{lote_origen}-C"
                
                # DEBUG: Log detallado del lote
                print(f"DEBUG Subprod: pallet={pallet.get('codigo')}, lote_nombre={pallet.get('lote_nombre')}, lot_name={pallet.get('lot_name')}, lote_origen={lote_origen}, lote_output={lote_output_name}")
                
                lotes_data.append({
                    'codigo': lote_output_name,
                    'producto_id': producto_id_output
                })
                
                # PACKAGE: Extraer solo el número y generar nombre correcto
                codigo_pallet = pallet['codigo']
                # Extraer solo el número (quitar PACK o PAC)
                if codigo_pallet.startswith('PACK'):
                    numero_pallet = codigo_pallet[4:]  # Quitar 'PACK'
                elif codigo_pallet.startswith('PAC'):
                    numero_pallet = codigo_pallet[3:]  # Quitar 'PAC'
                else:
                    numero_pallet = codigo_pallet
                package_name = f"PACK{numero_pallet}-C"
                
                package_names.append(package_name)
            
            # ✅ Crear TODOS los lotes en batch (2 llamadas máximo)
            lotes_map = self._buscar_o_crear_lotes_batch(lotes_data)
            
            # ✅ Crear TODOS los packages en batch (2 llamadas máximo)
            packages_map = self._buscar_o_crear_packages_batch(package_names)
            
            # Ahora crear los move.lines
            for idx, pallet in enumerate(data['pallets']):
                # LOTE: Usar nombre del lote original + sufijo -C
                # Prioridad: lot_name (frontend) -> lote_nombre (backend) -> codigo (fallback)
                lote_origen = pallet.get('lot_name') or pallet.get('lote_nombre') or pallet.get('codigo')
                lote_output_name = f"{lote_origen}-C"
                
                # PACKAGE: Extraer solo el número y generar nombre correcto
                codigo_pallet = pallet['codigo']
                if codigo_pallet.startswith('PACK'):
                    numero_pallet = codigo_pallet[4:]  # Quitar 'PACK'
                elif codigo_pallet.startswith('PAC'):
                    numero_pallet = codigo_pallet[3:]  # Quitar 'PAC'
                else:
                    numero_pallet = codigo_pallet
                package_name = f"PACK{numero_pallet}-C"
                
                # Obtener IDs del mapa (ya creados en batch)
                lote_id_output = lotes_map.get(lote_output_name)
                package_id = packages_map.get(package_name)
                
                # --- NUEVO: Si es pendiente de recepción, crear línea con qty=0 ---
                if pallet.get('pendiente_recepcion'):
                    print(f"DEBUG: Creando stock.move.line SUBPRODUCTO PENDIENTE (qty=0) para: {pallet['codigo']}")
                    
                    move_line_data = {
                        'move_id': move_id,
                        'product_id': producto_id_output,
                        'lot_id': lote_id_output,
                        'result_package_id': package_id,
                        'qty_done': 0.0,  # PENDIENTE: qty en 0 hasta que se confirme recepción
                        'reserved_uom_qty': 0.0,  # Sin reserva
                        'product_uom_id': 12,  # kg
                        'location_id': ubicacion_virtual,
                        'location_dest_id': config['ubicacion_destino_id'],
                        'state': 'draft',
                        'reference': f"{mo_name} [PENDIENTE: {pallet.get('kg', 0)} kg]",
                        'company_id': 1
                    }
                    
                    self.odoo.execute('stock.move.line', 'create', move_line_data)
                    continue  # Siguiente pallet
                
                # Flujo normal para pallets con stock
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
    


def get_tuneles_service(odoo: OdooClient) -> TunelesService:
    """Factory function para obtener el servicio de túneles."""
    return TunelesService(odoo)
