# POC GSFAT — Automação Visual Protheus

POC de automação determinística do módulo **GSFAT** do Protheus webapp (TOTVS Cloud), usando visão computacional, OCR localizado e workers paralelos isolados.

---

## 🚀 Quick Start

### 1. Configuração Inicial

```bash
# Clone e entre no diretório
cd playwright

# Copie o .env.example
cp .env.example .env

# Edite .env com suas credenciais
# IMPORTANTE: Altere JWT_SECRET_KEY em produção!

# Instale dependências
pip install -r requirements.txt

# Instale navegador Playwright
playwright install chromium
```

### 2. Inicializar Banco de Dados

```bash
# Execute migrations
alembic upgrade head

# Crie sua primeira API key
python scripts/manage_api_keys.py create "Minha API Key" --scopes jobs:read jobs:write

# Exemplo de saída:
# 🔑 Key: gsfat_X1Y2Z3A4B5C6...
# Guarde esta key!
```

### 3. Iniciar Serviços

```bash
# Opção A: Com Docker Compose (recomendado)
docker-compose up -d

# Opção B: Local (para desenvolvimento)
# Terminal 1: API
uvicorn presentation.api.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Worker Celery (Windows)
celery -A workers.celery_app worker -l info -P solo
```

### 4. Testar API

```bash
# Healthcheck básico
curl http://localhost:8000/health

# Healthcheck completo (verifica PostgreSQL + Redis)
curl http://localhost:8000/health/deep

# Documentação interativa
# Abra no navegador: http://localhost:8000/docs
```

### 5. Submeter um Job

```bash
# Defina sua API key
export API_KEY="gsfat_X1Y2Z3A4B5C6..."

# Submeta job
curl -X POST http://localhost:8000/jobs \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "faturar_pedido",
    "variables": {
      "pedido": "P-001"
    }
  }'

# Resposta:
# {
#   "job_id": "abc-123-def",
#   "status": "PENDING",
#   "workflow_id": "faturar_pedido",
#   "message": "Job enfileirado com sucesso."
# }
```

### 6. Consultar Status do Job

```bash
JOB_ID="abc-123-def"

curl http://localhost:8000/jobs/$JOB_ID \
  -H "X-API-Key: $API_KEY"

# Resposta:
# {
#   "job_id": "abc-123-def",
#   "status": "SUCCESS",
#   "workflow_id": "faturar_pedido",
#   "worker_id": "worker-1",
#   "started_at": "2026-05-29T10:00:00",
#   "finished_at": "2026-05-29T10:02:30",
#   "result": { ... }
# }
```

---

## Arquitetura

A aplicação segue **Clean Architecture** com **DDD**, dividida em quatro camadas com dependências sempre apontando para dentro (em direção ao domínio).

```
┌─────────────────────────────────────────────────────────┐
│                    PRESENTATION                         │
│              FastAPI  ·  Schemas (Pydantic)             │
├─────────────────────────────────────────────────────────┤
│                    APPLICATION                          │
│     Use Cases  ·  Ports (interfaces abstratas)          │
├─────────────────────────────────────────────────────────┤
│                      DOMAIN                             │
│   Entities  ·  Value Objects  ·  Repositories           │
│          Services  ·  State Machine                     │
├─────────────────────────────────────────────────────────┤
│                  INFRASTRUCTURE                         │
│  Playwright  ·  SQLite  ·  Celery  ·  OCR  ·  YAML     │
└─────────────────────────────────────────────────────────┘
```

### Fluxo de execução

```
Cliente HTTP
    │
    ▼
POST /jobs  (Presentation — FastAPI)
    │
    ▼
SubmitJobUseCase  (Application)
    │  salva Job no banco        enfileira na fila
    ▼                                  ▼
SQLiteJobRepository           CeleryJobDispatcher
(Infrastructure)                (Infrastructure)
                                       │
                                       ▼
                               Redis Queue
                                       │
                                       ▼
                           job_worker.py (Celery Worker — Windows)
                                       │
                                       ▼
                          WorkflowRunnerUseCase (Application)
                                       │
                             ┌─────────┴──────────┐
                             ▼                    ▼
                  YamlWorkflowSpecRepository   SQLiteJobRepository
                  (Infrastructure/Specs)       (Infrastructure)
                             │
                             ▼
                  WorkflowExecutionService (Domain Service)
                             │
                     ┌───────┴────────┐
                     ▼                ▼
               StateMachine      Action Registry
               (Domain)          (actions/)
                                       │
                                       ▼
                              PlaywrightSession
                              (Infrastructure/Browser)
                                       │
                                       ▼
                          Protheus Webapp (TOTVS Cloud)
```

---

## Estrutura do Projeto

```
poc_gsfat/
│
├── domain/                         # Regras de negócio puras
│   ├── entities/
│   │   ├── job.py                  # Job (aggregate root)
│   │   └── workflow.py             # WorkflowSpec, WorkflowStep, ScreenSpec
│   ├── value_objects/
│   │   ├── job_status.py           # Enum: pending/running/success/failed
│   │   ├── step_result.py          # Resultado imutável de cada step
│   │   └── screen_region.py        # Coordenadas de região de tela
│   ├── repositories/
│   │   ├── job_repository.py       # Interface AbstractJobRepository
│   │   └── workflow_spec_repository.py  # Interface AbstractWorkflowSpecRepository
│   └── services/
│       ├── state_machine.py        # Rastreia a tela atual da sessão
│       └── workflow_execution_service.py  # Motor de execução de steps
│
├── application/                    # Casos de uso — orquestração
│   ├── use_cases/
│   │   ├── submit_job_use_case.py  # Recebe comando e enfileira job
│   │   ├── get_job_status_use_case.py
│   │   └── workflow_runner_use_case.py  # Executa workflow no worker
│   └── ports/
│       ├── job_dispatcher_port.py  # Interface: despachar job para fila
│       └── session_port.py         # Interface: controle do browser
│
├── infrastructure/                 # Implementações concretas
│   ├── browser/
│   │   └── playwright_session.py   # Controla Protheus webapp via Playwright
│   ├── messaging/
│   │   └── celery_dispatcher.py    # Enfileira jobs no Redis/Celery
│   ├── persistence/
│   │   └── sqlite_job_repository.py  # Persiste jobs e logs em SQLite
│   ├── specs/
│   │   └── yaml_workflow_spec_repository.py  # Lê YAMLs de specs
│   └── vision/
│       ├── ocr_engine.py           # PaddleOCR — OCR localizado por região
│       └── screenshot_service.py   # Captura e salva screenshots
│
├── presentation/
│   └── api/
│       ├── main.py                 # FastAPI app + lifespan
│       ├── routes.py               # Endpoints: POST/GET /jobs
│       └── schemas.py              # Schemas Pydantic de request/response
│
├── actions/                        # Implementações dos steps do workflow
│   ├── registry.py                 # Mapa action_id → classe
│   ├── login.py                    # Abre Protheus e autentica
│   ├── search_routine.py           # Busca rotina na barra de pesquisa
│   ├── wait_screen.py              # Aguarda tela por anchors
│   ├── click_text.py               # Clica em elemento por texto
│   ├── keyboard.py                 # type / key / shortcut
│   └── misc.py                     # screenshot, assert_text, wait_text, extract_region, finish
│
├── workers/
│   ├── celery_app.py               # Configuração Celery (broker Redis)
│   ├── job_worker.py               # Task Celery — 1 worker = 1 sessão isolada
│   └── worker.yaml                 # Config do worker
│
├── specs/                          # Specs declarativas em YAML
│   ├── workflows/
│   │   └── faturar_pedido.yaml     # Workflow atual (MVP)
│   ├── screens/
│   │   ├── menu_principal.yaml     # Anchors do menu após login
│   │   └── tela_gsfat.yaml         # Anchors da Rotina de Corte
│   └── actions/
│       └── search_routine.yaml     # Configuração da action de busca
│
├── screenshots/                    # Screenshots capturados em runtime
├── logs/                           # banco SQLite (poc_gsfat.db)
├── replays/                        # (futuro) replay de sessões
│
├── settings.py                     # Lê .env e expõe configurações
├── config.yaml                     # Configurações gerais
├── docker-compose.yml              # Redis + API (coordinator)
├── Dockerfile.coordinator
├── requirements.txt
├── .env                            # Credenciais (não commitar)
└── .env.example
```

---

## Stack Técnica

| Camada       | Tecnologia         | Papel                                      |
|--------------|--------------------|--------------------------------------------|
| Runtime      | Python 3.12        | Linguagem base                             |
| API          | FastAPI            | Coordinator HTTP                           |
| Fila         | Redis + Celery     | Distribuição de jobs entre workers         |
| Browser      | Playwright         | Controle do Protheus webapp                |
| OCR          | PaddleOCR          | Leitura de texto em regiões da tela        |
| Visão        | OpenCV             | Template matching                          |
| Config       | YAML               | Specs de workflows, telas e actions        |
| Persistência | SQLite             | Log de jobs e steps                        |
| Infra local  | Docker Compose     | Redis + API no coordinator (Linux)         |

---

## Workflow Atual — MVP

```
login
  └─▶ wait_screen(menu_principal)
        └─▶ search_routine("Rotina de Corte")
              └─▶ wait_screen(tela_gsfat)
                    └─▶ screenshot(rotina_aberta)
                          └─▶ finish
```

---

## 🔒 Idempotência

Para garantir que um job não seja executado duas vezes (mesmo em caso de retry), use `idempotency_key`:

```bash
# Gere um UUID único
IDEMPOTENCY_KEY=$(uuidgen)

# Primeira tentativa
curl -X POST http://localhost:8000/jobs \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "faturar_pedido",
    "variables": {"pedido": "P-001"},
    "idempotency_key": "'$IDEMPOTENCY_KEY'"
  }'
# → Job criado: job_id = "abc-123"

# Retry (mesma key)
curl -X POST http://localhost:8000/jobs \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "faturar_pedido",
    "variables": {"pedido": "P-001"},
    "idempotency_key": "'$IDEMPOTENCY_KEY'"
  }'
# → Retorna job existente: job_id = "abc-123" (idempotent: true)
```

---

## 🔧 Gerenciamento de API Keys

```bash
# Criar nova key
python scripts/manage_api_keys.py create "Production Key" \
  --scopes jobs:read jobs:write \
  --expires-days 90

# Listar todas as keys
python scripts/manage_api_keys.py list

# Revogar uma key
python scripts/manage_api_keys.py revoke <KEY_ID>
```

**Scopes disponíveis:**
- `jobs:read` - Permite consultar status de jobs
- `jobs:write` - Permite criar e submeter jobs

---

## 🩺 Observabilidade

### Logs Estruturados

Logs incluem automaticamente `trace_id`, `job_id` e `workflow_id` para correlação:

```
2026-05-29 10:00:00 | INFO | trace_id=abc-123 | job_id=job-456 | workflow_id=faturar_pedido | Step login_protheus concluído em 2500ms
```

### Tracing Distribuído (OpenTelemetry + Jaeger)

```bash
# Habilite no .env
OTEL_ENABLED=true

# Acesse UI do Jaeger
# http://localhost:16686
```

### Circuit Breakers

Circuit breakers protegem contra falhas em cascata:

- **Protheus Login**: 5 falhas consecutivas → aberto por 60s
- **PostgreSQL**: 3 falhas consecutivas → aberto por 30s
- **Redis**: 3 falhas consecutivas → aberto por 20s

### Dead Letter Queue

Jobs que falharam após todos os retries vão para a DLQ:

```sql
-- Consultar jobs na DLQ
SELECT * FROM dead_letter_jobs ORDER BY created_at DESC LIMIT 10;
```

---

## 🐳 Docker

```bash
# Build
docker-compose build

# Up (com logs)
docker-compose up

# Up (background)
docker-compose up -d

# Logs da API
docker-compose logs -f api

# Parar
docker-compose down

# Limpar volumes (⚠️ apaga banco!)
docker-compose down -v
```

---

## 🔄 Migrations

```bash
# Criar nova migration
alembic revision --autogenerate -m "Add new table"

# Aplicar migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# Ver histórico
alembic history

# Ver SQL sem executar
alembic upgrade head --sql
```

---

## 📝 Scripts Utilitários

Todos os scripts utilitários estão em `/scripts`:

- **init_db.py** - Inicializa banco e cria primeira API key
- **manage_api_keys.py** - Gerencia API keys (criar, listar, revogar)
- **run_local.py** - Executa workflows localmente sem Celery/Redis

Ver documentação completa em [scripts/README.md](scripts/README.md)

---

## Regras Arquiteturais

- **1 worker = 1 sessão visual** — nunca compartilhar mouse, teclado ou foco entre workers
- **OCR localizado** — nunca rodar OCR na tela inteira; sempre em regiões mapeadas
- **Sem coordenadas fixas** — detecção por texto, template ou seletor CSS
- **Domínio sem dependências externas** — `domain/` não importa nada de infra
- **Specs como contrato** — toda automação é descrita em YAML antes de ser codificada

---

## Critérios de Sucesso da POC

- [ ] Abrir o Protheus webapp e autenticar
- [ ] Localizar e abrir a "Rotina de Corte" via busca
- [ ] Executar 5 workflows simultâneos sem conflito de foco
- [ ] Estabilidade > 95% em execuções repetidas
- [ ] Retry automático em caso de falha transitória

---

## 📚 Documentação

- **API Docs (Swagger)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc
- **Scripts**: [scripts/README.md](scripts/README.md)
