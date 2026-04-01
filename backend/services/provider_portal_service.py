"""Servicios para el portal de proveedores."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.config.settings import settings
from backend.services.recepcion_service import get_recepciones_mp
from backend.services.session_service import SessionService
from shared.odoo_client import OdooClient


PROVIDER_USERS_FILE = Path(__file__).parent.parent / "data" / "provider_portal_users.json"
PROVIDER_SESSIONS_FILE = Path(__file__).parent.parent / "data" / "provider_portal_sessions.json"
PROVIDER_SESSION_HOURS = 12
PROVIDER_INACTIVITY_MINUTES = 60
PROVIDER_SECRET_KEY = os.getenv(
    "PROVIDER_PORTAL_SECRET_KEY",
    os.getenv("SESSION_SECRET_KEY", secrets.token_hex(32)),
)


def _is_development() -> bool:
    return os.getenv("ENV", "production") == "development"


def _ensure_json_file(path: Path, default_content: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(default_content, indent=2), encoding="utf-8")


def _load_json(path: Path, default_content: Any) -> Any:
    _ensure_json_file(path, default_content)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default_content


def _save_json(path: Path, data: Any) -> None:
    _ensure_json_file(path, data)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")


def _normalize_rut(rut: str) -> str:
    raw = (rut or "").strip().upper()
    cleaned = "".join(ch for ch in raw if ch.isalnum())
    if len(cleaned) < 2:
        return cleaned
    return f"{cleaned[:-1]}-{cleaned[-1]}"


def _date_bounds(fecha_inicio: str, fecha_fin: str) -> Tuple[str, str, date, date]:
    start_date = date.fromisoformat(str(fecha_inicio)[:10])
    end_date = date.fromisoformat(str(fecha_fin)[:10])
    return (
        f"{start_date.isoformat()} 00:00:00",
        f"{end_date.isoformat()} 23:59:59",
        start_date,
        end_date,
    )


def _password_hash(password: str, salt: str) -> str:
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        120000,
    )
    return derived.hex()


def _build_token(payload: Dict[str, Any]) -> str:
    payload_str = json.dumps(payload, sort_keys=True, default=str)
    signature = hmac.new(
        PROVIDER_SECRET_KEY.encode("utf-8"),
        payload_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    encoded = base64.urlsafe_b64encode(payload_str.encode("utf-8")).decode("utf-8")
    return f"{encoded}.{signature}"


def _decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        encoded, signature = token.split(".", 1)
        payload_str = base64.urlsafe_b64decode(encoded.encode("utf-8")).decode("utf-8")
        expected_signature = hmac.new(
            PROVIDER_SECRET_KEY.encode("utf-8"),
            payload_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            return None
        return json.loads(payload_str)
    except Exception:
        return None


def _technical_odoo_client(
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> OdooClient:
    username = username or settings.ODOO_USER or os.getenv("ODOO_USER")
    password = password or settings.ODOO_PASSWORD or os.getenv("ODOO_PASSWORD")
    if not username or not password:
        raise ValueError(
            "Faltan ODOO_USER y ODOO_PASSWORD en el entorno para el portal de proveedores"
        )
    return OdooClient(username=username, password=password)


class ProviderPortalAuthService:
    """Autenticacion local del portal de proveedores."""

    @staticmethod
    def _load_users() -> List[Dict[str, Any]]:
        users = _load_json(PROVIDER_USERS_FILE, [])
        return users if isinstance(users, list) else []

    @staticmethod
    def _save_users(users: List[Dict[str, Any]]) -> None:
        _save_json(PROVIDER_USERS_FILE, users)

    @staticmethod
    def _load_sessions() -> Dict[str, Any]:
        sessions = _load_json(PROVIDER_SESSIONS_FILE, {})
        return sessions if isinstance(sessions, dict) else {}

    @staticmethod
    def _save_sessions(sessions: Dict[str, Any]) -> None:
        _save_json(PROVIDER_SESSIONS_FILE, sessions)

    @staticmethod
    def _find_user_by_rut(rut: str) -> Optional[Dict[str, Any]]:
        rut_normalized = _normalize_rut(rut)
        for user in ProviderPortalAuthService._load_users():
            if _normalize_rut(user.get("rut", "")) == rut_normalized:
                return user
        return None

    @staticmethod
    def _find_user_by_partner_id(partner_id: int) -> Optional[Dict[str, Any]]:
        for user in ProviderPortalAuthService._load_users():
            if int(user.get("partner_id", 0) or 0) == int(partner_id):
                return user
        return None

    @staticmethod
    def _issue_session(user: Dict[str, Any], internal_session_token: str = "") -> Dict[str, Any]:
        now = datetime.now()
        session_id = secrets.token_hex(16)
        session = {
            "session_id": session_id,
            "partner_id": user["partner_id"],
            "rut": user["rut"],
            "display_name": user.get("display_name") or user.get("name") or "Proveedor",
            "created_at": now.isoformat(),
            "last_activity": now.isoformat(),
            "expires_at": (now + timedelta(hours=PROVIDER_SESSION_HOURS)).isoformat(),
        }
        if internal_session_token and _is_development():
            session["internal_session_token"] = internal_session_token
        sessions = ProviderPortalAuthService._load_sessions()
        sessions[session_id] = session
        ProviderPortalAuthService._save_sessions(sessions)

        token = _build_token(
            {
                "session_id": session_id,
                "partner_id": user["partner_id"],
                "rut": user["rut"],
                "exp": session["expires_at"],
            }
        )
        return {"token": token, **session}

    @staticmethod
    def login(rut: str, password: str) -> Dict[str, Any]:
        user = ProviderPortalAuthService._find_user_by_rut(rut)
        if not user:
            raise ValueError("Proveedor no encontrado en el portal")
        if not user.get("active"):
            raise ValueError("Usuario portal inactivo")
        salt = user.get("password_salt")
        password_hash = user.get("password_hash")
        if not salt or not password_hash:
            raise ValueError("Usuario sin clave configurada")
        if _password_hash(password, salt) != password_hash:
            raise ValueError("Credenciales invalidas")
        return ProviderPortalAuthService._issue_session(user)

    @staticmethod
    def dev_auto_login(
        partner_id: Optional[int] = None,
        rut: Optional[str] = None,
        internal_session_token: str = "",
    ) -> Dict[str, Any]:
        runtime_username = ""
        runtime_password = ""
        if internal_session_token:
            creds = SessionService.get_odoo_credentials(internal_session_token)
            if creds:
                runtime_username, runtime_password = creds

        users = ProviderPortalAuthService._load_users()
        if not users and runtime_username and runtime_password:
            try:
                ProviderPortalAuthService.sync_users_from_odoo(
                    username=runtime_username,
                    password=runtime_password,
                )
            except Exception:
                pass
            users = ProviderPortalAuthService._load_users()

        if not users:
            try:
                ProviderPortalAuthService.sync_users_from_odoo()
            except Exception:
                # En dev permitimos iniciar sin Odoo configurado.
                pass
            users = ProviderPortalAuthService._load_users()
        if not users and _is_development():
            users = [
                {
                    "partner_id": 0,
                    "rut": "DEV-AUTO",
                    "display_name": "Proveedor Demo Dev",
                    "email": "",
                    "phone": "",
                    "city": "",
                    "active": True,
                    "password_salt": "",
                    "password_hash": "",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                }
            ]
            ProviderPortalAuthService._save_users(users)
        if not users:
            raise ValueError("No hay proveedores disponibles para auto-login")

        selected: Optional[Dict[str, Any]] = None
        if rut:
            selected = ProviderPortalAuthService._find_user_by_rut(rut)
        if partner_id:
            selected = ProviderPortalAuthService._find_user_by_partner_id(int(partner_id))

        if not selected:
            selected = next((u for u in users if u.get("active")), None)
        if not selected:
            selected = users[0]

        if not selected.get("active"):
            selected["active"] = True
            selected["updated_at"] = datetime.now().isoformat()
            ProviderPortalAuthService._save_users(users)

        return ProviderPortalAuthService._issue_session(
            selected,
            internal_session_token=internal_session_token,
        )

    @staticmethod
    def validate_session(token: str) -> Optional[Dict[str, Any]]:
        payload = _decode_token(token)
        if not payload:
            return None
        session_id = payload.get("session_id")
        sessions = ProviderPortalAuthService._load_sessions()
        session = sessions.get(session_id)
        if not session:
            return None

        now = datetime.now()
        expires_at = datetime.fromisoformat(session["expires_at"])
        last_activity = datetime.fromisoformat(session["last_activity"])
        if now > expires_at or now > last_activity + timedelta(minutes=PROVIDER_INACTIVITY_MINUTES):
            sessions.pop(session_id, None)
            ProviderPortalAuthService._save_sessions(sessions)
            return None
        return session

    @staticmethod
    def refresh_session(token: str) -> Optional[Dict[str, Any]]:
        session = ProviderPortalAuthService.validate_session(token)
        if not session:
            return None
        sessions = ProviderPortalAuthService._load_sessions()
        session_id = session["session_id"]
        sessions[session_id]["last_activity"] = datetime.now().isoformat()
        ProviderPortalAuthService._save_sessions(sessions)
        return sessions[session_id]

    @staticmethod
    def logout(token: str) -> bool:
        payload = _decode_token(token)
        if not payload:
            return False
        session_id = payload.get("session_id")
        sessions = ProviderPortalAuthService._load_sessions()
        if session_id in sessions:
            sessions.pop(session_id, None)
            ProviderPortalAuthService._save_sessions(sessions)
            return True
        return False

    @staticmethod
    def set_password(rut: str, password: str, activate: bool = True) -> Dict[str, Any]:
        users = ProviderPortalAuthService._load_users()
        normalized = _normalize_rut(rut)
        salt = secrets.token_hex(16)
        password_hash = _password_hash(password, salt)
        for user in users:
            if _normalize_rut(user.get("rut", "")) == normalized:
                user["password_salt"] = salt
                user["password_hash"] = password_hash
                user["active"] = activate
                user["updated_at"] = datetime.now().isoformat()
                ProviderPortalAuthService._save_users(users)
                return user
        raise ValueError("RUT no encontrado en usuarios portal")

    @staticmethod
    def sync_users_from_odoo(
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> Dict[str, Any]:
        odoo = _technical_odoo_client(username=username, password=password)
        pickings = odoo.search_read(
            "stock.picking",
            [
                ("picking_type_id", "in", [1, 151, 164, 217]),
                ("state", "=", "done"),
                ("partner_id", "!=", False),
                ("x_studio_categora_de_producto", "=", "MP"),
            ],
            ["partner_id"],
            limit=10000,
        )
        partner_ids = sorted(
            {
                partner[0]
                for item in pickings
                for partner in [item.get("partner_id")]
                if isinstance(partner, (list, tuple)) and partner and partner[0]
            }
        )
        if not partner_ids:
            return {"created": 0, "updated": 0, "total": 0}

        partners = odoo.read(
            "res.partner",
            partner_ids,
            ["id", "name", "vat", "email", "phone", "mobile", "city"],
        )
        users = ProviderPortalAuthService._load_users()
        users_by_partner = {int(user.get("partner_id", 0)): user for user in users}

        created = 0
        updated = 0
        for partner in partners:
            rut = _normalize_rut(partner.get("vat") or "")
            if not rut:
                continue
            existing = users_by_partner.get(partner["id"])
            base_record = {
                "partner_id": partner["id"],
                "rut": rut,
                "display_name": partner.get("name") or "Proveedor",
                "email": partner.get("email") or "",
                "phone": partner.get("phone") or partner.get("mobile") or "",
                "city": partner.get("city") or "",
                "updated_at": datetime.now().isoformat(),
            }
            if existing:
                existing.update(base_record)
                existing.setdefault("active", False)
                updated += 1
            else:
                users.append(
                    {
                        **base_record,
                        "active": False,
                        "password_salt": "",
                        "password_hash": "",
                        "created_at": datetime.now().isoformat(),
                    }
                )
                created += 1

        users.sort(key=lambda item: (item.get("display_name") or "").upper())
        ProviderPortalAuthService._save_users(users)
        return {"created": created, "updated": updated, "total": len(users)}

    @staticmethod
    def list_users() -> List[Dict[str, Any]]:
        return ProviderPortalAuthService._load_users()


class ProviderPortalDataService:
    """Datos visibles por un proveedor autenticado."""

    def __init__(self, provider_session: Optional[Dict[str, Any]] = None) -> None:
        self.demo_mode = False
        try:
            self.odoo = _technical_odoo_client()
            self.odoo_username = self.odoo.username
            self.odoo_password = self.odoo.password
        except Exception:
            session_token = (provider_session or {}).get("internal_session_token")
            if session_token:
                creds = SessionService.get_odoo_credentials(session_token)
                if creds:
                    username, password = creds
                    self.odoo = _technical_odoo_client(username=username, password=password)
                    self.odoo_username = self.odoo.username
                    self.odoo_password = self.odoo.password
                    return
            if not _is_development():
                raise
            self.demo_mode = True
            self.odoo = None
            self.odoo_username = ""
            self.odoo_password = ""

    def get_partner_profile(self, partner_id: int) -> Dict[str, Any]:
        if self.demo_mode:
            user = ProviderPortalAuthService._find_user_by_partner_id(partner_id)
            return {
                "partner_id": int(user.get("partner_id", partner_id) if user else partner_id),
                "name": (user or {}).get("display_name") or "Proveedor Demo",
                "rut": (user or {}).get("rut") or "DEV-AUTO",
                "email": (user or {}).get("email") or "",
                "phone": (user or {}).get("phone") or "",
                "city": (user or {}).get("city") or "",
            }
        partner = self.odoo.read(
            "res.partner",
            [partner_id],
            ["id", "name", "vat", "email", "phone", "mobile", "city"],
        )
        if not partner:
            raise ValueError("Proveedor no encontrado en Odoo")
        info = partner[0]
        return {
            "partner_id": info["id"],
            "name": info.get("name") or "Proveedor",
            "rut": _normalize_rut(info.get("vat") or ""),
            "email": info.get("email") or "",
            "phone": info.get("phone") or info.get("mobile") or "",
            "city": info.get("city") or "",
        }

    def get_recepciones(self, partner_id: int, fecha_inicio: str, fecha_fin: str) -> List[Dict[str, Any]]:
        if self.demo_mode:
            return []
        fecha_inicio_dt, fecha_fin_dt, start_date, end_date = _date_bounds(fecha_inicio, fecha_fin)
        recepciones = get_recepciones_mp(
            self.odoo_username,
            self.odoo_password,
            fecha_inicio_dt,
            fecha_fin_dt,
            productor_id=partner_id,
            solo_hechas=True,
        )
        if not recepciones:
            return []

        # Filtro estricto final por fecha para evitar cualquier desborde por datetime en Odoo.
        recepciones_filtradas: List[Dict[str, Any]] = []
        for item in recepciones:
            raw_fecha = str(item.get("fecha") or "")[:10]
            if not raw_fecha:
                continue
            try:
                fecha_item = date.fromisoformat(raw_fecha)
            except Exception:
                continue
            if start_date <= fecha_item <= end_date:
                recepciones_filtradas.append(item)
        recepciones = recepciones_filtradas
        if not recepciones:
            return []

        picking_ids = [item["id"] for item in recepciones if item.get("id")]
        quality_checks = self.odoo.search_read(
            "quality.check",
            [("picking_id", "in", picking_ids)],
            ["id", "name", "picking_id", "quality_state", "point_id", "create_date"],
            limit=10000,
        ) if picking_ids else []
        qc_by_picking: Dict[int, List[Dict[str, Any]]] = {}
        qc_ids: List[int] = []
        for qc in quality_checks:
            picking = qc.get("picking_id")
            picking_id = picking[0] if isinstance(picking, (list, tuple)) and picking else None
            if not picking_id:
                continue
            qc_by_picking.setdefault(picking_id, []).append(
                {
                    "id": qc.get("id"),
                    "name": qc.get("name") or "QC",
                    "quality_state": qc.get("quality_state") or "none",
                    "point": qc.get("point_id", [None, ""])[1] if qc.get("point_id") else "",
                    "create_date": qc.get("create_date") or "",
                }
            )
            qc_ids.append(qc.get("id"))

        attachments = self._get_attachments_for_recepciones(picking_ids, qc_ids)
        attachments_by_recepcion: Dict[int, List[Dict[str, Any]]] = {}
        photos_by_recepcion: Dict[int, List[Dict[str, Any]]] = {}
        for attachment in attachments:
            recepcion_id = attachment.pop("recepcion_id")
            attachments_by_recepcion.setdefault(recepcion_id, []).append(attachment)
            if attachment.get("mimetype", "").startswith("image/"):
                photos_by_recepcion.setdefault(recepcion_id, []).append(attachment)

        resultado = []
        for item in recepciones:
            rec_id = item.get("id")
            fotos = photos_by_recepcion.get(rec_id, [])
            documentos = attachments_by_recepcion.get(rec_id, [])
            resultado.append(
                {
                    **item,
                    "quality_checks": qc_by_picking.get(rec_id, []),
                    "fotos": fotos,
                    "documentos": documentos,
                    "cantidad_fotos": len(fotos),
                    "cantidad_documentos": len(documentos),
                }
            )
        return resultado

    def get_financial_documents(
        self,
        partner_id: int,
        fecha_inicio: str,
        fecha_fin: str,
        oc_references: Optional[List[str]] = None,
        limit: int = 500,
    ) -> Dict[str, List[Dict[str, Any]]]:
        if self.demo_mode:
            return {"proformas": [], "facturas": []}
        fecha_inicio_dt, fecha_fin_dt, _, _ = _date_bounds(fecha_inicio, fecha_fin)
        docs = self.odoo.search_read(
            "account.move",
            [
                ("partner_id", "=", partner_id),
                ("move_type", "=", "in_invoice"),
                ("state", "in", ["draft", "posted", "cancel"]),
                ("invoice_date", ">=", fecha_inicio_dt[:10]),
                ("invoice_date", "<=", fecha_fin_dt[:10]),
            ],
            [
                "id",
                "name",
                "ref",
                "invoice_date",
                "invoice_origin",
                "amount_total",
                "currency_id",
                "state",
                "payment_state",
            ],
            limit=limit,
            order="invoice_date desc, create_date desc",
        )
        oc_refs = [(ref or "").strip().upper() for ref in (oc_references or []) if (ref or "").strip()]
        if oc_refs:
            docs = [
                doc
                for doc in docs
                if any(ref in ((doc.get("invoice_origin") or "").upper()) for ref in oc_refs)
            ]

        invoice_ids = [doc["id"] for doc in docs]
        attachment_map = self._get_attachments_for_account_moves(invoice_ids)
        proformas: List[Dict[str, Any]] = []
        facturas: List[Dict[str, Any]] = []
        for doc in docs:
            row = {
                "id": doc["id"],
                "name": doc.get("name") or "Sin numero",
                "ref": doc.get("ref") or "",
                "invoice_date": doc.get("invoice_date") or "",
                "invoice_origin": doc.get("invoice_origin") or "",
                "amount_total": doc.get("amount_total") or 0,
                "currency": doc.get("currency_id", [None, "CLP"])[1] if doc.get("currency_id") else "CLP",
                "state": doc.get("state") or "draft",
                "payment_state": doc.get("payment_state") or "",
                "attachments": attachment_map.get(doc["id"], []),
            }
            if row["state"] == "draft":
                proformas.append(row)
            else:
                facturas.append(row)
        return {"proformas": proformas, "facturas": facturas}

    def get_dashboard(self, partner_id: int, fecha_inicio: str, fecha_fin: str) -> Dict[str, Any]:
        partner = self.get_partner_profile(partner_id)
        recepciones = self.get_recepciones(partner_id, fecha_inicio, fecha_fin)
        oc_refs = [item.get("oc_asociada", "") for item in recepciones if item.get("oc_asociada")]
        financial = self.get_financial_documents(partner_id, fecha_inicio, fecha_fin, oc_references=oc_refs)
        total_kg = sum(item.get("kg_recepcionados", 0) or 0 for item in recepciones)
        total_fotos = sum(item.get("cantidad_fotos", 0) for item in recepciones)
        total_guias = len({item.get("guia_despacho") for item in recepciones if item.get("guia_despacho")})
        quality_pass = sum(1 for item in recepciones if item.get("quality_state") == "pass")
        quality_fail = sum(1 for item in recepciones if item.get("quality_state") == "fail")
        return {
            "partner": partner,
            "summary": {
                "recepciones": len(recepciones),
                "kg_recepcionados": round(total_kg, 2),
                "guias": total_guias,
                "fotos": total_fotos,
                "quality_pass": quality_pass,
                "quality_fail": quality_fail,
                "proformas": len(financial["proformas"]),
                "facturas": len(financial["facturas"]),
            },
            "recepciones": recepciones,
            **financial,
        }

    def get_attachment_content(self, partner_id: int, attachment_id: int) -> Tuple[bytes, Dict[str, Any]]:
        if self.demo_mode:
            raise ValueError("Adjuntos no disponibles en modo dev sin Odoo")
        attachment_data = self.odoo.read(
            "ir.attachment",
            [attachment_id],
            ["id", "name", "datas", "mimetype", "res_model", "res_id"],
        )
        if not attachment_data:
            raise ValueError("Adjunto no encontrado")
        attachment = attachment_data[0]
        self._assert_attachment_access(partner_id, attachment)
        raw = base64.b64decode((attachment.get("datas") or "").encode("utf-8"))
        return raw, {
            "name": attachment.get("name") or f"attachment_{attachment_id}",
            "mimetype": attachment.get("mimetype") or "application/octet-stream",
        }

    def _get_attachments_for_recepciones(self, picking_ids: List[int], qc_ids: List[int]) -> List[Dict[str, Any]]:
        if not picking_ids and not qc_ids:
            return []
        domain: List[Any] = []
        if picking_ids and qc_ids:
            domain = [
                "|",
                "&", ("res_model", "=", "stock.picking"), ("res_id", "in", picking_ids),
                "&", ("res_model", "=", "quality.check"), ("res_id", "in", qc_ids),
            ]
        elif picking_ids:
            domain = [("res_model", "=", "stock.picking"), ("res_id", "in", picking_ids)]
        else:
            domain = [("res_model", "=", "quality.check"), ("res_id", "in", qc_ids)]

        attachments = self.odoo.search_read(
            "ir.attachment",
            domain,
            ["id", "name", "mimetype", "res_model", "res_id", "create_date"],
            limit=10000,
            order="create_date desc",
        )
        qc_to_picking = {}
        if qc_ids:
            quality_checks = self.odoo.read("quality.check", qc_ids, ["id", "picking_id"])
            for qc in quality_checks:
                picking = qc.get("picking_id")
                qc_to_picking[qc["id"]] = picking[0] if isinstance(picking, (list, tuple)) and picking else None

        result = []
        for attachment in attachments:
            res_model = attachment.get("res_model")
            res_id = attachment.get("res_id")
            recepcion_id = res_id if res_model == "stock.picking" else qc_to_picking.get(res_id)
            if not recepcion_id:
                continue
            result.append(
                {
                    "id": attachment["id"],
                    "name": attachment.get("name") or "Adjunto",
                    "mimetype": attachment.get("mimetype") or "application/octet-stream",
                    "res_model": res_model,
                    "res_id": res_id,
                    "create_date": attachment.get("create_date") or "",
                    "recepcion_id": recepcion_id,
                }
            )
        return result

    def _get_attachments_for_account_moves(self, invoice_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
        if not invoice_ids:
            return {}
        attachments = self.odoo.search_read(
            "ir.attachment",
            [("res_model", "=", "account.move"), ("res_id", "in", invoice_ids)],
            ["id", "name", "mimetype", "res_id", "create_date"],
            limit=10000,
            order="create_date desc",
        )
        result: Dict[int, List[Dict[str, Any]]] = {}
        for attachment in attachments:
            invoice_id = attachment.get("res_id")
            result.setdefault(invoice_id, []).append(
                {
                    "id": attachment["id"],
                    "name": attachment.get("name") or "Documento",
                    "mimetype": attachment.get("mimetype") or "application/octet-stream",
                    "create_date": attachment.get("create_date") or "",
                }
            )
        return result

    def _assert_attachment_access(self, partner_id: int, attachment: Dict[str, Any]) -> None:
        res_model = attachment.get("res_model")
        res_id = attachment.get("res_id")
        if res_model == "account.move":
            invoices = self.odoo.read("account.move", [res_id], ["partner_id"])
            invoice_partner = invoices[0].get("partner_id") if invoices else None
            access_partner_id = invoice_partner[0] if isinstance(invoice_partner, (list, tuple)) and invoice_partner else None
            if access_partner_id != partner_id:
                raise ValueError("Sin acceso al adjunto")
            return
        if res_model == "stock.picking":
            pickings = self.odoo.read("stock.picking", [res_id], ["partner_id"])
            picking_partner = pickings[0].get("partner_id") if pickings else None
            access_partner_id = picking_partner[0] if isinstance(picking_partner, (list, tuple)) and picking_partner else None
            if access_partner_id != partner_id:
                raise ValueError("Sin acceso al adjunto")
            return
        if res_model == "quality.check":
            checks = self.odoo.read("quality.check", [res_id], ["picking_id"])
            if not checks:
                raise ValueError("Sin acceso al adjunto")
            picking = checks[0].get("picking_id")
            picking_id = picking[0] if isinstance(picking, (list, tuple)) and picking else None
            if not picking_id:
                raise ValueError("Sin acceso al adjunto")
            pickings = self.odoo.read("stock.picking", [picking_id], ["partner_id"])
            picking_partner = pickings[0].get("partner_id") if pickings else None
            access_partner_id = picking_partner[0] if isinstance(picking_partner, (list, tuple)) and picking_partner else None
            if access_partner_id != partner_id:
                raise ValueError("Sin acceso al adjunto")
            return
        raise ValueError("Modelo de adjunto no permitido")
