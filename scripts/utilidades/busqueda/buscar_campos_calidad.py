"""
Búsqueda exhaustiva de campos relacionados con calidad, calibre, tipo y clasificación.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 100)
print("BÚSQUEDA EXHAUSTIVA DE CAMPOS DE CALIDAD")
print("=" * 100)

odoo = OdooClient(username=USERNAME, password=PASSWORD)
print("✅ Conectado\n")

# =============== PRODUCT.TEMPLATE ===============
print("=" * 100)
print("PRODUCT.TEMPLATE - Búsqueda de calibre y tipo")
print("=" * 100)

campos_template = odoo.execute('product.template', 'fields_get', [], {'attributes': ['string', 'type', 'relation']})

# Buscar TODOS los campos que podrían contener calibre
print("\n📏 Campos que podrían ser CALIBRE:")
for campo, info in sorted(campos_template.items()):
    descripcion = str(info.get('string', '')).lower()
    campo_lower = campo.lower()
    if any(x in campo_lower or x in descripcion for x in ['calibr', 'size', 'tamaño', 'medida']):
        print(f"  {campo:50s} | {info.get('string', 'N/A'):40s} | {info.get('type', 'N/A')}")

# Buscar campos que podrían ser tipo de fruta/categoría
print("\n🍓 Campos que podrían ser TIPO DE FRUTA / CATEGORÍA:")
for campo, info in sorted(campos_template.items()):
    descripcion = str(info.get('string', '')).lower()
    campo_lower = campo.lower()
    if any(x in campo_lower or x in descripcion for x in ['tipo', 'categor', 'especie', 'fruta', 'berry']):
        print(f"  {campo:50s} | {info.get('string', 'N/A'):40s} | {info.get('type', 'N/A')}")

# =============== QUALITY.CHECK ===============
print("\n" + "=" * 100)
print("QUALITY.CHECK - Búsqueda de clasificación y total defectos")
print("=" * 100)

campos_quality = odoo.execute('quality.check', 'fields_get', [], {'attributes': ['string', 'type', 'relation']})

# Buscar campos de clasificación/calificación
print("\n⭐ Campos que podrían ser CLASIFICACIÓN / CALIFICACIÓN:")
for campo, info in sorted(campos_quality.items()):
    descripcion = str(info.get('string', '')).lower()
    campo_lower = campo.lower()
    if any(x in campo_lower or x in descripcion for x in ['clasif', 'califi', 'grade', 'rating', 'calidad', 'quality']):
        print(f"  {campo:50s} | {info.get('string', 'N/A'):40s} | {info.get('type', 'N/A')}")

# Buscar campos de total defectos / porcentaje defectos
print("\n📊 Campos que podrían ser TOTAL DEFECTOS / % DEFECTOS:")
for campo, info in sorted(campos_quality.items()):
    descripcion = str(info.get('string', '')).lower()
    campo_lower = campo.lower()
    if any(x in campo_lower or x in descripcion for x in ['total', 'defect', 'porcent', '%', 'suma']):
        print(f"  {campo:50s} | {info.get('string', 'N/A'):40s} | {info.get('type', 'N/A')}")

# =============== OBTENER VALORES REALES ===============
print("\n" + "=" * 100)
print("OBTENIENDO VALORES REALES DE ALGUNOS REGISTROS")
print("=" * 100)

# Obtener un template real para ver sus valores
print("\n📦 Ejemplo de product.template real:")
templates = odoo.search_read('product.template', [], [], limit=1)
if templates:
    tmpl = templates[0]
    print(f"\nID: {tmpl.get('id')}")
    print(f"Nombre: {tmpl.get('name', 'N/A')}")
    
    # Mostrar campos x_studio que tengan valores
    print("\nCampos x_studio con valores:")
    for campo, valor in sorted(tmpl.items()):
        if campo.startswith('x_studio') and valor:
            print(f"  {campo:50s} = {valor}")

# Obtener un quality.check real
print("\n🔬 Ejemplo de quality.check real:")
qcs = odoo.search_read('quality.check', [], [], limit=1)
if qcs:
    qc = qcs[0]
    print(f"\nID: {qc.get('id')}")
    
    # Mostrar campos x_studio que tengan valores
    print("\nCampos x_studio con valores:")
    for campo, valor in sorted(qc.items()):
        if campo.startswith('x_studio') and valor:
            tipo_valor = type(valor).__name__
            if isinstance(valor, (list, tuple)) and len(valor) > 1:
                print(f"  {campo:50s} = {valor[1]} (many2one)")
            else:
                print(f"  {campo:50s} = {valor} ({tipo_valor})")

print("\n" + "=" * 100)
print("✅ BÚSQUEDA COMPLETADA")
print("=" * 100)
