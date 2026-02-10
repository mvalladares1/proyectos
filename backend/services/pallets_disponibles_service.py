"""
Servicio para obtener pallets disponibles que NO están en ninguna fabricación.
Excluye ubicaciones específicas de stock/cámaras.
"""
import logging
from typing import Dict, List, Any, Optionalfrom datetime import datetimefrom shared.odoo_client import OdooClient

logger = logging.getLogger(__name__)

# Ubicaciones a EXCLUIR (stock final, cámaras de congelado)
UBICACIONES_EXCLUIR = [
    'RF/Stock/Inventario Real',
    'VLK/Camara 1 -25°C',
    'VLK/Stock',
    'VLK/Camara 1 -25°C/A1',
    'VLK/Camara 1 -25°C/A2',
    'VLK/Camara 1 -25°C/A3',
    'VLK/Camara 1 -25°C/A4',
    'VLK/Camara 1 -25°C/A5',
    'VLK/Camara 1 -25°C/A6',
    'VLK/Camara 1 -25°C/A7',
]


class PalletsDisponiblesService:
    def __init__(self, username: str, password: str):
        self.odoo = OdooClient(username=username, password=password)
    
    def get_productos_2026(self) -> List[Dict[str, Any]]:
        """
        Obtiene productos únicos del año 2026 basados en lotes/pallets existentes.
        
        Returns:
            Lista de productos con id y nombre
        """
        try:
            # Buscar lotes creados en 2026
            domain_lots = [
                ('create_date', '>=', '2026-01-01'),
                ('create_date', '<', '2027-01-01'),
                ('product_id', '!=', False),
            ]
            
            lotes = self.odoo.search_read(
                'stock.lot',
                domain_lots,
                ['product_id'],
                limit=10000,
                order='create_date desc'
            )
            
            # Extraer productos únicos
            productos_dict = {}
            for lote in (lotes or []):
                prod = lote.get('product_id')
                if prod and isinstance(prod, (list, tuple)) and len(prod) > 1:
                    prod_id = prod[0]
                    prod_name = prod[1]
                    # Excluir códigos [3 y [4 (productos terminados)
                    if not prod_name.startswith('[3') and not prod_name.startswith('[4'):
                        if prod_id not in productos_dict:
                            productos_dict[prod_id] = {
                                'id': prod_id,
                                'nombre': prod_name
                            }
            
            resultado = sorted(productos_dict.values(), key=lambda x: x['nombre'])
            logger.info(f"[PALLETS] Productos 2026 encontrados: {len(resultado)}")
            return resultado
            
        except Exception as e:
            logger.error(f"[PALLETS] Error al obtener productos 2026: {str(e)}")
            return []
    
    def get_proveedores_compras(self) -> List[Dict[str, Any]]:
        """
        Obtiene proveedores (productores) del módulo de compras de Odoo.
        Filtra partners que tienen órdenes de compra.
        
        Returns:
            Lista de proveedores con id y nombre
        """
        try:
            # Buscar órdenes de compra del 2026
            domain_po = [
                ('date_order', '>=', '2026-01-01'),
                ('date_order', '<', '2027-01-01'),
                ('partner_id', '!=', False),
                ('state', 'in', ['purchase', 'done']),
            ]
            
            ordenes = self.odoo.search_read(
                'purchase.order',
                domain_po,
                ['partner_id'],
                limit=5000,
                order='date_order desc'
            )
            
            # Extraer proveedores únicos
            proveedores_dict = {}
            for orden in (ordenes or []):
                partner = orden.get('partner_id')
                if partner and isinstance(partner, (list, tuple)) and len(partner) > 1:
                    partner_id = partner[0]
                    partner_name = partner[1]
                    if partner_id not in proveedores_dict:
                        proveedores_dict[partner_id] = {
                            'id': partner_id,
                            'nombre': partner_name
                        }
            
            resultado = sorted(proveedores_dict.values(), key=lambda x: x['nombre'])
            logger.info(f"[PALLETS] Proveedores de compras encontrados: {len(resultado)}")
            return resultado
            
        except Exception as e:
            logger.error(f"[PALLETS] Error al obtener proveedores: {str(e)}")
            return []
    
    def get_pallets_disponibles(self, planta: Optional[str] = None, 
                                 producto_id: Optional[int] = None,
                                 proveedor_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Obtiene pallets con stock que NO están asignados a ninguna fabricación.
        
        Args:
            planta: 'VILKUN', 'RIO FUTURO' o None para todas
            producto_id: ID del producto para filtrar (opcional)
            proveedor_id: ID del proveedor/productor para filtrar (opcional, solo frescos)
        
        Returns:
            Dict con pallets disponibles y estadísticas
        """
        try:
            # 1. Obtener IDs de ubicaciones a excluir
            ubicaciones_excluir_ids = self._get_ubicaciones_excluir_ids()
            logger.info(f"[PALLETS] Ubicaciones excluidas: {len(ubicaciones_excluir_ids)} IDs")
            
            # 2. Obtener todos los quants con stock > 0 en ubicaciones internas
            domain_quants = [
                ('quantity', '>', 0),
                ('location_id.usage', '=', 'internal'),
            ]
            
            # Excluir ubicaciones
            if ubicaciones_excluir_ids:
                domain_quants.append(('location_id', 'not in', ubicaciones_excluir_ids))
            
            # Filtrar por planta
            if planta and planta != 'Todas':
                if planta.upper() in ['VILKUN', 'VLK']:
                    domain_quants.append(('location_id.complete_name', 'ilike', 'VLK'))
                else:
                    domain_quants.append(('location_id.complete_name', 'ilike', 'RF'))
            
            # Filtrar por producto si se especifica
            if producto_id:
                domain_quants.append(('product_id', '=', producto_id))
            
            quants = self.odoo.search_read(
                'stock.quant',
                domain_quants,
                ['package_id', 'lot_id', 'product_id', 'quantity', 
                 'location_id', 'in_date'],
                limit=10000,
                order='in_date desc'
            )
            
            logger.info(f"[PALLETS] Quants encontrados: {len(quants or [])}")
            
            if not quants:
                return self._empty_result()
            
            # Filtrar solo quants con package (pallet)
            quants_con_pallet = [q for q in quants if q.get('package_id')]
            logger.info(f"[PALLETS] Quants con pallet: {len(quants_con_pallet)}")
            
            if not quants_con_pallet:
                return self._empty_result()
            
            # 3. Obtener fecha de creación de los packages (pallets)
            package_ids = list(set([
                q['package_id'][0] if isinstance(q['package_id'], (list, tuple)) else q['package_id']
                for q in quants_con_pallet
            ]))
            package_create_dates = self._get_package_create_dates(package_ids)
            
            # 4. Obtener proveedores de lotes frescos (desde recepciones)
            lot_ids = list(set([
                q['lot_id'][0] if isinstance(q.get('lot_id'), (list, tuple)) else q.get('lot_id')
                for q in quants_con_pallet if q.get('lot_id')
            ]))
            lot_proveedores = self._get_lot_proveedores(lot_ids) if lot_ids else {}
            
            # 5. Obtener pallets que YA están en fabricación (como materia prima)
            pallets_en_fabricacion = self._get_pallets_en_fabricacion()
            logger.info(f"[PALLETS] Pallets en fabricación: {len(pallets_en_fabricacion)}")
            
            # 6. Filtrar: solo pallets que NO están en fabricación
            pallets_disponibles = []
            for q in quants_con_pallet:
                package_id = q['package_id'][0] if isinstance(q['package_id'], (list, tuple)) else q['package_id']
                package_name = q['package_id'][1] if isinstance(q['package_id'], (list, tuple)) else ''
                
                if package_id in pallets_en_fabricacion:
                    continue
                
                # Extraer datos
                product_name = ''
                product_id_val = None
                if isinstance(q.get('product_id'), (list, tuple)) and len(q['product_id']) > 1:
                    product_name = q['product_id'][1]
                    product_id_val = q['product_id'][0]
                
                # Excluir productos con código que empiece en [3 o [4
                if product_name.startswith('[3') or product_name.startswith('[4'):
                    continue
                
                lot_name = ''
                lot_id = None
                if isinstance(q.get('lot_id'), (list, tuple)) and len(q['lot_id']) > 1:
                    lot_name = q['lot_id'][1]
                    lot_id = q['lot_id'][0]
                
                location_name = ''
                if isinstance(q.get('location_id'), (list, tuple)) and len(q['location_id']) > 1:
                    location_name = q['location_id'][1]
                
                # Determinar tipo: congelado o fresco
                tipo = self._determinar_tipo(product_name, lot_name, location_name)
                
                # Determinar planta del pallet
                planta_pallet = self._determinar_planta(location_name, package_name)
                
                # Obtener proveedor del lote (para frescos viene de recepciones)
                proveedor_info = lot_proveedores.get(lot_id, {}) if lot_id else {}
                proveedor_nombre = proveedor_info.get('nombre', '')
                proveedor_id_val = proveedor_info.get('id')
                
                # Filtrar por proveedor si se especifica
                if proveedor_id and proveedor_id_val != proveedor_id:
                    continue
                
                # Obtener fecha de creación del pallet
                fecha_creacion = package_create_dates.get(package_id, '')
                
                pallets_disponibles.append({
                    'pallet': package_name,
                    'pallet_id': package_id,
                    'lote': lot_name,
                    'producto': product_name,
                    'producto_id': product_id_val,
                    'cantidad_kg': round(q.get('quantity', 0), 1),
                    'ubicacion': location_name,
                    'fecha_ingreso': str(q.get('in_date', ''))[:10] if q.get('in_date') else '',
                    'fecha_creacion': fecha_creacion,
                    'tipo': tipo,
                    'planta': planta_pallet,
                    'proveedor': proveedor_nombre,
                    'proveedor_id': proveedor_id_val,
                })
            
            # Agrupar por planta
            por_planta = {}
            for p in pallets_disponibles:
                pl = p['planta']
                if pl not in por_planta:
                    por_planta[pl] = []
                por_planta[pl].append(p)
            
            # Estadísticas
            total_kg = sum(p['cantidad_kg'] for p in pallets_disponibles)
            total_pallets = len(pallets_disponibles)
            congelados = [p for p in pallets_disponibles if p['tipo'] == 'Congelado']
            frescos = [p for p in pallets_disponibles if p['tipo'] == 'Fresco']
            
            return {
                'pallets': pallets_disponibles,
                'por_planta': por_planta,
                'estadisticas': {
                    'total_pallets': total_pallets,
                    'total_kg': round(total_kg, 1),
                    'congelados': len(congelados),
                    'frescos': len(frescos),
                    'kg_congelados': round(sum(p['cantidad_kg'] for p in congelados), 1),
                    'kg_frescos': round(sum(p['cantidad_kg'] for p in frescos), 1),
                    'plantas': list(por_planta.keys()),
                }
            }
            
        except Exception as e:
            logger.error(f"[PALLETS] Error: {str(e)}", exc_info=True)
            raise
    
    def _get_ubicaciones_excluir_ids(self) -> List[int]:
        """Obtiene los IDs de las ubicaciones a excluir."""
        domain = []
        for ub in UBICACIONES_EXCLUIR:
            domain.append(('complete_name', '=', ub))
        
        # Construir domain OR
        if len(domain) > 1:
            or_domain = ['|'] * (len(domain) - 1)
            or_domain.extend(domain)
        else:
            or_domain = domain
        
        ubicaciones = self.odoo.search_read(
            'stock.location',
            or_domain,
            ['id', 'complete_name'],
            limit=50
        )
        
        ids = [u['id'] for u in (ubicaciones or [])]
        logger.info(f"[PALLETS] Ubicaciones excluidas encontradas: {[u.get('complete_name') for u in (ubicaciones or [])]}")
        return ids
    
    def _get_pallets_en_fabricacion(self) -> set:
        """
        Obtiene IDs de pallets (package_id) que están en alguna fabricación
        como materia prima, independiente del estado de la MO (excepto cancel).
        
        Busca en stock.move.line los pallets usados como origen en movimientos
        de consumo de fabricación.
        """
        # Buscar TODOS los stock.move que sean consumo de fabricación (raw_material_production_id != False)
        # y que no estén cancelados
        moves_consumo = self.odoo.search_read(
            'stock.move',
            [
                ('raw_material_production_id', '!=', False),
                ('raw_material_production_id.state', '!=', 'cancel'),
            ],
            ['id'],
            limit=50000,
            order='id desc'
        )
        
        if not moves_consumo:
            return set()
        
        move_ids = [m['id'] for m in moves_consumo]
        logger.info(f"[PALLETS] Moves de consumo de fabricación: {len(move_ids)}")
        
        # Buscar move lines con package_id (pallet de origen)
        # Hacer en batches para no exceder límites
        package_ids = set()
        batch_size = 5000
        
        for i in range(0, len(move_ids), batch_size):
            batch = move_ids[i:i + batch_size]
            move_lines = self.odoo.search_read(
                'stock.move.line',
                [
                    ('move_id', 'in', batch),
                    ('package_id', '!=', False),
                ],
                ['package_id'],
                limit=50000
            )
            
            for ml in (move_lines or []):
                pkg = ml.get('package_id')
                if pkg:
                    pkg_id = pkg[0] if isinstance(pkg, (list, tuple)) else pkg
                    package_ids.add(pkg_id)
        
        logger.info(f"[PALLETS] Total pallets en fabricación: {len(package_ids)}")
        return package_ids
    
    def _get_package_create_dates(self, package_ids: List[int]) -> Dict[int, str]:
        """Obtiene las fechas de creación de los packages (pallets)."""
        if not package_ids:
            return {}
        
        try:
            packages = self.odoo.search_read(
                'stock.quant.package',
                [('id', 'in', package_ids)],
                ['id', 'create_date'],
                limit=len(package_ids)
            )
            
            result = {}
            for pkg in (packages or []):
                create_date = pkg.get('create_date', '')
                if create_date:
                    result[pkg['id']] = str(create_date)[:10]
            
            return result
        except Exception as e:
            logger.error(f"[PALLETS] Error obteniendo fechas de packages: {str(e)}")
            return {}
    
    def _get_lot_proveedores(self, lot_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """
        Obtiene los proveedores de los lotes basándose en las recepciones (stock.picking).
        Para frescos, el proveedor viene del picking de recepción.
        """
        if not lot_ids:
            return {}
        
        try:
            # Buscar move lines con estos lotes que vengan de recepciones
            move_lines = self.odoo.search_read(
                'stock.move.line',
                [
                    ('lot_id', 'in', lot_ids),
                    ('picking_id.picking_type_code', '=', 'incoming'),
                ],
                ['lot_id', 'picking_id'],
                limit=10000,
                order='id desc'
            )
            
            # Obtener IDs únicos de pickings
            picking_ids = list(set([
                ml['picking_id'][0] if isinstance(ml.get('picking_id'), (list, tuple)) else ml.get('picking_id')
                for ml in (move_lines or []) if ml.get('picking_id')
            ]))
            
            if not picking_ids:
                return {}
            
            # Obtener pickings con partner_id
            pickings = self.odoo.search_read(
                'stock.picking',
                [('id', 'in', picking_ids)],
                ['id', 'partner_id'],
                limit=len(picking_ids)
            )
            
            picking_partner_map = {}
            for p in (pickings or []):
                partner = p.get('partner_id')
                if partner and isinstance(partner, (list, tuple)) and len(partner) > 1:
                    picking_partner_map[p['id']] = {
                        'id': partner[0],
                        'nombre': partner[1]
                    }
            
            # Mapear lote -> proveedor
            lot_proveedor = {}
            for ml in (move_lines or []):
                lot = ml.get('lot_id')
                picking = ml.get('picking_id')
                if lot and picking:
                    lot_id = lot[0] if isinstance(lot, (list, tuple)) else lot
                    picking_id = picking[0] if isinstance(picking, (list, tuple)) else picking
                    if lot_id not in lot_proveedor and picking_id in picking_partner_map:
                        lot_proveedor[lot_id] = picking_partner_map[picking_id]
            
            logger.info(f"[PALLETS] Proveedores de lotes encontrados: {len(lot_proveedor)}")
            return lot_proveedor
            
        except Exception as e:
            logger.error(f"[PALLETS] Error obteniendo proveedores de lotes: {str(e)}")
            return {}
    
    def _determinar_tipo(self, product_name: str, lot_name: str, location_name: str) -> str:
        """Determina si el pallet es Congelado o Fresco.
        
        Reglas:
        - Código [1...] = Fresco
        - Código [2...] = Congelado
        - Lote con -C al final = Congelado
        - IQF, FROZEN, CONGELADO en nombre = Congelado
        """
        product_upper = product_name.upper()
        lot_upper = lot_name.upper()
        
        # Si el lote contiene -C es congelado
        if '-C' in lot_upper:
            return 'Congelado'
        
        # Si el producto empieza con código [2 = congelado
        if product_name.startswith('[2'):
            return 'Congelado'
        
        # Si el producto empieza con código [1 = fresco
        if product_name.startswith('[1'):
            return 'Fresco'
        
        # Si tiene IQF, CONGELADO, FROZEN en el nombre
        if 'IQF' in product_upper or 'CONGELADO' in product_upper or 'FROZEN' in product_upper:
            return 'Congelado'
        
        return 'Fresco'
    
    def _determinar_planta(self, location_name: str, package_name: str) -> str:
        """Determina la planta del pallet."""
        combined = (location_name + ' ' + package_name).upper()
        
        if 'VLK' in combined or 'VILKUN' in combined:
            return 'VILKUN'
        return 'RIO FUTURO'
    
    def _empty_result(self) -> Dict[str, Any]:
        return {
            'pallets': [],
            'por_planta': {},
            'estadisticas': {
                'total_pallets': 0,
                'total_kg': 0,
                'congelados': 0,
                'frescos': 0,
                'kg_congelados': 0,
                'kg_frescos': 0,
                'plantas': [],
            }
        }
