# Domain model

- `Organization`, `Membership`, `StudentProfile`: tenant and identity boundary.
- `OfficialSource`: version-aware evidence with verification state.
- `ProcedureTemplate`, `ProcedureVersion`, `ProcedureStep`, `Requirement`: configurable workflow definition.
- `Case`, `CaseRequirement`, `Document`, `Comment`: reproducible student case and item-level review.
- `Session`, `MaxIdentity`: validated external identity and internal authentication.
- `AuditLog`, `NotificationOutbox`, `LLMRun`: traceability without document content or secrets.

Case transitions are enforced by a domain state machine. Item review uses a monotonically increasing version; stale writes receive HTTP 409. Government status and university package verification are separate concepts.

