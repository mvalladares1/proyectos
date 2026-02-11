#!/usr/bin/env python3
"""
Script para buscar IDs de cuentas analíticas en Odoo
Específicamente para el campo analytic_distribution en purchase.order.line
"""
import xmlrpc.client

URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'

# Credenciales
username = input("Usuario (email): ").strip()
password = input("Password: ").strip()

print(f"\n🔌 Conectando a {URL}...")

try:
    # Autenticar
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, username, password, {})
    
    if not uid:
        print("❌ Error: Credenciales inválidas")
        exit(1)
    
    print(f"✅ Conectado como User ID: {uid}\n")
    
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    
    # Buscar en account.analytic.account (cuentas analíticas principales)
    print("🔍 Buscando en account.analytic.account...")
    cuentas_analiticas = models.execute_kw(
        DB, uid, password,
        'account.analytic.account', 'search_read',
        [[('name', 'ilike', 'Abastecimiento')]],
        {'fields': ['id', 'name', 'code', 'plan_id', 'active']}
    )
    
    if cuentas_analiticas:
        print(f"\n📊 Encontradas {len(cuentas_analiticas)} cuenta(s) analítica(s):")
        for cuenta in cuentas_analiticas:
            print(f"  - ID: {cuenta['id']}")
            print(f"    Nombre: {cuenta['name']}")
            print(f"    Código: {cuenta.get('code', 'N/A')}")
            print(f"    Plan: {cuenta.get('plan_id', 'N/A')}")
            print(f"    Activa: {cuenta.get('active', True)}")
            print()
    else:
        print("  ⚠️ No se encontraron cuentas analíticas con 'Abastecimiento'\n")
    
    # Buscar en account.analytic.plan (planes analíticos)
    print("🔍 Buscando en account.analytic.plan...")
    planes = models.execute_kw(
        DB, uid, password,
        'account.analytic.plan', 'search_read',
        [[]],
        {'fields': ['id', 'name', 'parent_id'], 'limit': 50}
    )
    
    if planes:
        print(f"\n📋 Planes analíticos disponibles ({len(planes)}):")
        for plan in planes:
            print(f"  - ID: {plan['id']} | {plan['name']} | Parent: {plan.get('parent_id', 'None')}")
    
    # Buscar en account.analytic.tag (etiquetas analíticas)
    print("\n🔍 Buscando en account.analytic.tag...")
    try:
        tags = models.execute_kw(
            DB, uid, password,
            'account.analytic.tag', 'search_read',
            [[('name', 'ilike', 'Abastecimiento')]],
            {'fields': ['id', 'name', 'color', 'active_analytic_distribution']}
        )
        
        if tags:
            print(f"\n🏷️ Encontradas {len(tags)} etiqueta(s) analítica(s):")
            for tag in tags:
                print(f"  - ID: {tag['id']}")
                print(f"    Nombre: {tag['name']}")
                print(f"    Color: {tag.get('color', 'N/A')}")
                print(f"    Active: {tag.get('active_analytic_distribution', False)}")
                print()
        else:
            print("  ⚠️ No se encontraron tags analíticos con 'Abastecimiento'\n")
    except Exception as e:
        print(f"  ℹ️ Modelo account.analytic.tag no disponible o error: {e}\n")
    
    # Ejemplo de uso en analytic_distribution
    if cuentas_analiticas:
        cuenta_id = cuentas_analiticas[0]['id']
        print("\n" + "="*60)
        print("💡 EJEMPLO DE USO en analytic_distribution:")
        print("="*60)
        print(f"\nPara una distribución 100% a '{cuentas_analiticas[0]['name']}':")
        print(f"""
analytic_distribution = {{
    "{cuenta_id}": 100
}}
""")
        print("\nPara distribución entre dos cuentas (50% cada una):")
        if len(cuentas_analiticas) > 1:
            print(f"""
analytic_distribution = {{
    "{cuentas_analiticas[0]['id']}": 50,
    "{cuentas_analiticas[1]['id']}": 50
}}
""")
        else:
            print(f"""
analytic_distribution = {{
    "{cuenta_id}": 50,
    "OTRA_CUENTA_ID": 50
}}
""")
        
        print("\n📝 Nota: El JSON debe estar como string al guardar en Odoo:")
        print('import json')
        print(f'analytic_distribution_str = json.dumps({{"{cuenta_id}": 100}})')
    
    # Buscar todas las cuentas analíticas (sin filtro)
    print("\n" + "="*60)
    print("📊 TODAS LAS CUENTAS ANALÍTICAS DISPONIBLES:")
    print("="*60)
    todas_cuentas = models.execute_kw(
        DB, uid, password,
        'account.analytic.account', 'search_read',
        [[]],
        {'fields': ['id', 'name', 'code', 'plan_id'], 'limit': 100}
    )
    
    for cuenta in todas_cuentas:
        plan_name = cuenta['plan_id'][1] if cuenta.get('plan_id') and isinstance(cuenta['plan_id'], (list, tuple)) else 'Sin plan'
        print(f"  ID {cuenta['id']:4d} | {cuenta['name']:40s} | Code: {cuenta.get('code', 'N/A'):10s} | Plan: {plan_name}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
