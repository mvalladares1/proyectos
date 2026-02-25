"""
Servicio para gestión de etiquetas de pallets
Obtiene información de pallets desde stock.move.line
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from shared.odoo_client import OdooClient
from backend.utils import clean_record

logger = logging.getLogger(__name__)


class EtiquetasPalletService:
    """
    Servicio para obtener información de pallets y generar etiquetas.
    """
    
    def __init__(self, username: str, password: str):
        self.odoo = OdooClient(username=username, password=password)
    
    def obtener_clientes(self) -> List[Dict]:
        """
        Obtiene la lista de clientes desde res.partner (módulo VENTAS).
        """
        try:
            domain = [
                ('customer_rank', '>', 0)
            ]
            
            clientes = self.odoo.search_read(
                'res.partner',
                domain,
                ['name', 'vat', 'city', 'country_id'],
                limit=500,
                order='name asc'
            )
            
            return [clean_record(c) for c in clientes]
        except Exception as e:
            logger.error(f"Error obteniendo clientes: {e}")
            return []
    
    def _extraer_kg_por_caja(self, nombre_producto: str) -> Optional[float]:
        """
        Extrae los kg por caja del nombre del producto.
        Busca patrones como "10 kg", "10kg", "10 Kg", etc.
        
        Returns:
            float con kg por caja, o None si no se encuentra
        """
        if not nombre_producto:
            return None
        
        # Buscar patrones: número seguido de kg (con o sin espacio)
        # Ej: "10 kg", "10kg", "10 Kg", "10KG"
        patterns = [
            r'(\d+(?:\.\d+)?)\s*kg',  # "10 kg" o "10kg"
            r'(\d+(?:\.\d+)?)\s*KG',  # "10 KG" o "10KG"
            r'(\d+(?:\.\d+)?)\s*Kg',  # "10 Kg"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, nombre_producto, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except:
                    continue
        
        return None
    
    def _calcular_cantidad_cajas(self, peso_total_kg: float, nombre_producto: str) -> int:
        """
        Calcula la cantidad de cajas basándose en el peso total y el peso por caja
        extraído del nombre del producto.
        
        Args:
            peso_total_kg: Peso total del pallet en kg
            nombre_producto: Nombre del producto (contiene info de kg por caja)
        
        Returns:
            int con cantidad de cajas calculada
        """
        kg_por_caja = self._extraer_kg_por_caja(nombre_producto)
        
        if kg_por_caja and kg_por_caja > 0:
            cantidad_cajas = int(peso_total_kg / kg_por_caja)
            logger.info(f"Calculado: {peso_total_kg}kg / {kg_por_caja}kg por caja = {cantidad_cajas} cajas")
            return cantidad_cajas
        else:
            # Si no se puede extraer, devolver 0
            logger.warning(f"No se pudo extraer kg por caja de: {nombre_producto}")
            return 0
    
    def buscar_ordenes(self, termino_busqueda: str) -> List[Dict]:
        """
        Busca órdenes de producción Y transfers/pickings por nombre/referencia.
        """
        try:
            resultados = []
            
            # Buscar en mrp.production (órdenes de fabricación)
            domain_prod = [
                '|',
                ('name', 'ilike', termino_busqueda),
                ('origin', 'ilike', termino_busqueda)
            ]
            
            ordenes_prod = self.odoo.search_read(
                'mrp.production',
                domain_prod,
                ['name', 'product_id', 'origin', 'state', 'date_finished', 'lot_producing_id', 'x_studio_clientes'],
                limit=25
            )
            
            for o in ordenes_prod:
                o['_modelo'] = 'mrp.production'
                # Extraer nombre del cliente si existe
                cliente = o.get('x_studio_clientes')
                if cliente and isinstance(cliente, (list, tuple)):
                    o['cliente_nombre'] = cliente[1] if len(cliente) > 1 else ''
                else:
                    o['cliente_nombre'] = ''
                resultados.append(clean_record(o))
            
            # Buscar en stock.picking (transfers)
            domain_picking = [
                '|',
                ('name', 'ilike', termino_busqueda),
                ('origin', 'ilike', termino_busqueda)
            ]
            
            pickings = self.odoo.search_read(
                'stock.picking',
                domain_picking,
                ['name', 'origin', 'state', 'date_done', 'picking_type_id', 'partner_id'],
                limit=25
            )
            
            for p in pickings:
                p['_modelo'] = 'stock.picking'
                # Ajustar formato para compatibilidad
                p['product_id'] = ['', p.get('picking_type_id', ['', ''])[1] if isinstance(p.get('picking_type_id'), list) else '']
                # Extraer nombre del cliente desde partner_id
                partner = p.get('partner_id')
                if partner and isinstance(partner, (list, tuple)) and len(partner) > 1:
                    p['cliente_nombre'] = partner[1]
                else:
                    p['cliente_nombre'] = ''
                resultados.append(clean_record(p))
            
            return resultados
        except Exception as e:
            logger.error(f"Error buscando órdenes: {e}")
            return []
    
    def obtener_pallets_orden(self, orden_name: str) -> List[Dict]:
        """
        Obtiene todos los pallets (result_package_id) de una orden/picking.
        """
        try:
            fecha_proceso = None
            move_ids = []
            move_product_map = {}  # move_id → product_id del stock.move
            
            # Intentar buscar como mrp.production primero
            ordenes = self.odoo.search_read(
                'mrp.production',
                [('name', '=', orden_name)],
                ['id', 'name', 'date_finished', 'move_finished_ids', 'x_studio_clientes', 'x_studio_inicio_de_proceso'],
                limit=1
            )
            
            cliente_nombre = ''
            
            fecha_inicio = None
            
            if ordenes:
                # Es una orden de producción
                orden = ordenes[0]
                fecha_proceso = orden.get('date_finished')
                fecha_inicio = orden.get('x_studio_inicio_de_proceso')
                
                # Extraer cliente
                cliente = orden.get('x_studio_clientes')
                if cliente and isinstance(cliente, (list, tuple)):
                    cliente_nombre = cliente[1] if len(cliente) > 1 else ''
                
                # Buscar stock.move de SALIDA (producto terminado + subproductos)
                # Solo production_id — NO raw_material_production_id (eso es materia prima/consumo)
                moves = self.odoo.search_read(
                    'stock.move',
                    [('production_id', '=', orden['id'])],
                    ['id', 'product_id'],
                    limit=500
                )
                move_ids = [m['id'] for m in moves]
                # Mapeo move_id → product_id del stock.move (producto real de la orden)
                move_product_map = {}
                for m in moves:
                    pid = m.get('product_id')
                    move_product_map[m['id']] = pid
                logger.info(f"Orden producción {orden_name}: {len(move_ids)} moves de salida encontrados")
            else:
                # Buscar como stock.picking
                pickings = self.odoo.search_read(
                    'stock.picking',
                    [('name', '=', orden_name)],
                    ['id', 'name', 'date_done', 'partner_id'],
                    limit=1
                )
                
                if pickings:
                    picking = pickings[0]
                    fecha_proceso = picking.get('date_done')
                    
                    # Extraer cliente desde partner_id del picking
                    partner = picking.get('partner_id')
                    if partner and isinstance(partner, (list, tuple)) and len(partner) > 1:
                        cliente_nombre = partner[1]
                    
                    # Buscar stock.move directamente por picking_id
                    moves = self.odoo.search_read(
                        'stock.move',
                        [('picking_id', '=', picking['id'])],
                        ['id', 'product_id'],
                        limit=500
                    )
                    move_ids = [m['id'] for m in moves]
                    # Mapeo move_id → product_id del stock.move
                    move_product_map = {}
                    for m in moves:
                        pid = m.get('product_id')
                        move_product_map[m['id']] = pid
                    logger.info(f"Picking {orden_name}: {len(move_ids)} moves (búsqueda directa)")
                else:
                    logger.warning(f"No se encontró orden/picking {orden_name}")
                    return []
            
            if not move_ids:
                logger.warning(f"No hay moves para {orden_name}")
                return []
            
            # Buscar stock.move.line con result_package_id de estos moves
            move_lines = self.odoo.search_read(
                'stock.move.line',
                [
                    ('move_id', 'in', move_ids),
                    ('result_package_id', '!=', False)
                ],
                [
                    'move_id',
                    'result_package_id',
                    'product_id',
                    'qty_done',
                    'lot_id',
                    'date'
                ],
                limit=500
            )
            
            # Fallback: si no encontramos move_lines por move_id, buscar directamente por picking_id
            if not move_lines and not ordenes:
                # Para stock.picking, buscar move_lines directamente por picking_id
                picking_id = pickings[0]['id'] if pickings else None
                if picking_id:
                    move_lines = self.odoo.search_read(
                        'stock.move.line',
                        [
                            ('picking_id', '=', picking_id),
                            ('result_package_id', '!=', False)
                        ],
                        [
                            'move_id',
                            'result_package_id',
                            'product_id',
                            'qty_done',
                            'lot_id',
                            'date'
                        ],
                        limit=500
                    )
                    logger.info(f"Fallback picking_id: {len(move_lines)} move_lines para {orden_name}")
            
            logger.info(f"Encontrados {len(move_lines)} move_lines con pallets para {orden_name}")
            
            # Agrupar por result_package_id (solo los que tengan kg > 0)
            # Se usa el product_id del stock.move padre (producto real de la orden),
            # NO el del move_line (que puede diferir por temas internos de Odoo)
            pallets_dict = {}
            # {package_key: {product_key: {'product_id': ..., 'lot_id': ..., 'qty': float}}}
            pallets_product_qty = {}
            
            for line in move_lines:
                package_id = line.get('result_package_id')
                qty_done = line.get('qty_done', 0)
                
                # Solo incluir si tiene kg ingresados
                if not package_id or qty_done <= 0:
                    continue
                
                package_key = package_id[0] if isinstance(package_id, (list, tuple)) else package_id
                
                # Obtener product_id del stock.move padre (el correcto de la orden)
                line_move_id = line.get('move_id')
                move_id_key = line_move_id[0] if isinstance(line_move_id, (list, tuple)) else line_move_id
                # Usar producto del move si existe en el map, sino caer al del move_line
                real_product = move_product_map.get(move_id_key, line.get('product_id')) if move_product_map else line.get('product_id')
                
                if package_key not in pallets_dict:
                    lot_id = line.get('lot_id')
                    lot_name = lot_id[1] if isinstance(lot_id, (list, tuple)) and len(lot_id) > 1 else ''
                    
                    pallets_dict[package_key] = {
                        'package_id': package_id[0] if isinstance(package_id, (list, tuple)) else package_id,
                        'package_name': package_id[1] if isinstance(package_id, (list, tuple)) else str(package_id),
                        'product_id': real_product,
                        'lot_id': lot_id,
                        'lot_name': lot_name,
                        'fecha_elaboracion': line.get('date') or fecha_proceso,
                        'qty_total': 0,
                        'move_lines': []
                    }
                    pallets_product_qty[package_key] = {}
                else:
                    # Siempre conservar la fecha más antigua (inicio del pallet)
                    line_date = line.get('date')
                    existing_date = pallets_dict[package_key].get('fecha_elaboracion')
                    if line_date and existing_date and str(line_date) < str(existing_date):
                        pallets_dict[package_key]['fecha_elaboracion'] = line_date
                        logger.info(f"Pallet {package_key}: fecha actualizada a {line_date} (más antigua que {existing_date})")
                
                # Rastrear cantidad por producto para determinar el principal
                real_product_key = real_product[0] if isinstance(real_product, (list, tuple)) else real_product
                if real_product_key not in pallets_product_qty[package_key]:
                    pallets_product_qty[package_key][real_product_key] = {
                        'product_id': real_product,
                        'lot_id': line.get('lot_id'),
                        'qty': 0
                    }
                pallets_product_qty[package_key][real_product_key]['qty'] += qty_done
                
                pallets_dict[package_key]['qty_total'] += qty_done
                pallets_dict[package_key]['move_lines'].append(clean_record(line))
            
            # Asignar el producto con mayor cantidad a cada pallet
            for package_key, products in pallets_product_qty.items():
                if len(products) > 1:
                    # Hay múltiples productos en este pallet — usar el de mayor cantidad
                    best = max(products.values(), key=lambda x: x['qty'])
                    old_pid = pallets_dict[package_key]['product_id']
                    old_name = old_pid[1] if isinstance(old_pid, (list, tuple)) else str(old_pid)
                    new_name = best['product_id'][1] if isinstance(best['product_id'], (list, tuple)) else str(best['product_id'])
                    pallets_dict[package_key]['product_id'] = best['product_id']
                    lot_id = best['lot_id']
                    pallets_dict[package_key]['lot_id'] = lot_id
                    pallets_dict[package_key]['lot_name'] = lot_id[1] if isinstance(lot_id, (list, tuple)) and len(lot_id) > 1 else ''
                    logger.info(f"Pallet {package_key}: producto corregido de '{old_name}' a '{new_name}' (mayor qty: {best['qty']} kg)")
            
            # Obtener información adicional de cada package
            pallets_resultado = []
            for pallet_info in pallets_dict.values():
                # Obtener detalles del package (incluir barcode/qr)
                try:
                    package_details = self.odoo.search_read(
                        'stock.quant.package',
                        [('id', '=', pallet_info['package_id'])],
                        ['name', 'packaging_id', 'location_id', 'quant_ids', 'barcode'],
                        limit=1
                    )
                    
                    if package_details:
                        pkg = package_details[0]
                        pallet_info['package_details'] = clean_record(pkg)
                        
                        # Guardar el barcode/QR de Odoo
                        pallet_info['barcode'] = pkg.get('barcode') or pkg.get('name', '')
                        
                        # Obtener peso del pallet desde stock.quant
                        if pkg.get('quant_ids'):
                            quants = self.odoo.search_read(
                                'stock.quant',
                                [('id', 'in', pkg['quant_ids'])],
                                ['quantity', 'product_id', 'lot_id'],
                                limit=100
                            )
                            
                            peso_total = sum(q.get('quantity', 0) for q in quants)
                            pallet_info['peso_pallet_kg'] = peso_total
                except Exception as e:
                    logger.warning(f"Error obteniendo detalles de package {pallet_info['package_id']}: {e}")
                    pallet_info['peso_pallet_kg'] = pallet_info['qty_total']  # Fallback
                    pallet_info['barcode'] = pallet_info.get('package_name', '')
                
                # Calcular cantidad de cajas y fechas del proceso
                fecha_elab = pallet_info.get('fecha_elaboracion')
                product_id = pallet_info.get('product_id')
                product_name = product_id[1] if isinstance(product_id, (list, tuple)) else str(product_id)
                
                # Guardar nombre del producto para el frontend
                pallet_info['producto_nombre'] = product_name
                
                # Calcular cantidad de cajas basándose en el peso y nombre del producto
                peso_kg = pallet_info.get('peso_pallet_kg', 0)
                pallet_info['cantidad_cajas'] = self._calcular_cantidad_cajas(peso_kg, product_name)
                
                # Agregar cliente de la orden
                pallet_info['cliente_nombre'] = cliente_nombre
                
                # Formatear x_studio_fecha_inicio para etiquetas 100x50
                if fecha_inicio:
                    try:
                        if isinstance(fecha_inicio, str):
                            fi_dt = datetime.fromisoformat(fecha_inicio.replace('Z', '+00:00'))
                        else:
                            fi_dt = fecha_inicio
                        pallet_info['fecha_inicio_fmt'] = fi_dt.strftime('%d.%m.%Y')
                    except:
                        pallet_info['fecha_inicio_fmt'] = ''
                else:
                    pallet_info['fecha_inicio_fmt'] = ''
                
                # Usar la fecha del proceso para elaboración y vencimiento (ambas iguales)
                if fecha_elab:
                    try:
                        if isinstance(fecha_elab, str):
                            fecha_dt = datetime.fromisoformat(fecha_elab.replace('Z', '+00:00'))
                        else:
                            fecha_dt = fecha_elab
                        fecha_fmt = fecha_dt.strftime('%d.%m.%Y')
                        pallet_info['fecha_vencimiento'] = fecha_fmt
                        pallet_info['fecha_elaboracion_fmt'] = fecha_fmt
                    except:
                        pallet_info['fecha_vencimiento'] = ''
                        pallet_info['fecha_elaboracion_fmt'] = ''
                else:
                    pallet_info['fecha_vencimiento'] = ''
                    pallet_info['fecha_elaboracion_fmt'] = ''
                
                pallets_resultado.append(pallet_info)
            
            return pallets_resultado
            
        except Exception as e:
            logger.error(f"Error obteniendo pallets de orden {orden_name}: {e}")
            return []
    
    def obtener_info_etiqueta(self, package_id: int, cliente: str = "") -> Optional[Dict]:
        """
        Obtiene toda la información necesaria para una etiqueta de pallet.
        
        Returns:
            Dict con campos: nombre_producto, codigo_producto, peso_pallet_kg,
            cantidad_cajas, fecha_elaboracion, fecha_vencimiento, lote_produccion,
            numero_pallet, cliente
        """
        try:
            # Obtener package
            packages = self.odoo.search_read(
                'stock.quant.package',
                [('id', '=', package_id)],
                ['name', 'quant_ids', 'location_id'],
                limit=1
            )
            
            if not packages:
                return None
            
            package = packages[0]
            
            # Obtener quants del pallet
            quants = self.odoo.search_read(
                'stock.quant',
                [('id', 'in', package.get('quant_ids', []))],
                ['product_id', 'quantity', 'lot_id', 'in_date'],
                limit=100
            )
            
            if not quants:
                return None
            
            # Tomar el primer quant como referencia (asumiendo un solo producto por pallet)
            primer_quant = quants[0]
            product_id = primer_quant.get('product_id')
            lot_id = primer_quant.get('lot_id')
            
            # Obtener info del producto
            product_info = self.odoo.search_read(
                'product.product',
                [('id', '=', product_id[0] if isinstance(product_id, (list, tuple)) else product_id)],
                ['name', 'default_code', 'weight'],
                limit=1
            )
            
            if not product_info:
                return None
            
            producto = product_info[0]
            
            # Calcular peso total
            peso_total = sum(q.get('quantity', 0) for q in quants)
            
            # Calcular cantidad de cajas basándose en el nombre del producto
            nombre_producto = producto.get('name', '')
            cantidad_cajas = self._calcular_cantidad_cajas(peso_total, nombre_producto)
            
            # Obtener fecha de elaboración del proceso
            fecha_elab = primer_quant.get('in_date')
            if fecha_elab:
                try:
                    fecha_dt = datetime.fromisoformat(fecha_elab.replace('Z', '+00:00'))
                    fecha_fmt = fecha_dt.strftime('%d.%m.%Y')
                    # Usar la misma fecha para elaboración y vencimiento
                    fecha_elaboracion_fmt = fecha_fmt
                    fecha_vencimiento_fmt = fecha_fmt
                except:
                    fecha_elaboracion_fmt = ''
                    fecha_vencimiento_fmt = ''
            else:
                fecha_elaboracion_fmt = datetime.now().strftime('%d.%m.%Y')
                fecha_vencimiento_fmt = datetime.now().strftime('%d.%m.%Y')
            
            # Nombre del lote
            lote_name = lot_id[1] if isinstance(lot_id, (list, tuple)) and lot_id else ''
            
            return {
                'cliente': cliente,
                'nombre_producto': producto.get('name', ''),
                'codigo_producto': producto.get('default_code', ''),
                'peso_pallet_kg': int(peso_total),
                'cantidad_cajas': cantidad_cajas,
                'fecha_elaboracion': fecha_elaboracion_fmt,
                'fecha_vencimiento': fecha_vencimiento_fmt,
                'lote_produccion': lote_name,
                'numero_pallet': package.get('name', ''),
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo info de etiqueta para package {package_id}: {e}")
            return None
