# Architecture

UniFlow is a monorepo with a React Mini App, FastAPI application, PostgreSQL and a database-backed worker. HTTP controllers authorize and validate requests, application services coordinate transactions, domain modules own state/rule/deadline logic, and integrations implement MAX, LLM and storage ports.

`Case → ProcedureVersion → Requirement` is immutable in meaning: an active procedure cannot be edited; a new version is cloned/imported and activated. Existing cases continue to point to the version used at creation.

The API and worker share one backend image. Business transactions append a `NotificationOutbox` row. The worker claims rows with `FOR UPDATE SKIP LOCKED`, delivers at least once, and retries with exponential backoff. No Redis is required.

External ports include `StorageBackend`, `LLMProvider`, `MaxClient`, and the documented future `UniversitySISAdapter`/`GovernmentAdapter`. No fictitious government adapter exists.

