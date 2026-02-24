#!/usr/bin/env python3
"""
Script de migración para mover datos legacy a SQLite.
Ejecutar una vez en el servidor para migrar:
1. OVERRIDE_ORIGEN_PICKING (hardcoded) → override_origen table
2. exclusiones.json → exclusiones_valorizacion table

Uso: python scripts/migrate_permissions_to_db.py
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.permissions_service import (
    bulk_add_override_origen,
    bulk_add_exclusiones,
    get_override_origen_map,
    get_exclusiones_list,
)
from backend.services.recepcion_service import _LEGACY_OVERRIDE_ORIGEN_PICKING

print("=" * 60)
print("MIGRACIÓN DE DATOS A SQLITE")
print("=" * 60)

# 1. Migrar overrides de origen
print("\n📦 1. Migrando OVERRIDE_ORIGEN_PICKING...")
print(f"   Overrides legacy encontrados: {len(_LEGACY_OVERRIDE_ORIGEN_PICKING)}")

try:
    result = bulk_add_override_origen(_LEGACY_OVERRIDE_ORIGEN_PICKING)
    print(f"   ✅ Overrides en DB ahora: {len(result)}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# 2. Migrar exclusiones desde JSON
print("\n🚫 2. Migrando exclusiones.json...")
exclusiones_file = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "shared", "exclusiones.json"
)

if os.path.exists(exclusiones_file):
    import json
    try:
        with open(exclusiones_file, 'r') as f:
            data = json.load(f)
        
        albaranes = data.get("recepciones", [])
        print(f"   Exclusiones encontradas en JSON: {len(albaranes)}")
        
        if albaranes:
            result = bulk_add_exclusiones(albaranes, "Migración desde JSON")
            print(f"   ✅ Exclusiones en DB ahora: {len(result)}")
        else:
            print(f"   ⚠️  No hay exclusiones para migrar")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
else:
    print(f"   ⚠️  Archivo {exclusiones_file} no encontrado")

# 3. Verificar estado final
print("\n📊 3. Estado final:")
print(f"   Overrides en DB: {len(get_override_origen_map())}")
print(f"   Exclusiones en DB: {len(get_exclusiones_list())}")

print("\n" + "=" * 60)
print("✅ MIGRACIÓN COMPLETADA")
print("=" * 60)
