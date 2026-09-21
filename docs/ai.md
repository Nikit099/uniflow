# Grounded AI

Four pipelines are configured: requirement explanation, student question routing, staff case summary and plain-language translation. Versioned prompts live in `apps/api/app/ai/prompts`.

Retrieval currently searches only `VERIFIED` source excerpts in the organization boundary. The provider receives minimal case context plus retrieved excerpts. Structured output is validated and source IDs must be a subset of supplied sources. Missing coverage yields an explicit insufficient-information answer and a human escalation path.

AI cannot change workflow state, accept or reject documents, determine legal status, change deadlines, verify sources or claim a government action. An unavailable provider returns a recoverable UI state and never makes the core case flow unready.

