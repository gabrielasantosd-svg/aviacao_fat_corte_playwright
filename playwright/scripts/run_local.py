"""
run_local.py — executa um workflow diretamente, sem Celery nem Redis.
Ideal para desenvolvimento e testes locais.

Uso:
    python run_local.py
    python run_local.py --workflow faturar_pedido
"""

import argparse
import logging
import os
import sys
import uuid

# Garante que o diretório do projeto está no path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Configuração de logging ───────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
log_format = "%(asctime)s %(levelname)-8s %(name)s | %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.StreamHandler(sys.stdout),  # console
        logging.FileHandler("logs/run_local.log", encoding="utf-8"),  # arquivo
    ],
)
logging.getLogger("playwright").setLevel(logging.WARNING)  # silencia spam do Playwright
logging.getLogger("asyncio").setLevel(logging.WARNING)

from actions import ACTION_REGISTRY
from application.use_cases import WorkflowRunnerUseCase
from domain.entities import Job
from infrastructure.browser import PlaywrightSession
from infrastructure.persistence import SQLiteJobRepository
from infrastructure.screens import SCREEN_HANDLER_REGISTRY
from infrastructure.specs import YamlWorkflowSpecRepository
from settings import settings


def main():
    parser = argparse.ArgumentParser(description="POC GSFAT — runner local")
    parser.add_argument("--workflow", default="faturar_pedido", help="ID do workflow YAML")
    parser.add_argument("--headless", action="store_true", help="Rodar browser em modo headless")
    parser.add_argument(
        "--keep-open", action="store_true", help="Manter navegador aberto após execução"
    )
    args = parser.parse_args()

    # Validações básicas
    if not settings.PROTHEUS_USER:
        print("[ERRO] PROTHEUS_USER não definido no .env")
        sys.exit(1)
    if not settings.PROTHEUS_PASSWORD:
        print("[ERRO] PROTHEUS_PASSWORD não definido no .env")
        sys.exit(1)

    job_id = str(uuid.uuid4())
    print(f"\n{'=' * 55}")
    print("  POC GSFAT — Execução Local")
    print(f"{'=' * 55}")
    print(f"  Workflow : {args.workflow}")
    print(f"  Job ID   : {job_id}")
    print(f"  URL      : {settings.PROTHEUS_URL}")
    print(f"  Usuário  : {settings.PROTHEUS_USER}")
    print(f"  Headless : {args.headless}")
    print(f"  Keep Open: {args.keep_open}")
    print(f"{'=' * 55}\n")

    # Cria as pastas necessárias
    os.makedirs(settings.SCREENSHOTS_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(settings.LOG_DB_PATH), exist_ok=True)

    # Monta o job no banco
    repo = SQLiteJobRepository()
    job = Job(id=job_id, workflow_id=args.workflow, variables={})
    repo.save(job)

    # Sessão Playwright isolada
    session = PlaywrightSession(headless=args.headless, timeout_ms=30_000)

    use_case = WorkflowRunnerUseCase(
        job_repo=repo,
        spec_repo=YamlWorkflowSpecRepository(),
        session=session,
        action_registry=ACTION_REGISTRY,
        screen_handler_registry=SCREEN_HANDLER_REGISTRY,
    )

    try:
        result = use_case.execute(
            job_id=job_id,
            workflow_id=args.workflow,
            variables={},
        )
        print("\n[OK] Workflow concluído com sucesso!")
        print(f"     Resultado: {result}")
        print(f"     Screenshots em: {settings.SCREENSHOTS_DIR}/")
        print(f"     Logs em: {settings.LOG_DB_PATH}\n")

        # Mantém navegador aberto se solicitado
        if args.keep_open and not args.headless:
            print("\n[INFO] Navegador mantido aberto. Pressione Enter para fechar...")
            input()

    except Exception as exc:
        print(f"\n[ERRO] Falha na execução: {exc}\n")

        # Sempre mantém navegador aberto em caso de erro (exceto headless)
        if not args.headless:
            print("[INFO] Navegador mantido aberto para inspeção. Pressione Enter para fechar...")
            input()

        sys.exit(1)

    finally:
        session.close()


if __name__ == "__main__":
    main()
