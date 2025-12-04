"""
Cliente Odoo compartido usando XML-RPC.
Compatible con todos los dashboards del sistema.
"""
import xmlrpc.client
from typing import Optional, List, Dict, Any
import pandas as pd
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


class OdooClient:
    """
    Cliente XML-RPC para conectar con Odoo.
    Puede usar credenciales del .env o credenciales proporcionadas por el usuario.
    """
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        Inicializa el cliente Odoo.
        
        Args:
            username: Usuario de Odoo (email). Si no se proporciona, usa .env
            password: API Key de Odoo. Si no se proporciona, usa .env
        """
        self.url = os.getenv("ODOO_URL")
        self.db = os.getenv("ODOO_DB")
        
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
    
    def execute(self, model: str, method: str, *args, **kwargs) -> Any:
        """
        Ejecuta un método genérico en Odoo.
        """
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, method, list(args), kwargs
        )


def get_odoo_client(username: str = None, password: str = None) -> OdooClient:
    """
    Factory function para obtener un cliente Odoo.
    """
    return OdooClient(username=username, password=password)
