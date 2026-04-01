"""CLI para sincronizar y administrar usuarios del portal de proveedores."""
from __future__ import annotations

import argparse

from backend.services.provider_portal_service import ProviderPortalAuthService


def main() -> None:
    parser = argparse.ArgumentParser(description="Administracion de usuarios del portal de proveedores")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("sync", help="Sincroniza proveedores MP desde Odoo")
    subparsers.add_parser("list", help="Lista usuarios portal")

    set_password_parser = subparsers.add_parser("set-password", help="Configura clave para un proveedor")
    set_password_parser.add_argument("--rut", required=True, help="RUT del proveedor")
    set_password_parser.add_argument("--password", required=True, help="Clave a configurar")
    set_password_parser.add_argument("--inactive", action="store_true", help="Deja usuario inactivo")

    args = parser.parse_args()

    if args.command == "sync":
        result = ProviderPortalAuthService.sync_users_from_odoo()
        print(result)
        return

    if args.command == "list":
        for user in ProviderPortalAuthService.list_users():
            print(
                f"partner_id={user.get('partner_id')} | rut={user.get('rut')} | "
                f"active={user.get('active')} | nombre={user.get('display_name')}"
            )
        return

    if args.command == "set-password":
        user = ProviderPortalAuthService.set_password(
            rut=args.rut,
            password=args.password,
            activate=not args.inactive,
        )
        print(
            f"Clave actualizada para {user.get('display_name')} "
            f"({user.get('rut')}) active={user.get('active')}"
        )


if __name__ == "__main__":
    main()
