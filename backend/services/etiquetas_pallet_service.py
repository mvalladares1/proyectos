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
# Removed DB cache: no persistent reservations. Simple in-memory/no-op behaviors below.

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

    def obtener_candidatos_previos(self, package_id: int, product_name: Optional[str] = None, manejo: Optional[str] = None, variedad: Optional[str] = None, limit: int = 500) -> List[Dict]:
        """
        Dado un `package_id` (pallet destino), devuelve los paquetes ORIGEN
        que lo conformaron. Usa la ruta MRP confirmada:

          result_package_id → move → production_id (OP que produjo este pallet)
          → raw_material_production_id (movimientos de consumo de esa OP)
          → move_lines → package_id (pallets fuente consumidos)

        Si no tiene OP, busca relación directa de pickings (package_id → result_package_id).
        Si tampoco → busca recepción (es hoja sin orígenes).

        Returns:
          - Lista de candidatos con package_id, package_name, qty, producto, lote, etc.
          - is_reception=True si el pallet viene de una recepción
          - mo_name si tiene orden de producción
        """
        try:
            # ═══════════════════════════════════════════════════════════
            # PASO 1: Buscar la OP que PRODUJO este pallet
            # ═══════════════════════════════════════════════════════════
            mo = self._find_mo_for_package(package_id)

            if mo:
                # Tiene OP → buscar pallets consumidos por esa OP
                return self._get_consumed_packages(mo, package_id)

            # ═══════════════════════════════════════════════════════════
            # PASO 2: Sin OP → buscar relación directa en pickings
            #   (package_id → result_package_id en la misma move_line)
            # ═══════════════════════════════════════════════════════════
            direct = self._get_direct_source_packages(package_id)
            if direct:
                return direct

            # ═══════════════════════════════════════════════════════════
            # PASO 3: Sin OP ni pickings con fuentes → verificar recepción
            # ═══════════════════════════════════════════════════════════
            recep = self._buscar_recepcion_pkg(package_id)
            if recep:
                # Es un pallet de recepción → retornar lista vacía
                # pero con metadata de recepción en el response
                return []

            return []

        except Exception as e:
            logger.error(f"Error obteniendo candidatos previos para package {package_id}: {e}")
            return []

    def _find_mo_for_package(self, pkg_id: int) -> Optional[Dict]:
        """
        Encuentra la OP (mrp.production) que produjo un pallet.
        Ruta: result_package_id → stock.move.line → stock.move → production_id → mrp.production
        Optimizado: hace batch de move_ids en una sola query.
        """
        sml = self.odoo.search_read(
            'stock.move.line',
            [('result_package_id', '=', pkg_id)],
            ['move_id'],
            limit=10,
        )
        if not sml:
            return None

        # Batch: obtener todos los move_ids de una vez
        move_ids = []
        for s in sml:
            mid = s.get('move_id')
            if mid:
                move_ids.append(mid[0] if isinstance(mid, (list, tuple)) else mid)

        if not move_ids:
            return None

        # Una sola query para todos los moves
        moves = self.odoo.search_read(
            'stock.move',
            [('id', 'in', move_ids), ('production_id', '!=', False)],
            ['production_id'],
            limit=1,
        )
        if not moves:
            return None

        prod_id_val = moves[0].get('production_id')
        if not prod_id_val:
            return None
        mo_id = prod_id_val[0] if isinstance(prod_id_val, (list, tuple)) else prod_id_val

        mos = self.odoo.search_read(
            'mrp.production',
            [('id', '=', mo_id)],
            ['id', 'name', 'product_id'],
            limit=1,
        )
        return mos[0] if mos else None

    def _get_consumed_packages(self, mo: Dict, dest_package_id: int) -> List[Dict]:
        """
        Dado una OP, obtiene los pallets consumidos como materia prima
        que corresponden al result_package `dest_package_id`.

        Cuando la OP produce UN SOLO pallet resultado → devuelve todos los consumidos.
        Cuando produce MÚLTIPLES resultados (ej. congelado produce PACK####-C por cada PACK####):
          1. Si las líneas de consumo tienen result_package_id → filtra directamente
          2. Si no, usa coincidencia de nombre (PACK0002622-C ← PACK0002622)
          3. Los consumidos que no corresponden a OTRO resultado se incluyen como compartidos

        Ruta: raw_material_production_id → stock.move → move_lines → package_id
        """
        mo_id = mo['id']
        mo_name = mo.get('name', '')

        # Buscar movimientos de consumo de la OP
        moves = self.odoo.search_read(
            'stock.move',
            [
                ('raw_material_production_id', '=', mo_id),
                ('state', '=', 'done'),
            ],
            ['id'],
        )
        if not moves:
            return []

        move_ids = [m['id'] for m in moves]

        # Obtener move_lines con package_id (fuente) Y result_package_id si existe
        smls = self.odoo.search_read(
            'stock.move.line',
            [
                ('move_id', 'in', move_ids),
                ('package_id', '!=', False),
            ],
            ['package_id', 'result_package_id', 'product_id', 'qty_done', 'lot_id', 'date'],
        )

        if not smls:
            return []

        # ── Verificar si las líneas de consumo tienen result_package_id ──
        # Si sí → podemos filtrar directamente
        has_result_link = any(s.get('result_package_id') for s in smls)

        # Agrupar por package fuente, opcionalmente filtrando por result_package_id
        candidates: Dict[int, dict] = {}
        for s in smls:
            pkg = s.get('package_id')
            if not pkg:
                continue
            pkg_id = pkg[0] if isinstance(pkg, (list, tuple)) else pkg
            pkg_name = pkg[1] if isinstance(pkg, (list, tuple)) and len(pkg) > 1 else str(pkg_id)
            if pkg_id == dest_package_id:
                continue

            # Si hay link directo result_package_id en consumo, filtrar
            if has_result_link:
                rpkg = s.get('result_package_id')
                if rpkg:
                    rpkg_id = rpkg[0] if isinstance(rpkg, (list, tuple)) else rpkg
                    if rpkg_id != dest_package_id:
                        continue  # Esta línea de consumo fue para OTRO resultado

            prod = s.get('product_id')
            prod_id = prod[0] if prod and isinstance(prod, (list, tuple)) else prod
            prod_nm = prod[1] if prod and isinstance(prod, (list, tuple)) and len(prod) > 1 else ''
            qty = float(s.get('qty_done', 0) or 0)
            lot = s.get('lot_id')
            lot_name = lot[1] if isinstance(lot, (list, tuple)) and len(lot) > 1 else ''

            if pkg_id not in candidates:
                candidates[pkg_id] = {
                    'package_id': pkg_id,
                    'package_name': pkg_name,
                    'product_id': prod_id,
                    'product_name': prod_nm,
                    'qty_total': 0.0,
                    'lot_name': lot_name,
                    'last_date': s.get('date'),
                    'mo_name': mo_name,
                    'source_type': 'production',
                }
            candidates[pkg_id]['qty_total'] += qty
            d = s.get('date')
            if d and (not candidates[pkg_id]['last_date'] or str(d) > str(candidates[pkg_id]['last_date'])):
                candidates[pkg_id]['last_date'] = d

        results = list(candidates.values())

        # ── Si no hubo filtro por result_package_id, intentar por nombre ──
        if not has_result_link and results:
            results = self._narrow_consumed_by_result(results, dest_package_id, mo_id)

        results.sort(key=lambda x: x.get('qty_total', 0), reverse=True)
        return results

    def _narrow_consumed_by_result(self, candidates: List[Dict],
                                   dest_package_id: int, mo_id: int) -> List[Dict]:
        """
        Cuando una OP produjo MÚLTIPLES result_package_ids, filtra los
        candidatos consumidos para mostrar solo los que corresponden
        a `dest_package_id` (por coincidencia de nombre) y los compartidos.

        Ejemplo: OP congelado produce PACK0002622-C y PACK0002339-C.
          - Para PACK0002622-C → devuelve PACK0002622 (match) + compartidos
          - Excluye PACK0002339 porque ese corresponde a PACK0002339-C
        """
        # Buscar cuántos result_package_ids produjo esta OP
        prod_moves = self.odoo.search_read(
            'stock.move',
            [('production_id', '=', mo_id), ('state', '=', 'done')],
            ['id'],
        )
        if not prod_moves:
            return candidates

        prod_move_ids = [m['id'] for m in prod_moves]
        result_smls = self.odoo.search_read(
            'stock.move.line',
            [('move_id', 'in', prod_move_ids), ('result_package_id', '!=', False)],
            ['result_package_id'],
        )

        result_pkgs: Dict[int, str] = {}  # id → name
        for rs in result_smls:
            rpkg = rs.get('result_package_id')
            if rpkg:
                rid = rpkg[0] if isinstance(rpkg, (list, tuple)) else rpkg
                rname = rpkg[1] if isinstance(rpkg, (list, tuple)) and len(rpkg) > 1 else ''
                result_pkgs[rid] = rname

        # Si solo 1 resultado → devolver todo (no hay ambigüedad)
        if len(result_pkgs) <= 1:
            return candidates

        # Obtener nombre base del pallet destino
        dest_name = result_pkgs.get(dest_package_id, '')
        if not dest_name:
            pkg = self.odoo.search_read(
                'stock.quant.package', [('id', '=', dest_package_id)],
                ['name'], limit=1,
            )
            dest_name = pkg[0]['name'] if pkg else ''

        dest_base = self._strip_pallet_suffix(dest_name)

        # Mapear nombres base de TODOS los resultados
        other_result_bases: set = set()
        for rid, rname in result_pkgs.items():
            if rid != dest_package_id:
                other_result_bases.add(self._strip_pallet_suffix(rname))

        # Clasificar cada candidato consumido
        matched: List[Dict] = []    # coincide con nuestro resultado
        shared: List[Dict] = []     # no coincide con ninguno → compartido
        for c in candidates:
            c_base = self._strip_pallet_suffix(c['package_name'])
            if c_base == dest_base:
                matched.append(c)
            elif c_base in other_result_bases:
                pass  # coincide con OTRO resultado → excluir
            else:
                shared.append(c)

        if matched:
            return matched + shared

        # Sin matches por nombre → devolver todo (fallback seguro)
        return candidates

    @staticmethod
    def _strip_pallet_suffix(name: str) -> str:
        """
        Quita sufijos tipo -C, -A, -B, -IQF, etc. de un nombre de pallet.
        PACK0002622-C → PACK0002622
        """
        if not name:
            return ''
        n = name.strip().upper()
        m = re.match(r'^(PACK\d+)(-[A-Za-z0-9]+)?$', n)
        if m:
            return m.group(1)
        return n

    def _get_direct_source_packages(self, package_id: int) -> List[Dict]:
        """
        Para pickings/transferencias internas donde package_id (fuente) y
        result_package_id (destino) están en la misma move_line.
        """
        mls = self.odoo.search_read(
            'stock.move.line',
            [
                ('result_package_id', '=', package_id),
                ('package_id', '!=', False),
                ('qty_done', '>', 0),
            ],
            ['package_id', 'product_id', 'qty_done', 'lot_id', 'date', 'picking_id'],
            limit=500,
        )
        if not mls:
            return []

        candidates: Dict[int, dict] = {}
        for ml in mls:
            src_pkg = ml.get('package_id')
            if not src_pkg:
                continue
            src_id = src_pkg[0] if isinstance(src_pkg, (list, tuple)) else src_pkg
            if src_id == package_id:
                continue

            src_name = src_pkg[1] if isinstance(src_pkg, (list, tuple)) and len(src_pkg) > 1 else str(src_id)
            prod = ml.get('product_id')
            prod_id = prod[0] if prod and isinstance(prod, (list, tuple)) else prod
            prod_nm = prod[1] if prod and isinstance(prod, (list, tuple)) and len(prod) > 1 else ''
            qty = float(ml.get('qty_done', 0) or 0)
            lot = ml.get('lot_id')
            lot_name = lot[1] if isinstance(lot, (list, tuple)) and len(lot) > 1 else ''

            pick = ml.get('picking_id')
            pick_name = pick[1] if isinstance(pick, (list, tuple)) and len(pick) > 1 else ''

            if src_id not in candidates:
                candidates[src_id] = {
                    'package_id': src_id,
                    'package_name': src_name,
                    'product_id': prod_id,
                    'product_name': prod_nm,
                    'qty_total': 0.0,
                    'lot_name': lot_name,
                    'last_date': ml.get('date'),
                    'picking_name': pick_name,
                    'source_type': 'transfer',
                }
            candidates[src_id]['qty_total'] += qty
            d = ml.get('date')
            if d and (not candidates[src_id]['last_date'] or str(d) > str(candidates[src_id]['last_date'])):
                candidates[src_id]['last_date'] = d

        results = list(candidates.values())
        results.sort(key=lambda x: x.get('qty_total', 0), reverse=True)
        return results

    def _buscar_recepcion_pkg(self, pkg_id: int) -> Optional[Dict]:
        """Busca si un pallet llegó en un picking de recepción. Optimizado con batch."""
        smls = self.odoo.search_read(
            'stock.move.line',
            [('result_package_id', '=', pkg_id)],
            ['picking_id'],
            limit=10,
        )
        pick_ids = []
        for sml in smls:
            pick_id = sml.get('picking_id')
            if pick_id:
                pick_ids.append(pick_id[0] if isinstance(pick_id, (list, tuple)) else pick_id)

        if not pick_ids:
            return None

        # Una sola query con todos los picking_ids
        picks = self.odoo.search_read(
            'stock.picking',
            [
                ('id', 'in', pick_ids),
                ('picking_type_id', 'in', [1, 217, 164]),
            ],
            ['id', 'name', 'x_studio_gua_de_despacho', 'partner_id', 'date_done'],
            limit=1,
        )
        if picks:
            p = picks[0]
            partner = p.get('partner_id')
            return {
                'picking_name': p.get('name', ''),
                'guia_despacho': p.get('x_studio_gua_de_despacho') or '',
                'proveedor': partner[1] if isinstance(partner, (list, tuple)) and len(partner) > 1 else '',
                'fecha': str(p.get('date_done') or '')[:10],
            }
        return None

    # ═══════════════════════════════════════════════════════════
    # Trazabilidad completa recursiva (un solo llamado)
    # ═══════════════════════════════════════════════════════════

    def trazar_completo(self, package_id: int, max_levels: int = 10) -> Dict:
        """
        Traza un pallet recursivamente hasta las recepciones en un solo llamado.
        Devuelve el árbol completo con todos los nodos y niveles.

        Returns:
            {
                root_id, root_name,
                nodes: [{ node_id, pkg_id, pkg_name, parent_node_id,
                          mo_name, level, is_leaf, reception_info,
                          qty, product_name, lot_name }],
                levels: int,
                reception_count: int,
                leaf_count: int,
            }
        """
        # Obtener nombre del pallet raíz
        pkg_info = self.odoo.search_read(
            'stock.quant.package', [('id', '=', package_id)],
            ['name'], limit=1,
        )
        root_name = pkg_info[0]['name'] if pkg_info else f'ID-{package_id}'

        node_counter = 0
        all_nodes: List[Dict] = []
        visited: set = set()  # pkg_ids ya procesados por ancestro, para ciclos

        def _next_id():
            nonlocal node_counter
            node_counter += 1
            return node_counter

        def _trace_level(queue: List[Dict], level: int):
            """Procesa una cola de nodos pendientes en un nivel dado."""
            if level > max_levels or not queue:
                # Marcar como hojas si excedimos max_levels
                for n in queue:
                    n['is_leaf'] = True
                return

            next_queue: List[Dict] = []

            # Cache de resultados por pkg_id para no repetir queries
            cache: Dict[int, Dict] = {}

            for node in queue:
                pid = node['pkg_id']

                # Evitar ciclo: si este pkg_id ya está en los ancestros de este nodo
                ancestors = set()
                cur = node
                while cur.get('_parent_ref'):
                    ancestors.add(cur['_parent_ref']['pkg_id'])
                    cur = cur['_parent_ref']
                if pid in ancestors:
                    node['is_leaf'] = True
                    continue

                # Buscar candidatos (con cache)
                if pid not in cache:
                    mo = self._find_mo_for_package(pid)
                    if mo:
                        cands = self._get_consumed_packages(mo, pid)
                        mo_name = mo.get('name', '')
                    else:
                        direct = self._get_direct_source_packages(pid)
                        if direct:
                            cands = direct
                            mo_name = ''
                        else:
                            cands = []
                            mo_name = ''

                    rec = None
                    if not cands:
                        rec = self._buscar_recepcion_pkg(pid)

                    cache[pid] = {'cands': cands, 'mo_name': mo_name, 'rec': rec}

                cached = cache[pid]
                node['mo_name'] = cached['mo_name']

                if not cached['cands']:
                    node['is_leaf'] = True
                    if cached['rec']:
                        node['reception_info'] = cached['rec']
                    continue

                # Crear nodos hijos
                for c in cached['cands']:
                    c_id = c.get('package_id')
                    if not c_id:
                        continue
                    child = {
                        'node_id': _next_id(),
                        'pkg_id': c_id,
                        'pkg_name': c.get('package_name', str(c_id)),
                        'parent_node_id': node['node_id'],
                        'mo_name': cached['mo_name'],
                        'level': level + 1,
                        'is_leaf': False,
                        'reception_info': None,
                        'qty': c.get('qty_total', 0),
                        'product_name': c.get('product_name', ''),
                        'lot_name': c.get('lot_name', ''),
                        '_parent_ref': node,  # referencia temporal para ancestros
                    }
                    all_nodes.append(child)
                    next_queue.append(child)

            # Recursar al siguiente nivel
            if next_queue:
                _trace_level(next_queue, level + 1)

        # ── Nodo raíz ──
        root_node = {
            'node_id': _next_id(),
            'pkg_id': package_id,
            'pkg_name': root_name,
            'parent_node_id': None,
            'mo_name': None,
            'level': 0,
            'is_leaf': False,
            'reception_info': None,
            'qty': None,
            'product_name': '',
            'lot_name': '',
            '_parent_ref': None,
        }
        all_nodes.append(root_node)

        # ── Trazar recursivamente ──
        _trace_level([root_node], 0)

        # Limpiar _parent_ref (no serializable)
        for n in all_nodes:
            n.pop('_parent_ref', None)

        # Métricas
        max_level = max(n['level'] for n in all_nodes)
        leaf_count = sum(1 for n in all_nodes if n['is_leaf'])
        rec_count = sum(1 for n in all_nodes if n.get('reception_info'))

        return {
            'root_id': package_id,
            'root_name': root_name,
            'nodes': all_nodes,
            'levels': max_level + 1,
            'leaf_count': leaf_count,
            'reception_count': rec_count,
        }

    # ═══════════════════════════════════════════════════════════
    # Trazabilidad FORWARD (de origen hacia destinos)
    # ═══════════════════════════════════════════════════════════

    def _find_destination_packages(self, pkg_id: int) -> List[Dict]:
        """
        Dado un package, encuentra los pallets DESTINO donde fue consumido.
        Ruta: package_id (consumido) → stock.move.line → move_id
              → production_id (OP que lo consumió) → result move_lines → result_package_id
        También cubre transfers: package_id → result_package_id en la misma move_line.
        """
        # Buscar move_lines donde este pallet fue consumido (package_id = pkg_id)
        smls = self.odoo.search_read(
            'stock.move.line',
            [
                ('package_id', '=', pkg_id),
                ('qty_done', '>', 0),
            ],
            ['move_id', 'result_package_id', 'product_id', 'qty_done', 'lot_id', 'date'],
            limit=500,
        )
        if not smls:
            return []

        candidates: Dict[int, dict] = {}

        # 1) Transfers directos: si result_package_id != package_id
        for sml in smls:
            rpkg = sml.get('result_package_id')
            if not rpkg:
                continue
            rpkg_id = rpkg[0] if isinstance(rpkg, (list, tuple)) else rpkg
            rpkg_name = rpkg[1] if isinstance(rpkg, (list, tuple)) and len(rpkg) > 1 else str(rpkg_id)
            if rpkg_id == pkg_id:
                continue  # mismo pallet, no es destino

            prod = sml.get('product_id')
            prod_nm = prod[1] if prod and isinstance(prod, (list, tuple)) and len(prod) > 1 else ''
            qty = float(sml.get('qty_done', 0) or 0)
            lot = sml.get('lot_id')
            lot_name = lot[1] if isinstance(lot, (list, tuple)) and len(lot) > 1 else ''

            if rpkg_id not in candidates:
                candidates[rpkg_id] = {
                    'package_id': rpkg_id,
                    'package_name': rpkg_name,
                    'product_name': prod_nm,
                    'qty_total': 0.0,
                    'lot_name': lot_name,
                    'last_date': sml.get('date'),
                    'mo_name': '',
                    'source_type': 'transfer',
                }
            candidates[rpkg_id]['qty_total'] += qty

        # 2) Producción: buscar OP que consumió este pallet
        move_ids = []
        for sml in smls:
            mid = sml.get('move_id')
            if mid:
                move_ids.append(mid[0] if isinstance(mid, (list, tuple)) else mid)

        if move_ids:
            # Buscar moves de consumo con raw_material_production_id
            raw_moves = self.odoo.search_read(
                'stock.move',
                [('id', 'in', move_ids), ('raw_material_production_id', '!=', False)],
                ['raw_material_production_id'],
                limit=50,
            )
            mo_ids = set()
            for rm in raw_moves:
                rmpi = rm.get('raw_material_production_id')
                if rmpi:
                    mo_ids.add(rmpi[0] if isinstance(rmpi, (list, tuple)) else rmpi)

            for mo_id in mo_ids:
                # Buscar pallets resultado de esta OP
                prod_moves = self.odoo.search_read(
                    'stock.move',
                    [('production_id', '=', mo_id), ('state', '=', 'done')],
                    ['id'],
                    limit=50,
                )
                if not prod_moves:
                    continue

                # Obtener nombre de la OP
                mo_info = self.odoo.search_read(
                    'mrp.production', [('id', '=', mo_id)],
                    ['name'], limit=1,
                )
                mo_name = mo_info[0]['name'] if mo_info else ''

                prod_move_ids = [m['id'] for m in prod_moves]
                result_smls = self.odoo.search_read(
                    'stock.move.line',
                    [
                        ('move_id', 'in', prod_move_ids),
                        ('result_package_id', '!=', False),
                        ('qty_done', '>', 0),
                    ],
                    ['result_package_id', 'product_id', 'qty_done', 'lot_id', 'date'],
                    limit=500,
                )

                for rs in result_smls:
                    rpkg = rs.get('result_package_id')
                    if not rpkg:
                        continue
                    rpkg_id = rpkg[0] if isinstance(rpkg, (list, tuple)) else rpkg
                    rpkg_name = rpkg[1] if isinstance(rpkg, (list, tuple)) and len(rpkg) > 1 else str(rpkg_id)
                    if rpkg_id == pkg_id:
                        continue

                    prod = rs.get('product_id')
                    prod_nm = prod[1] if prod and isinstance(prod, (list, tuple)) and len(prod) > 1 else ''
                    qty = float(rs.get('qty_done', 0) or 0)
                    lot = rs.get('lot_id')
                    lot_name = lot[1] if isinstance(lot, (list, tuple)) and len(lot) > 1 else ''

                    if rpkg_id not in candidates:
                        candidates[rpkg_id] = {
                            'package_id': rpkg_id,
                            'package_name': rpkg_name,
                            'product_name': prod_nm,
                            'qty_total': 0.0,
                            'lot_name': lot_name,
                            'last_date': rs.get('date'),
                            'mo_name': mo_name,
                            'source_type': 'production',
                        }
                    candidates[rpkg_id]['qty_total'] += qty
                    if not candidates[rpkg_id]['mo_name']:
                        candidates[rpkg_id]['mo_name'] = mo_name

        results = list(candidates.values())
        results.sort(key=lambda x: x.get('qty_total', 0), reverse=True)
        return results

    def _buscar_despacho_pkg(self, pkg_id: int) -> Optional[Dict]:
        """Busca si un pallet salió en un picking de despacho/venta (forward leaf)."""
        smls = self.odoo.search_read(
            'stock.move.line',
            [('package_id', '=', pkg_id), ('qty_done', '>', 0)],
            ['picking_id'],
            limit=10,
        )
        pick_ids = []
        for sml in smls:
            pick_id = sml.get('picking_id')
            if pick_id:
                pick_ids.append(pick_id[0] if isinstance(pick_id, (list, tuple)) else pick_id)

        if not pick_ids:
            return None

        # Buscar pickings de salida (delivery orders) — picking_type_id para outgoing
        picks = self.odoo.search_read(
            'stock.picking',
            [
                ('id', 'in', pick_ids),
                ('picking_type_id.code', '=', 'outgoing'),
            ],
            ['id', 'name', 'partner_id', 'date_done', 'origin'],
            limit=1,
        )
        if picks:
            p = picks[0]
            partner = p.get('partner_id')
            return {
                'picking_name': p.get('name', ''),
                'cliente': partner[1] if isinstance(partner, (list, tuple)) and len(partner) > 1 else '',
                'fecha': str(p.get('date_done') or '')[:10],
                'origin': p.get('origin', ''),
            }
        return None

    def trazar_forward(self, package_id: int, max_levels: int = 10) -> Dict:
        """
        Traza un pallet HACIA ADELANTE: desde el origen hacia sus destinos.
        Encuentra dónde fue consumido y qué pallets se produjeron a partir de él.

        Returns: misma estructura que trazar_completo pero en dirección forward.
        """
        pkg_info = self.odoo.search_read(
            'stock.quant.package', [('id', '=', package_id)],
            ['name'], limit=1,
        )
        root_name = pkg_info[0]['name'] if pkg_info else f'ID-{package_id}'

        node_counter = 0
        all_nodes: List[Dict] = []
        visited: set = set()

        def _next_id():
            nonlocal node_counter
            node_counter += 1
            return node_counter

        def _trace_forward_level(queue: List[Dict], level: int):
            if level > max_levels or not queue:
                for n in queue:
                    n['is_leaf'] = True
                return

            next_queue: List[Dict] = []
            cache: Dict[int, Dict] = {}

            for node in queue:
                pid = node['pkg_id']

                # Evitar ciclos
                ancestors = set()
                cur = node
                while cur.get('_parent_ref'):
                    ancestors.add(cur['_parent_ref']['pkg_id'])
                    cur = cur['_parent_ref']
                if pid in ancestors:
                    node['is_leaf'] = True
                    continue

                if pid not in cache:
                    dests = self._find_destination_packages(pid)
                    despacho = None
                    if not dests:
                        despacho = self._buscar_despacho_pkg(pid)
                    cache[pid] = {'dests': dests, 'despacho': despacho}

                cached = cache[pid]

                if not cached['dests']:
                    node['is_leaf'] = True
                    if cached['despacho']:
                        node['dispatch_info'] = cached['despacho']
                    # Buscar recepción también (nodo origen)
                    if level == 0:
                        rec = self._buscar_recepcion_pkg(pid)
                        if rec:
                            node['reception_info'] = rec
                    continue

                for c in cached['dests']:
                    c_id = c.get('package_id')
                    if not c_id:
                        continue
                    child = {
                        'node_id': _next_id(),
                        'pkg_id': c_id,
                        'pkg_name': c.get('package_name', str(c_id)),
                        'parent_node_id': node['node_id'],
                        'mo_name': c.get('mo_name', ''),
                        'level': level + 1,
                        'is_leaf': False,
                        'reception_info': None,
                        'dispatch_info': None,
                        'qty': c.get('qty_total', 0),
                        'product_name': c.get('product_name', ''),
                        'lot_name': c.get('lot_name', ''),
                        '_parent_ref': node,
                    }
                    all_nodes.append(child)
                    next_queue.append(child)

            if next_queue:
                _trace_forward_level(next_queue, level + 1)

        # Nodo raíz — buscar si tiene recepción (puede ser el origen)
        rec_info = self._buscar_recepcion_pkg(package_id)
        root_node = {
            'node_id': _next_id(),
            'pkg_id': package_id,
            'pkg_name': root_name,
            'parent_node_id': None,
            'mo_name': None,
            'level': 0,
            'is_leaf': False,
            'reception_info': rec_info,
            'dispatch_info': None,
            'qty': None,
            'product_name': '',
            'lot_name': '',
            '_parent_ref': None,
        }
        all_nodes.append(root_node)

        _trace_forward_level([root_node], 0)

        for n in all_nodes:
            n.pop('_parent_ref', None)

        max_level = max(n['level'] for n in all_nodes)
        leaf_count = sum(1 for n in all_nodes if n['is_leaf'])
        dispatch_count = sum(1 for n in all_nodes if n.get('dispatch_info'))
        rec_count = sum(1 for n in all_nodes if n.get('reception_info'))

        return {
            'root_id': package_id,
            'root_name': root_name,
            'nodes': all_nodes,
            'levels': max_level + 1,
            'leaf_count': leaf_count,
            'reception_count': rec_count,
            'dispatch_count': dispatch_count,
            'direction': 'forward',
        }

    # ═══════════════════════════════════════════════════════════
    # Búsqueda de pallets por LOTE
    # ═══════════════════════════════════════════════════════════

    def buscar_pallets_por_lote(self, lot_name: str) -> List[Dict]:
        """
        Busca todos los pallets asociados a un lote de producción.
        Retorna lista de {package_id, package_name, product_name, qty, lot_name}.
        """
        # Buscar el lote
        lots = self.odoo.search_read(
            'stock.lot',
            [('name', 'ilike', lot_name.strip())],
            ['id', 'name', 'product_id'],
            limit=20,
        )
        if not lots:
            return []

        lot_ids = [l['id'] for l in lots]

        # Buscar quants con esos lotes que estén en un paquete
        quants = self.odoo.search_read(
            'stock.quant',
            [
                ('lot_id', 'in', lot_ids),
                ('package_id', '!=', False),
                ('quantity', '>', 0),
            ],
            ['package_id', 'product_id', 'quantity', 'lot_id'],
            limit=500,
        )

        # También buscar move_lines con esos lotes (para lotes ya consumidos)
        move_lines = self.odoo.search_read(
            'stock.move.line',
            [
                ('lot_id', 'in', lot_ids),
                ('result_package_id', '!=', False),
                ('qty_done', '>', 0),
            ],
            ['result_package_id', 'product_id', 'qty_done', 'lot_id'],
            limit=1000,
        )

        pallets: Dict[int, dict] = {}

        for q in quants:
            pkg = q.get('package_id')
            if not pkg:
                continue
            pkg_id = pkg[0] if isinstance(pkg, (list, tuple)) else pkg
            pkg_name = pkg[1] if isinstance(pkg, (list, tuple)) and len(pkg) > 1 else str(pkg_id)
            prod = q.get('product_id')
            prod_name = prod[1] if isinstance(prod, (list, tuple)) and len(prod) > 1 else ''
            lot = q.get('lot_id')
            lot_nm = lot[1] if isinstance(lot, (list, tuple)) and len(lot) > 1 else ''

            if pkg_id not in pallets:
                pallets[pkg_id] = {
                    'package_id': pkg_id,
                    'package_name': pkg_name,
                    'product_name': prod_name,
                    'qty': 0,
                    'lot_name': lot_nm,
                    'source': 'quant',
                }
            pallets[pkg_id]['qty'] += float(q.get('quantity', 0))

        for ml in move_lines:
            rpkg = ml.get('result_package_id')
            if not rpkg:
                continue
            pkg_id = rpkg[0] if isinstance(rpkg, (list, tuple)) else rpkg
            pkg_name = rpkg[1] if isinstance(rpkg, (list, tuple)) and len(rpkg) > 1 else str(pkg_id)
            prod = ml.get('product_id')
            prod_name = prod[1] if isinstance(prod, (list, tuple)) and len(prod) > 1 else ''
            lot = ml.get('lot_id')
            lot_nm = lot[1] if isinstance(lot, (list, tuple)) and len(lot) > 1 else ''

            if pkg_id not in pallets:
                pallets[pkg_id] = {
                    'package_id': pkg_id,
                    'package_name': pkg_name,
                    'product_name': prod_name,
                    'qty': 0,
                    'lot_name': lot_nm,
                    'source': 'move_line',
                }
            pallets[pkg_id]['qty'] += float(ml.get('qty_done', 0))

        results = list(pallets.values())
        results.sort(key=lambda x: x.get('package_name', ''))
        return results

    def trazar_lote_completo(self, lot_name: str, direction: str = 'backward', max_levels: int = 10) -> Dict:
        """
        Traza todos los pallets de un lote en la dirección indicada.
        Combina los resultados de cada pallet en un solo árbol con nodo raíz virtual (el lote).

        Args:
            lot_name: Nombre del lote
            direction: 'backward' o 'forward'
            max_levels: Máximo de niveles a trazar

        Returns:
            Estructura similar a trazar_completo pero con raíz virtual del lote.
        """
        pallets = self.buscar_pallets_por_lote(lot_name)
        if not pallets:
            return {
                'root_id': None,
                'root_name': f'Lote: {lot_name}',
                'nodes': [],
                'levels': 0,
                'leaf_count': 0,
                'reception_count': 0,
                'dispatch_count': 0,
                'direction': direction,
                'lot_name': lot_name,
                'pallets_found': 0,
            }

        # Crear nodo raíz virtual para el lote
        all_nodes: List[Dict] = []
        node_counter = 0

        def _next_id():
            nonlocal node_counter
            node_counter += 1
            return node_counter

        lot_root = {
            'node_id': _next_id(),
            'pkg_id': None,
            'pkg_name': f'LOTE: {lot_name}',
            'parent_node_id': None,
            'mo_name': None,
            'level': 0,
            'is_leaf': False,
            'reception_info': None,
            'dispatch_info': None,
            'qty': None,
            'product_name': pallets[0].get('product_name', '') if pallets else '',
            'lot_name': lot_name,
        }
        all_nodes.append(lot_root)

        total_rec = 0
        total_dispatch = 0
        max_depth = 0

        for pallet in pallets:
            pkg_id = pallet['package_id']
            trace_fn = self.trazar_forward if direction == 'forward' else self.trazar_completo
            sub_result = trace_fn(pkg_id, max_levels=max_levels)

            sub_nodes = sub_result.get('nodes', [])
            if not sub_nodes:
                continue

            # Remap node_ids para evitar colisiones
            id_map = {}
            for sn in sub_nodes:
                old_id = sn['node_id']
                new_id = _next_id()
                id_map[old_id] = new_id
                sn['node_id'] = new_id

            # Remap parent_node_ids
            for sn in sub_nodes:
                if sn['parent_node_id'] is None:
                    # Es raíz del sub-árbol → conectar al lote root
                    sn['parent_node_id'] = lot_root['node_id']
                    sn['level'] = 1
                else:
                    sn['parent_node_id'] = id_map.get(sn['parent_node_id'], sn['parent_node_id'])
                    sn['level'] = sn['level'] + 1

            all_nodes.extend(sub_nodes)
            total_rec += sub_result.get('reception_count', 0)
            total_dispatch += sub_result.get('dispatch_count', 0)
            if sub_nodes:
                sub_max = max(sn['level'] for sn in sub_nodes)
                if sub_max > max_depth:
                    max_depth = sub_max

        leaf_count = sum(1 for n in all_nodes if n.get('is_leaf'))

        return {
            'root_id': None,
            'root_name': f'Lote: {lot_name}',
            'nodes': all_nodes,
            'levels': max_depth + 1 if all_nodes else 0,
            'leaf_count': leaf_count,
            'reception_count': total_rec,
            'dispatch_count': total_dispatch,
            'direction': direction,
            'lot_name': lot_name,
            'pallets_found': len(pallets),
        }

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
    
    def _calcular_carton_no_inicio(self, package_id: int, fecha_inicio_proceso: str = None, orden_actual: str = None) -> int:
        """
        Calcula el número inicial de cartón (CARTON NO.) para un pallet basado en procesos previos.
        Si se pasa orden_actual, suma solo movimientos de órdenes anteriores (por nombre).
        """
        try:
            domain = [('result_package_id', '=', package_id), ('qty_done', '>', 0)]
            move_lines = self.odoo.search_read(
                'stock.move.line',
                domain,
                ['qty_done', 'move_id'],
                limit=2000
            )
            total_cajas_previas = 0
            if orden_actual:
                # Buscar el id de la orden actual
                move_ids = [ml['move_id'][0] if isinstance(ml['move_id'], (list, tuple)) else ml['move_id'] for ml in move_lines if ml.get('move_id')]
                if move_ids:
                    moves = self.odoo.search_read(
                        'stock.move',
                        [('id', 'in', list(set(move_ids)))],
                        ['id', 'origin', 'picking_id', 'reference', 'name'],
                        limit=2000
                    )
                    # Mapear move_id a nombre de orden
                    moveid_to_orden = {m['id']: (m.get('origin') or m.get('reference') or m.get('name') or '') for m in moves}
                    for ml in move_lines:
                        mid = ml.get('move_id')
                        mid_val = mid[0] if isinstance(mid, (list, tuple)) else mid
                        orden_ml = moveid_to_orden.get(mid_val, '')
                        if orden_ml and orden_ml < orden_actual:
                            total_cajas_previas += int(ml.get('qty_done', 0))
                else:
                    total_cajas_previas = 0
            else:
                total_cajas_previas = sum(int(ml.get('qty_done', 0)) for ml in move_lines)
            return total_cajas_previas + 1  # El siguiente número de cartón
        except Exception as e:
            logger.error(f"Error calculando CARTON NO. inicial para package {package_id}: {e}")
            return 1  # Por defecto, empezar en 1

    def reservar_cartones(self, package_id: int, package_name: str, qty: int, orden_actual: str = '', usuario: str = '') -> Dict:
        """
        Reserva atómica de `qty` cartones para un pallet usando la caché SQLite.
        Devuelve dict con `start_carton` y `qty`.
        """
        try:
            # DB-less behavior: do not persist, return start 1 for simplicity
            return {"start_carton": 1, "qty": int(qty)}
        except Exception as e:
            logger.error(f"Error reservando cartones para package {package_id}: {e}")
            raise

    def asegurar_bloque_labels(self, package_id: int, package_name: str, block_size: int = 90, orden_actual: str = '', usuario: str = '') -> Dict:
        """
        Al sacar un pallet NUA, genera 90 etiquetas sin guardar reservas ni usar DB.
        Devuelve start_carton=1, qty=block_size, pdf_path y lista de etiquetas con carton_no correlativo.
        """
        try:
            from backend.utils.generador_etiquetas import GeneradorEtiquetasPDF
            # Obtener datos base para las etiquetas
            info = self.obtener_info_etiqueta(package_id=package_id, cliente='', fecha_inicio_proceso=None, orden_actual=orden_actual)
            lista = []
            for i in range(int(block_size)):
                item = {
                    'nombre_producto': info.get('nombre_producto') if info else package_name,
                    'codigo_producto': info.get('codigo_producto') if info else '',
                    'peso_pallet_kg': info.get('peso_pallet_kg') if info else 0,
                    'cantidad_cajas': info.get('cantidad_cajas') if info else 0,
                    'fecha_elaboracion': info.get('fecha_elaboracion') if info else '',
                    'fecha_vencimiento': info.get('fecha_vencimiento') if info else '',
                    'lote_produccion': info.get('lote_produccion') if info else '',
                    'numero_pallet': info.get('numero_pallet') if info else package_name,
                    'carton_no': i + 1
                }
                lista.append(item)
            import os
            base_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
            os.makedirs(base_dir, exist_ok=True)
            generador = GeneradorEtiquetasPDF()
            pdf_bytes = generador.generar_etiquetas_multiples(lista)
            out_path = os.path.join(base_dir, f'etiquetas_block_{package_id}.pdf')
            with open(out_path, 'wb') as f:
                f.write(pdf_bytes)
            return {"start_carton": 1, "qty": int(block_size), "pdf_path": out_path, "etiquetas": lista}
        except Exception as e:
            logger.error(f"Error generando etiquetas NUA para package {package_id}: {e}")
            raise
    
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
            
            # Para cada pallet, buscar la fecha más antigua de TODOS sus move lines
            # (no solo los de esta orden, porque un pallet puede haberse iniciado en otra)
            package_ids = [p['package_id'] for p in pallets_dict.values()]
            if package_ids:
                all_move_lines_fechas = self.odoo.search_read(
                    'stock.move.line',
                    [
                        ('result_package_id', 'in', package_ids),
                        ('qty_done', '>', 0),
                        ('date', '!=', False)
                    ],
                    ['result_package_id', 'date'],
                    limit=2000,
                    order='date asc'
                )
                # Mapear package_id → fecha más antigua
                fecha_inicio_pallet = {}
                for ml in all_move_lines_fechas:
                    rpid = ml.get('result_package_id')
                    pk = rpid[0] if isinstance(rpid, (list, tuple)) else rpid
                    ml_date = ml.get('date')
                    if pk not in fecha_inicio_pallet and ml_date:
                        fecha_inicio_pallet[pk] = ml_date  # Ya viene ordenado asc, el primero es el más antiguo
                
                # Actualizar fecha_elaboracion de cada pallet con la fecha global más antigua
                for pk, fecha_antigua in fecha_inicio_pallet.items():
                    if pk in pallets_dict:
                        current = pallets_dict[pk].get('fecha_elaboracion')
                        if not current or (fecha_antigua and str(fecha_antigua) < str(current)):
                            pallets_dict[pk]['fecha_elaboracion'] = fecha_antigua
                            logger.info(f"Pallet {pk}: fecha corregida a {fecha_antigua} (más antigua global, antes: {current})")
            
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
                
                # Fecha de elaboración y vencimiento (+2 años)
                if fecha_elab:
                    try:
                        if isinstance(fecha_elab, str):
                            fecha_dt = datetime.fromisoformat(fecha_elab.replace('Z', '+00:00'))
                        else:
                            fecha_dt = fecha_elab
                        pallet_info['fecha_elaboracion_fmt'] = fecha_dt.strftime('%d.%m.%Y')
                        # Fecha de vencimiento = fecha elaboración + 2 años
                        try:
                            fecha_venc_dt = fecha_dt.replace(year=fecha_dt.year + 2)
                        except ValueError:
                            # Manejo de 29 de febrero: si la fecha es 29/02, usar 28/02 + 2 años
                            fecha_venc_dt = fecha_dt.replace(month=2, day=28, year=fecha_dt.year + 2)
                        pallet_info['fecha_vencimiento'] = fecha_venc_dt.strftime('%d.%m.%Y')
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
    
    def obtener_info_etiqueta(self, package_id: int, cliente: str = "", fecha_inicio_proceso: str = None, orden_actual: str = None) -> Optional[Dict]:
        """
        Obtiene toda la información necesaria para una etiqueta de pallet.
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
                    fecha_elaboracion_fmt = fecha_dt.strftime('%d.%m.%Y')
                    # Fecha de vencimiento = fecha elaboración + 2 años
                    try:
                        fecha_venc_dt = fecha_dt.replace(year=fecha_dt.year + 2)
                    except ValueError:
                        # Manejo de 29 de febrero
                        fecha_venc_dt = fecha_dt.replace(month=2, day=28, year=fecha_dt.year + 2)
                    fecha_vencimiento_fmt = fecha_venc_dt.strftime('%d.%m.%Y')
                except:
                    fecha_elaboracion_fmt = ''
                    fecha_vencimiento_fmt = ''
            else:
                now = datetime.now()
                fecha_elaboracion_fmt = now.strftime('%d.%m.%Y')
                # Vencimiento = hoy + 2 años
                try:
                    fecha_venc_dt = now.replace(year=now.year + 2)
                except ValueError:
                    fecha_venc_dt = now.replace(month=2, day=28, year=now.year + 2)
                fecha_vencimiento_fmt = fecha_venc_dt.strftime('%d.%m.%Y')
            
            # Nombre del lote
            lote_name = lot_id[1] if isinstance(lot_id, (list, tuple)) and lot_id else ''
            
            # Calcular correlativo inicial de cartón
            carton_no_inicio = self._calcular_carton_no_inicio(package_id, fecha_inicio_proceso, orden_actual)
            
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
                'carton_no_inicio': carton_no_inicio,
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo info de etiqueta para package {package_id}: {e}")
            return None
