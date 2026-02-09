"""
Script para obtener las reglas de aprobación de Studio configuradas para purchase.order
"""
import xmlrpc.client
import json

URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'

# Credenciales - cambiar por las reales
USERNAME = input("Usuario Odoo: ")
PASSWORD = input("Contraseña: ")

# Conectar
common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
uid = common.authenticate(DB, USERNAME, PASSWORD, {})

if not uid:
    print("❌ Error de autenticación")
    exit(1)

print(f"✅ Conectado como usuario ID: {uid}\n")

models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

# 1. Obtener reglas de aprobación de Studio para purchase.order
print("=" * 80)
print("📋 REGLAS DE APROBACIÓN DE STUDIO PARA PURCHASE.ORDER")
print("=" * 80)

try:
    # Primero obtener TODAS las reglas para ver qué campos tienen
    reglas = models.execute_kw(
        DB, uid, PASSWORD,
        'studio.approval.rule', 'search_read',
        [[]],  # Sin filtro para ver todas
        {'fields': []}  # Todos los campos
    )
    
    if not reglas:
        print("⚠️  No se encontraron reglas de Studio")
    else:
        print(f"\n✅ Se encontraron {len(reglas)} regla(s) en total:\n")
        
        # Filtrar solo las de purchase.order
        reglas_po = [r for r in reglas if 'purchase.order' in str(r.get('model_id', '')) or 'purchase' in r.get('name', '').lower()]
        
        print(f"📦 Reglas relacionadas con Purchase Order: {len(reglas_po)}\n")
        
        for idx, regla in enumerate(reglas_po, 1):
            print(f"\n{'─' * 80}")
            print(f"REGLA #{idx}")
            print(f"{'─' * 80}")
            print(f"ID: {regla['id']}")
            print(f"Nombre: {regla.get('name', 'N/A')}")
            
            # Modelo
            if regla.get('model_id'):
                modelo = regla['model_id'][1] if isinstance(regla['model_id'], list) else regla['model_id']
                print(f"Modelo: {modelo}")
            
            print(f"Activa: {'✅ Sí' if regla.get('active') else '❌ No'}")
            print(f"Mensaje: {regla.get('message', 'N/A')}")
            print(f"Exclusivo (solo un usuario): {regla.get('exclusive_user', False)}")
            print(f"Método: {regla.get('method', 'N/A')}")
            print(f"Acción: {regla.get('action_id', 'N/A')}")
            
            # Grupo
            if regla.get('group_id'):
                print(f"Grupo: {regla['group_id'][1] if isinstance(regla['group_id'], list) else regla['group_id']}")
            
            # Usuarios
            if regla.get('user_ids'):
                print(f"Usuarios asignados: {len(regla['user_ids'])} usuario(s)")
                # Obtener nombres de usuarios
                if regla['user_ids']:
                    usuarios = models.execute_kw(
                        DB, uid, PASSWORD,
                        'res.users', 'read',
                        [regla['user_ids']],
                        {'fields': ['id', 'name', 'login']}
                    )
                    for user in usuarios:
                        print(f"  - [{user['id']}] {user['name']} ({user['login']})")
            
            # Dominio
            if regla.get('domain'):
                print(f"Dominio (filtro): {regla['domain']}")
            
            # Otros campos útiles
            if regla.get('can_validate'):
                print(f"Puede validar: {regla['can_validate']}")
            if regla.get('notification_order'):
                print(f"Orden de notificación: {regla['notification_order']}")
        
        # Mostrar TODAS las reglas para referencia
        print(f"\n\n{'═' * 80}")
        print(f"📋 TODAS LAS REGLAS ({len(reglas)} total)")
        print(f"{'═' * 80}\n")
        for regla in reglas:
            modelo_str = regla['model_id'][1] if regla.get('model_id') and isinstance(regla['model_id'], list) else 'N/A'
            print(f"ID {regla['id']}: {regla.get('name', 'Sin nombre')} | Modelo: {modelo_str}")

except Exception as e:
    print(f"❌ Error al obtener reglas: {e}")
    print("\nVerificando si existe el modelo studio.approval.rule...")
    
    try:
        # Verificar modelos disponibles
        modelos = models.execute_kw(
            DB, uid, PASSWORD,
            'ir.model', 'search_read',
            [[('model', 'ilike', 'studio')]],
            {'fields': ['model', 'name']}
        )
        print(f"\n📦 Modelos de Studio disponibles:")
        for modelo in modelos:
            print(f"  - {modelo['model']}: {modelo['name']}")
    except Exception as e2:
        print(f"❌ Error: {e2}")

# 2. Buscar entradas de aprobación existentes
print("\n" + "=" * 80)
print("📝 ENTRADAS DE APROBACIÓN EXISTENTES (studio.approval.entry)")
print("=" * 80)

try:
    entradas = models.execute_kw(
        DB, uid, PASSWORD,
        'studio.approval.entry', 'search_read',
        [[('model', '=', 'purchase.order')]],
        {'fields': ['id', 'res_id', 'rule_id', 'user_id', 'approved', 'create_date'], 'limit': 10, 'order': 'create_date desc'}
    )
    
    if entradas:
        print(f"\n✅ Se encontraron {len(entradas)} entrada(s) recientes:\n")
        
        for entrada in entradas:
            print(f"\nEntrada ID: {entrada['id']}")
            print(f"  OC ID: {entrada.get('res_id')}")
            print(f"  Regla ID: {entrada['rule_id'][1] if isinstance(entrada['rule_id'], list) else entrada['rule_id']}")
            print(f"  Usuario: {entrada['user_id'][1] if isinstance(entrada['user_id'], list) else entrada['user_id']}")
            print(f"  Aprobado: {'✅ Sí' if entrada.get('approved') else '❌ No'}")
            print(f"  Fecha: {entrada.get('create_date')}")
    else:
        print("⚠️  No se encontraron entradas de aprobación para purchase.order")
        
except Exception as e:
    print(f"❌ Error al obtener entradas: {e}")

# 3. Verificar OCs con estado relacionado a aprobaciones
print("\n" + "=" * 80)
print("📦 EJEMPLO DE OC CON INFORMACIÓN DE ESTADO")
print("=" * 80)

try:
    ocs = models.execute_kw(
        DB, uid, PASSWORD,
        'purchase.order', 'search_read',
        [[('x_studio_categora_de_producto', '=', 'TRANSPORTES'), ('state', '=', 'draft')]],
        {'fields': ['id', 'name', 'state', 'approval_status'], 'limit': 3}
    )
    
    if ocs:
        print(f"\nEjemplo de 3 OCs en draft:")
        for oc in ocs:
            print(f"\n  OC: {oc['name']} (ID: {oc['id']})")
            print(f"  Estado: {oc['state']}")
            print(f"  Approval Status: {oc.get('approval_status', 'N/A')}")
    
except Exception as e:
    print(f"Nota: {e}")

print("\n" + "=" * 80)
print("✅ Script completado")
print("=" * 80)
