# Security

Controls include organization-scoped queries, role dependencies, file ownership checks, CSRF and origin validation, hashed random session tokens, MAX signature freshness, upload size/type/signature validation, randomized storage paths, output `nosniff`, CSP headers, optimistic locking, webhook deduplication and immutable-by-UI audit logs.

Production guards reject the demo secret, demo auth/mode, known demo DB credentials and non-HTTPS public URL. Secrets are environment-only and excluded from logs and API responses.

Before a pilot: complete threat modelling, DPIA/legal review, retention and deletion policy, antivirus/CDR, backups and restore exercises, secret manager, key rotation, gateway rate limiting and incident response.

