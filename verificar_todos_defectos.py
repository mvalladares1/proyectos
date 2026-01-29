"""
Verificar TODOS los campos de defectos en quality.check
"""
import sys
sys.path.append(r'c:\new\RIO FUTURO\DASHBOARD')
from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

odoo = OdooClient(username=USERNAME, password=PASSWORD)

print("=" * 100)
print("BÚSQUEDA DE TODOS LOS CAMPOS DE DEFECTOS EN QUALITY.CHECK")
print("=" * 100)

campos_quality = odoo.execute('quality.check', 'fields_get', [], {'attributes': ['string', 'type']})

print("\n📋 Campos que podrían ser DEFECTOS (x_studio con números/medidas):")
print("-" * 100)

defectos_encontrados = []
for campo, info in sorted(campos_quality.items()):
    if campo.startswith('x_studio'):
        descripcion = str(info.get('string', '')).lower()
        tipo = info.get('type', '')
        
        # Buscar campos que parecen defectos (contienen palabras clave)
        palabras_defecto = ['defecto', 'hongos', 'inmadura', 'sobremadura', 'deshidratado', 
                           'crumble', 'mecánico', 'insecto', 'deformes', 'verde', 'herida',
                           'partida', 'molida', 'materias', 'extrañas', 'gramos', 'daño',
                           'dao', 'fruta', 'presencia', 'total']
        
        es_defecto = any(palabra in campo.lower() or palabra in descripcion for palabra in palabras_defecto)
        
        if es_defecto and tipo in ['float', 'integer']:
            defectos_encontrados.append((campo, info.get('string', 'N/A'), tipo))
            print(f"  ✓ {campo:50s} | {info.get('string', 'N/A'):40s} | {tipo}")

print(f"\n✅ Total de campos de defectos encontrados: {len(defectos_encontrados)}")

# Buscar un quality check real con datos para ver qué campos se usan
print("\n" + "=" * 100)
print("VERIFICANDO QUALITY CHECK REAL CON DATOS")
print("=" * 100)

qc_ejemplo = odoo.search_read(
    'quality.check',
    [('x_studio_total_def_calidad', '>', 0)],
    [],
    limit=1
)

if qc_ejemplo:
    print(f"\n📊 Quality Check ID: {qc_ejemplo[0].get('id')}")
    print("\nCampos x_studio con valores > 0:")
    print("-" * 100)
    
    for campo, valor in sorted(qc_ejemplo[0].items()):
        if campo.startswith('x_studio'):
            # Solo mostrar si tiene valor numérico > 0 o string no vacío
            if isinstance(valor, (int, float)) and valor > 0:
                print(f"  {campo:50s} = {valor}")
            elif isinstance(valor, str) and valor and valor != 'False':
                print(f"  {campo:50s} = {valor}")

print("\n" + "=" * 100)
