"""
Buscar y eliminar la tabla "N° PEDIDO DE COMPRA / REFERENCIA RECEPCION"
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

print("=" * 100)
print("BUSCAR TABLA 'N° PEDIDO DE COMPRA' / 'REFERENCIA RECEPCION'")
print("=" * 100)

# Buscar templates que contengan esta tabla
templates = models.execute_kw(db, uid, password,
    'ir.ui.view', 'search_read',
    [[
        ['type', '=', 'qweb'],
        '|',
        ['arch_db', 'ilike', 'PEDIDO DE COMPRA'],
        ['arch_db', 'ilike', 'REFERENCIA RECEPCION']
    ]],
    {'fields': ['id', 'name', 'key', 'inherit_id', 'arch_db'], 'limit': 20}
)

print(f"\n✅ Templates encontrados: {len(templates)}")

for t in templates:
    print(f"\n  ID: {t['id']}")
    print(f"  name: {t['name']}")
    print(f"  key: {t.get('key', '-')}")
    print(f"  inherit_id: {t.get('inherit_id', '-')}")
    
    arch = t.get('arch_db', '')
    
    # Guardar para análisis
    with open(f"template_pedido_{t['id']}.xml", 'w', encoding='utf-8') as f:
        f.write(arch)
    print(f"  📄 Guardado: template_pedido_{t['id']}.xml")
    
    # Ver fragmento relevante
    if 'PEDIDO DE COMPRA' in arch:
        import re
        lines = arch.split('\n')
        for i, line in enumerate(lines):
            if 'PEDIDO DE COMPRA' in line or 'REFERENCIA RECEPCION' in line:
                start = max(0, i-3)
                end = min(len(lines), i+15)
                print(f"\n  📋 Fragmento (líneas {start}-{end}):")
                for li, l in enumerate(lines[start:end]):
                    print(f"    {start+li+1}: {l[:100]}")
                break
