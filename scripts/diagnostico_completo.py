"""
Script de diagnóstico COMPLETO con TRAZABILIDAD DE LOTES CORREGIDA
Busca específicamente el movimiento de RECEPCIÓN (desde Vendors)
"""
import sys
import os
from getpass import getpass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient


# ===== EXCLUSIONES =====
EXCLUDED_CATEGORIES = ["insumo", "envase", "etiqueta", "embalaje", "merma"]
EXCLUDED_PRODUCT_NAMES = [
    "caja", "bolsa", "insumo", "envase", "pallet", "etiqueta",
    "doy pe", "cajas de exportación", "caja exportación"
]
EXCLUDED_PRODUCTION = ["proceso retail", "proceso", "merma"]


def is_excluded_consumo(product_name, category_name=''):
    if not product_name:
        return True
    name_lower = product_name.lower()
    cat_lower = (category_name or '').lower()
    if any(exc in cat_lower for exc in EXCLUDED_CATEGORIES):
        return True
    if any(exc in name_lower for exc in EXCLUDED_PRODUCT_NAMES):
        return True
    return False


def is_excluded_produccion(product_name, category_name=''):
    if not product_name:
        return True
    name_lower = product_name.lower()
    cat_lower = (category_name or '').lower()
    if any(exc in name_lower for exc in EXCLUDED_PRODUCTION):
        return True
    if "merma" in cat_lower:
        return True
    return False


def get_lot_origin(odoo, lot_id):
    """
    Busca el origen de un lote - específicamente la RECEPCIÓN desde proveedor.
    Busca el movimiento donde location_id contiene 'Vendor' o picking_type = Recepciones MP.
    """
    if not lot_id:
        return None
    
    try:
        # Obtener TODOS los movimientos del lote para encontrar la recepción
        move_lines = odoo.search_read(
            'stock.move.line',
            [['lot_id', '=', lot_id]],
            ['move_id', 'picking_id', 'location_id', 'location_dest_id', 'date'],
            limit=20,
            order='date asc'
        )
        
        if not move_lines:
            return {'proveedor': 'Sin movimientos', 'fecha_recepcion': '', 'origin': ''}
        
        # Buscar el movimiento que viene desde 'Vendors' (location_id = 4 o nombre contiene 'Vendor')
        for ml in move_lines:
            loc_id = ml.get('location_id')
            if loc_id:
                loc_name = loc_id[1] if isinstance(loc_id, (list, tuple)) and len(loc_id) > 1 else str(loc_id)
                
                # Si viene de Vendors/Proveedores
                if 'vendor' in loc_name.lower() or 'proveedor' in loc_name.lower():
                    picking_info = ml.get('picking_id')
                    if picking_info:
                        pickings = odoo.read('stock.picking', [picking_info[0]], 
                            ['partner_id', 'origin', 'scheduled_date'])
                        if pickings and pickings[0].get('partner_id'):
                            partner = pickings[0]['partner_id']
                            return {
                                'proveedor': partner[1] if isinstance(partner, (list, tuple)) else str(partner),
                                'fecha_recepcion': str(pickings[0].get('scheduled_date', ''))[:10],
                                'origin': pickings[0].get('origin', '')
                            }
        
        # Si no encontramos movimiento desde Vendors, buscar picking con picking_type_id = 1 (Recepciones MP)
        for ml in move_lines:
            picking_info = ml.get('picking_id')
            if picking_info:
                pickings = odoo.read('stock.picking', [picking_info[0]], 
                    ['partner_id', 'origin', 'scheduled_date', 'picking_type_id'])
                if pickings:
                    p = pickings[0]
                    picking_type = p.get('picking_type_id')
                    # Si es Recepciones MP (ID=1) o el nombre contiene 'Recepcion'
                    if picking_type:
                        type_id = picking_type[0] if isinstance(picking_type, (list, tuple)) else picking_type
                        type_name = picking_type[1] if isinstance(picking_type, (list, tuple)) and len(picking_type) > 1 else ''
                        
                        if type_id == 1 or 'recep' in type_name.lower():
                            partner = p.get('partner_id')
                            if partner:
                                return {
                                    'proveedor': partner[1] if isinstance(partner, (list, tuple)) else str(partner),
                                    'fecha_recepcion': str(p.get('scheduled_date', ''))[:10],
                                    'origin': p.get('origin', '')
                                }
        
        # Si aún no encontramos, podría ser un lote producido internamente
        return {'proveedor': 'Producido internamente', 'fecha_recepcion': '', 'origin': ''}
        
    except Exception as e:
        return {'proveedor': f'Error: {str(e)[:30]}', 'fecha_recepcion': '', 'origin': ''}


def main():
    print("="*120)
    print("🔍 DIAGNÓSTICO COMPLETO CON TRAZABILIDAD CORREGIDA")
    print("="*120)
    
    print("\n📝 Ingresa las credenciales de Odoo:")
    username = input("   Usuario (email): ").strip()
    password = getpass("   API Key: ").strip()
    
    try:
        odoo = OdooClient(username=username, password=password)
        print("\n✅ Conectado a Odoo")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return
    
    fecha = input("\n📅 Fecha a consultar (YYYY-MM-DD): ").strip() or "2025-12-01"
    
    # ===== BUSCAR MOs =====
    print(f"\n{'='*120}")
    print(f"BUSCAR MOs del {fecha}")
    print("="*120)
    
    domain = [
        ['state', 'in', ['done', 'to_close']],
        ['date_planned_start', '>=', fecha],
        ['date_planned_start', '<=', fecha + ' 23:59:59']
    ]
    
    mos = odoo.search_read(
        'mrp.production',
        domain,
        ['name', 'product_id', 'product_qty', 'qty_produced', 'state',
         'date_planned_start', 'move_raw_ids', 'move_finished_ids',
         'x_studio_dotacin', 'x_studio_hh', 'x_studio_hh_efectiva'],
        limit=20
    )
    
    print(f"\n📊 MOs encontradas: {len(mos)}")
    
    # Resumen total
    total_mp_global = 0
    total_pt_global = 0
    
    for mo in mos:
        print(f"\n{'='*120}")
        print(f"📦 MO: {mo['name']} | State: {mo['state']}")
        print(f"   Producto: {mo.get('product_id', ['', 'N/A'])[1] if mo.get('product_id') else 'N/A'}")
        print(f"   Fecha: {mo.get('date_planned_start')} | Dotación: {mo.get('x_studio_dotacin', 'N/A')} | HH: {mo.get('x_studio_hh', 'N/A')}")
        print("="*120)
        
        move_raw_ids = mo.get('move_raw_ids', [])
        move_finished_ids = mo.get('move_finished_ids', [])
        
        # ===== CONSUMOS con TRAZABILIDAD =====
        print(f"\n📥 CONSUMOS (MP)")
        print("-"*120)
        
        lotes_unicos = {}
        total_mp_filtrado = 0
        
        if move_raw_ids:
            consumos_raw = odoo.search_read(
                'stock.move.line',
                [['move_id', 'in', move_raw_ids]],
                ['product_id', 'lot_id', 'qty_done', 'product_category_name'],
                limit=100
            )
            
            for c in consumos_raw:
                prod_info = c.get('product_id')
                prod_name = prod_info[1] if prod_info else 'N/A'
                lot_info = c.get('lot_id')
                lot_id = lot_info[0] if lot_info else None
                lot_name = lot_info[1] if lot_info else 'SIN LOTE'
                qty = c.get('qty_done', 0) or 0
                category = c.get('product_category_name', '') or ''
                
                excluido = is_excluded_consumo(prod_name, category)
                
                if not excluido and qty > 0:
                    total_mp_filtrado += qty
                    
                    if lot_id not in lotes_unicos:
                        lotes_unicos[lot_id] = {
                            'lot_name': lot_name,
                            'product_name': prod_name,
                            'qty': 0,
                            'lot_id': lot_id
                        }
                    lotes_unicos[lot_id]['qty'] += qty
            
            print(f"{'Lote':<12} {'Producto':<45} {'Kg':>10}  {'Proveedor':<35} {'OC':<12} {'Fecha'}")
            print("-"*130)
            
            for lot_id, data in lotes_unicos.items():
                origin = get_lot_origin(odoo, lot_id) if lot_id else None
                proveedor = origin.get('proveedor', 'N/A')[:33] if origin else 'N/A'
                oc = origin.get('origin', '')[:10] if origin else ''
                fecha_rec = origin.get('fecha_recepcion', '') if origin else ''
                
                print(f"{data['lot_name'][:10]:<12} {data['product_name'][:43]:<45} {data['qty']:>10.2f}  {proveedor:<35} {oc:<12} {fecha_rec}")
            
            print("-"*130)
            print(f"{'TOTAL MP:':<70} {total_mp_filtrado:>10.2f} Kg")
        
        total_mp_global += total_mp_filtrado
        
        # ===== PRODUCCIÓN =====
        print(f"\n📤 PRODUCCIÓN (PT)")
        print("-"*120)
        
        total_pt_filtrado = 0
        productos_pt = {}
        
        if move_finished_ids:
            produccion_raw = odoo.search_read(
                'stock.move.line',
                [['move_id', 'in', move_finished_ids]],
                ['product_id', 'lot_id', 'qty_done', 'product_category_name'],
                limit=100
            )
            
            for p in produccion_raw:
                prod_info = p.get('product_id')
                prod_name = prod_info[1] if prod_info else 'N/A'
                prod_id = prod_info[0] if prod_info else 0
                lot_info = p.get('lot_id')
                lot_name = lot_info[1] if lot_info else 'SIN LOTE'
                qty = p.get('qty_done', 0) or 0
                category = p.get('product_category_name', '') or ''
                
                excluido = is_excluded_produccion(prod_name, category)
                
                if not excluido and qty > 0:
                    total_pt_filtrado += qty
                    
                    key = (prod_id, lot_info[0] if lot_info else None)
                    if key not in productos_pt:
                        productos_pt[key] = {
                            'product_name': prod_name,
                            'lot_name': lot_name,
                            'qty': 0
                        }
                    productos_pt[key]['qty'] += qty
            
            print(f"{'Lote':<15} {'Producto':<75} {'Kg':>12}")
            print("-"*105)
            
            for key, data in productos_pt.items():
                print(f"{data['lot_name'][:13]:<15} {data['product_name'][:73]:<75} {data['qty']:>10.2f}")
            
            print("-"*105)
            print(f"{'TOTAL PT:':<93} {total_pt_filtrado:>10.2f} Kg")
        
        total_pt_global += total_pt_filtrado
        
        # ===== RESUMEN MO =====
        print(f"\n📊 RESUMEN MO")
        print("-"*50)
        
        if total_mp_filtrado > 0:
            rendimiento = (total_pt_filtrado / total_mp_filtrado) * 100
            merma = total_mp_filtrado - total_pt_filtrado
            merma_pct = (merma / total_mp_filtrado) * 100
        else:
            rendimiento = 0
            merma = 0
            merma_pct = 0
        
        print(f"   MP Consumido:     {total_mp_filtrado:>12.2f} Kg")
        print(f"   PT Producido:     {total_pt_filtrado:>12.2f} Kg")
        print(f"   Rendimiento:      {rendimiento:>12.2f} %")
        print(f"   Merma:            {merma:>12.2f} Kg ({merma_pct:.1f}%)")
    
    # ===== RESUMEN GLOBAL =====
    print(f"\n{'='*120}")
    print("📈 RESUMEN GLOBAL DEL PERÍODO")
    print("="*120)
    
    if total_mp_global > 0:
        rend_global = (total_pt_global / total_mp_global) * 100
        merma_global = total_mp_global - total_pt_global
    else:
        rend_global = 0
        merma_global = 0
    
    print(f"   Total MP:         {total_mp_global:>12.2f} Kg")
    print(f"   Total PT:         {total_pt_global:>12.2f} Kg")
    print(f"   Rendimiento:      {rend_global:>12.2f} %")
    print(f"   Merma Total:      {merma_global:>12.2f} Kg")
    print(f"   MOs procesadas:   {len(mos)}")
    
    print("\n" + "="*120)
    print("🏁 FIN DE DIAGNÓSTICO")
    print("="*120)


if __name__ == "__main__":
    main()
