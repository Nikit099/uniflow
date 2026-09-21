# ADR 002: PostgreSQL transactional outbox

Status: accepted. Notification intent is committed with case changes and claimed with `SKIP LOCKED`. This provides at-least-once delivery without adding Redis; consumers and templates remain idempotent.

