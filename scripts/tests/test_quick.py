import sys
sys.path.append('backend')
from services.recepcion_defectos_service import generar_reporte_defectos_excel

username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

print("Generando Excel con defectos actualizados...")
archivo = generar_reporte_defectos_excel(username, password, '2026-01-30', '2026-01-31', origenes=['RFP'])
print(f'✅ Excel generado exitosamente')
print(f'Tamaño: {len(archivo)} bytes')
print('Abre el archivo generado en shared/temp/ para verificar los defectos')
