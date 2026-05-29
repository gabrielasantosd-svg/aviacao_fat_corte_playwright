"""
Script CLI para gerenciar API keys.
Uso: python manage_api_keys.py create "Nome da Key" --scopes jobs:read jobs:write
"""

import argparse
from datetime import datetime, timedelta

from infrastructure.persistence.models import ApiKeyModel
from infrastructure.persistence.postgres_job_repository import SessionLocal
from infrastructure.security import AuthService


def create_key(name: str, scopes: list[str], expires_days: int | None = None):
    """Cria uma nova API key."""
    db = SessionLocal()
    try:
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)

        key, api_key_model = AuthService.create_api_key_record(
            db=db, name=name, scopes=scopes, expires_at=expires_at
        )

        print("[OK] API key criada com sucesso!")
        print(f"[INFO] Key: {key}")
        print(f"[INFO] Nome: {api_key_model.name}")
        print(f"[INFO] Scopes: {', '.join(api_key_model.scopes)}")
        print(f"[INFO] Criada em: {api_key_model.created_at}")
        if expires_at:
            print(f"[INFO] Expira em: {expires_at}")
        print("\n[IMPORTANTE] Guarde esta key em local seguro. Ela nao sera exibida novamente!")
        print(f"\n[TESTE] curl -H 'X-API-Key: {key}' http://localhost:8000/health/deep")

    finally:
        db.close()


def list_keys():
    """Lista todas as API keys (sem mostrar a key em si)."""
    db = SessionLocal()
    try:
        keys = db.query(ApiKeyModel).order_by(ApiKeyModel.created_at.desc()).all()

        if not keys:
            print("Nenhuma API key encontrada.")
            return

        print(f"\n{'ID':<38} {'Nome':<25} {'Ativa':<8} {'Criada em':<20}")
        print("-" * 100)
        for key in keys:
            status = "Sim" if key.is_active else "Nao"
            created = key.created_at.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{key.id:<38} {key.name:<25} {status:<8} {created:<20}")

    finally:
        db.close()


def revoke_key(key_id: str):
    """Revoga (desativa) uma API key."""
    db = SessionLocal()
    try:
        api_key = db.query(ApiKeyModel).filter(ApiKeyModel.id == key_id).first()

        if not api_key:
            print(f"[ERRO] API key com ID {key_id} nao encontrada.")
            return

        api_key.is_active = False
        db.commit()

        print(f"[OK] API key '{api_key.name}' revogada com sucesso.")

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Gerenciador de API Keys")
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponíveis")

    # Create
    create_parser = subparsers.add_parser("create", help="Criar nova API key")
    create_parser.add_argument("name", help="Nome identificador da key")
    create_parser.add_argument(
        "--scopes",
        nargs="+",
        default=["jobs:read", "jobs:write"],
        help="Scopes (permissões) da key",
    )
    create_parser.add_argument(
        "--expires-days", type=int, help="Dias até expiração (opcional)"
    )

    # List
    subparsers.add_parser("list", help="Listar todas as API keys")

    # Revoke
    revoke_parser = subparsers.add_parser("revoke", help="Revogar (desativar) uma API key")
    revoke_parser.add_argument("key_id", help="ID da key a ser revogada")

    args = parser.parse_args()

    if args.command == "create":
        create_key(args.name, args.scopes, args.expires_days)
    elif args.command == "list":
        list_keys()
    elif args.command == "revoke":
        revoke_key(args.key_id)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
