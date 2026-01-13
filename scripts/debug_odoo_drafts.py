#!/usr/bin/env python3
"""
Debug: Verificar asientos en estado DRAFT en Odoo
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient
import json

def main():
    print("="*60)
    print("🔍 DEBUG: ASIENTOS EN DRAFT EN ODOO")
    print("="*60)
    
    username = input("\n👤 Usuario Odoo: ").strip()
    password = input("🔑 API Key: ").strip()
    
    print("\n🔌 Conectando a Odoo...")
    odoo = OdooClient(username=username, password=password)
    
    # 1. Buscar TODOS los asientos en draft de 2026
    print("\n1️⃣ Buscando asientos (account.move) en estado DRAFT de 2026...")
    moves = odoo.search_read(
        "account.move",
        [
            ["state", "=", "draft"],
            ["date", ">=", "2026-01-01"],
            ["date", "<=", "2026-12-31"]
        ],
        ["id", "name", "date", "state", "move_type", "amount_total", "partner_id"],
        limit=50
    )
    
    print(f"\n📋 Asientos en draft encontrados: {len(moves)}")
    for m in moves[:20]:
        partner = m.get("partner_id", [None, ""])[1] if m.get("partner_id") else "Sin partner"
        print(f"   - {m['date']} | {m['name']} | {m['move_type']} | ${m['amount_total']:,.0f} | {partner[:30]}")
    
    if len(moves) > 20:
        print(f"   ... y {len(moves) - 20} más")
    
    # 2. Buscar líneas de movimiento en draft con cuentas de banco/caja
    print("\n2️⃣ Buscando líneas (account.move.line) en draft con cuentas de efectivo...")
    
    # Primero obtener cuentas de efectivo (prefijo 110, 111)
    cuentas_efectivo = odoo.search_read(
        "account.account",
        ["|", ["code", "=like", "110%"], ["code", "=like", "111%"]],
        ["id", "code", "name"],
        limit=20
    )
    
    print(f"\n   Cuentas de efectivo configuradas ({len(cuentas_efectivo)}):")
    for c in cuentas_efectivo:
        print(f"     - {c['code']}: {c['name'][:40]}")
    
    cuenta_ids = [c["id"] for c in cuentas_efectivo]
    
    if cuenta_ids:
        lines = odoo.search_read(
            "account.move.line",
            [
                ["parent_state", "=", "draft"],
                ["account_id", "in", cuenta_ids],
                ["date", ">=", "2026-01-01"],
                ["date", "<=", "2026-12-31"]
            ],
            ["id", "move_id", "account_id", "date", "name", "debit", "credit", "balance"],
            limit=50
        )
        
        print(f"\n   Líneas en draft con cuentas de efectivo: {len(lines)}")
        for ln in lines[:20]:
            acc = ln.get("account_id", [None, ""])[1] if ln.get("account_id") else ""
            move = ln.get("move_id", [None, ""])[1] if ln.get("move_id") else ""
            print(f"     - {ln['date']} | {acc[:15]} | {move[:20]} | Saldo: ${ln['balance']:,.0f}")
    else:
        print("   ⚠️ No se encontraron cuentas de efectivo")
    
    # 3. Verificar qué asientos tienen líneas en cuentas de efectivo
    print("\n3️⃣ Conclusión:")
    if len(moves) == 0:
        print("   ❌ No hay NINGÚN asiento en draft para 2026")
        print("   💡 Para que la proyección funcione, necesitas facturas/asientos")
        print("      en estado borrador con fechas futuras")
    elif not cuenta_ids:
        print("   ⚠️ No hay cuentas de efectivo configuradas (110xxx, 111xxx)")
    elif len(lines) == 0:
        print(f"   ⚠️ Hay {len(moves)} asientos en draft pero NINGUNO toca cuentas de efectivo")
        print("   💡 Las facturas en borrador probablemente son de:")
        print("      - Cuentas por cobrar (clientes)")
        print("      - Cuentas por pagar (proveedores)")
        print("   💡 Estas afectan el flujo cuando se PAGAN, no cuando se crean")
    else:
        print(f"   ✅ Hay {len(lines)} líneas en draft que tocan cuentas de efectivo")
        print("   ✅ Estas deberían aparecer como proyección")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
