# Appendix L: Generative AI Usage & Audit Log

In compliance with academic integrity guidelines for BEng Final Year Research, this log documents all development-time use of AI coding assistants and runtime use of LLMs within the ReqVerify pipeline.

## 1. Development-Time Assistance Log

| Date | Tool + Model | Purpose | Prompt Summary | Output Used How | Verified By |
|---|---|---|---|---|---|
| 2026-10-18 | Antigravity (Claude 3.7 Sonnet) | Literature & Technology Verification | Verified SDK versions, package names, DOIs, and corrections to blueprint | Incorporated into `implementation-guide.md` and `docs/decision-log.md` | Primary researcher cross-checked with official docs & arXiv |
| 2026-10-19 | Antigravity (Claude 3.7 Sonnet) | Planning & Architecture Scaffolding | Produced comprehensive phase plans (`planning/phase-XX/PLAN.md`) and master roadmap | Governs Phase 00–10 implementation tasks | Traceability matrix verified against guide §1–§16 |

## 2. Runtime Pipeline Model Invariant

| Pipeline Agent | Model ID | Effort Level | Temperature / Sampling | Verification & Guard |
|---|---|---|---|---|
| Agent 1 (Analyst) | `claude-sonnet-5-5` | `medium` | None (deterministic defaults) | Pydantic v2 structured output parsing |
| Agent 2 (Explorer) | N/A (Algorithmic / Playwright) | N/A | N/A | DOM/ARIA snapshot line parser |
| Agent 3 (Generator) | `claude-sonnet-5-5` | `medium` | None | AST safety checker & immutable assertions |
| Agent 3 (Critic) | `claude-sonnet-5-5` | `medium` | None | Pydantic structured output (`CriticVerdict`) |
| Agent 4 (Verifier) | N/A (Deterministic) | N/A | N/A | Status mapper & frozen confidence formula |
