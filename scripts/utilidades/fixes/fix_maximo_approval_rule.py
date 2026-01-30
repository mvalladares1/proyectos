"""
Script para corregir la regla de aprobación 142 de MÁXIMO SEPÚLVEDA
Debe aprobar OCs de TRANSPORTES con categoría SERVICIOS cuando estén en estado 'sent'
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("Conectando...")
odoo = OdooClient(username=USERNAME, password=PASSWORD)
print("OK\n")

# 1. Leer la regla actual
print("=" * 100)
print("REGLA ACTUAL (ID 142)")
print("=" * 100)

rule = odoo.search_read(
    'studio.approval.rule',
    [['id', '=', 142]],
    ['id', 'name', 'model_id', 'group_id', 'responsible_id', 'domain', 'active', 'method'],
    limit=1
)

if not rule:
    print("❌ No se encontró la regla 142")
    sys.exit(1)

rule = rule[0]

print(f"Nombre: {rule.get('name', '')}")
print(f"Activa: {rule.get('active', False)}")
print(f"Método: {rule.get('method', '')}")

responsible = rule.get('responsible_id')
responsible_name = responsible[1] if isinstance(responsible, (list, tuple)) else responsible
print(f"Responsable: {responsible_name}")

print(f"\nDominio ACTUAL:")
print(f"  {rule.get('domain', '')}")

# 2. Definir el nuevo dominio correcto
print("\n" + "=" * 100)
print("NUEVO DOMINIO A APLICAR")
print("=" * 100)

nuevo_dominio = [
    '&',
    '&',
    ['x_studio_selection_field_yUNPd', '=', 'TRANSPORTES'],
    ['x_studio_categora_de_producto', '=', 'SERVICIOS'],
    ['state', '=', 'sent']
]

print(f"\nDominio NUEVO:")
print(f"  {nuevo_dominio}")
print("\nCondiciones:")
print("  - Area Solicitante = TRANSPORTES")
print("  - Categoría de Producto = SERVICIOS")
print("  - Estado = sent (enviada)")
print("\nEsto significa:")
print("  Máximo Sepúlveda debe aprobar OCs de fletes/transportes (SERVICIOS)")
print("  cuando la OC sea enviada al proveedor (estado 'sent')")

# 3. Confirmar cambio
print("\n" + "=" * 100)
respuesta = input("¿Deseas actualizar la regla 142 con este nuevo dominio? (si/no): ")

if respuesta.lower() not in ['si', 's', 'yes', 'y']:
    print("\n❌ Operación cancelada")
    sys.exit(0)

# 4. Actualizar la regla
print("\nActualizando regla...")

try:
    result = odoo.models.execute_kw(
        odoo.db, odoo.uid, odoo.password,
        'studio.approval.rule', 'write',
        [[142], {
            'domain': str(nuevo_dominio)
        }]
    )
    
    if result:
        print("✅ Regla 142 actualizada correctamente")
        
        # Verificar el cambio
        print("\nVerificando cambio...")
        updated_rule = odoo.search_read(
            'studio.approval.rule',
            [['id', '=', 142]],
            ['id', 'name', 'domain'],
            limit=1
        )
        
        if updated_rule:
            print(f"\nDominio actualizado:")
            print(f"  {updated_rule[0].get('domain', '')}")
    else:
        print("❌ Error al actualizar la regla")
        
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

print("\n" + "=" * 100)
print("✅ PROCESO COMPLETADO")
print("=" * 100)
print("\nAhora cuando se envíe una OC (estado 'sent') que cumpla:")
print("  - Area Solicitante = TRANSPORTES")
print("  - Categoría = SERVICIOS")
print("\nSe creará automáticamente una actividad de aprobación para:")
print(f"  {responsible_name}")
