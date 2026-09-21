# UniFlow

Production-like MVP системы сопровождения иностранных студентов в административных процессах университета. UniFlow строится вокруг `Case`: студент всегда видит следующее действие, сотрудник проверяет каждый пункт отдельно, а организация управляет версионными процедурами и проверенными источниками.

> Demo University — демонстрационная конфигурация с синтетическими данными. Проект не является системой университета, МВД или Госуслуг и не подтверждает государственный миграционный статус.

## Quick start

```bash
docker compose up --build
```

Откройте [http://localhost:8080](http://localhost:8080). Миграции и идемпотентный demo seed выполняются автоматически. Реальные MAX- и LLM-секреты для локального сценария не нужны.

Если `8080` занят, используйте `WEB_PORT=18080 docker compose up --build` и откройте `http://localhost:18080`. Для другого порта добавьте origin через `ALLOWED_ORIGINS`.

## Что реализовано

- Mobile-first student app с onboarding-ready профилем, next best action, checklist, загрузкой документов, исправлениями, RU/EN и явной границей «проверено университетом».
- Desktop-first staff queue, назначение дела, независимая проверка требований, обязательная причина возврата и optimistic locking.
- Organization admin: источники, версии процедур, активация только новой версии, JSON import и внутренние агрегаты.
- FastAPI API, PostgreSQL 16, SQLAlchemy async, Alembic, UUID, tenant isolation, RBAC, audit и transactional outbox.
- Декларативный rule DSL без `eval`, case state machine, configurable deadlines и source provenance.
- Filesystem storage за authenticated endpoint; PDF/JPEG/PNG, сигнатура MIME, лимит 10 MB, случайные storage keys, Docker volume.
- MAX initData HMAC validation, session cookie, CSRF/origin checks, webhook dedupe, real/fake MAX adapters and Mini App bridge.
- OpenAI-compatible LLM adapter, четыре versioned prompts, verified-source retrieval, structured grounded output и graceful disabled state.
- OpenAPI, `DATA-API.yaml`, synthetic fixtures, unit/UI tests и CI.

## Main scenario

1. Войти как Student и открыть активное дело.
2. Добавить безопасные demo PDF/JPG/PNG к трём обязательным пунктам и отправить комплект.
3. Войти как Staff, открыть дело, принять два пункта, третий вернуть с конкретной причиной.
4. Снова войти как Student, заменить проблемный документ и повторно отправить комплект.
5. Staff принимает исправление и нажимает «Подтвердить проверку комплекта».
6. Student видит: «Университет подтвердил готовность комплекта. Это не является подтверждением решения государственного органа».

Подробный сценарий: [docs/demo.md](docs/demo.md).

## Architecture

```text
MAX Bot / MAX Mini App / Browser
              │
        nginx + React
              │ /api/v1
            FastAPI ── FilesystemStorage volume
              │
         PostgreSQL 16
              │ transactional outbox
            Worker ── MAX API / local demo inbox

External, optional: OpenAI-compatible LLM endpoint
```

Domain logic (rules, states, deadlines) does not depend on controllers or external services. Existing cases retain their `ProcedureVersion`; activation affects only new cases. The priority of truth is official source → verified university configuration → staff input → system calculation → AI explanation.

More: [architecture](docs/architecture.md), [domain model](docs/domain-model.md), [security](docs/security.md).

## Tech stack

Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 async, asyncpg, Alembic, PostgreSQL 16, React 19, TypeScript strict, Vite, TanStack Query, React Hook Form, i18next, nginx and Docker Compose.

## Docker and ports

| Service | Purpose | Port |
|---|---|---|
| `web` | nginx + SPA + reverse proxy | `8080` |
| `api` | FastAPI | internal `8000` |
| `worker` | outbox/reminders/cleanup | internal |
| `db` | PostgreSQL 16 | internal `5432` |

```bash
docker compose up --build -d
docker compose ps
curl http://localhost:8080/health/ready
docker compose logs -f api worker
docker compose down
```

Reset all local demo data (removes named database/upload volumes):

```bash
make demo-reset
```

## Demo accounts

These are local synthetic test credentials. `/demo-login` performs role selection without a password and exists only when `APP_ENV != production` and `DEMO_AUTH_ENABLED=true`.

| Role | Account | Demo password for fixtures |
|---|---|---|
| Student | `student@demo.local` | `demo-only-password` |
| Staff | `staff@demo.local` | `demo-only-password` |
| Organization admin | `admin@demo.local` | `demo-only-password` |

## Environment variables

Copy `.env.example` only when overriding defaults. Key settings:

- `APP_ENV`, `PUBLIC_BASE_URL`, `DATABASE_URL`, `SESSION_SECRET`
- `DEMO_MODE`, `DEMO_AUTH_ENABLED`, `DEMO_SEED`
- `FILE_STORAGE_PATH`, `FILE_MAX_SIZE_MB`
- `MAX_ENABLED`, `MAX_API_BASE_URL`, `MAX_BOT_TOKEN`, `MAX_WEBHOOK_SECRET`, `MAX_WEBAPP_AUTH_MAX_AGE_SECONDS`
- `LLM_ENABLED`, `LLM_PRIMARY_BASE_URL`, `LLM_PRIMARY_API_KEY`, `LLM_PRIMARY_MODEL`

Production startup rejects the default session secret, demo features, non-HTTPS public URL and known demo database credentials.

## MAX integration

The real adapter targets `https://platform-api2.max.ru`, sends the bot token only in the `Authorization` header and uses webhook delivery in production. The Mini App sends `window.WebApp.initData`; the backend validates the HMAC-SHA256 signature and `auth_date` before trusting `user.id`, then issues its own Secure/HttpOnly/SameSite session.

To connect MAX:

1. Create a bot and Mini App in the MAX partner platform.
2. Set an HTTPS `PUBLIC_BASE_URL`, `MAX_ENABLED=true`, `MAX_BOT_TOKEN` and `MAX_WEBHOOK_SECRET`.
3. Register `POST /api/v1/integrations/max/webhook` as the webhook and enable `bot_started`/`message_created` events.
4. Configure the Mini App URL and use a case-safe opaque `start_param` such as `case_ab12cd`.

Without a token the local fake adapter stores notifications as explicitly labelled local simulation; no MAX delivery is claimed. Details: [docs/max-integration.md](docs/max-integration.md).

## LLM integration

AI functionality requires an OpenAI-compatible endpoint. Set `LLM_ENABLED=true`, base URL, key and allowlisted model. Secrets remain in environment variables and are never returned to the browser.

The workflow remains fully usable when AI is disabled or times out. AI cannot mutate status, accept/reject documents, change deadlines, verify sources or assert government actions. Details: [docs/ai.md](docs/ai.md).

## Data, sources and privacy

Every critical requirement references a source. Only `VERIFIED` excerpts are eligible for grounded retrieval. Important values carry an origin such as `UNIVERSITY_CONFIG`, `STAFF_INPUT`, `SYSTEM_CALCULATION`, `LLM_GENERATED` or `SYNTHETIC_DEMO`.

The repository contains no real passport or migration documents. Do not upload real personal documents during demos or user tests. See [data provenance](docs/data-provenance.md) and [research](docs/research.md).

## API and tests

- Swagger UI: [http://localhost:8080/api/docs](http://localhost:8080/api/docs)
- Runtime schema: `/api/v1/openapi.json`
- Checked-in schema: `openapi.yaml`
- Hackathon checks: `DATA-API.yaml`

```bash
make test
make lint
make build
make openapi
./scripts/smoke.sh
```

CI checks backend lint/type/tests, frontend lint/type/tests/build, OpenAPI drift, secret patterns and Docker builds.

## Security

Server-side MAX validation, hashed opaque sessions/invites, HttpOnly cookies, CSRF and origin checks, tenant-scoped queries, RBAC, file authorization, upload signature/size validation, no public upload root, structured errors, audit logs and production configuration guards are implemented. This hackathon MVP still requires a formal threat model, secret manager, antivirus/CDR and personal-data legal review before a real pilot.

## Known limitations

- No official МВД/Госуслуги integration and no claim of government registration.
- Demo University requirements and URL are synthetic, not universal Russian-law guidance.
- Filesystem storage is local; use an S3-compatible adapter and malware scanning for production.
- Working-day deadlines return `REQUIRES_CONFIRMATION` until a verified calendar is configured.
- MAX and external LLM calls require credentials and network access; local demo uses explicit substitutes.
- Internal rate limiting is suitable for one process only; production should enforce limits at the gateway.

## Production deployment notes

Disable all demo flags, provide strong secrets through a secret manager, use HTTPS, managed PostgreSQL/backups, object storage, malware scanning, retention/deletion policies, centralized observability and a reverse proxy/WAF. Validate each university's sources, process owner and personal-data basis before activation.

## Further documentation

[User flow](docs/user-flow.md) · [Scaling](docs/scaling.md) · [Pilot](docs/pilot.md) · [Known limitations](docs/known-limitations.md) · [ADRs](docs/adr/001-monorepo.md)
