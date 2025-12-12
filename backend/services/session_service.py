"""
Servicio de gestión de sesiones con tokens JWT.
Maneja expiración, inactividad y persistencia de sesiones.
"""
import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

# JWT con HMAC - sin dependencias externas pesadas
import hmac
import base64


# Configuración de sesiones
SESSION_MAX_AGE_HOURS = 8  # Expiración máxima de sesión
INACTIVITY_TIMEOUT_MINUTES = 30  # Timeout por inactividad
SECRET_KEY = os.getenv("SESSION_SECRET_KEY", secrets.token_hex(32))
SESSIONS_FILE = Path(__file__).parent.parent / "data" / "sessions.json"


def _ensure_sessions_file():
    """Asegura que el archivo de sesiones existe."""
    SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not SESSIONS_FILE.exists():
        SESSIONS_FILE.write_text("{}")


def _load_sessions() -> Dict[str, Any]:
    """Carga sesiones desde archivo."""
    _ensure_sessions_file()
    try:
        return json.loads(SESSIONS_FILE.read_text())
    except:
        return {}


def _save_sessions(sessions: Dict[str, Any]):
    """Guarda sesiones en archivo."""
    _ensure_sessions_file()
    SESSIONS_FILE.write_text(json.dumps(sessions, indent=2, default=str))


def _generate_token(data: Dict[str, Any]) -> str:
    """Genera un token simple con HMAC."""
    payload = json.dumps(data, sort_keys=True, default=str)
    signature = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    token_data = base64.urlsafe_b64encode(payload.encode()).decode()
    return f"{token_data}.{signature}"


def _verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verifica y decodifica un token."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        
        token_data, signature = parts
        payload = base64.urlsafe_b64decode(token_data.encode()).decode()
        
        expected_sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        
        return json.loads(payload)
    except:
        return None


class SessionService:
    """Servicio de gestión de sesiones."""
    
    @staticmethod
    def create_session(username: str, uid: int, odoo_password: str) -> str:
        """
        Crea una nueva sesión y retorna el token.
        El password se encripta con el token para uso interno.
        """
        session_id = secrets.token_hex(16)
        now = datetime.now()
        
        # Encriptar password con session_id
        password_key = hashlib.sha256((session_id + SECRET_KEY).encode()).hexdigest()[:32]
        encrypted_password = base64.urlsafe_b64encode(
            bytes(a ^ b for a, b in zip(odoo_password.encode(), (password_key * 10).encode()))
        ).decode()
        
        session_data = {
            "session_id": session_id,
            "username": username,
            "uid": uid,
            "created_at": now.isoformat(),
            "last_activity": now.isoformat(),
            "expires_at": (now + timedelta(hours=SESSION_MAX_AGE_HOURS)).isoformat(),
            "encrypted_password": encrypted_password
        }
        
        # Guardar sesión
        sessions = _load_sessions()
        sessions[session_id] = session_data
        _save_sessions(sessions)
        
        # Generar token para el cliente
        token_payload = {
            "session_id": session_id,
            "username": username,
            "uid": uid,
            "exp": (now + timedelta(hours=SESSION_MAX_AGE_HOURS)).isoformat()
        }
        
        return _generate_token(token_payload)
    
    @staticmethod
    def validate_session(token: str) -> Optional[Dict[str, Any]]:
        """
        Valida un token y retorna los datos de sesión si es válido.
        También verifica expiración e inactividad.
        """
        payload = _verify_token(token)
        if not payload:
            return None
        
        session_id = payload.get("session_id")
        if not session_id:
            return None
        
        sessions = _load_sessions()
        session = sessions.get(session_id)
        
        if not session:
            return None
        
        now = datetime.now()
        
        # Verificar expiración máxima
        expires_at = datetime.fromisoformat(session["expires_at"])
        if now > expires_at:
            SessionService.invalidate_session(token)
            return None
        
        # Verificar inactividad
        last_activity = datetime.fromisoformat(session["last_activity"])
        inactivity_limit = last_activity + timedelta(minutes=INACTIVITY_TIMEOUT_MINUTES)
        if now > inactivity_limit:
            SessionService.invalidate_session(token)
            return None
        
        return {
            "username": session["username"],
            "uid": session["uid"],
            "session_id": session_id,
            "created_at": session["created_at"],
            "expires_at": session["expires_at"],
            "last_activity": session["last_activity"]
        }
    
    @staticmethod
    def refresh_activity(token: str) -> bool:
        """Actualiza el timestamp de última actividad."""
        payload = _verify_token(token)
        if not payload:
            return False
        
        session_id = payload.get("session_id")
        sessions = _load_sessions()
        
        if session_id not in sessions:
            return False
        
        sessions[session_id]["last_activity"] = datetime.now().isoformat()
        _save_sessions(sessions)
        return True
    
    @staticmethod
    def get_odoo_credentials(token: str) -> Optional[tuple]:
        """
        Obtiene las credenciales de Odoo para una sesión válida.
        Retorna (username, password) o None.
        """
        payload = _verify_token(token)
        if not payload:
            return None
        
        session_id = payload.get("session_id")
        sessions = _load_sessions()
        session = sessions.get(session_id)
        
        if not session:
            return None
        
        # Desencriptar password
        try:
            password_key = hashlib.sha256((session_id + SECRET_KEY).encode()).hexdigest()[:32]
            encrypted = base64.urlsafe_b64decode(session["encrypted_password"].encode())
            password = bytes(a ^ b for a, b in zip(encrypted, (password_key * 10).encode())).decode()
            return (session["username"], password)
        except:
            return None
    
    @staticmethod
    def invalidate_session(token: str) -> bool:
        """Invalida/cierra una sesión."""
        payload = _verify_token(token)
        if not payload:
            return False
        
        session_id = payload.get("session_id")
        sessions = _load_sessions()
        
        if session_id in sessions:
            del sessions[session_id]
            _save_sessions(sessions)
            return True
        
        return False
    
    @staticmethod
    def cleanup_expired_sessions():
        """Limpia sesiones expiradas del almacenamiento."""
        sessions = _load_sessions()
        now = datetime.now()
        
        to_delete = []
        for session_id, session in sessions.items():
            expires_at = datetime.fromisoformat(session["expires_at"])
            last_activity = datetime.fromisoformat(session["last_activity"])
            inactivity_limit = last_activity + timedelta(minutes=INACTIVITY_TIMEOUT_MINUTES)
            
            if now > expires_at or now > inactivity_limit:
                to_delete.append(session_id)
        
        for session_id in to_delete:
            del sessions[session_id]
        
        if to_delete:
            _save_sessions(sessions)
        
        return len(to_delete)
    
    @staticmethod
    def get_session_info(token: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de la sesión incluyendo tiempo restante."""
        session = SessionService.validate_session(token)
        if not session:
            return None
        
        now = datetime.now()
        expires_at = datetime.fromisoformat(session["expires_at"])
        last_activity = datetime.fromisoformat(session["last_activity"])
        
        time_remaining = expires_at - now
        inactivity_remaining = (last_activity + timedelta(minutes=INACTIVITY_TIMEOUT_MINUTES)) - now
        
        return {
            **session,
            "time_remaining_seconds": max(0, int(time_remaining.total_seconds())),
            "inactivity_remaining_seconds": max(0, int(inactivity_remaining.total_seconds())),
            "time_remaining_formatted": str(time_remaining).split(".")[0] if time_remaining.total_seconds() > 0 else "0:00:00",
        }
