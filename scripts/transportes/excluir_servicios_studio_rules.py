import xmlrpc.client

# Conexión a Odoo
url = "https://riofuturo.server98c6e.oerpondemand.net"
db = "riofuturo-master"
username = "mvalladares@riofuturo.cl"
password = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print("=" * 80)
print("MODIFICAR REGLAS DE STUDIO PARA EXCLUIR SERVICIOS")
print("=" * 80)

# Lista de reglas a modificar
reglas_a_modificar = [
    64,  # Gerencia General - CLP > 1.5M
    65,  # Gerencia General - USD > 1500
    83,  # Gerente A&F - USD > 300
    84,  # Gerente A&F - ADMIN/TI
    96,  # Aprobaciones / Finanzas (ESTA ES LA QUE SALE EN EL POPUP)
    120, # Control de Gestion (ESTA TAMBIÉN)
    123, # Gerencia General - UF > 80
    124, # Gerente A&F - UF
]

print("\n1. MODIFICANDO REGLAS PARA EXCLUIR SERVICIOS:")
print("-" * 80)

for regla_id in reglas_a_modificar:
    try:
        # Leer regla actual
        regla = models.execute_kw(db, uid, password, 'studio.approval.rule', 'read',
            [regla_id], {'fields': ['name', 'domain']})
        
        if regla:
            nombre = regla[0]['name']
            dominio_actual = regla[0].get('domain', [])
            
            # Agregar exclusión de SERVICIOS al dominio
            if dominio_actual:
                # Convertir string a lista si es necesario
                if isinstance(dominio_actual, str):
                    import ast
                    try:
                        dominio_actual = ast.literal_eval(dominio_actual)
                    except:
                        print(f"  ⚠️  ID {regla_id}: No se pudo parsear dominio")
                        continue
                
                # Agregar condición de exclusión de SERVICIOS
                nuevo_dominio = ['&'] + dominio_actual + [['x_studio_categora_de_producto', '!=', 'SERVICIOS']]
            else:
                nuevo_dominio = [['x_studio_categora_de_producto', '!=', 'SERVICIOS']]
            
            # Actualizar regla
            result = models.execute_kw(db, uid, password, 'studio.approval.rule', 'write',
                [[regla_id], {'domain': str(nuevo_dominio)}])
            
            if result:
                print(f"  ✅ ID {regla_id}: {nombre}")
                print(f"      Nuevo dominio: {nuevo_dominio}")
            else:
                print(f"  ❌ ID {regla_id}: Error al actualizar")
    
    except Exception as e:
        print(f"  ❌ ID {regla_id}: {e}")

print("\n" + "=" * 80)
print("✅ REGLAS MODIFICADAS")
print("=" * 80)
print("\nAhora las reglas de aprobación NO se aplicarán a categoría SERVICIOS.")
print("Esto incluye TRANSPORTES.")
print("\n⚠️  IMPORTANTE: Recarga Odoo (Ctrl+F5) para que tome los cambios")
