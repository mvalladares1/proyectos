"""
Servicio para obtener pallets disponibles que NO están en ninguna fabricación.
Excluye ubicaciones específicas de stock/cámaras.
"""
import logging
from typing import Dict, List, Any, Optional
from shared.odoo_client import OdooClient

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
    
    def get_pallets_disponibles(self, planta: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene pallets con stock que NO están asignados a ninguna fabricación.
        
        Args:
            planta: 'VILKUN', 'RIO FUTURO' o None para todas
        
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
            
            # 3. Obtener pallets que YA están en fabricación (como materia prima)
            pallets_en_fabricacion = self._get_pallets_en_fabricacion()
            logger.info(f"[PALLETS] Pallets en fabricación: {len(pallets_en_fabricacion)}")
            
            # 4. Filtrar: solo pallets que NO están en fabricación
            pallets_disponibles = []
            for q in quants_con_pallet:
                package_id = q['package_id'][0] if isinstance(q['package_id'], (list, tuple)) else q['package_id']
                package_name = q['package_id'][1] if isinstance(q['package_id'], (list, tuple)) else ''
                
                if package_id in pallets_en_fabricacion:
                    continue
                
                # Extraer datos
                product_name = ''
                if isinstance(q.get('product_id'), (list, tuple)) and len(q['product_id']) > 1:
                    product_name = q['product_id'][1]
                
                lot_name = ''
                if isinstance(q.get('lot_id'), (list, tuple)) and len(q['lot_id']) > 1:
                    lot_name = q['lot_id'][1]
                
                location_name = ''
                if isinstance(q.get('location_id'), (list, tuple)) and len(q['location_id']) > 1:
                    location_name = q['location_id'][1]
                
                # Determinar tipo: congelado o fresco
                tipo = self._determinar_tipo(product_name, lot_name, location_name)
                
                # Determinar planta del pallet
                planta_pallet = self._determinar_planta(location_name, package_name)
                
                pallets_disponibles.append({
                    'pallet': package_name,
                    'pallet_id': package_id,
                    'lote': lot_name,
                    'producto': product_name,
                    'cantidad_kg': round(q.get('quantity', 0), 1),
                    'ubicacion': location_name,
                    'fecha_ingreso': str(q.get('in_date', ''))[:10] if q.get('in_date') else '',
                    'tipo': tipo,
                    'planta': planta_pallet,
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
        como materia prima (move_raw_ids), independiente del estado de la MO.
        """
        # Buscar MOs que NO estén canceladas
        mos = self.odoo.search_read(
            'mrp.production',
            [('state', '!=', 'cancel')],
            ['id', 'move_raw_ids'],
            limit=5000,
            order='id desc'
        )
        
        if not mos:
            return set()
        
        # Obtener todos los move_raw_ids
        all_move_ids = []
        for mo in mos:
            raw_ids = mo.get('move_raw_ids', [])
            if raw_ids:
                all_move_ids.extend(raw_ids)
        
        if not all_move_ids:
            return set()
        
        # Buscar move lines con package_id
        move_lines = self.odoo.search_read(
            'stock.move.line',
            [('move_id', 'in', all_move_ids), ('package_id', '!=', False)],
            ['package_id'],
            limit=50000
        )
        
        package_ids = set()
        for ml in (move_lines or []):
            pkg = ml.get('package_id')
            if pkg:
                pkg_id = pkg[0] if isinstance(pkg, (list, tuple)) else pkg
                package_ids.add(pkg_id)
        
        return package_ids
    
    def _determinar_tipo(self, product_name: str, lot_name: str, location_name: str) -> str:
        """Determina si el pallet es Congelado o Fresco."""
        product_upper = product_name.upper()
        lot_upper = lot_name.upper()
        location_upper = location_name.upper()
        
        # Si el lote termina en -C es congelado
        if lot_upper.endswith('-C'):
            return 'Congelado'
        
        # Si está en cámara de congelado
        if 'CAMARA' in location_upper or '-25' in location_upper or 'CONGELADO' in location_upper:
            return 'Congelado'
        
        # Si el producto empieza con código 2 (congelado)
        if product_upper.startswith('[2'):
            return 'Congelado'
        
        # Si tiene IQF, CONGELADO en el nombre
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
