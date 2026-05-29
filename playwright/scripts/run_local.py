"""Executa um workflow localmente, sem Celery nem Redis.

Ideal para desenvolvimento e testes locais.

Uso:
    python run_local.py
    python run_local.py --workflow faturar_pedido
"""

import argparse
import logging
import sys
import uuid
from pathlib import Path

# Garante que o diretório do projeto está no path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Configuração de logging
Path("logs").mkdir(parents=True, exist_ok=True)
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
    parser = argparse.ArgumentParser(description="POC GSFAT - runner local")
    parser.add_argument("--workflow", default="faturar_pedido", help="ID do workflow YAML")
    parser.add_argument("--headless", action="store_true", help="Rodar browser em modo headless")
    parser.add_argument(
        "--keep-open", action="store_true", help="Manter navegador aberto após a execução"
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
    print("  POC GSFAT - Execução Local")
    print(f"{'=' * 55}")
    print(f"  Workflow : {args.workflow}")
    print(f"  Job ID   : {job_id}")
    print(f"  URL      : {settings.PROTHEUS_URL}")
    print(f"  Usuário  : {settings.PROTHEUS_USER}")
    print(f"  Headless : {args.headless}")
    print(f"  Keep Open: {args.keep_open}")
    print(f"{'=' * 55}\n")

    # Cria as pastas necessárias
    Path(settings.SCREENSHOTS_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.LOG_DB_PATH).parent.mkdir(parents=True, exist_ok=True)

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

    error_occurred = False

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

    except Exception as exc:
        error_occurred = True
        print(f"\n[ERRO] Falha na execução: {exc}\n")

    finally:
        # O input() precisa vir ANTES do session.close(), senão o Playwright
        # encerra o browser junto com o processo Python.
        if not args.headless:
            if error_occurred:
                print("[INFO] Navegador mantido aberto para inspeção. Pressione Enter para fechar...")
                input()
            elif args.keep_open:
                print("\n[INFO] Navegador mantido aberto. Pressione Enter para fechar...")
                input()
        session.close()

    if error_occurred:
        sys.exit(1)


if __name__ == "__main__":
    main()
