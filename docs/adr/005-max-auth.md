# ADR 005: MAX launch validation and internal sessions

Status: accepted. The server validates signed/fresh MAX `initData`, links `MaxIdentity`, then issues its own revocable hashed session. Client-side unsafe identity and localStorage tokens are rejected.

