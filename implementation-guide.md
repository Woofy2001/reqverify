# ReqVerify — Implementation Guide

**Prepared:** 18 October 2026 · **Candidate:** Induwara Yasas Jayakody (w2052261 / 20230744) · **Supervisor:** Mr. Asanjay Fernando · **IIT / University of Westminster**

This guide turns your *Technical Implementation Blueprint & Defense Dossier* into a start-ready build plan. I checked the blueprint's technical claims against official documentation, publisher pages and arXiv this session. **Several items in the blueprint are out of date or wrong, and one of them (the pinned model) will stop the project from running at all.** Read §1 before writing any code.

**How to read the status marks**

| Mark | Meaning |
|---|---|
| ✅ | Verified: I opened an official / primary source this session (§16 lists them). |
| ⚠️ | Not fully verified. Check it yourself before relying on it. |
| 💡 | My engineering or methodology recommendation. It is judgement, not a sourced fact. |

---

## 1. Corrections to the blueprint (read first)

| # | Blueprint says | What the research found | What to do |
|---|---|---|---|
| 1 | Pin `claude-sonnet-4-20250514` (NFR-02) ✅ | Anthropic lists this model as **Retired**. It was deprecated 14 Apr 2026 and retired **15 Jun 2026**. Requests to retired models fail. The official recommended replacement is `claude-sonnet-5-5`. | Use `claude-sonnet-5-5`. Update the proposal text, NFR-02 and your GenAI log. State in the dissertation that the change was forced by retirement. |
| 2 | `temperature=0.0` for reproducibility ✅ | Setting `temperature`, `top_p` or `top_k` to a non-default value returns **HTTP 400** on Claude 4.7 and later models, including Sonnet 5.5. The Python SDK ≥ 1.0 removes these parameters, so passing them raises `TypeError`. | Delete the parameter. Get reproducibility from the SQLite cache, run manifests and logged response IDs (§6.4), not from temperature. |
| 3 | Agent 2 uses "accessibility-tree snapshotting" ✅ | `page.accessibility` was **removed in Playwright 1.57**. The supported route is `aria_snapshot()`: `locator.aria_snapshot()` since 1.49, `page.aria_snapshot()` since 1.59. | Use `aria_snapshot()`. Require Playwright ≥ 1.59 (current stable is 1.63). |
| 4 | Fuchß et al. DOI `10.1109/REW65646.2025.00032` / `document/10705423` ✅ | The author's own page gives **DOI `10.1109/REW66121.2025.00006`**, IEEE Xplore `https://ieeexplore.ieee.org/document/11190238`, pp. 5–12, REW 2025, Valencia. | Replace the DOI and URL. Also remove the placeholder `…/document/10123456`. |
| 5 | Pydantic `ge/le/min_length` constraints are "enforced at every agent boundary" ✅ | The Claude structured-outputs API does **not** support numeric or string-length constraints in the schema. The SDK helper strips them, adds them to the field description, and validates the response client-side. | Use `client.messages.parse()`. Treat the Pydantic validators as client-side checks. Count validation failures as a metric and retry. |
| 6 | `rationale` = "mandatory NL rationale" ✅ | The docs warn that a schema property that asks for the model's thinking or step-by-step reasoning may trigger a `reasoning_extraction` refusal. They recommend asking for a short explanation. | Word the field as a *one-sentence justification*. Handle `stop_reason == "refusal"` (§6.3). |
| 7 | "Huang *proves*…", "Xiong *proved* severe overconfidence", "*definitive* survey" (He et al.) ✅ | Huang et al. report that LLMs struggle to self-correct reasoning *without external feedback*. Xiong et al. report that verbalized confidence *tends* to be overconfident, that calibration improves with model scale, and that it is "still far from ideal". They tested GPT-4, LLaMA 2 and similar models, not Claude. He et al. is a systematic review of 71 studies plus a research agenda. | Soften the wording ("report", "provide evidence"). Make RQ2 a genuine empirical question about Sonnet 5.5. |
| 8 | WebTestPilot gap: "outputs raw execution logs; lacks requirement-level traceability and confidence scoring" ⚠️ | The paper describes decomposing an NL requirement into (condition, action, expectation) steps with **inferred pre/post-condition oracles**, evaluated on four bug-injected web apps. It does produce verdicts. | Read the full paper before the viva. Rewrite the gap claim precisely, e.g. what it does *not* report: per-condition confidence, a calibration study, an execution-grounded critic ablation. |
| 9 | Status set is PASS/FAIL/**UNTESTED** in §1 but PASS/FAIL/**ERROR**/UNTESTED in the schema | Internal inconsistency. | Use four statuses and define them (§7.3). |
| 10 | "Playwright Test Runner" and "Python/TypeScript scripts" | In Python the runner is `pytest` + `pytest-playwright`. The `@playwright/test` runner is a separate Node tool. | Decision: **generate Python / pytest-playwright only** (D2). |
| 11 | Ali et al. (2025), Springer ER/LNCS ✅ | The chapter belongs to ER 2024 (the 44th Int'l Conf. on Conceptual Modeling), pp. 295–314. Springer's metadata gives 2025; most citing papers write 2024. | Pick one convention and use it everywhere. Authors are Syed Juned Ali, Varun Naganathan, Dominik Bork. |
| 12 | Baltes & Ralph (2022) cited to justify the "small-scale evaluation" label | That paper is a critical review of **sampling** in SE research and its generalizability problems. Runeson & Höst (2009) is the case-study guideline. | Cite Baltes & Ralph for the generalizability limitation. Cite Runeson & Höst for what a "case study" is and why you are not claiming one. |
| 13 | Demo app "Next.js" (no version) ✅ | Next.js 15 reaches end of life on **21 Oct 2026**. Next.js 16 is the supported LTS line (requires Node ≥ 20.9, TypeScript ≥ 5.1). | Build TechStore on Next.js 16. |

Not an error, but note: the blueprint's NFR-03 rewording ("bounded cyclic graph … terminating deterministically in an acyclic terminal state within ≤ 3 iterations") matches how LangGraph handles cycles. Cycles need an explicit termination condition, and `recursion_limit` is only a safety net (§10).

---

## 2. Verified technology baseline (as of 18 Oct 2026)

| Component | Use in ReqVerify | Verified state | Mark |
|---|---|---|---|
| **Claude Sonnet 5.5** (`claude-sonnet-5-5`) | The single pinned model for all agents | Released 28 Sep 2026. 1M-token context, 128K max output. $2 / MTok input, $10 / MTok output, cache read $0.10 / MTok, Batch API 50% off. Status Active, retirement "not sooner than 28 Sep 2027". Adaptive thinking runs by default. Default effort `high`. | ✅ |
| Claude Sonnet 4.6 (`claude-sonnet-4-6`) | Fallback only | Active, but retirement "not sooner than **17 Feb 2027**". If your week 1 starts 19 Oct 2026, that date falls in week 18 (the calibration phase). | ✅ |
| Anthropic Python SDK | LLM calls | v1.0.0 released 20 Aug 2026 (requires Python ≥ 3.10, new HTTP layer). v1.1.0 followed on 26 Aug 2026. A package mirror lists later 1.x releases. Pin the exact version you install. | ✅ / ⚠️ latest |
| Structured outputs | Typed agent outputs | Supported on Sonnet 5.5. Uses `output_config.format`. `client.messages.parse()` accepts a Pydantic model and returns `parsed_output`. Works with the Batch API and streaming; incompatible with citations and with message prefilling. | ✅ |
| **LangGraph** | Orchestration | 1.2.x line. 1.2.14 released 6 Oct 2026. | ✅ |
| **Playwright for Python** | Agent 2 explorer + Agent 3/4 runner | 1.63 is the current stable docs version (Chromium 153.0.8010.12). `page.aria_snapshot()` since 1.59; `boxes` option 1.60; `aria_snapshots` option in `tracing.start()` since 1.63; Ubuntu 20.04 no longer supported in 1.63. | ✅ |
| `pytest` + `pytest-playwright` | Runner for generated tests | Documented plugin with `page`, `browser`, `browser_context_args` fixtures. Async needs the separate `pytest-playwright-asyncio`. | ✅ (versions ⚠️) |
| **Pydantic v2** | Contracts | 2.13.x. v2.13.5 (28 Aug 2026) is the latest I found. | ✅ / ⚠️ newer |
| **Next.js** | TechStore SUT | 16.x (Active LTS Oct 2025 → Oct 2027). Node ≥ 20.9. TypeScript ≥ 5.1. Turbopack is the default bundler. `next build` no longer runs the linter. | ✅ |
| Python | Backend | 3.11+ is fine (the Anthropic SDK needs ≥ 3.10). | ✅ SDK / ⚠️ LangGraph minimum |
| Node.js | TechStore | Use the current LTS, minimum 20.9 for Next.js 16. Check nodejs.org for the current LTS number. | ⚠️ |

### 2.1 Suggested `pyproject.toml` dependencies

```toml
[project]
name = "reqverify"
requires-python = ">=3.11"
dependencies = [
  "anthropic>=1.0,<2",
  "langgraph>=1.2,<2",
  "playwright>=1.59,<2",      # >=1.59 for page.aria_snapshot()
  "pydantic>=2.13,<3",
  "pytest",
  "pytest-playwright",
  "fastapi",
  "uvicorn",
  "jinja2",
  "pyyaml",
  "pypdf",                    # PDF requirement ingestion
  "numpy", "pandas", "scipy", "scikit-learn", "matplotlib",
]
# Optional: SQLite checkpointer for LangGraph (package name ⚠️ verify with pip):
#   pip install langgraph-checkpoint-sqlite
```

💡 Commit a lockfile (`pip freeze > requirements.lock`, or use `uv`/`pip-tools`). Your results are only reproducible if the exact versions are recorded. Also record the Playwright browser build (Chromium 153.0.8010.12 for Playwright 1.63).

---

## 3. Decisions to lock before coding

| ID | Decision | Recommendation | Why |
|---|---|---|---|
| D1 | Model and parameters | `claude-sonnet-5-5`. Set `max_tokens` explicitly. Omit `temperature/top_p/top_k` and any prefill. Leave `thinking` unset (adaptive on by default). Record the effort level used (default `high`). Do **not** send `thinking: {"type": "disabled"}` (returns 400). | ✅ These are the documented behaviours of Sonnet 5.5. |
| D2 | Language of generated tests | Python + `pytest-playwright` only. | 💡 One toolchain, one probe, one result parser. |
| D3 | Status semantics | `PASS`, `FAIL`, `ERROR`, `UNTESTED` (definitions in §7.3). | 💡 Removes the blueprint inconsistency. |
| D4 | Condition IDs | Generated in code from (requirement ID + verbatim source span + ordinal), never from the LLM's paraphrase. | 💡 NFR-06 says "text hashing". Hashing the LLM-written predicate would change the ID whenever the wording varies between runs, which breaks cross-run matching. |
| D5 | Cache vs replicates | Cache key includes a `run_id`. Dev work uses `run_id="dev"` (shared cache). Each evaluation replicate uses its own `run_id`. | 💡 Without this, your "5–10 independent iterations" would silently replay the same cached answer. |
| D6 | Mutants are evaluation-only | The pipeline must never see mutant metadata or source. | 💡 Prevents leakage and protects the black-box claim. |
| D7 | Critic may not weaken assertions | The critic and generator may change locators, waits and navigation steps. They may **not** change the asserted expectation derived from the condition. Log every diff. | 💡 Otherwise the critic can "repair" a test until it passes against a defective app, which masks the defect and invalidates RQ3 and RQ4. |
| D8 | Agent 3 topology | Compile Agent 3 as a LangGraph subgraph run once per condition, with an explicit `iteration` counter in state. `recursion_limit` is a safety net, not the iteration cap. | ✅ LangGraph counts super-steps, not your loop iterations. |
| D9 | SUT stack | Next.js 16 + SQLite or in-memory data, Docker image per variant. Mutants are switched by an environment variable. Defect registry lives in `techstore/mutants/registry.yaml` (the answer key). | 💡 One codebase, many variants, easy to reset. |
| D10 | Baselines | (a) zero-shot single-pass LLM → Playwright script (required). (b) WebTestPilot (public repo) as a stretch comparison ⚠️ check feasibility and licence. | 💡 |
| D11 | RQ4 protocol | **P-B (primary):** run the full pipeline on each SUT variant (clean + mutants), which is what "verify a live app without source" means. **P-A (secondary, cheaper):** generate tests on the clean app once, then execute them on each mutant. | 💡 P-B is more faithful but more expensive and exposes the test-fitting risk (D7). |
| D12 | Pre-registration | Freeze the analysis plan (metric definitions, number of ECE bins, how `overall_confidence` is computed, statistical tests) in a dated file before the first evaluation run. | 💡 Protects you against viva criticism of post-hoc tuning. |
| D13 | Dev vs evaluation split | Tune prompts on a small separate **dev app and dev requirements** (e.g. a one-page shop or todo app), not on TechStore's evaluation requirements. | 💡 With only ~24 conditions, prompt-tuning on the evaluation set would leak straight into RQ1. |

---

## 4. Environment setup

```bash
# Prerequisites: Python 3.11+, Node 20.9+ (LTS), Docker, git
git init reqverify && cd reqverify
python3.11 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install "anthropic>=1.0,<2" "langgraph>=1.2,<2" "playwright>=1.59,<2" \
            "pydantic>=2.13,<3" pytest pytest-playwright fastapi uvicorn jinja2 \
            pyyaml pypdf numpy pandas scipy scikit-learn matplotlib
playwright install chromium            # downloads the browser build matching your Playwright version
pip freeze > requirements.lock

# TechStore (SUT)
npx create-next-app@latest techstore    # accept TypeScript + App Router defaults
```

```bash
# .env.example  (never commit the real .env)
ANTHROPIC_API_KEY=sk-ant-...
REQVERIFY_MODEL=claude-sonnet-5-5
```

```gitignore
.env
.venv/
cache/*.sqlite          # archive the final cache as a release artifact instead
runs/**/traces/
node_modules/
```

**Docker for the evaluation runs.** Pin a specific Playwright image tag, because Playwright states that `latest` tags are no longer published and recommends pinning. Pattern: `mcr.microsoft.com/playwright/python:v<your-playwright-version>` ⚠️ confirm the exact tag exists on MCR before relying on it.

---

## 5. Repository layout

```
reqverify/
├─ pyproject.toml · requirements.lock · .env.example · README.md
├─ src/reqverify/
│  ├─ llm/            client.py (parse + SQLite cache + manifest), prompts/
│  ├─ schemas/        contracts.py
│  ├─ agents/         analyst.py · explorer.py · generator.py · critic.py · probe.py · verifier.py
│  ├─ graph/          agent3_subgraph.py · pipeline.py
│  ├─ reporting/      json_report.py · html_report.py · templates/report.html.j2
│  └─ cli.py          reqverify run --requirements docs/reqs.md --url http://localhost:3000
├─ techstore/         Next.js app, mutants/registry.yaml, Dockerfile, docker-compose.yml
├─ eval/
│  ├─ ground_truth/   requirements.md · conditions.csv · mutants_expected.csv
│  ├─ analysis_plan.md        (frozen before first eval run; D12)
│  ├─ run_eval.py · metrics.py · stats.py · notebooks/
│  └─ baselines/      zero_shot.py
├─ dev_app/           tiny separate app + requirements for prompt development (D13)
├─ runs/              one folder per run_id: manifest.json, results.json, report.html, traces/
├─ docs/              decision-log.md · appendix_L_genai_log.md · appendix_N_ethics.md
└─ tests/             unit tests with recorded LLM fixtures
```

---

## 6. LLM layer

### 6.1 Request settings (Sonnet 5.5)

| Setting | Value | Notes |
|---|---|---|
| `model` | `claude-sonnet-5-5` | ✅ The only ID listed in the docs I read. I found no dated snapshot alias, so reproducibility must come from your own logs and cache. |
| `max_tokens` | Start at 16,000 | ✅ `max_tokens` covers thinking plus visible text under adaptive thinking. A truncated response (`stop_reason == "max_tokens"`) can break the schema. ⚠️ If the SDK asks you to stream for very large values, use `client.messages.stream(...)`. |
| `output_format` (helper) / `output_config.format` | Pydantic model | ✅ Recommended path: `client.messages.parse(..., output_format=Model)` → `response.parsed_output`. |
| `output_config.effort` | `low` / `medium` / `high` (default) / `xhigh` / `max` | ✅ Sonnet 5.5 supports all five. Effort changes cost and quality, so keep it constant across an ablation and record it. |
| `temperature`, `top_p`, `top_k` | **Do not send** | ✅ 400 / `TypeError`. |
| Assistant prefill | **Do not use** | ✅ 400. Use structured outputs instead. |
| Forced `tool_choice` | **Do not use** | ✅ Listed as returning 400 on Sonnet 5.5. |
| `thinking` | Omit (adaptive on) | ✅ `{"type":"disabled"}` returns 400. |

💡 **Spike S-1 (day 1–2):** the docs show the `parse()` helper and `output_config.effort` separately. I did not find an example combining them. Test whether `messages.parse(..., output_format=Model, output_config={"effort": "medium"})` works. If it does not, call `messages.create(...)` with `output_config={"effort": ..., "format": {"type": "json_schema", "schema": transform_schema(Model)}}` and validate with `Model.model_validate_json(...)`. The docs describe `transform_schema()` in the `anthropic` package; confirm its import path in your installed SDK.

### 6.2 Structured-output limits that affect your schemas ✅

- Every object must set `additionalProperties: false` (the SDK helper does this for you).
- Unsupported: recursive schemas, numeric constraints, string-length constraints, `minItems` other than 0 or 1.
- Limits per request: ≤ 24 optional parameters in total, ≤ 16 parameters using union types. Every `Optional[...]` field is a union, so keep few.
- First use of a new schema adds latency while the grammar compiles (cached for 24 h). Changing `output_config.format` invalidates the prompt cache for that conversation thread, so **keep each agent's schema stable**.
- Enum capitalization is not guaranteed in rare cases. Compare enum values case-insensitively.
- Refusals and `max_tokens` truncation can produce output that does not match the schema.

### 6.3 Client with cache and manifest (starter code)

```python
# src/reqverify/llm/client.py
from __future__ import annotations
import hashlib, json, sqlite3, time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Type, TypeVar

import anthropic
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
DEFAULT_MODEL = "claude-sonnet-5-5"


class RefusalError(RuntimeError): ...
class TruncatedError(RuntimeError): ...


@dataclass
class CallMeta:
    response_id: str
    model: str
    input_tokens: int
    output_tokens: int
    stop_reason: str
    latency_s: float
    cache_hit: bool


class LLMClient:
    def __init__(self, db_path="cache/llm_cache.sqlite", model=DEFAULT_MODEL,
                 run_id="dev", use_cache=True, max_tokens=16_000):
        self.client = anthropic.Anthropic()        # reads ANTHROPIC_API_KEY
        self.model, self.run_id = model, run_id
        self.use_cache, self.max_tokens = use_cache, max_tokens
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(db_path)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS calls(key TEXT PRIMARY KEY, created REAL, "
            "run_id TEXT, request TEXT, response TEXT, meta TEXT)")

    def _key(self, system: str, user: str, schema: Type[BaseModel]) -> str:
        payload = json.dumps(
            {"model": self.model, "system": system, "user": user,
             "schema": schema.model_json_schema(), "run_id": self.run_id},
            sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def parse(self, system: str, user: str, schema: Type[T]) -> tuple[T, CallMeta]:
        key = self._key(system, user, schema)
        if self.use_cache:
            row = self.db.execute(
                "SELECT response, meta FROM calls WHERE key=?", (key,)).fetchone()
            if row:
                meta = {**json.loads(row[1]), "cache_hit": True}
                return schema.model_validate_json(row[0]), CallMeta(**meta)

        t0 = time.time()
        resp = self.client.messages.parse(
            model=self.model, max_tokens=self.max_tokens, system=system,
            messages=[{"role": "user", "content": user}],
            output_format=schema)                  # see Spike S-1 for adding effort
        if resp.stop_reason == "refusal":
            raise RefusalError("Model refused; inspect prompt / schema wording")
        if resp.stop_reason == "max_tokens":
            raise TruncatedError("Raise max_tokens or shorten the task")

        parsed: T = resp.parsed_output
        meta = CallMeta(resp.id, resp.model, resp.usage.input_tokens,
                        resp.usage.output_tokens, resp.stop_reason,
                        time.time() - t0, False)
        self.db.execute(
            "INSERT OR REPLACE INTO calls VALUES (?,?,?,?,?,?)",
            (key, time.time(), self.run_id, json.dumps({"system": system, "user": user}),
             parsed.model_dump_json(), json.dumps(asdict(meta))))
        self.db.commit()
        return parsed, meta
```

Verify the response field names (`id`, `model`, `usage.*`, `stop_reason`, `parsed_output`) against your installed SDK in Spike S-1. Add retry with backoff for rate-limit and server errors, and set `max_retries` on the client explicitly.

### 6.4 Reproducibility without `temperature`

1. **Cache:** the same (model, system, user, schema, `run_id`) returns the stored answer. Dev work and unit tests replay from it.
2. **Replicates:** an evaluation replicate uses a fresh `run_id`, so the model is called again. The API still samples at its default settings, so replicates can differ, which is what you want to measure. ⚠️ Confirm this empirically in week 2 by running the same prompt twice with the cache bypassed.
3. **Manifest:** write `runs/<run_id>/manifest.json` with: model ID, effort, SDK versions (`anthropic`, `playwright`, `langgraph`, `pydantic`), Playwright browser build, git commit of ReqVerify and TechStore, mutant ID, document SHA-256, every response ID, token usage, cache-hit ratio.
4. **Archive:** at submission, freeze the cache and run folders (for example a Zenodo or university-repository deposit). Anthropic will retire Sonnet 5.5 eventually, so an archived cache is the only way a marker can replay your results later.

### 6.5 Cost model (illustrative; measure in week 2)

Official prices ✅: $2 / MTok input, $10 / MTok output, cache read $0.10 / MTok, Batch API −50%. Adaptive thinking tokens count as output tokens, so cost depends on effort.

**Assumptions (mine, not sourced):** 6,000 input tokens and 3,000 output tokens per call → $0.012 + $0.030 = **$0.042 per call**. 24 conditions, 11 SUT variants (clean + 10 mutants).

| Scenario (per replicate, protocol P-B) | LLM calls | Cost | ×5 replicates | ×10 replicates |
|---|---|---|---|---|
| Critic ON, typical (≈ 3 calls / condition) | 792 | ≈ $33 | ≈ $166 | ≈ $333 |
| Critic ON, worst case (3 × generate + 3 × critic = 6 calls / condition) | 1,584 | ≈ $67 | ≈ $333 | ≈ $665 |
| Critic OFF (1 call / condition) | 264 | ≈ $11 | ≈ $55 | ≈ $111 |

This excludes Agents 1 and 2 and the zero-shot baseline. The critic loop is interactive, so the Batch discount does not apply there. Agent 1 extraction across replicates can use it. **Decision rule:** run 5 replicates under P-B, and use P-A for extra replicates if budget is tight. Put a hard per-run token budget in the CLI.

---

## 7. Data contracts (revised schemas)

Changes from the blueprint: (1) the LLM returns a smaller object, and IDs and hashes are added in code; (2) probe results (from execution) are separated from critic judgement (from the LLM); (3) added `source_span`, `untested_reason`, `critic_iterations`, `needs_human_review`; (4) rationale wording avoids "reasoning" language.

### 7.1 Code

```python
# src/reqverify/schemas/contracts.py
from __future__ import annotations
import hashlib
from typing import Literal, Optional
from pydantic import BaseModel, Field


def normalize(s: str) -> str:
    return " ".join(s.lower().split())


def make_condition_id(req_id: str, source_span: str, ordinal: int) -> str:
    h = hashlib.sha256(f"{req_id}|{normalize(source_span)}|{ordinal}".encode()).hexdigest()[:8]
    return f"{req_id}.{ordinal}-{h}"


# ---- Agent 1: what the LLM returns -------------------------------------------------
class LLMCondition(BaseModel):
    source_requirement_id: str = Field(description="ID of the requirement, exactly as written in the document, e.g. REQ-01")
    source_span: str = Field(description="Verbatim text copied from the requirement that this condition comes from")
    predicate_text: str = Field(description="One atomic, verifiable assertion about observable behaviour")
    is_testable: bool = Field(description="True if a user can observe this through the web UI alone")
    untestable_reason: Optional[str] = Field(default=None, description="Short reason if not testable")
    extraction_confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this extraction, 0 to 1")
    rationale: str = Field(min_length=10, description="One short sentence saying why this is a separate atomic condition")


class LLMExtraction(BaseModel):
    conditions: list[LLMCondition]


# ---- After post-processing in code -------------------------------------------------
class ExtractedCondition(LLMCondition):
    condition_id: str
    document_hash: str


class CoverageMatrix(BaseModel):
    document_hash: str            # SHA-256 of the ingested document
    model: str
    conditions: list[ExtractedCondition]


# ---- Agent 2 -----------------------------------------------------------------------
class UIElementSelector(BaseModel):
    element_id: str
    role: str                     # ARIA role from aria_snapshot, e.g. button, textbox
    accessible_name: str
    locator_code: str             # e.g. page.get_by_role("button", name="Add to cart")
    page_url: str


# ---- Agent 3: execution evidence vs LLM judgement ----------------------------------
class ProbeResult(BaseModel):    # produced by running the script, NOT by the LLM
    exit_code: int
    outcome: Literal["passed", "assertion_failed", "runtime_error", "timeout"]
    exception_type: Optional[str] = None
    stdout_tail: str = ""
    duration_s: float
    trace_path: Optional[str] = None


class CriticVerdict(BaseModel):  # produced by the LLM
    verdict: Literal["APPROVE", "REJECT"]
    assertion_validity_score: float = Field(ge=0.0, le=1.0)
    critique_notes: str
    suggested_refinement: Optional[str] = None


# ---- Agent 4 -----------------------------------------------------------------------
Status = Literal["PASS", "FAIL", "ERROR", "UNTESTED"]
UntestedReason = Literal["not_ui_observable", "no_selector_found", "critic_not_converged"]


class RequirementVerificationResult(BaseModel):
    requirement_id: str
    condition_id: str
    execution_status: Status
    untested_reason: Optional[UntestedReason] = None
    test_script_ref: Optional[str] = None
    critic_iterations: int = 0
    overall_confidence: float = Field(ge=0.0, le=1.0)
    audit_rationale: str
    needs_human_review: bool = False
```

### 7.2 Post-processing rules for Agent 1 (in code, not in the prompt)

1. Reject or flag any condition whose `source_span` is not a substring of the document after whitespace normalization.
2. Assign IDs with `make_condition_id(req_id, source_span, ordinal)`.
3. Drop exact duplicates; log near-duplicates for review.
4. Count schema-validation failures, refusals and truncations per run (report them in the dissertation).

### 7.3 Status semantics (definitions to put in the dissertation)

| Status | Meaning | Derived from |
|---|---|---|
| `PASS` | A critic-approved script ran and its assertion held. | Probe `passed` + `APPROVE` |
| `FAIL` | The script ran, selectors resolved, and the assertion did **not** hold. | Probe `assertion_failed` (exception type `AssertionError`) + `APPROVE` |
| `ERROR` | The script could not complete: locator timeout, navigation error, crash. | Probe `runtime_error` or `timeout` |
| `UNTESTED` | No valid test exists. Always carries `untested_reason`: not UI-observable (e.g. REQ-09 backend-only), no selector found, or critic did not converge in ≤ 3 iterations (also `needs_human_review=True`). | Agent 1 / 2 / 3 |

💡 **Spike S-4 (week 2):** Playwright's `expect(...)` failures should surface as `AssertionError`, and locator or action timeouts as Playwright's own `TimeoutError`. Prove this with 3 hand-written tests before building the classifier. `pytest` exit code 1 covers both situations, so you must classify by exception type, using a small pytest plugin hook (`pytest_runtest_makereport`) that writes JSON.

---

## 8. TechStore SUT, ground truth and mutants

### 8.1 TechStore scope (blueprint: 5 pages)

Login · Product filtering · Cart (with discount) · Multi-step checkout · Admin order status. Next.js 16 (App Router), TypeScript, in-memory or SQLite data seeded deterministically. Provide one seeded test user and one admin user (credentials go into the ReqVerify config, not the prompts).

💡 **Accessibility is a controlled factor.** Agent 2 depends on ARIA roles and accessible names. Build the clean app with proper labels and roles, and record this as a stated assumption. Optionally add one deliberately poor-ARIA page as a failure-mode study (stretch).

### 8.2 Requirements document and ground truth

Write `eval/ground_truth/requirements.md` with 15–20 requirements (`REQ-01` …) in plain English, as a QA lead would. Then write `conditions.csv`:

| Column | Example |
|---|---|
| `req_id` | `REQ-03` |
| `condition_id` | `C-03.2` (human label for the answer key; matching to system output is by span/semantics, not ID) |
| `predicate` | "A discount code that is valid reduces the cart total by the stated percentage." |
| `ui_observable` | `true` |
| `expected_clean` | `PASS` |
| `source_span` | exact sentence in the requirements doc |

Plus `mutants_expected.csv`: one row per (condition, mutant) with the expected verdict (`FAIL` where the mutant violates the condition, otherwise `PASS`).

Process rules 💡:
- Author the ground truth **before** running any agent. Get your supervisor's signed review of at least a sample (blueprint requirement).
- Include REQ-09 as a backend-only requirement. It is your designed `UNTESTED` case.
- Keep a short written matching protocol: how an extracted condition counts as "the same" as a ground-truth one (RQ1). Use a second reviewer on a sample and report agreement.

### 8.3 Mutant registry (10 seeded defects)

Create `techstore/mutants/registry.yaml`. Each entry: `id`, `module`, `description`, `env_flag`, `violated_conditions`. Suggested starting set (illustrative; align to your real conditions once written):

| ID | Module | Defect |
|---|---|---|
| M01 | Login | Email validation regex accepts `a@b` |
| M02 | Login | Minimum password length not enforced |
| M03 | Catalog | Price filter off-by-one (`<` instead of `≤`) |
| M04 | Catalog | "Out of stock" badge missing when stock = 0 |
| M05 | Cart | Line total ignores quantity |
| M06 | Cart | Discount applied inverted (adds instead of subtracts) |
| M07 | Checkout | Step 2 accepts an empty address |
| M08 | Checkout | Order total omits shipping |
| M09 | Admin | Status cannot be changed to "Shipped" |
| M10 | Cart | Cart not cleared after successful checkout |

Switch with an environment variable (for example `MUTANT=M06`) and build one Docker tag per variant. Keep `registry.yaml` outside the image the pipeline can reach (D6).

---

## 9. Agent specifications

### Agent 1 — Requirements Analyst

- **Input:** requirements Markdown or PDF (`pypdf` for PDF text).
- **Output:** `CoverageMatrix`.
- **Steps:** (1) read text and compute SHA-256; (2) split deterministically on `REQ-\d+` headings; (3) one LLM call per requirement (smaller prompts, cache-friendly) returning `LLMExtraction`; (4) post-process per §7.2.
- **Done when:** 100% schema-valid output on the dev requirements; 100% of `source_span`s found in the document; unit tests replay from recorded fixtures; first RQ1 precision/recall computed on the dev set (not the evaluation set).
- **Pitfall:** do not ask for "step-by-step reasoning" in a schema field (see §1 item 6).

### Agent 2 — App Explorer

- **Input:** base URL, credentials, `CoverageMatrix` (to guide which flows matter).
- **Output:** `SelectorMap` (`list[UIElementSelector]` per page state).
- **Core call:** `page.aria_snapshot()` (Playwright ≥ 1.59), or `page.locator("body").aria_snapshot()` on 1.49–1.58. `mode="ai"` and `boxes` options exist in newer releases; compare default vs `ai` output on TechStore in a spike and pick one.
- **Snapshot parsing 💡:** the snapshot is YAML-like text with entries such as `- button "Add to cart"`. Write a tolerant line parser and unit-test it against real saved snapshots, not invented samples.
- **Locator generation:** role + accessible name → `page.get_by_role("button", name="Add to cart")`. Locators are strict by default, so duplicates raise an error. Handle them with `exact=True`, scoping to a parent locator, or `.nth()`. Record when no usable locator exists (`no_selector_found` → `UNTESTED`).
- **Exploration strategy 💡:** start with a deterministic crawl of navigation links and a login step, then add requirement-guided exploration for stateful flows (cart → checkout). Wait on explicit conditions, not fixed sleeps. In Playwright 1.63, `page.frame_locator()` without a selector searches any frame, which helps with iframes.
- **Done when:** every ARIA-reachable interactive element on the 5 pages is recorded, and the stateful flows can be reached by script.

### Agent 3 — Test Generator + Critic

- **Generator:** one pytest-playwright test per testable condition. The docstring contains the `condition_id`. Locators come only from the `SelectorMap`. The asserted expectation is derived from `predicate_text` and is **immutable across iterations** (D7).
- **Safety 💡:** you are executing LLM-written code. Run `ast.parse`, reject forbidden imports (`os`, `subprocess`, `socket`, `requests`, …), and execute in a subprocess or container with a timeout and with network access limited to the SUT.
- **Probe:** run `pytest` on the single script via `subprocess.run([...], timeout=60)` with a small plugin that records outcome and exception type into a `ProbeResult`. Save a Playwright trace (`context.tracing.start(screenshots=True, snapshots=True)`, plus `aria_snapshots=True` on Playwright 1.63) as audit evidence.
- **Critic:** the LLM receives the condition, the script, the `ProbeResult` and a snapshot excerpt, and returns `CriticVerdict`. It must distinguish a **test bug** (bad locator, missing wait) from an **application defect** (assertion legitimately failing). Only test bugs may be repaired.
- **Loop cap:** 3 iterations. After that, `UNTESTED` with `critic_not_converged` and `needs_human_review=True`.
- **Never** give the critic mutant information or access to a second SUT variant at runtime (D6).
- **Done when:** the loop terminates on all 24 conditions on the clean app; FAIL vs ERROR classification matches your hand-written tests (Spike S-4).

### Agent 4 — Execution and Verification

- **Input:** approved scripts + live SUT. **Output:** `RequirementVerificationResult` list, JSON and HTML report.
- **Steps:** run each approved script in a fresh browser context; bind outcomes to `condition_id` via the plugin's JSON; compute `overall_confidence` (D12: freeze the formula, for example `extraction_confidence × assertion_validity_score`); render a report with requirement ID, condition, status, confidence, rationale, script link, trace link, critic iterations.
- **Generated tests must be self-contained** (login → add to cart → checkout) because multi-step state cannot be assumed between tests. Reset the SUT between pipeline runs from the evaluation harness, not from the agents.
- **Done when:** the JSON validates against the schema and the HTML report opens with working trace links.

---

## 10. LangGraph wiring

✅ From the LangGraph docs: conditional edges route by a function (`add_conditional_edges(node, router, mapping)`); `recursion_limit` counts super-steps and raises `GraphRecursionError` when exceeded; the checkpointer interface includes SQLite and in-memory savers.

```python
# src/reqverify/graph/agent3_subgraph.py
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END

MAX_CRITIC_ITERS = 3


class CondState(TypedDict, total=False):
    condition: dict      # ExtractedCondition.model_dump()
    selectors: list[dict]
    script: str
    probe: dict          # ProbeResult.model_dump()
    critic: dict         # CriticVerdict.model_dump()
    iteration: int
    final: str           # "approved" | "not_converged"


def generate(state: CondState) -> dict:
    it = state.get("iteration", 0) + 1
    # LLM call; on it > 1 include state["critic"]["suggested_refinement"]
    script = "..."
    return {"script": script, "iteration": it}


def probe(state: CondState) -> dict:
    return {"probe": {...}}      # subprocess run → ProbeResult


def critic(state: CondState) -> dict:
    return {"critic": {...}}     # LLM call → CriticVerdict


def route(state: CondState) -> Literal["generate", "approved", "not_converged"]:
    if state["critic"]["verdict"] == "APPROVE":
        return "approved"
    if state["iteration"] >= MAX_CRITIC_ITERS:
        return "not_converged"
    return "generate"


def build_agent3():
    g = StateGraph(CondState)
    g.add_node("generate", generate)
    g.add_node("probe", probe)
    g.add_node("critic", critic)
    g.add_node("approved", lambda s: {"final": "approved"})
    g.add_node("not_converged", lambda s: {"final": "not_converged"})
    g.add_edge(START, "generate")
    g.add_edge("generate", "probe")
    g.add_edge("probe", "critic")
    g.add_conditional_edges("critic", route, {
        "generate": "generate", "approved": "approved", "not_converged": "not_converged"})
    g.add_edge("approved", END)
    g.add_edge("not_converged", END)
    return g.compile()

# usage: build_agent3().invoke({"condition": c, "selectors": s}, {"recursion_limit": 25})
```

Notes 💡:
- Each loop iteration uses about 3 super-steps (generate → probe → critic), so 3 iterations fit comfortably under the default limit of 25 for one condition. If you put all 24 conditions in a single graph, you would hit the limit. Hence D8: one subgraph invocation per condition.
- Keep the outer pipeline (Agent 1 → 2 → loop over conditions → Agent 4) as a small parent graph whose middle node loops over conditions and calls the compiled subgraph.
- For resumability, compile with a SQLite checkpointer (`langgraph.checkpoint.sqlite.SqliteSaver`, package name ⚠️ verify) keyed by `thread_id = f"{run_id}:{condition_id}"`.
- Add a unit test that forces `REJECT` forever and asserts the graph ends in `not_converged` after exactly 3 iterations. That test is your evidence for NFR-03.

---

## 11. Evaluation protocol and statistics

### 11.1 What is measured

| RQ | Unit of analysis | Metrics | Notes |
|---|---|---|---|
| RQ1 extraction | Extracted vs ground-truth conditions, per replicate | Precision, recall, F1 | Target: recall ≥ 0.80. **Fix ≥ vs > consistently.** Needs the matching protocol in §8.2. |
| RQ2 calibration | (condition × SUT variant) verdicts; label = verdict equals ground truth | ECE, Brier score, reliability diagram, AUROC | 💡 Pearson on a binary outcome is a weak choice; report Brier and AUROC too. With ~264 verdicts per replicate, use 5–10 bins and show bin counts. Compare verbalized confidence with consistency across replicates if budget allows. |
| RQ3 critic ablation | Same conditions, same SUT, critic ON vs OFF | First-pass pass rate, final pass rate, mapping accuracy, Δ and CI | Paired test over conditions (e.g. Wilcoxon signed-rank). Keep model, effort and prompts identical. |
| RQ4 end-to-end | (condition × SUT variant) verdict vs expected verdict | Accuracy, per-class P/R, **fault-detection recall** (mutants detected / 10), false-alarm rate on the clean app, UNTESTED precision | Primary protocol P-B, secondary P-A (D11). |

### 11.2 Run design

- 5–10 independent replicates per condition of the experiment, each with its own `run_id` (D5).
- Run the **zero-shot baseline** on the same SUT variants and the same replicate count.
- Report mean ± SD across replicates, plus bootstrap 95% CIs. 💡 Bootstrap over **conditions** (the repeated unit), not over pooled run-level rows, because the same 24 conditions recur in every replicate.

### 11.3 Starter code

```python
# eval/metrics.py
import numpy as np
from scipy.stats import bootstrap

def ece(conf, correct, n_bins=10):
    conf = np.asarray(conf, float); correct = np.asarray(correct, float)
    edges = np.linspace(0, 1, n_bins + 1)
    idx = np.clip(np.digitize(conf, edges[1:-1], right=True), 0, n_bins - 1)
    out = 0.0
    for b in range(n_bins):
        m = idx == b
        if m.any():
            out += m.mean() * abs(correct[m].mean() - conf[m].mean())
    return out

def brier(conf, correct):
    conf = np.asarray(conf, float); correct = np.asarray(correct, float)
    return float(np.mean((conf - correct) ** 2))

def boot_ci(per_condition_values, stat=np.mean, n=10_000, seed=0):
    res = bootstrap((np.asarray(per_condition_values),), stat,
                    confidence_level=0.95, n_resamples=n,
                    random_state=np.random.default_rng(seed))
    return res.confidence_interval.low, res.confidence_interval.high
```

(`sklearn.metrics.roc_auc_score` and `sklearn.calibration.calibration_curve` cover AUROC and reliability-curve points. Unit-test `ece` on hand-made examples before using it.)

### 11.4 Validity threats to write up honestly

- Single self-built app and self-authored requirements (author bias → mitigate with supervisor sign-off and the dev/evaluation split).
- ARIA quality of TechStore is a controlled assumption.
- Mutants are author-chosen and may not represent real defects. If time allows, test on WebTestPilot's bug-injected benchmark apps ⚠️ check whether the repository releases them.
- Model drift: Sonnet 5.5 will be retired eventually. Archive cache and manifests (§6.4).

---

## 12. 20-week plan (assuming Week 1 starts Mon 19 Oct 2026; shift to your real dates)

| Wk | Starts | Deliverable |
|---|---|---|
| 1 | 19 Oct | Repo, lockfile, `.env`, LLM client + cache (S-1), blueprint corrections applied to proposal text |
| 2 | 26 Oct | Spikes S-2 (aria snapshot parse), S-3 (LangGraph loop with stubs), S-4 (FAIL vs ERROR), S-5 (cache + `run_id`); cost measurement; dev app |
| 3 | 2 Nov | TechStore pages 1–3; requirements doc draft; frozen analysis plan v0 |
| 4 | 9 Nov | TechStore pages 4–5; ground truth complete; supervisor review of sample |
| 5 | 16 Nov | Mutant registry + Docker variants; Agent 1 v1 |
| 6 | 23 Nov | Agent 1 evaluated on dev set; prompt freeze for Agent 1 |
| 7 | 30 Nov | Agent 2 crawl + selector map |
| 8 | 7 Dec | Agent 2 stateful flows; UNTESTED/no-selector handling |
| 9 | 14 Dec | Agent 3 generator + safety checks + probe |
| 10 | 21 Dec | Agent 3 critic + loop; zero-shot baseline |
| 11 | 28 Dec | Agent 4 runner + JSON/HTML report |
| 12 | 4 Jan | End-to-end pipeline on clean app; first full manifest |
| 13 | 11 Jan | Integration hardening; budget guards; **analysis plan frozen** |
| 14 | 18 Jan | Evaluation: replicates 1–2 (P-B), baseline |
| 15 | 25 Jan | Evaluation: replicates 3–5; critic-OFF runs |
| 16 | 1 Feb | Evaluation: remaining replicates / P-A runs |
| 17 | 8 Feb | RQ1–RQ4 statistics, calibration plots |
| 18 | 15 Feb | Gap-filling runs; archive cache and runs |
| 19 | 22 Feb | Writing: methods, results |
| 20 | 1 Mar | Discussion, limitations, appendices L and N, viva prep |

Weekly ritual 💡: one-page decision log entry (what changed, why, evidence). It feeds Appendix L (GenAI audit log) and the design-rationale chapter.

---

## 13. Risk register (updated)

| Risk | Likelihood | Mitigation |
|---|---|---|
| Pinned model unavailable (the blueprint's model is retired) | Certain if unchanged | §1 item 1: use `claude-sonnet-5-5`. |
| Non-reproducible results (no temperature control) | High | §6.4: cache, replicates, manifest, archive. |
| Critic "repairs" tests to fit defects | Medium | D7 assertion immutability; diff logging; separate analysis of repaired vs unrepaired tests. |
| Prompt overfitting to the evaluation set | Medium | D13 dev/evaluation split. |
| Cost overrun | Medium | §6.5 budget; per-run token guard; 5 replicates under P-B first. |
| Non-ARIA elements invisible to Agent 2 | Medium | Record `no_selector_found`; report as a finding. |
| Schema refusals or truncation | Medium | Short rationale field wording; `max_tokens` headroom; metrics for refusals. |
| Executing LLM-written code | Medium | AST checks, forbidden imports, subprocess/container, timeouts, network limits. |
| Ground-truth author bias | Medium | Supervisor sign-off, second reviewer on a sample, matching protocol. |
| Library churn (SDK 1.x moving fast, LangGraph minor releases) | Medium | Lockfile, exact versions in the manifest, no mid-evaluation upgrades. |
| Hallucinated or wrong citations | Medium | §16 verification log. Re-verify every reference before submission. |

---

## 14. Updated defence wording

- **Q1 (vs WebTestPilot).** Do not claim it "outputs raw logs". Say: WebTestPilot infers pre/post-condition oracles over symbolized GUI elements for NL requirements and evaluates on bug-injected apps. ReqVerify's contribution is a per-condition, auditable verification matrix with calibrated confidence, tool-grounded critic ablation and an explicit `UNTESTED` class. Cite what you verified; keep any "does not report X" claim limited to what you checked in the paper.
- **Q2 (can you trust the confidence?).** "Not by assumption. Verbalized confidence has been reported to be overconfident in earlier models (Xiong et al., ICLR 2024). I measure ECE, Brier score and AUROC for Claude Sonnet 5.5, and report any miscalibration as a finding."
- **Q3 (single self-built app).** Concede the external-validity limit (Baltes & Ralph, 2022: sampling and generalizability). Point to internal validity: controlled variants, 10 seeded mutants, a frozen analysis plan, multiple replicates with bootstrap CIs. Do not call it a "case study" (Runeson & Höst, 2009).
- **Q4 (why Sonnet 5.5 and not Sonnet 4?).** "Claude Sonnet 4 was retired on 15 June 2026. I used the vendor's recommended replacement, pinned the model ID, and archived all inputs and outputs."

---

## 15. Appendix L template (GenAI audit log)

| Date | Tool + model | Purpose | Prompt summary | Output used how | Verified by |
|---|---|---|---|---|---|
| 2026-10-18 | Claude (chat) | Literature/technology verification for implementation guide | Asked for web-verified versions, DOIs, corrections | Informed §1–§2 of this guide | Cross-checked against the sources in §16 |

Log both the *development-time* use of AI assistants and the *runtime* use of Claude inside ReqVerify (model ID, dates, purpose).

---

## 16. Sources and verification log

### 16.1 Official documentation and release pages (opened this session)

| Topic | URL |
|---|---|
| Model lifecycle / retirements | https://platform.claude.com/docs/en/about-claude/model-deprecations |
| Sonnet 5.5 overview (pricing, context, defaults) | https://platform.claude.com/docs/en/models/sonnet-5-5/overview |
| Sonnet 5.5 migration (400-error settings) | https://platform.claude.com/docs/en/models/sonnet-5-5/migration-guide |
| Structured outputs | https://platform.claude.com/docs/en/build-with-claude/structured-outputs |
| Effort parameter | https://platform.claude.com/docs/en/build-with-claude/effort |
| Anthropic Python SDK 1.0.0 release | https://newreleases.io/project/github/anthropics/anthropic-sdk-python/release/v1.0.0 |
| Playwright Python release notes | https://playwright.dev/python/docs/release-notes |
| Playwright Locator API (`aria_snapshot`) | https://playwright.dev/python/docs/api/class-locator |
| Playwright pytest plugin | https://playwright.dev/python/docs/test-runners |
| LangGraph Graph API (conditional edges, recursion) | https://docs.langchain.com/oss/python/langgraph/graph-api |
| LangGraph how-to (recursion limit) | https://docs.langchain.com/oss/python/langgraph/use-graph-api |
| LangGraph 1.2.14 release | https://github.com/langchain-ai/langgraph/releases/tag/1.2.14 |
| Pydantic 2.13.5 changelog | https://github.com/pydantic/pydantic/blob/v2.13.5/HISTORY.md |
| Next.js installation (system requirements) | https://nextjs.org/docs/app/getting-started/installation |
| Next.js 16 upgrade guide | https://nextjs.org/docs/pages/guides/upgrading/version-16 |

### 16.2 Papers

| Reference | Verified details | Link |
|---|---|---|
| Teoh et al., WebTestPilot | arXiv:2602.11724 (Feb 2026); *Proc. ACM Softw. Eng.* 3(FSE), article FSE087, 2026; DOI 10.1145/3797115 (from the authors' repository citation) | https://arxiv.org/abs/2602.11724 |
| Kong et al., WebTestBench | arXiv:2603.25226 (26 Mar 2026); checklist generation + defect detection; benchmark and WebTester baseline | https://arxiv.org/abs/2603.25226 |
| Alian et al., AutoE2E ("Feature-Driven End-To-End Test Generation") | arXiv:2408.01894; ICSE 2025; 79% feature coverage on E2EBench | https://arxiv.org/abs/2408.01894 |
| Hey, Fuchß, Keim, Koziolek, "Requirements Traceability Link Recovery via RAG" | REFSQ 2025, Springer LNCS, pp. 381–397, ISBN 978-3-031-88531-0. ⚠️ DOI not retrieved; get it from the Springer page. | https://fuchss.org/publications/ |
| Ali, Naganathan, Bork, "Establishing Traceability … by Combining RAG and LLMs" | ER 2024 (Springer), pp. 295–314; Springer metadata year 2025 | https://link.springer.com/chapter/10.1007/978-3-031-75872-0_16 |
| Fuchß, Schwedt, Keim, Hey, "Beyond Retrieval: … LLM Ensembles for Candidate Filtering in Requirements Traceability" | IEEE REW 2025, pp. 5–12; **DOI 10.1109/REW66121.2025.00006**; IEEE Xplore 11190238 | https://fuchss.org/conferences/aire25/ |
| Huang et al., "LLMs Cannot Self-Correct Reasoning Yet" | ICLR 2024; arXiv:2310.01798 | https://arxiv.org/abs/2310.01798 |
| Gou et al., CRITIC | ICLR 2024; arXiv:2305.11738 | https://arxiv.org/abs/2305.11738 |
| Xiong et al., "Can LLMs Express Their Uncertainty?" | ICLR 2024; arXiv:2306.13063 | https://arxiv.org/abs/2306.13063 |
| He, Treude, Lo, "LLM-Based Multi-Agent Systems for SE" | ACM TOSEM 2025; arXiv:2404.04834; systematic review of 71 studies | https://arxiv.org/abs/2404.04834 |
| Runeson & Höst, case-study guidelines | *Empirical Software Engineering* 14(2), 131–164, 2009; DOI 10.1007/s10664-008-9102-8 | http://dx.doi.org/10.1007/s10664-008-9102-8 |
| Baltes & Ralph, "Sampling in SE Research" | *Empirical Software Engineering*, 2022; arXiv:2002.07764 | https://arxiv.org/abs/2002.07764 |

### 16.3 Still unverified (do these in week 1)

1. WebTestPilot: read the full paper and confirm exactly what it reports (verdict granularity, confidence, ablations) before finalizing the gap claim.
2. Hey et al. (REFSQ 2025): retrieve the DOI.
3. Exact MCR tag for the pinned Playwright Python Docker image.
4. Package name and import path for the LangGraph SQLite checkpointer.
5. Whether `messages.parse(output_format=…)` can be combined with `output_config.effort` (Spike S-1), and the exact import path of `transform_schema`.
6. Current Node.js LTS number and LangGraph's minimum Python version.
7. Anthropic SDK latest 1.x version (a mirror listed releases newer than 1.1.0).
8. Whether WebTestPilot's benchmark apps are publicly released (for an external-validity extension).
9. LESP governance requirements: check your department's current template, since I did not find a public source.

### 16.4 Week-1 checklist

- [ ] Replace the model and remove `temperature` in the proposal/NFR-02 text
- [ ] Fix the Fuchß DOI and remove the placeholder URL
- [ ] Reword NFR-03 (bounded cycle, ≤ 3 iterations)
- [ ] Reword Huang / Xiong / He / WebTestPilot claims (§1 items 7–8)
- [ ] Create repo, venv, lockfile, `.env`
- [ ] Implement `LLMClient` + cache + `run_id`; run Spike S-1
- [ ] Hand-write 3 Playwright tests and run Spike S-4 (FAIL vs ERROR)
- [ ] Save 3 real `aria_snapshot()` outputs from any web page for parser development (S-2)
- [ ] Start `docs/decision-log.md` and `docs/appendix_L_genai_log.md`
