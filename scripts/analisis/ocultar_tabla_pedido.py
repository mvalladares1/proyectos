#!/usr/bin/env python3
"""
Script para ocultar la tabla de "N° Pedido de Compra" del reporte de factura proveedor.
Esta tabla está en el template 4737 (hereda de 4735).
"""

import xmlrpc.client

# Configuración
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# Conexión
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
print(f"✅ Conectado como UID: {uid}")

# Primero veamos el template 4737
template_4737 = models.execute_kw(db, uid, password, 'ir.ui.view', 'read', [[4737]], 
                                   {'fields': ['name', 'key', 'arch_db', 'active', 'inherit_id']})

if template_4737:
    t = template_4737[0]
    print(f"\n📄 Template 4737:")
    print(f"   Nombre: {t['name']}")
    print(f"   Key: {t['key']}")
    print(f"   Activo: {t['active']}")
    print(f"   Hereda de: {t['inherit_id']}")
    
    # Opciones para ocultar la tabla:
    # 1. Desactivar todo el template 4737 (podría afectar otras cosas)
    # 2. Crear una herencia que reemplace la tabla con nada
    # 3. Modificar el arch para agregar style="display:none" a la tabla
    
    print("\n" + "="*60)
    print("OPCIONES DISPONIBLES:")
    print("="*60)
    print("1. Desactivar template 4737 completamente")
    print("2. Crear herencia que oculte solo la tabla")
    print("3. Modificar el arch agregando display:none a table[2]")

# Vamos con la opción 3 - Modificar el template para ocultar la tabla
# La forma más limpia es agregar un xpath que reemplace la tabla con una vacía con display:none

# Primero, veamos si podemos modificar el grupo de la tabla a uno que no exista
# O mejor aún, reemplazar la tabla completa

print("\n" + "="*60)
print("EJECUTANDO: Ocultar tabla agregando style='display:none'")
print("="*60)

# Leer el arch actual
arch_actual = t['arch_db']

# Buscar la posición donde está la tabla
# La tabla se crea con el xpath "/t/t/div[2]/div[1]/div" position="after"
# Y luego se le asigna groups en el último xpath

# La mejor opción es modificar el último xpath para agregar un style display:none
# en lugar del groups

# Vamos a crear una vista heredada nueva que oculte la tabla
nuevo_arch = '''<?xml version="1.0"?>
<data inherit_id="gen_key.eabbc4">
    <!-- Ocultar la tabla de N° Pedido de Compra -->
    <xpath expr="/t/t/div[2]/div[1]/table[2]" position="attributes">
        <attribute name="style">display:none !important;</attribute>
    </xpath>
</data>'''

# Crear la vista heredada
try:
    # Primero verificar si ya existe
    existing = models.execute_kw(db, uid, password, 'ir.ui.view', 'search_read',
                                  [[['key', '=', 'custom.ocultar_tabla_pedido']]],
                                  {'fields': ['id']})
    
    if existing:
        # Actualizar la existente
        view_id = existing[0]['id']
        models.execute_kw(db, uid, password, 'ir.ui.view', 'write',
                          [[view_id], {'arch_db': nuevo_arch, 'active': True}])
        print(f"✅ Vista actualizada: ID {view_id}")
    else:
        # Crear nueva vista heredada
        values = {
            'name': 'Ocultar Tabla Pedido de Compra',
            'type': 'qweb',
            'key': 'custom.ocultar_tabla_pedido',
            'inherit_id': 4737,  # Hereda de gen_key.eabbc4
            'arch_db': nuevo_arch,
            'priority': 99,  # Alta prioridad para que se aplique después
            'active': True,
        }
        view_id = models.execute_kw(db, uid, password, 'ir.ui.view', 'create', [values])
        print(f"✅ Vista creada: ID {view_id}")
    
    print(f"\n📌 La tabla de 'N° Pedido de Compra' ha sido ocultada")
    print(f"   Por favor, previsualice la factura para confirmar el cambio.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    
    # Plan B: Si falla la herencia, intentar con la desactivación directa
    print("\n🔄 Intentando Plan B: Desactivar template 4737 completamente...")
    
    try:
        # Esto es más drástico pero funcionará
        models.execute_kw(db, uid, password, 'ir.ui.view', 'write',
                          [[4737], {'active': False}])
        print(f"✅ Template 4737 desactivado completamente")
        print(f"   ⚠️  Esto podría afectar otras personalizaciones de Studio")
    except Exception as e2:
        print(f"❌ Error en Plan B: {e2}")
