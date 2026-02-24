"""
Limpiar herencias innecesarias que se crearon antes
(agregaban columnas al template equivocado)
"""
import xmlrpc.client

# Configuración
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# Conectar
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print("=" * 80)
print("LIMPIAR HERENCIAS INNECESARIAS")
print("=" * 80)

# Buscar las vistas que creamos incorrectamente
views_to_remove = [
    'l10n_cl.informations.po_date',
    'account.report_invoice_document.po_date_column'
]

for view_name in views_to_remove:
    views = models.execute_kw(db, uid, password,
        'ir.ui.view', 'search_read',
        [[['name', '=', view_name]]],
        {'fields': ['id', 'name', 'active']}
    )
    
    if views:
        for v in views:
            print(f"\n🗑️  Eliminando vista: {v['name']} (ID: {v['id']})")
            try:
                models.execute_kw(db, uid, password,
                    'ir.ui.view', 'unlink', [[v['id']]]
                )
                print(f"   ✅ Eliminada")
            except Exception as e:
                print(f"   ❌ Error: {e}")
    else:
        print(f"\n✓ Vista '{view_name}' no existe (ya eliminada o nunca creada)")

print("\n✅ Limpieza completada")
