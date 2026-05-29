#!/usr/bin/env python
"""
Script para inicializar o banco de dados e criar primeira API key.
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.persistence.postgres_job_repository import PostgresJobRepository
from infrastructure.security import AuthService
from infrastructure.persistence.models import Base
from infrastructure.persistence.postgres_job_repository import engine, SessionLocal


def init_database():
    """Cria todas as tabelas no banco de dados."""
    print("🔄 Criando schema do banco de dados...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Schema criado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao criar schema: {e}")
        sys.exit(1)


def create_initial_api_key():
    """Cria uma API key inicial para testes."""
    print("\n🔐 Criando API key inicial...")
    db = SessionLocal()
    try:
        key, api_key_model = AuthService.create_api_key_record(
            db=db,
            name="Initial Development Key",
            scopes=["jobs:read", "jobs:write"],
            expires_at=None,
        )

        print("✅ API Key criada com sucesso!")
        print(f"\n🔑 API Key: {key}")
        print(f"📝 Nome: {api_key_model.name}")
        print(f"🔒 Scopes: {', '.join(api_key_model.scopes)}")
        print("\n⚠️  IMPORTANTE: Guarde esta key em local seguro!")
        print(f"\n🧪 Teste com:")
        print(f"curl -H 'X-API-Key: {key}' http://localhost:8000/health/deep")
        print(f"\n💾 Salve no .env:")
        print(f"INITIAL_API_KEY={key}")

    except Exception as e:
        print(f"❌ Erro ao criar API key: {e}")
        sys.exit(1)
    finally:
        db.close()


def main():
    print("=" * 70)
    print("  INICIALIZADOR DO BANCO DE DADOS - GSFAT Automation")
    print("=" * 70)

    # 1. Criar schema
    init_database()

    # 2. Criar API key inicial
    create_initial_api_key()

    print("\n" + "=" * 70)
    print("✨ Inicialização concluída! Próximos passos:")
    print("=" * 70)
    print("1. Inicie a API: uvicorn presentation.api.main:app --reload")
    print("2. Inicie o worker: celery -A workers.celery_app worker -l info -P solo")
    print("3. Acesse a documentação: http://localhost:8000/docs")
    print("=" * 70)


if __name__ == "__main__":
    main()
