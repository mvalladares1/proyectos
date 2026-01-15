"""
Script para analizar campos x_studio_ no utilizados en Odoo 16
Se conecta vía API usando email y API key
"""
import xmlrpc.client
from collections import defaultdict
import json


class OdooStudioAnalyzer:
    def __init__(self, url, db, email, api_key):
        """
        Inicializa conexión con Odoo
        
        Args:
            url: URL de Odoo (ej: https://tudominio.odoo.com)
            db: Nombre de la base de datos
            email: Email del usuario
            api_key: API Key generada en Odoo
        """
        self.url = url
        self.db = db
        self.email = email
        self.api_key = api_key
        
        # Endpoints
        self.common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        self.models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        # Autenticar
        self.uid = self.common.authenticate(db, email, api_key, {})
        if not self.uid:
            raise Exception("Error de autenticación. Verifica tus credenciales.")
        
        print(f"✅ Conectado exitosamente a Odoo como {email} (UID: {self.uid})")
    
    def execute(self, model, method, *args, **kwargs):
        """Ejecuta una llamada al modelo de Odoo"""
        return self.models.execute_kw(
            self.db, self.uid, self.api_key,
            model, method, args, kwargs
        )
    
    def get_all_models(self):
        """Obtiene todos los modelos del sistema"""
        models = self.execute('ir.model', 'search_read', 
                             [], 
                             ['model', 'name'])
        return {m['model']: m['name'] for m in models}
    
    def get_studio_fields(self, model_name):
        """Obtiene todos los campos x_studio_ de un modelo específico"""
        try:
            fields = self.execute(
                'ir.model.fields',
                'search_read',
                [['model', '=', model_name], ['name', 'like', 'x_studio_%']],
                ['name', 'field_description', 'ttype', 'model']
            )
            return fields
        except Exception as e:
            # Algunos modelos pueden no ser accesibles
            return []
    
    def check_field_usage_in_views(self, model_name, field_name):
        """
        Verifica si un campo está siendo usado en vistas, reportes, etc.
        
        Returns:
            dict con información de uso en UI: {
                'in_views': bool,
                'view_count': int,
                'view_types': list,
                'view_names': list
            }
        """
        try:
            # Buscar en vistas (ir.ui.view) que contengan el nombre del campo
            views = self.execute(
                'ir.ui.view',
                'search_read',
                [
                    ['model', '=', model_name],
                    '|',
                    ['arch_db', 'ilike', f'field name="{field_name}"'],
                    ['arch_db', 'ilike', f'field="{field_name}"']
                ],
                ['name', 'type', 'arch_db']
            )
            
            view_types = []
            view_names = []
            
            for view in views:
                if view.get('type'):
                    view_types.append(view['type'])
                if view.get('name'):
                    view_names.append(view['name'])
            
            return {
                'in_views': len(views) > 0,
                'view_count': len(views),
                'view_types': list(set(view_types)),
                'view_names': view_names
            }
        except Exception as e:
            return {
                'in_views': None,
                'view_count': 0,
                'view_types': [],
                'view_names': [],
                'error': str(e)[:100]
            }
    
    def check_field_in_reports(self, model_name, field_name):
        """Verifica si el campo está en reportes QWeb"""
        try:
            # Buscar en reportes que mencionen el campo
            reports = self.execute(
                'ir.actions.report',
                'search_read',
                [['model', '=', model_name]],
                ['name', 'report_name']
            )
            
            # Para cada reporte, buscar en su template
            found_in_reports = []
            for report in reports:
                # Buscar vistas QWeb relacionadas
                qweb_views = self.execute(
                    'ir.ui.view',
                    'search_read',
                    [
                        ['type', '=', 'qweb'],
                        ['arch_db', 'ilike', field_name]
                    ],
                    ['name']
                )
                if qweb_views:
                    found_in_reports.append(report.get('name', 'Unknown'))
            
            return {
                'in_reports': len(found_in_reports) > 0,
                'report_names': found_in_reports
            }
        except Exception as e:
            return {
                'in_reports': None,
                'report_names': [],
                'error': str(e)[:100]
            }
    
    def check_field_usage(self, model_name, field_name):
        """
        Verifica si un campo está siendo usado en la interfaz (vistas, reportes, etc)
        NO verifica si tiene datos, sino si está en uso en la UI
        
        Returns:
            dict con información de uso completo
        """
        try:
            # Verificar uso en vistas
            view_usage = self.check_field_usage_in_views(model_name, field_name)
            
            # Verificar uso en reportes
            report_usage = self.check_field_in_reports(model_name, field_name)
            
            # Determinar si está en uso
            is_used = view_usage.get('in_views', False) or report_usage.get('in_reports', False)
            
            usage_locations = []
            if view_usage.get('in_views'):
                usage_locations.extend([f"Vista {vt}" for vt in view_usage.get('view_types', [])])
            if report_usage.get('in_reports'):
                usage_locations.append("Reportes")
            
            return {
                'is_used': is_used,
                'usage_locations': usage_locations,
                'views': view_usage,
                'reports': report_usage
            }
        except Exception as e:
            return {
                'is_used': None,
                'usage_locations': [],
                'views': {},
                'reports': {},
                'error': str(e)[:100]
            }
    
    def analyze_all_studio_fields(self, skip_models=None):
        """
        Analiza todos los campos x_studio_ en todo el sistema
        
        Args:
            skip_models: Lista de modelos a omitir (ej: modelos abstractos)
        """
        if skip_models is None:
            skip_models = [
                'base', 'ir.actions.act_window.view', 'ir.actions.report',
                'ir.ui.view', 'ir.model.data', 'ir.module.module'
            ]
        
        print("\n🔍 Analizando campos x_studio_ en todos los modelos...")
        print("-" * 80)
        
        # Obtener todos los modelos
        all_models = self.get_all_models()
        
        results = {
            'unused_fields': [],
            'used_fields': [],
            'error_fields': [],
            'summary': defaultdict(int)
        }
        
        total_models = len(all_models)
        processed = 0
        
        for model_name, model_display_name in all_models.items():
            processed += 1
            
            # Omitir modelos en la lista de exclusión
            if any(skip in model_name for skip in skip_models):
                continue
            
            # Obtener campos studio del modelo
            studio_fields = self.get_studio_fields(model_name)
            
            if not studio_fields:
                continue
            
            print(f"\n[{processed}/{total_models}] Analizando: {model_display_name} ({model_name})")
            print(f"   Campos x_studio_ encontrados: {len(studio_fields)}")
            
            for field in studio_fields:
                field_name = field['name']
                field_desc = field['field_description']
                field_type = field['ttype']
                
                # Verificar uso del campo en vistas/reportes
                usage = self.check_field_usage(model_name, field_name)
                
                field_info = {
                    'model': model_name,
                    'model_name': model_display_name,
                    'field': field_name,
                    'description': field_desc,
                    'type': field_type,
                    'usage': usage
                }
                
                if usage.get('error'):
                    results['error_fields'].append(field_info)
                    results['summary']['errors'] += 1
                    print(f"   ⚠️  {field_name}: ERROR - {usage['error'][:50]}")
                elif usage.get('is_used'):
                    results['used_fields'].append(field_info)
                    results['summary']['used'] += 1
                    locations = ", ".join(usage.get('usage_locations', []))
                    print(f"   ✅ {field_name}: USADO en {locations}")
                else:
                    results['unused_fields'].append(field_info)
                    results['summary']['unused'] += 1
                    print(f"   ❌ {field_name}: NO USADO en vistas/reportes")
        
        return results
    
    def generate_report(self, results, output_file='campos_studio_analisis.json'):
        """Genera un reporte en formato JSON"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n📄 Reporte guardado en: {output_file}")
    
    def print_summary(self, results):
        """Imprime un resumen del análisis"""
        print("\n" + "=" * 80)
        print("📊 RESUMEN DEL ANÁLISIS")
        print("=" * 80)
        
        summary = results['summary']
        total = summary['used'] + summary['unused'] + summary['errors']
        
        print(f"\n📈 Total de campos x_studio_ analizados: {total}")
        print(f"   ✅ Campos en uso: {summary['used']} ({summary['used']/total*100:.1f}%)")
        print(f"   ❌ Campos NO usados: {summary['unused']} ({summary['unused']/total*100:.1f}%)")
        print(f"   ⚠️  Campos con error: {summary['errors']} ({summary['errors']/total*100:.1f}%)")
        
        # Top 20 campos no usados
        if results['unused_fields']:
            print(f"\n🔴 TOP CAMPOS NO UTILIZADOS EN VISTAS:")
            print("-" * 80)
            for field in results['unused_fields'][:20]:
                print(f"   • {field['model_name']}")
                print(f"     Campo: {field['field']} ({field['type']})")
                print(f"     Descripción: {field['description']}")
                print()
        
        # Modelos con más campos no usados
        unused_by_model = defaultdict(int)
        for field in results['unused_fields']:
            unused_by_model[field['model_name']] += 1
        
        if unused_by_model:
            print(f"\n📋 MODELOS CON MÁS CAMPOS NO USADOS:")
            print("-" * 80)
            sorted_models = sorted(unused_by_model.items(), key=lambda x: x[1], reverse=True)
            for model, count in sorted_models[:10]:
                print(f"   {count:3d} campos - {model}")


def main():
    """Función principal"""
    print("=" * 80)
    print("🔧 ANALIZADOR DE CAMPOS X_STUDIO_ EN ODOO 16")
    print("=" * 80)
    
    # Configuración de conexión
    URL = "https://riofuturo.server98c6e.oerpondemand.net"  # Cambiar por tu URL
    DB = "riofuturo-master"  # Cambiar por tu base de datos
    EMAIL = "mvalladares@riofuturo.cl"  # Cambiar por tu email
    API_KEY = "c0766224bec30cac071ffe43a858c9ccbd521ddd"  # Cambiar por tu API key
    
    print("\n⚙️  Configuración:")
    print(f"   URL: {URL}")
    print(f"   DB: {DB}")
    print(f"   Email: {EMAIL}")
    
    try:
        # Crear analizador
        analyzer = OdooStudioAnalyzer(URL, DB, EMAIL, API_KEY)
        
        # Analizar todos los campos
        results = analyzer.analyze_all_studio_fields()
        
        # Imprimir resumen
        analyzer.print_summary(results)
        
        # Guardar reporte
        analyzer.generate_report(results)
        
        print("\n✨ Análisis completado exitosamente!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
