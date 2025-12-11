"""
Script de diagnóstico - ¿Por qué no salen las MOs del 01/12/2025?
"""
import sys
import os
from getpass import getpass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient


def main():
    print("="*80)
    print("🔍 DIAGNÓSTICO - MOs del 01/12/2025")
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
    
    fecha = "2025-12-01"
    
    # ===== TEST 1: Buscar por date_planned_start =====
    print(f"\n{'='*80}")
    print("TEST 1: Buscar MOs por date_planned_start")
    print("="*80)
    
    domain1 = [
        ['state', '=', 'done'],
        ['date_planned_start', '>=', fecha],
        ['date_planned_start', '<=', fecha + ' 23:59:59']
    ]
    print(f"Domain: {domain1}")
    
    mos1 = odoo.search_read(
        'mrp.production',
        domain1,
        ['name', 'state', 'date_planned_start', 'date_finished', 'product_id'],
        limit=20
    )
    print(f"Resultados: {len(mos1)}")
    for mo in mos1:
        print(f"  - {mo['name']} | state={mo['state']} | planned={mo.get('date_planned_start')} | finished={mo.get('date_finished')}")
    
    # ===== TEST 2: Buscar SIN filtro de state (ver todas) =====
    print(f"\n{'='*80}")
    print("TEST 2: Buscar TODAS las MOs del día (sin filtro state)")
    print("="*80)
    
    domain2 = [
        ['date_planned_start', '>=', fecha],
        ['date_planned_start', '<=', fecha + ' 23:59:59']
    ]
    print(f"Domain: {domain2}")
    
    mos2 = odoo.search_read(
        'mrp.production',
        domain2,
        ['name', 'state', 'date_planned_start', 'date_finished', 'product_id'],
        limit=20
    )
    print(f"Resultados: {len(mos2)}")
    for mo in mos2:
        print(f"  - {mo['name']} | state={mo['state']} | planned={mo.get('date_planned_start')}")
    
    # ===== TEST 3: Buscar por nombre específico =====
    print(f"\n{'='*80}")
    print("TEST 3: Buscar MO específica WH/Transf/00668")
    print("="*80)
    
    mos3 = odoo.search_read(
        'mrp.production',
        [['name', '=', 'WH/Transf/00668']],
        ['name', 'state', 'date_planned_start', 'date_finished', 'move_raw_ids', 'move_finished_ids'],
        limit=1
    )
    print(f"Resultados: {len(mos3)}")
    for mo in mos3:
        print(f"  - {mo['name']}")
        print(f"    state: {mo['state']}")
        print(f"    date_planned_start: {mo.get('date_planned_start')}")
        print(f"    date_finished: {mo.get('date_finished')}")
        print(f"    move_raw_ids: {mo.get('move_raw_ids', [])[:5]}...")
        print(f"    move_finished_ids: {mo.get('move_finished_ids', [])[:5]}...")
    
    # ===== TEST 4: Buscar por date_finished =====
    print(f"\n{'='*80}")
    print("TEST 4: Buscar por date_finished (en caso que la fecha esté ahí)")
    print("="*80)
    
    domain4 = [
        ['state', '=', 'done'],
        ['date_finished', '>=', fecha],
        ['date_finished', '<=', fecha + ' 23:59:59']
    ]
    print(f"Domain: {domain4}")
    
    mos4 = odoo.search_read(
        'mrp.production',
        domain4,
        ['name', 'state', 'date_planned_start', 'date_finished'],
        limit=20
    )
    print(f"Resultados: {len(mos4)}")
    for mo in mos4:
        print(f"  - {mo['name']} | planned={mo.get('date_planned_start')} | finished={mo.get('date_finished')}")
    
    # ===== TEST 5: Buscar por date_start =====
    print(f"\n{'='*80}")
    print("TEST 5: Buscar por date_start")
    print("="*80)
    
    domain5 = [
        ['state', '=', 'done'],
        ['date_start', '>=', fecha],
        ['date_start', '<=', fecha + ' 23:59:59']
    ]
    print(f"Domain: {domain5}")
    
    mos5 = odoo.search_read(
        'mrp.production',
        domain5,
        ['name', 'state', 'date_start', 'date_planned_start', 'date_finished'],
        limit=20
    )
    print(f"Resultados: {len(mos5)}")
    for mo in mos5:
        print(f"  - {mo['name']} | start={mo.get('date_start')} | planned={mo.get('date_planned_start')}")
    
    print("\n" + "="*80)
    print("🏁 FIN DE DIAGNÓSTICO")
    print("="*80)


if __name__ == "__main__":
    main()
