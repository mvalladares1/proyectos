"""
Script para depurar asientos borrador (Draft) de leasing en Enero 2026
"""
import sys
import os
from datetime import datetime

# Agregar path para importar OdooClient
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

def main():
    print("\n" + "=" * 80)
    print("  DEBUG LEASING DRAFT ENERO 2026")
    print("=" * 80)
    
    # Credenciales (hardcodeadas para test rápido, mismas que debug_flujo_caja_forense.py)
    username = "mvalladares@riofuturo.cl"
    password = "c0766224bec30cac071ffe43a858c9ccbd521ddd"
    
    try:
        odoo = OdooClient(username=username, password=password)
        print("✅ Conectado a Odoo\n")
        
        # 1. Buscar líneas en la cuenta de leasing para Enero 2026 (Draft y Posted)
        cuenta_leasing = '82010102'
        fecha_inicio = '2026-01-01'
        fecha_fin = '2026-01-31'
        
        print(f"🔎 Buscando líneas en cuenta {cuenta_leasing} entre {fecha_inicio} y {fecha_fin} (Draft incluido)...")
        
        domain = [
            ('account_id.code', '=', cuenta_leasing),
            ('date', '>=', fecha_inicio),
            ('date', '<=', fecha_fin),
            ('parent_state', 'in', ['posted', 'draft'])
        ]
        
        lineas = odoo.search_read('account.move.line', domain, 
            ['date', 'name', 'debit', 'credit', 'move_id', 'parent_state', 'move_type'],
            limit=20
        )
        
        print(f"👉 Se encontraron {len(lineas)} líneas:\n")
        
        moves_analizados = set()
        
        for l in lineas:
            move_id = l['move_id'][0]
            move_name = l['move_id'][1]
            estado = l['parent_state']
            tipo = l.get('move_type', 'N/A') # move_type suele estar en move, no line, pero a veces Odoo lo pasa
            
            print(f"📅 {l['date']} | {estado.upper()} | {l['name'][:40]:40} | D:{l['debit']:,.0f} | Move: {move_name}")
            moves_analizados.add(move_id)

        print("\n" + "-"*80)
        print("🔎 ANALIZANDO LOS ASIENTOS PADRE (MOVES)")
        
        if moves_analizados:
            moves = odoo.read('account.move', list(moves_analizados), ['name', 'state', 'move_type', 'date', 'invoice_date_due'])
            
            for m in moves:
                print(f"🧾 ID: {m['id']} | Ref: {m['name']} | Tipo: {m['move_type']} | Estado: {m['state']} | Fecha: {m['date']}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
