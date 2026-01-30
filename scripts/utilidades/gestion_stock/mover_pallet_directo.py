"""
Script para mover pallet PACK0026832 directamente cambiando ubicación de quants
De: RF/Stock/Camara 0°C REAL
A: RF/Stock/Camara 8 0°C

Uso:
    python scripts/mover_pallet_directo.py
"""

import sys
import os

# Agregar el directorio raíz al path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient

# Credenciales
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

def main():
    """Mueve el pallet directamente cambiando la ubicación de sus quants."""
    
    print("=" * 80)
    print("MOVIMIENTO DIRECTO DE PALLET - PACK0026832")
    print("=" * 80)
    
    # Conectar a Odoo
    print("\n1. Conectando a Odoo...")
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    print("   ✓ Conectado exitosamente")
    
    # Buscar el paquete
    print("\n2. Buscando paquete PACK0026832...")
    packages = odoo.search_read(
        "stock.quant.package",
        [("name", "=", "PACK0026832")],
        ["id", "name"]
    )
    
    if not packages:
        print("   ✗ ERROR: Paquete no encontrado")
        return
    
    package_id = packages[0]["id"]
    print(f"   ✓ Paquete encontrado (ID: {package_id})")
    
    # Buscar ubicación origen (INVERTIDO: ahora desde Camara 8)
    print("\n3. Buscando ubicación origen: RF/Stock/Camara 8 0°C...")
    loc_origen = odoo.search_read(
        "stock.location",
        [("complete_name", "=", "RF/Stock/Camara 8 0°C")],
        ["id", "name"]
    )
    
    if not loc_origen:
        print("   ✗ ERROR: Ubicación origen no encontrada")
        return
    
    loc_origen_id = loc_origen[0]["id"]
    print(f"   ✓ Ubicación origen (ID: {loc_origen_id})")
    
    # Buscar ubicación destino (INVERTIDO: ahora a Camara 0)
    print("\n4. Buscando ubicación destino: RF/Stock/Camara 0°C REAL...")
    loc_destino = odoo.search_read(
        "stock.location",
        [("complete_name", "=", "RF/Stock/Camara 0°C REAL")],
        ["id", "name"]
    )
    
    if not loc_destino:
        print("   ✗ ERROR: Ubicación destino no encontrada")
        return
    
    loc_destino_id = loc_destino[0]["id"]
    print(f"   ✓ Ubicación destino (ID: {loc_destino_id})")
    
    # Buscar todos los quants del paquete en la ubicación origen
    print("\n5. Buscando quants del paquete en ubicación origen...")
    quants = odoo.search_read(
        "stock.quant",
        [
            ("package_id", "=", package_id),
            ("location_id", "=", loc_origen_id),
            ("quantity", ">", 0)
        ],
        ["id", "product_id", "lot_id", "quantity", "reserved_quantity"]
    )
    
    if not quants:
        print("   ⚠️  No se encontraron quants del paquete en ubicación origen")
        print("   El paquete puede estar en otra ubicación o vacío")
        return
    
    print(f"   ✓ Encontrados {len(quants)} quants")
    print("\n   Detalles:")
    total_kg = 0
    for q in quants:
        prod_name = q["product_id"][1] if q.get("product_id") else "N/A"
        lot_name = q["lot_id"][1] if q.get("lot_id") else "N/A"
        reservado = q.get("reserved_quantity", 0)
        total_kg += q["quantity"]
        
        print(f"      - ID {q['id']}: {q['quantity']} kg | {prod_name[:40]} | Lote: {lot_name}")
        if reservado > 0:
            print(f"        └─ ⚠️  {reservado} kg reservados")
    
    print(f"\n   Total a mover: {total_kg} kg")
    
    # Mover los quants
    print("\n6. Moviendo quants a ubicación destino...")
    movidos = 0
    errores = 0
    
    for q in quants:
        try:
            # Si tiene cantidad reservada, liberarla primero
            if q.get("reserved_quantity", 0) > 0:
                print(f"   Liberando {q['reserved_quantity']} kg reservados del quant {q['id']}...")
                odoo.execute("stock.quant", "write", [q["id"]], {"reserved_quantity": 0})
            
            # Cambiar la ubicación
            odoo.execute("stock.quant", "write", [q["id"]], {"location_id": loc_destino_id})
            movidos += 1
            print(f"   ✓ Quant {q['id']} movido ({q['quantity']} kg)")
        except Exception as e:
            errores += 1
            print(f"   ✗ Error moviendo quant {q['id']}: {e}")
    
    # Verificar resultado final
    print("\n7. Verificando resultado...")
    quants_destino = odoo.search_read(
        "stock.quant",
        [
            ("package_id", "=", package_id),
            ("location_id", "=", loc_destino_id),
            ("quantity", ">", 0)
        ],
        ["quantity"]
    )
    
    total_destino = sum(q["quantity"] for q in quants_destino)
    
    quants_origen_restantes = odoo.search_read(
        "stock.quant",
        [
            ("package_id", "=", package_id),
            ("location_id", "=", loc_origen_id),
            ("quantity", ">", 0)
        ],
        ["quantity"]
    )
    
    total_origen = sum(q["quantity"] for q in quants_origen_restantes)
    
    print("\n" + "=" * 80)
    print("MOVIMIENTO COMPLETADO")
    print("=" * 80)
    print(f"\nRESUMEN:")
    print(f"  - Paquete: PACK0026832")
    print(f"  - Origen: RF/Stock/Camara 0°C REAL")
    print(f"  - Destino: RF/Stock/Camara 8 0°C")
    print(f"  - Quants movidos: {movidos}")
    print(f"  - Errores: {errores}")
    print(f"  - Total en origen ahora: {total_origen} kg")
    print(f"  - Total en destino ahora: {total_destino} kg")
    
    # Registrar en el modelo de Trasferencias Dashboard
    if errores == 0 and total_origen == 0:
        print("\n✅ Paquete movido completamente a destino")
        print("\n6. Registrando en logs de Trasferencias Dashboard...")
        
        try:
            from datetime import datetime
            
            # Preparar detalles
            detalles_texto = "\n".join([
                f"- {q['quantity']} kg | {q['product_id'][1]} | Lote: {q['lot_id'][1] if q.get('lot_id') else 'N/A'}"
                for q in quants
            ])
            
            # Crear registro
            log_vals = {
                "x_name": f"PACK0026832 → Camara 8",
                "x_fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "x_paquete_id": package_id,
                "x_ubicacion_origen_id": loc_origen_id,
                "x_ubicacion_destino_id": loc_destino_id,
                "x_total_kg": total_kg,
                "x_cantidad_quants": movidos,
                "x_detalles": detalles_texto,
                "x_estado": "success",
                "x_origen_sistema": "script"
            }
            
            log_id = odoo.execute("x_trasferencias_dashboard_v2", "create", log_vals)
            print(f"   ✓ Registro creado en Trasferencias Dashboard (ID: {log_id})")
        except Exception as e:
            print(f"   ⚠ No se pudo registrar en logs: {e}")
    elif errores > 0:
        print("\n⚠️  Movimiento completado con errores")
    else:
        print("\n⚠️  Aún quedan quants en origen")


if __name__ == "__main__":
    main()
