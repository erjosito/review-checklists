# Provider and MCP contracts

Status: **design only**, 2026-09-11. The local CLI/web prototype is implemented;
no provider adapters, embedding index, agent tool execution, or MCP transport is
implemented by this document.

The implemented core is a Python CLI plus localhost UI, SQLite working state,
JSON/HTML export, and the shared schema/versioned JSON bundle described in the
[corpus contract](corpus-contract.md). Individual YAML files under `v2/recos`
remain the authoring source; the directory name is historical. Corpus API/package
publication, provider-backed freshness automation and customer-hosted
collaboration remain deferred. Source-backed proposals still require
deterministic validation and human review.

## 1. Optional provider boundary

The review core must not depend on an LLM. Provider orchestration sits above
`Review`, never inside corpus ingestion or state persistence.

Separate text generation from embeddings: a provider may support completions but
not embedding vectors. In particular, Copilot entitlement must not be treated as
evidence of an embedding API, and SDK/CLI availability must be verified during
adapter implementation.

Proposed Python contract (illustrative, not a runtime implementation):

```python
from dataclasses import dataclass
from typing import Literal, Mapping, Protocol


@dataclass(frozen=True)
class ContextReference:
    recommendation_id: str
    review_revision: int
    evidence_run_ids: tuple[int, ...]
    text: str


@dataclass(frozen=True)
class CompletionRequest:
    task: Literal["report", "triage", "explain"]
    instructions: str
    context: tuple[ContextReference, ...]
    output_schema: Mapping[str, object]
    max_output_tokens: int
    timeout_seconds: float


@dataclass(frozen=True)
class CompletionResult:
    text: str
    provider: str
    model: str
    finish_reason: Literal["stop", "length", "refusal"]


class CompletionProvider(Protocol):
    async def complete(self, request: CompletionRequest) -> CompletionResult: ...


@dataclass(frozen=True)
class EmbeddingResult:
    vectors: tuple[tuple[float, ...], ...]
    model: str
    dimensions: int


class EmbeddingProvider(Protocol):
    async def embed(self, texts: tuple[str, ...]) -> EmbeddingResult: ...
```

Provider metadata declares `id`, supported capabilities and data boundary
(`local` or `remote`). The application validates that requested capabilities exist;
no silent fallback to a different model/provider or an empty "successful" response.

The **application**, not the adapter, owns:

1. Retrieval over the pinned corpus and current evidence, initially keyword-based.
   Vector retrieval is optional and indexed by corpus hash + embedding provider,
   model and dimension; vectors from different models must never be mixed.
2. Prompt templates and minimal, explicitly selected context. Source text, comments,
   query results and model responses are untrusted data, not tool instructions.
3. JSON-schema validation and citation verification. Every proposed finding must
   cite an existing recommendation GUID and, when applicable, recorded evidence.
   Invalid JSON, invented citations, refusal or output truncation is an explicit
   failure, not an accepted assessment.
4. Egress approval for remote providers: show the provider, context categories and
   scope before sending customer data. A private Azure endpoint is not by itself
   a guarantee that all processing remains inside the customer's tenant.
5. Timeouts, cancellation, output limits and bounded retries for transient failures.
   Authentication, policy, invalid-output and unsupported-capability errors are
   surfaced distinctly. Never log tokens, API keys or raw customer prompts.
6. Proposal preview and human acceptance. Generated text is not automatically
   committed to review status/comments, and model-generated KQL cannot run.

A completion adapter has **no Azure credentials, review write access or tool
execution authority**. If the chosen Copilot integration has agent/tool capabilities,
disable them for this boundary; do not implement `complete()` by giving an
unrestricted agent the review directory. Use native APIs rather than shell command
interpolation or parsing human-readable CLI output.

### Provider sequencing and acceptance

| Adapter | Intended role | Required discovery before implementation |
| --- | --- | --- |
| Copilot | Recommended default for entitled reviewers | Supported SDK/auth path, text-only operation and tool isolation |
| Azure AI Foundry/OpenAI | Customer-controlled endpoint | Deployment/model, authentication, retention and egress policy |
| Local model | Offline/regulated option | Endpoint locality, model capabilities, resource requirements |
| GitHub Models / direct APIs | Optional alternatives | Credential handling, pricing, rate limits and data policy |

No provider is selected or probed at startup. Missing configuration leaves AI
disabled. Secrets belong in environment/OS credential storage, never the review
database or report. Initial adapter acceptance requires fake-transport tests for
success, timeout, refusal, invalid schema, unsupported embedding capability,
cancelled requests and denied egress; then an explicit, budgeted live smoke test.

## 2. MCP server surface

Use a **local stdio MCP server** launched by the user's agent host, configured with
an explicit review database path. No network listener, separate database, or
backend identity. Logs go to stderr; stdout is reserved for MCP messages.

The MCP adapter calls the same `Review` and ARG service operations as CLI/web.
It does not scrape HTML or invoke shell commands. The agent host supplies its
own model; it need not configure the in-app completion provider.

### Resources and tools

Proposed resources:

- `review://current/metadata`: schema version, snapshot hash and assessment counts.
- `review://current/items/{guid}`: recommendation snapshot, status, comments, revision.
- `review://current/evidence/{run_id}`: query, scope, timestamps, outcome, truncation
  and paged saved results.

Proposed tools (names are contracts to implement, not currently available tools):

| Tool | Required inputs | Result / boundary |
| --- | --- | --- |
| `list_recommendations` | optional search/status/severity/WAF/service/ARG-only filters; limit, cursor | Bounded item summaries and next cursor, using shared filter semantics |
| `get_recommendation` | recommendation GUID | Pinned recommendation and assessment revision |
| `get_evidence` | run ID; limit, cursor | Bounded rows, run outcome and explicit truncation metadata |
| `propose_assessment` | GUID, expected revision, proposed status/comments, citations | Preview proposal; no review mutation |
| `apply_assessment` | proposal ID, expected revision, approval token | Apply only the approved proposal via optimistic concurrency |
| `run_arg` | GUID, explicit subscription GUIDs, approval token | Execute pinned query only; evidence run ID; no status update |
| `export_review` | format (`json` or `html`) | Local resource handle, not an arbitrary caller-supplied file path |

Status, severity, WAF and service filters accept arrays: any value within a filter
may match (OR), while different filter categories intersect (AND). Empty arrays
do not restrict results. This matches CLI/web multi-select behavior. Search remains
text and the ARG-only option remains boolean.

Search/list result limits default to 50 and cap at 200. Evidence pages default to
100 and cap at 1,000. Cap text sizes separately so large descriptions cannot defeat
row-count limits. Cursors carry a review version; reject stale cursors. Do not stream
the entire customer inventory into the model by default.

### Authorization and human intent

Read-only tools are the startup default. Tool annotations describe read/write
behavior but are **not** an authorization mechanism.

Writes and Azure execution require an explicit local approval mechanism owned by
the application, not a `confirmed: true` value supplied by the agent. Before
enabling these tools, implement a trusted local approval UI/CLI that issues
single-use, short-lived tokens bound to the exact proposal or to the query hash +
subscription scope. Tokens must be invalidated after use or review revision change.
An agent prompt alone cannot grant itself access. Until this mechanism exists,
ship only read-only MCP tools.

MCP read access is itself data disclosure to the configured agent host/model.
Explain that boundary during setup and require explicit user approval before
attaching sensitive reviews. Local stdio does not imply that the host's model is
local. A future remote/team MCP service needs separate authentication and is not
part of this design.

### Error and evidence semantics

Transport/schema problems use standard MCP errors. Domain failures are tool errors,
with stable codes such as `not_found`, `revision_conflict`, `approval_required`,
`invalid_scope`, `azure_error` and `results_truncated`. Truncation may accompany
usable rows but must never be represented as complete evidence.

An ARG failure creates a failed evidence attempt exactly as CLI/web does. It must
not erase previous success or change a status. Error messages must be actionable
without leaking credentials. Query correctness and compliance interpretation remain
human responsibilities.

## 3. Next integration acceptance gates

1. Read-only MCP: official SDK conformance, stdio isolation, bounded/paged output,
   untrusted-content handling, unknown-ID errors and no write/execution capability.
2. Completion provider: capability detection, schema/citation validation and
   explicit egress approval, with the no-provider workflow unchanged.
3. Mutating MCP tools: trusted local approvals, stale-revision rejection, replay
   prevention and shared-service behavior identical across CLI/web/MCP.
4. Only then consider corpus refresh automation or team deployment. Keep all corpus
   AI changes behind PR validation and human merge.
