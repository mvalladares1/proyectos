"""
Servicio de Trazabilidad de Pallets
Traza un pallet hacia atrás a través de órdenes de fabricación hasta llegar
a materia prima (MP/fresco) y sus recepciones correspondientes.

Lógica:
1. El PACK a trazar es un paquete de destino (result_package_id) en una orden
2. En esa orden hay paquetes de origen (package_id) que coinciden en fruta/manejo/variedad
3. Esos pallets de origen se buscan como destino en otras órdenes, y así sucesivamente
4. Hasta llegar a pallets con categoría MP (Materia Prima / Fresco / Túnel)
5. Esos pallets MP se buscan en recepciones para obtener guía de despacho y proveedor
"""
import logging
from typing import Dict, List, Optional, Any
from shared.odoo_client import OdooClient
from backend.utils import clean_record

logger = logging.getLogger(__name__)


class TrazabilidadPalletService:
    """
    Servicio para trazar pallets hacia atrás a través de la cadena productiva.
    """

    MAX_DEPTH = 15  # Límite de profundidad para evitar loops infinitos

    def __init__(self, username: str, password: str):
        self.odoo = OdooClient(username=username, password=password)
        self._visited_packages = set()  # Para evitar ciclos

    # ------------------------------------------------------------------
    # MÉTODO PRINCIPAL
    # ------------------------------------------------------------------
    def trazar_pallet(self, pallet_name: str) -> Dict[str, Any]:
        """
        Traza un pallet hacia atrás hasta materia prima.

        Args:
            pallet_name: Nombre del pallet (ej: PACK0012345)

        Returns:
            {
                "pallet_origen": str,
                "arbol": [nodos...],        # lista plana con info de cada nivel
                "materia_prima": [           # pallets MP encontrados al final
                    {
                        "pallet": str,
                        "producto": str,
                        "lote": str,
                        "recepcion": str,
                        "guia_despacho": str,
                        "proveedor": str,
                        "fecha_recepcion": str,
                        "kg": float,
                    }
                ],
                "niveles": int,
                "error": str | None
            }
        """
        self._visited_packages = set()

        # 1. Buscar el package por nombre
        packages = self.odoo.search_read(
            'stock.quant.package',
            [('name', '=', pallet_name)],
            ['id', 'name'],
            limit=1
        )
        if not packages:
            return {
                "pallet_origen": pallet_name,
                "arbol": [],
                "materia_prima": [],
                "niveles": 0,
                "error": f"No se encontró el pallet '{pallet_name}'"
            }

        package = packages[0]
        package_id = package['id']
        package_display = package.get('name', pallet_name)

        # 2. Recorrer hacia atrás
        arbol = []
        hojas_mp = []
        self._trazar_recursivo(
            package_id=package_id,
            package_name=package_display,
            depth=0,
            arbol=arbol,
            hojas_mp=hojas_mp
        )

        # 3. Para las hojas MP, buscar recepciones
        materia_prima = self._buscar_recepciones_mp(hojas_mp)

        return {
            "pallet_origen": package_display,
            "arbol": arbol,
            "materia_prima": materia_prima,
            "niveles": max((n['nivel'] for n in arbol), default=0),
            "error": None
        }

    # ------------------------------------------------------------------
    # RECURSIÓN
    # ------------------------------------------------------------------
    def _trazar_recursivo(
        self,
        package_id: int,
        package_name: str,
        depth: int,
        arbol: List[Dict],
        hojas_mp: List[Dict]
    ):
        """Recorre hacia atrás por las órdenes de fabricación."""
        if depth > self.MAX_DEPTH:
            return
        if package_id in self._visited_packages:
            return
        self._visited_packages.add(package_id)

        # Buscar move lines donde este pallet es resultado (destino)
        move_lines_dest = self.odoo.search_read(
            'stock.move.line',
            [
                ('result_package_id', '=', package_id),
                ('qty_done', '>', 0),
                ('state', '=', 'done')
            ],
            ['move_id', 'product_id', 'lot_id', 'qty_done', 'date', 'package_id',
             'result_package_id', 'picking_id'],
            limit=200
        )

        if not move_lines_dest:
            # No tiene movimientos como destino → podría ser MP o pallet sin historia
            # Verificar si tiene quants para obtener producto
            info = self._get_package_info(package_id, package_name)
            info['nivel'] = depth
            info['es_mp'] = True
            arbol.append(info)
            hojas_mp.append(info)
            return

        # Obtener info del producto de este pallet
        first_line = move_lines_dest[0]
        prod_info = first_line.get('product_id', [False, ''])
        prod_name = prod_info[1] if isinstance(prod_info, (list, tuple)) and len(prod_info) > 1 else ''
        lot_info = first_line.get('lot_id', [False, ''])
        lot_name = lot_info[1] if isinstance(lot_info, (list, tuple)) and len(lot_info) > 1 else ''
        total_kg = sum(ml.get('qty_done', 0) for ml in move_lines_dest)

        # Determinar si es un movimiento de producción o de picking
        move_ids = list(set(
            ml['move_id'][0] if isinstance(ml.get('move_id'), (list, tuple)) else ml.get('move_id')
            for ml in move_lines_dest if ml.get('move_id')
        ))

        # Buscar los stock.move para saber si vienen de producción
        orden_info = self._get_orden_from_moves(move_ids)

        # Determinar si es categoría MP (fresco)
        es_mp = self._es_materia_prima(prod_info, package_name)

        nodo = {
            'nivel': depth,
            'pallet': package_name,
            'package_id': package_id,
            'producto': prod_name,
            'lote': lot_name,
            'kg': round(total_kg, 2),
            'orden': orden_info.get('orden_name', ''),
            'orden_id': orden_info.get('orden_id', 0),
            'tipo_orden': orden_info.get('tipo', ''),  # 'produccion' o 'picking'
            'fecha': str(first_line.get('date', '')),
            'es_mp': es_mp,
        }
        arbol.append(nodo)

        if es_mp:
            hojas_mp.append(nodo)
            return

        # Si viene de una orden de producción, buscar los paquetes de ORIGEN (consumo)
        if orden_info.get('tipo') == 'produccion' and orden_info.get('orden_id'):
            self._buscar_origenes_produccion(
                orden_id=orden_info['orden_id'],
                depth=depth,
                arbol=arbol,
                hojas_mp=hojas_mp
            )
        elif orden_info.get('tipo') == 'picking':
            # Si es un picking, buscar los paquetes de origen en el mismo picking
            self._buscar_origenes_picking(
                move_lines_dest=move_lines_dest,
                depth=depth,
                arbol=arbol,
                hojas_mp=hojas_mp
            )
        else:
            # Intentar buscar pallets de origen directamente desde los move lines
            self._buscar_origenes_directos(
                move_lines_dest=move_lines_dest,
                depth=depth,
                arbol=arbol,
                hojas_mp=hojas_mp
            )

    # ------------------------------------------------------------------
    # BUSCAR ORÍGENES EN PRODUCCIÓN
    # ------------------------------------------------------------------
    def _buscar_origenes_produccion(
        self, orden_id: int, depth: int,
        arbol: List[Dict], hojas_mp: List[Dict]
    ):
        """
        Busca los pallets de origen (materia prima consumida) en una orden de fabricación.
        Estos son los paquetes de origen (package_id) en los move lines de consumo (raw).
        """
        # Buscar moves de consumo (raw_material_production_id)
        raw_moves = self.odoo.search_read(
            'stock.move',
            [('raw_material_production_id', '=', orden_id)],
            ['id'],
            limit=500
        )
        raw_move_ids = [m['id'] for m in raw_moves]

        if not raw_move_ids:
            return

        # Buscar move lines de consumo con package_id (paquete de origen)
        consume_lines = self.odoo.search_read(
            'stock.move.line',
            [
                ('move_id', 'in', raw_move_ids),
                ('package_id', '!=', False),
                ('qty_done', '>', 0),
                ('state', '=', 'done')
            ],
            ['package_id', 'product_id', 'lot_id', 'qty_done'],
            limit=500
        )

        # Obtener paquetes de origen únicos
        origenes = {}
        for cl in consume_lines:
            pkg = cl.get('package_id')
            if not pkg:
                continue
            pkg_id = pkg[0] if isinstance(pkg, (list, tuple)) else pkg
            pkg_name = pkg[1] if isinstance(pkg, (list, tuple)) and len(pkg) > 1 else ''
            if pkg_id not in origenes:
                origenes[pkg_id] = pkg_name

        # Trazar cada paquete de origen recursivamente
        for pkg_id, pkg_name in origenes.items():
            self._trazar_recursivo(
                package_id=pkg_id,
                package_name=pkg_name,
                depth=depth + 1,
                arbol=arbol,
                hojas_mp=hojas_mp
            )

    # ------------------------------------------------------------------
    # BUSCAR ORÍGENES EN PICKING
    # ------------------------------------------------------------------
    def _buscar_origenes_picking(
        self, move_lines_dest: List[Dict], depth: int,
        arbol: List[Dict], hojas_mp: List[Dict]
    ):
        """Busca pallets de origen en un picking (package_id de los move lines)."""
        origenes = {}
        for ml in move_lines_dest:
            pkg = ml.get('package_id')
            if not pkg:
                continue
            pkg_id = pkg[0] if isinstance(pkg, (list, tuple)) else pkg
            pkg_name = pkg[1] if isinstance(pkg, (list, tuple)) and len(pkg) > 1 else ''
            if pkg_id not in origenes:
                origenes[pkg_id] = pkg_name

        for pkg_id, pkg_name in origenes.items():
            self._trazar_recursivo(
                package_id=pkg_id,
                package_name=pkg_name,
                depth=depth + 1,
                arbol=arbol,
                hojas_mp=hojas_mp
            )

    # ------------------------------------------------------------------
    # BUSCAR ORÍGENES DIRECTOS
    # ------------------------------------------------------------------
    def _buscar_origenes_directos(
        self, move_lines_dest: List[Dict], depth: int,
        arbol: List[Dict], hojas_mp: List[Dict]
    ):
        """Busca pallets de origen directamente en los move lines."""
        origenes = {}
        for ml in move_lines_dest:
            pkg = ml.get('package_id')
            if not pkg:
                continue
            pkg_id = pkg[0] if isinstance(pkg, (list, tuple)) else pkg
            pkg_name = pkg[1] if isinstance(pkg, (list, tuple)) and len(pkg) > 1 else ''
            if pkg_id not in origenes and pkg_id not in self._visited_packages:
                origenes[pkg_id] = pkg_name

        for pkg_id, pkg_name in origenes.items():
            self._trazar_recursivo(
                package_id=pkg_id,
                package_name=pkg_name,
                depth=depth + 1,
                arbol=arbol,
                hojas_mp=hojas_mp
            )

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------
    def _get_orden_from_moves(self, move_ids: List[int]) -> Dict:
        """Obtiene la orden de fabricación o picking asociado a los moves."""
        if not move_ids:
            return {'orden_name': '', 'orden_id': 0, 'tipo': ''}

        moves = self.odoo.search_read(
            'stock.move',
            [('id', 'in', move_ids)],
            ['production_id', 'raw_material_production_id', 'picking_id', 'origin'],
            limit=50
        )

        # Priorizar producción
        for m in moves:
            prod = m.get('production_id')
            if prod and isinstance(prod, (list, tuple)) and prod[0]:
                return {
                    'orden_name': prod[1] if len(prod) > 1 else '',
                    'orden_id': prod[0],
                    'tipo': 'produccion'
                }

        # También verificar raw_material_production_id
        for m in moves:
            raw_prod = m.get('raw_material_production_id')
            if raw_prod and isinstance(raw_prod, (list, tuple)) and raw_prod[0]:
                return {
                    'orden_name': raw_prod[1] if len(raw_prod) > 1 else '',
                    'orden_id': raw_prod[0],
                    'tipo': 'produccion'
                }

        # Fallback a picking
        for m in moves:
            picking = m.get('picking_id')
            if picking and isinstance(picking, (list, tuple)) and picking[0]:
                return {
                    'orden_name': picking[1] if len(picking) > 1 else '',
                    'orden_id': picking[0],
                    'tipo': 'picking'
                }

        return {'orden_name': '', 'orden_id': 0, 'tipo': ''}

    def _es_materia_prima(self, product_info, package_name: str = '') -> bool:
        """
        Determina si un producto es materia prima (fresco / MP).
        Se basa en:
        - Categoría del producto contiene 'MP' o 'Materia Prima'
        - Código de producto empieza con '1' o '2' (prefijos MP)
        - El producto tiene 'fresco' en el nombre
        """
        prod_id = None
        prod_name = ''
        if isinstance(product_info, (list, tuple)):
            prod_id = product_info[0] if len(product_info) > 0 else None
            prod_name = product_info[1] if len(product_info) > 1 else ''
        elif isinstance(product_info, dict):
            prod_id = product_info.get('id')
            prod_name = product_info.get('name', '')

        # Verificar por nombre
        name_lower = (prod_name or '').lower()
        if 'fresco' in name_lower or 'materia prima' in name_lower:
            return True

        # Verificar código de producto (prefijos 1x o 2x son MP)
        if prod_id:
            try:
                products = self.odoo.search_read(
                    'product.product',
                    [('id', '=', prod_id)],
                    ['default_code', 'categ_id'],
                    limit=1
                )
                if products:
                    code = (products[0].get('default_code') or '').strip()
                    if code and len(code) >= 2 and code[0] in ('1', '2'):
                        return True

                    categ = products[0].get('categ_id')
                    if categ and isinstance(categ, (list, tuple)) and len(categ) > 1:
                        categ_name = (categ[1] or '').upper()
                        if 'MP' in categ_name or 'MATERIA PRIMA' in categ_name or 'FRESCO' in categ_name:
                            return True
            except Exception as e:
                logger.warning(f"Error verificando categoría de producto {prod_id}: {e}")

        return False

    def _get_package_info(self, package_id: int, package_name: str) -> Dict:
        """Obtiene información básica de un pallet desde sus quants."""
        try:
            quants = self.odoo.search_read(
                'stock.quant',
                [('package_id', '=', package_id)],
                ['product_id', 'lot_id', 'quantity'],
                limit=10
            )
            if quants:
                q = quants[0]
                prod = q.get('product_id', [False, ''])
                lot = q.get('lot_id', [False, ''])
                total_qty = sum(qnt.get('quantity', 0) for qnt in quants)
                return {
                    'pallet': package_name,
                    'package_id': package_id,
                    'producto': prod[1] if isinstance(prod, (list, tuple)) and len(prod) > 1 else '',
                    'lote': lot[1] if isinstance(lot, (list, tuple)) and len(lot) > 1 else '',
                    'kg': round(total_qty, 2),
                    'orden': '',
                    'orden_id': 0,
                    'tipo_orden': '',
                    'fecha': '',
                    'es_mp': True,
                }
        except Exception as e:
            logger.warning(f"Error obteniendo info de package {package_id}: {e}")

        return {
            'pallet': package_name,
            'package_id': package_id,
            'producto': '',
            'lote': '',
            'kg': 0,
            'orden': '',
            'orden_id': 0,
            'tipo_orden': '',
            'fecha': '',
            'es_mp': True,
        }

    # ------------------------------------------------------------------
    # BUSCAR RECEPCIONES PARA PALLETS MP
    # ------------------------------------------------------------------
    def _buscar_recepciones_mp(self, hojas_mp: List[Dict]) -> List[Dict]:
        """
        Para cada pallet de materia prima, busca la recepción donde fue ingresado.
        Obtiene guía de despacho (x_studio_gua_de_despacho) y proveedor (partner_id).
        """
        resultado = []
        for hoja in hojas_mp:
            pkg_id = hoja.get('package_id')
            pkg_name = hoja.get('pallet', '')
            if not pkg_id:
                resultado.append({
                    'pallet': pkg_name,
                    'producto': hoja.get('producto', ''),
                    'lote': hoja.get('lote', ''),
                    'kg': hoja.get('kg', 0),
                    'recepcion': '',
                    'guia_despacho': '',
                    'proveedor': '',
                    'fecha_recepcion': '',
                })
                continue

            recep_info = self._buscar_recepcion_de_pallet(pkg_id)
            resultado.append({
                'pallet': pkg_name,
                'producto': hoja.get('producto', ''),
                'lote': hoja.get('lote', ''),
                'kg': hoja.get('kg', 0),
                'recepcion': recep_info.get('recepcion', ''),
                'guia_despacho': recep_info.get('guia_despacho', ''),
                'proveedor': recep_info.get('proveedor', ''),
                'fecha_recepcion': recep_info.get('fecha_recepcion', ''),
            })

        return resultado

    def _buscar_recepcion_de_pallet(self, package_id: int) -> Dict:
        """
        Busca la recepción (stock.picking de tipo recepción) donde apareció este pallet.
        """
        try:
            # Buscar move lines donde este pallet aparece como result_package_id
            # en recepciones (picking_type con code='incoming')
            move_lines = self.odoo.search_read(
                'stock.move.line',
                [
                    ('result_package_id', '=', package_id),
                    ('state', '=', 'done'),
                    ('picking_id', '!=', False)
                ],
                ['picking_id', 'qty_done', 'date'],
                limit=50
            )

            if not move_lines:
                # Intentar con package_id (origen)
                move_lines = self.odoo.search_read(
                    'stock.move.line',
                    [
                        ('package_id', '=', package_id),
                        ('state', '=', 'done'),
                        ('picking_id', '!=', False)
                    ],
                    ['picking_id', 'qty_done', 'date'],
                    limit=50
                )

            if not move_lines:
                return {}

            # Obtener pickings y filtrar los de tipo recepción
            picking_ids = list(set(
                ml['picking_id'][0] if isinstance(ml.get('picking_id'), (list, tuple)) else ml.get('picking_id')
                for ml in move_lines if ml.get('picking_id')
            ))

            if not picking_ids:
                return {}

            pickings = self.odoo.search_read(
                'stock.picking',
                [('id', 'in', picking_ids)],
                ['name', 'partner_id', 'x_studio_gua_de_despacho', 'date_done',
                 'scheduled_date', 'picking_type_id', 'x_studio_categora_de_producto'],
                limit=50
            )

            # Priorizar recepciones (picking_type_id en [1, 217, 164] o categoría MP)
            RECEPCION_TYPES = [1, 217, 164]
            recepcion = None

            for p in pickings:
                pt = p.get('picking_type_id')
                pt_id = pt[0] if isinstance(pt, (list, tuple)) else pt
                cat = p.get('x_studio_categora_de_producto', '')
                if pt_id in RECEPCION_TYPES or cat == 'MP':
                    recepcion = p
                    break

            # Si no encontramos recepción específica, usar el primer picking
            if not recepcion and pickings:
                recepcion = pickings[0]

            if not recepcion:
                return {}

            partner = recepcion.get('partner_id')
            partner_name = ''
            if partner and isinstance(partner, (list, tuple)) and len(partner) > 1:
                partner_name = partner[1]

            guia = recepcion.get('x_studio_gua_de_despacho', '') or ''
            fecha = recepcion.get('date_done') or recepcion.get('scheduled_date') or ''

            return {
                'recepcion': recepcion.get('name', ''),
                'guia_despacho': str(guia),
                'proveedor': partner_name,
                'fecha_recepcion': str(fecha),
            }

        except Exception as e:
            logger.error(f"Error buscando recepción para pallet {package_id}: {e}")
            return {}
