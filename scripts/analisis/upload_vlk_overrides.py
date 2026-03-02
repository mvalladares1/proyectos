"""
Script para subir overrides de origen VLK al servidor
Toma los albaranes del Excel forense y los marca como VILKUN en permissions.db
"""
import pandas as pd
import subprocess
import os

# Ruta al Excel generado
EXCEL_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'output', 'forense_tunel_vlk_v2_20260226_113419.xlsx')

# Servidor
SERVER = "debian@167.114.114.51"
DB_PATH = "/home/debian/apps/proyectos/data/permissions.db"

def main():
    print("=" * 80)
    print("CARGA MASIVA DE OVERRIDES VLK -> VILKUN")
    print("=" * 80)
    
    # 1. Leer Excel
    print("\n[1/4] Leyendo Excel...")
    df = pd.read_excel(EXCEL_PATH, sheet_name='Recepciones Unicas')
    pickings = df['Albaran'].dropna().unique().tolist()
    print(f"  OK {len(pickings)} albaranes únicos")
    
    # 2. Filtrar solo los que empiezan con RF/RFP (son los de Rio Futuro que deben ir a Vilkun)
    # Excluir los que ya tienen VILKUN en el nombre
    pickings_rf = [p for p in pickings if p.startswith('RF/RFP/') and 'VLK' not in p.upper()]
    print(f"  OK {len(pickings_rf)} albaranes RF/RFP a sobrescribir como VILKUN")
    
    # 3. Generar SQL
    print("\n[2/4] Generando SQL...")
    sql_lines = []
    for picking in pickings_rf:
        # Escapar comillas simples
        safe_picking = picking.replace("'", "''")
        sql_lines.append(f"INSERT OR REPLACE INTO override_origen (picking_name, origen, created_at) VALUES ('{safe_picking}', 'VILKUN', datetime('now'));")
    
    sql_content = "\n".join(sql_lines)
    
    # Guardar SQL localmente para referencia
    sql_path = os.path.join(os.path.dirname(EXCEL_PATH), 'vlk_overrides.sql')
    with open(sql_path, 'w', encoding='utf-8') as f:
        f.write(sql_content)
    print(f"  OK SQL guardado en: {sql_path}")
    print(f"  Primeras 3 líneas:\n    {sql_lines[0]}\n    {sql_lines[1]}\n    {sql_lines[2]}")
    
    # 4. Verificar overrides actuales en el servidor
    print("\n[3/4] Verificando overrides actuales en servidor...")
    cmd_count = f'ssh {SERVER} "sqlite3 {DB_PATH} \\"SELECT COUNT(*) FROM override_origen;\\""'
    result = subprocess.run(cmd_count, shell=True, capture_output=True, text=True)
    current_count = result.stdout.strip()
    print(f"  Overrides actuales: {current_count}")
    
    # 5. Preguntar confirmación
    print("\n" + "=" * 80)
    print(f"RESUMEN:")
    print(f"  - Albaranes a marcar como VILKUN: {len(pickings_rf)}")
    print(f"  - Overrides actuales en DB: {current_count}")
    print(f"  - Servidor: {SERVER}")
    print(f"  - DB: {DB_PATH}")
    print("=" * 80)
    
    confirm = input("\n¿Ejecutar la carga? (s/n): ").strip().lower()
    if confirm != 's':
        print("Cancelado.")
        return
    
    # 6. Ejecutar
    print("\n[4/4] Ejecutando carga en servidor...")
    
    # Copiar SQL al servidor y ejecutar
    remote_sql = "/tmp/vlk_overrides.sql"
    
    # Subir archivo
    cmd_upload = f'scp "{sql_path}" {SERVER}:{remote_sql}'
    print(f"  Subiendo SQL...")
    subprocess.run(cmd_upload, shell=True, check=True)
    
    # Ejecutar SQL
    cmd_exec = f'ssh {SERVER} "sqlite3 {DB_PATH} < {remote_sql}"'
    print(f"  Ejecutando SQL...")
    subprocess.run(cmd_exec, shell=True, check=True)
    
    # Verificar resultado
    result = subprocess.run(cmd_count, shell=True, capture_output=True, text=True)
    new_count = result.stdout.strip()
    print(f"\n  OK Overrides después de carga: {new_count}")
    
    # Limpiar
    subprocess.run(f'ssh {SERVER} "rm {remote_sql}"', shell=True)
    
    print("\n" + "=" * 80)
    print("CARGA COMPLETADA!")
    print("=" * 80)


if __name__ == '__main__':
    main()
