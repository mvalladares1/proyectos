"""
Cliente Odoo compartido usando XML-RPC.
Compatible con todos los dashboards del sistema.
"""
import xmlrpc.client
from typing import Optional, List, Dict, Any
import pandas as pd
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde múltiples ubicaciones posibles
# 1. Directorio actual
# 2. Directorio del archivo
# 3. Directorio raíz del proyecto
load_dotenv()  # Intenta directorio actual
load_dotenv(Path(__file__).parent.parent / ".env")  # Raíz del proyecto


class OdooClient:
    """
    Cliente XML-RPC para conectar con Odoo.
    Puede usar credenciales del .env o credenciales proporcionadas por el usuario.
    """
    
    # Valores por defecto para URL y DB (pueden ser sobreescritos por .env o parámetros)
    DEFAULT_URL = "https://riofuturo.server98c6e.oerpondemand.net"
    DEFAULT_DB = "riofuturo-master"
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None,
                 url: Optional[str] = None, db: Optional[str] = None):
        """
        Inicializa el cliente Odoo.
        
        Args:
            username: Usuario de Odoo (email). Si no se proporciona, usa .env
            password: API Key de Odoo. Si no se proporciona, usa .env
            url: URL de Odoo. Si no se proporciona, usa .env o DEFAULT_URL
            db: Base de datos de Odoo. Si no se proporciona, usa .env o DEFAULT_DB
        """
        self.url = url or os.getenv("ODOO_URL") or self.DEFAULT_URL
        self.db = db or os.getenv("ODOO_DB") or self.DEFAULT_DB
        
        # Usar credenciales proporcionadas o del .env
        self.username = username if username else os.getenv("ODOO_USER")
        self.password = password if password else os.getenv("ODOO_PASSWORD")
        
        if not all([self.url, self.db, self.username, self.password]):
            raise ValueError("Faltan credenciales de Odoo. Verificar .env o parámetros.")
        
        # Conectar
        self.common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
        self.uid = self.common.authenticate(self.db, self.username, self.password, {})
        
        if not self.uid:
            raise Exception("Error de autenticación con Odoo")
        
        self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
    
    def search(self, model: str, domain: List, limit: int = None, order: str = None) -> List[int]:
        """
        Busca registros en Odoo.
        
        Args:
            model: Nombre del modelo (ej: 'product.product')
            domain: Dominio de búsqueda
            limit: Límite de resultados
            order: Ordenamiento
            
        Returns:
            Lista de IDs encontrados
        """
        kwargs = {}
        if limit:
            kwargs['limit'] = limit
        if order:
            kwargs['order'] = order
            
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, 'search', [domain], kwargs
        )
    
    def read(self, model: str, ids: List[int], fields: List[str] = None) -> List[Dict]:
        """
        Lee registros de Odoo.
        
        Args:
            model: Nombre del modelo
            ids: Lista de IDs a leer
            fields: Campos a leer (None = todos)
            
        Returns:
            Lista de diccionarios con los datos
        """
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
            
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, 'read', [ids], kwargs
        )
    
    def search_read(self, model: str, domain: List, fields: List[str] = None, 
                    limit: int = None, order: str = None) -> List[Dict]:
        """
        Busca y lee registros en una sola llamada.
        
        Args:
            model: Nombre del modelo
            domain: Dominio de búsqueda
            fields: Campos a leer
            limit: Límite de resultados
            order: Ordenamiento
            
        Returns:
            Lista de diccionarios con los datos
        """
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        if limit:
            kwargs['limit'] = limit
        if order:
            kwargs['order'] = order
            
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, 'search_read', [domain], kwargs
        )
    
    def write(self, model: str, ids: List[int], vals: Dict) -> bool:
        """
        Actualiza registros en Odoo.
        
        Args:
            model: Nombre del modelo
            ids: Lista de IDs a actualizar
            vals: Diccionario con valores a escribir
            
        Returns:
            True si fue exitoso
        """
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, 'write', [ids, vals]
        )
    
    def execute(self, model: str, method: str, *args, **kwargs) -> Any:
        """
        Ejecuta un método genérico en Odoo.
        """
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, method, list(args), kwargs
        )
    
    # ============ Métodos de Consulta Paralela ============
    
    def parallel_search_read(self, queries: List[Dict], max_workers: int = 5) -> List[List[Dict]]:
        """
        Ejecuta múltiples search_read en paralelo usando ThreadPoolExecutor.
        
        Args:
            queries: Lista de diccionarios con parámetros de búsqueda:
                - model: str (requerido)
                - domain: List (requerido)
                - fields: List[str] (opcional)
                - limit: int (opcional)
                - order: str (opcional)
            max_workers: Número máximo de hilos (default: 5)
            
        Returns:
            Lista de resultados en el mismo orden que las queries
            
        Ejemplo:
            results = odoo.parallel_search_read([
                {"model": "product.product", "domain": [], "fields": ["name"]},
                {"model": "res.partner", "domain": [], "fields": ["name"]},
            ])
            products, partners = results
        """
        import concurrent.futures
        
        def execute_query(query: Dict) -> List[Dict]:
            return self.search_read(
                model=query['model'],
                domain=query.get('domain', []),
                fields=query.get('fields'),
                limit=query.get('limit'),
                order=query.get('order')
            )
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(execute_query, q) for q in queries]
            results = [f.result() for f in futures]
        
        return results
    
    def parallel_execute(self, calls: List[Dict], max_workers: int = 5) -> List[Any]:
        """
        Ejecuta múltiples métodos en paralelo.
        
        Args:
            calls: Lista de diccionarios con:
                - model: str
                - method: str
                - args: List (opcional)
                - kwargs: Dict (opcional)
            max_workers: Número máximo de hilos
            
        Returns:
            Lista de resultados en el mismo orden
        """
        import concurrent.futures
        
        def execute_call(call: Dict) -> Any:
            return self.execute(
                call['model'],
                call['method'],
                *call.get('args', []),
                **call.get('kwargs', {})
            )
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(execute_call, c) for c in calls]
            results = [f.result() for f in futures]
        
        return results


def get_odoo_client(username: str = None, password: str = None, 
                    url: str = None, db: str = None) -> OdooClient:
    """
    Factory function para obtener un cliente Odoo.
    """
    return OdooClient(username=username, password=password, url=url, db=db)
