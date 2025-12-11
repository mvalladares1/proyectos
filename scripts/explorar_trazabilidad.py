"""
Script para explorar cómo encontrar el proveedor de un lote
"""
import sys
import os
from getpass import getpass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient


def main():
    print("="*80)
    print("🔍 EXPLORAR TRAZABILIDAD DE LOTES")
    print("="*80)
    
    print("\n📝 Ingresa las credenciales de Odoo:")
    username = input("   Usuario (email): ").strip()
    password = getpass("   API Key: ").strip()
    
    try:
        odoo = OdooClient(username=username, password=password)
        print("\n✅ Conectado a Odoo")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return
    
    # Lotes a investigar
    lotes_nombres = ['0000356', '0000386', '0000375', '0000377']
    
    for lot_name in lotes_nombres:
        print(f"\n{'='*80}")
        print(f"📦 LOTE: {lot_name}")
        print("="*80)
        
        # Buscar el lote
        lotes = odoo.search_read(
            'stock.lot',
            [['name', '=', lot_name]],
            ['id', 'name', 'product_id', 'company_id', 'create_date'],
            limit=1
        )
        
        if not lotes:
            print("   ❌ Lote no encontrado")
            continue
        
        lot = lotes[0]
        lot_id = lot['id']
        print(f"   ID: {lot_id}")
        print(f"   Producto: {lot.get('product_id')}")
        print(f"   Fecha creación: {lot.get('create_date')}")
        
        # ===== MÉTODO 1: Buscar a través de stock.move.line =====
        print(f"\n📍 MÉTODO 1: stock.move.line (primer movimiento)")
        
        move_lines = odoo.search_read(
            'stock.move.line',
            [['lot_id', '=', lot_id]],
            ['move_id', 'picking_id', 'date', 'location_id', 'location_dest_id'],
            limit=5,
            order='date asc'
        )
        
        for ml in move_lines[:3]:
            print(f"   - Move: {ml.get('move_id')}")
            print(f"     Picking: {ml.get('picking_id')}")
            print(f"     Fecha: {ml.get('date')}")
            print(f"     Loc origen: {ml.get('location_id')}")
            print(f"     Loc destino: {ml.get('location_dest_id')}")
            
            picking_info = ml.get('picking_id')
            if picking_info:
                pickings = odoo.read('stock.picking', [picking_info[0]], 
                    ['partner_id', 'picking_type_id', 'origin', 'scheduled_date'])
                if pickings:
                    p = pickings[0]
                    print(f"     → Partner: {p.get('partner_id')}")
                    print(f"     → Tipo: {p.get('picking_type_id')}")
                    print(f"     → Origen: {p.get('origin')}")
        
        # ===== MÉTODO 2: Buscar purchase.order.line =====
        print(f"\n📍 MÉTODO 2: purchase.order.line (buscar por lote)")
        
        # Ver si hay un campo que relacione lotes con purchase.order
        try:
            # Buscar en stock.move por purchase_line_id
            moves = odoo.search_read(
                'stock.move',
                [['lot_ids', 'in', [lot_id]]],
                ['purchase_line_id', 'origin', 'picking_id'],
                limit=5
            )
            print(f"   Moves con lot_ids: {len(moves)}")
            for m in moves:
                print(f"   - purchase_line_id: {m.get('purchase_line_id')}")
                print(f"     origin: {m.get('origin')}")
        except Exception as e:
            print(f"   Error buscando moves: {e}")
        
        # ===== MÉTODO 3: Buscar stock.picking con origin que sea PO =====
        print(f"\n📍 MÉTODO 3: Buscar picking con origin = PO")
        
        if move_lines:
            for ml in move_lines[:3]:
                picking_info = ml.get('picking_id')
                if picking_info:
                    pickings = odoo.read('stock.picking', [picking_info[0]], 
                        ['origin', 'partner_id', 'picking_type_id'])
                    if pickings:
                        origin = pickings[0].get('origin', '')
                        print(f"   Picking: {picking_info[1]} | Origin: {origin}")
                        
                        # Si origin parece ser un PO
                        if origin and ('OC' in origin or 'PO' in origin or origin.startswith('S')):
                            # Buscar la purchase.order
                            pos = odoo.search_read(
                                'purchase.order',
                                [['name', '=', origin]],
                                ['partner_id', 'date_order'],
                                limit=1
                            )
                            if pos:
                                print(f"   → PO encontrada: {origin}")
                                print(f"   → Proveedor: {pos[0].get('partner_id')}")
                                print(f"   → Fecha: {pos[0].get('date_order')}")
        
        # ===== MÉTODO 4: Buscar directamente en purchase.order relacionadas al producto =====
        print(f"\n📍 MÉTODO 4: Buscar en stock.move.line con purchase info")
        
        try:
            # Obtener el move_id del primer movimiento
            if move_lines:
                move_id = move_lines[0].get('move_id')
                if move_id:
                    moves = odoo.read('stock.move', [move_id[0]], 
                        ['purchase_line_id', 'origin', 'picking_id', 'picking_type_id'])
                    if moves:
                        m = moves[0]
                        print(f"   purchase_line_id: {m.get('purchase_line_id')}")
                        print(f"   origin: {m.get('origin')}")
                        
                        # Si hay purchase_line_id, obtener el proveedor
                        pl_info = m.get('purchase_line_id')
                        if pl_info:
                            pls = odoo.read('purchase.order.line', [pl_info[0]], ['order_id'])
                            if pls:
                                po_id = pls[0].get('order_id')
                                if po_id:
                                    pos = odoo.read('purchase.order', [po_id[0]], ['partner_id', 'date_order'])
                                    if pos:
                                        print(f"   → Proveedor: {pos[0].get('partner_id')}")
        except Exception as e:
            print(f"   Error: {e}")
    
    print("\n" + "="*80)
    print("🏁 FIN")
    print("="*80)


if __name__ == "__main__":
    main()
