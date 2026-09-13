# Next-Generation Review Checklists — Design Decisions

Status: **Draft / living document**
Last updated: 2026-09-13

This document captures the design decisions for evolving the Azure Review Checklists
project beyond the macro-enabled Excel spreadsheet, leveraging the existing structured
recommendation corpus (`v2/recos/**`) and modern tooling including LLMs.

It is a decision log, not an implementation spec. Decisions are revisited as we learn more.

---

## 1. Context & motivation

### Where the project stands today

- **v1** — monolithic `checklists/*.json`, imported into a macro-enabled Excel
  spreadsheet (VBA + VBA-JSON). Translated to several languages via Azure Translator.
  Azure Resource Graph (ARG) queries run with the **user's own credentials**.
  Azure Monitor workbooks render ARG results dynamically.
- **v2 (in progress)** — one structured file per recommendation under
  `v2/recos/Services` and `v2/recos/Practices` (~2000 files), sourced from APRL and
  WAF service guides, with embedded ARG queries, GUID labels, severity, and WAF pillar
  metadata. Consolidated by GitHub Actions (`get_aprl`, `get_waf_sg`, `autotag`, etc.).
- **web (prototype)** — Flask + MySQL on Azure Container Instances, `filldb` /
  `fillgraphdb` init containers; managed identity on the roadmap.

### Problems with the current macro spreadsheet

- Macro-enabled (`.xlsm`) files are restricted in many organizations for security
  reasons; VBA also does not work on Excel for Mac.
- Hard to collaborate / version control review state.

### Core constraint to preserve

The current model requires **no additional permissions**: ARG queries run with the
reviewer's own read-only access to the subscription(s). Any successor should preserve
this "no extra grants" property for the baseline experience.

### Current-state caveat — Azure AI endpoints decommissioned

The Azure-hosted AI endpoints previously used by the pipeline have been **decommissioned**;
re-enabling them would require deploying new model endpoints. Impact:

- **Automatic translation is currently broken.** `translate.py` (and the `translate.yml` /
  `translatev2.yml` workflows) depend on an **Azure Translator** endpoint
  (`AZURE_TRANSLATOR_ENDPOINT/REGION/KEY`) that no longer exists.
- **`cl.py v1tov2` reco-renaming is broken.** It depends on an **Azure Text Analytics**
  endpoint (`--text-analytics-endpoint`).
- **Embedding-based dedup still works.** `merge_waf_checklists.py` uses a **local**
  `sentence_transformers` model — no Azure endpoint — so it is unaffected.

Implication: this *strengthens* the case for replacing the broken Azure-hosted paths with
the provider-pluggable LLM approach — feature **(10) LLM-based translation** is not just an
enhancement, it restores a capability that is presently non-functional.

---

## Decision A — Distribution & authentication architecture

### A.1 Primary: local-first app (run on the reviewer's machine) — **CHOSEN**

A small, self-contained app (CLI that launches a localhost web UI, or single binary /
container) that runs on the reviewer's own machine.

- Authenticates to Azure using `DefaultAzureCredential` → the reviewer's existing
  `az login` / CLI session.
- **Zero new grants, no consent prompts, no hosted backend, no data leaving the machine.**
- Preserves the exact "runs with user credentials" property of the spreadsheet.
- Review state persists to a local, git-friendly file (SQLite or JSON).

This is the macro-spreadsheet replacement and the focus of initial effort.

**First milestone (2026-09-11):** Python CLI + localhost Flask UI, served by
Waitress, with SQLite working state and git-friendly JSON export. Implemented
under [`review_checklists/`](../../review_checklists/README.md); the existing web app
is preserved. The package name is independent of release versions; corpus tooling
is being modernized separately under Decision C.
The prototype restricts `DefaultAzureCredential` to the existing Azure CLI session.
Azure query execution sends query/scope to Azure; optional remote AI would require
separate data-egress approval. Local-first is not a promise that explicit Azure
operations are offline.

### A.2 Team option: customer-deployed app with managed identity — **DEFERRED (specced)**

For multi-user / persistent engagements. One-click `azd up` deploys a Container App +
system-assigned managed identity with Reader on the target subscription(s).

- The tradeoff (app needs an identity) is acceptable **because the customer owns the
  identity and controls its scope** — no third party gets access.
- **Sequenced after A.1.** Nothing in A.1 blocks adding A.2 later.

**Authentication design for A.2** (low complexity — config, not code):

Two **independent** identities — do not conflate them:

| Direction | Identity | Purpose |
|---|---|---|
| App → Azure | Managed identity (Reader) | Runs ARG queries |
| Human → App | Entra ID built-in auth ("Easy Auth") | Controls who can open the UI |

- **Authentication:** platform-managed Entra ID built-in auth provider (App Service
  Easy Auth / Container Apps built-in auth). No MSAL code, no secrets stored. Requests
  arrive with a validated identity.
- **Authorization (escalating levels):**
  1. **Assignment required** — set "User assignment required = Yes" on the enterprise
     app and assign only named reviewers or a single security group. Blocks everyone
     else in the tenant. Meets the "not everybody can access" requirement on its own.
  2. **App roles** — `Reviewer` / `Admin` roles in token claims for read-only vs. edit.
  3. **Network boundary** — ingress IP allowlist or private endpoint (defense in depth).
- **The real effort in A.2** is not auth; it is multi-user concurrent state, persistent
  storage with backup, and deployment lifecycle/cost ownership.

### A.3 Other options considered (not chosen now)

- **VS Code extension** — natural for the MS/partner audience, reuses Azure Account
  session. Kept as a possible future surface.
- **Static SPA + bring-your-own-token (MSAL)** — no backend, but requires an app
  registration the user consents to (slightly worse on "no extra permission").

---

## Decision B — LLM features are optional and provider-pluggable

### B.1 Positioning — **CHOSEN**

- The **core review works with zero LLM**: load checklist, run ARG with user creds, set
  status/comments, export report. This preserves the "no extra requirements" baseline.
- LLM features (B.3) light up **only if a provider is configured**; otherwise the
  related UI is hidden/disabled.
- LLM capability is delivered via a **pluggable provider abstraction** — the heavy parts
  (RAG retrieval over `v2/recos`, prompt templates, schema validation) are
  provider-agnostic; only a thin `complete()` / `embed()` seam is provider-specific.

### B.2 Provider options

| Provider | Audience | Notes |
|---|---|---|
| **GitHub Copilot** (SDK / Copilot CLI / VS Code) | MS employees & partners | **Recommended default** for the primary audience; reuses existing entitlement |
| **GitHub Models** | Anyone with a GitHub account | Free/low-tier on-ramp for non-Copilot users |
| **Azure AI Foundry / Azure OpenAI** | Customers with their own Azure | Fits the A.2 deployment; data stays in tenant |
| **OpenAI / Anthropic direct** | BYO API key | Simplest fallback |
| **Local (Ollama / ONNX)** | Air-gapped / regulated orgs | No data egress |

**Native GitHub Copilot integration is the recommended default for MS employees and
partners**, who already have the entitlement.

### B.3 Candidate LLM features

Two distinct audiences:

- **Reviewers (run the tool)** — LLM optional:
  - **(5) Narrative report generation** — exec summary, prioritized remediation roadmap,
    per-pillar WAF scoring, grounded (RAG) on the checklist corpus.
  - **(6) Finding triage & evidence-linking** — cluster non-compliant ARG results,
    explain *why* each violates the recommendation, draft the "Comments" cell.
  - **(7) Conversational review assistant** — query live review state + corpus; best
    delivered by exposing the corpus + review state as an **MCP server** so Copilot CLI /
    VS Code Copilot / any agent can drive a review without a bespoke chat UI.
- **Contributors (improve the repo)** — LLM runs in CI / their own Copilot, **invisible
  to reviewers**:
  - **(8) Authoring copilot** — draft title/description/severity/WAF pillar, propose ARG
    queries, semantic duplicate detection against existing GUIDs, schema validation in PR.
  - **(9) ARG query generation/repair** — for recos marked `automatable` but lacking a
    query.
  - **(10) LLM-based translation** — terminology-aware, glossary-respecting replacement
    for Azure Translator, including long-form descriptions.

---

## Decision C — Content & pipeline modernization — CHOSEN

The follow-on phase retains individual YAML authoring files, distributes
deterministic versioned JSON bundles, and keeps SQLite for review working state.
The strengthened schema records canonical IDs, retired-ID aliases, explicit
services, honest automation/result semantics, and source/freshness metadata.
See the [corpus contract](../../review_checklists/docs/corpus-contract.md).

- **(11) Distribution** — local JSON bundles first; hosted APIs/package registries remain deferred.
- **(12) Schema convergence** — a single authoritative recommendation schema;
  legacy formats remain renderers rather than competing authoring models.
- **(13) Provenance & freshness** — preserve unknown dates/revisions as unknown.
  Automatic upstream-change issue creation remains future work.

### C.1 Corpus refresh: LLM-assisted curation with deterministic gates — **CHOSEN**

Question considered: should the YAML corpus become a "knowledge base" refreshed
periodically by an LLM (e.g. GitHub Copilot), replacing the mechanical Python pipelines
triggered by upstream repo updates?

**Revised decision (2026-09-11):** disable scheduled APRL, AKS-checklist, and WAF
service-guide imports. Keep importer scripts/workflow dispatch as deprecated manual
fallbacks. The original automatic-mechanical-ingestion proposal is superseded;
deterministic parsing, schema/identity validation, assembly, and rendering remain.
Neither an LLM nor a manual importer bypasses human review.

Refreshes cite public evidence, distinguish updates from justified additions, and
record uncertain findings. ARG text is executable code: inventory is not a
violation, an available query is not a validated query, and empty results are not
compliance. Utilization, billing, licensing, and business-context checks may need
non-ARG evidence. Confirmed duplicate merges keep existing survivor IDs and retired
aliases; ambiguous or scope-conflicting overlaps stay separate.

**Where the LLM genuinely adds value** (judgment tasks):

- Semantic dedup & conflict detection across overlapping sources (improving on the
  string-based `find_duplicate_guids`; note embeddings are *already* used in
  `merge_waf_checklists.py`).
- Consolidation/summarization into larger bodies (e.g. WAF write-ups).
- Change triage — explain upstream diffs, flag breaking/semantic changes, draft updates.
- Drafting new fields (description, severity, WAF pillar) and proposing ARG queries for
  `automatable`-but-unqueried recos.

**The pattern — LLM-in-the-loop, never autonomous-on-main:**

```
public-source research → LLM-assisted proposal (dedup / draft / explain)
  → PR → deterministic schema/identity/bundle checks → human merge
```

Determinism and provenance are preserved at the `main`-branch boundary; LLM leverage
happens inside the *proposal* step. Live ARG validation requires separately
authorized subscription scope; offline CI must not imply it occurred.

---

## Appendix — Current mechanical pipeline inventory (`scripts/`)

Tasks performed today by scripts / GitHub Actions, for reference when deciding what stays
mechanical vs. gains an LLM-in-the-loop layer:

| Script | Task | Hybrid candidate? |
|---|---|---|
| `sync_folder.py` | Pull latest files from the repo's main branch | No — pure transport |
| `translate.py` | Translate checklist to es/ja/pt/ko/zh-Hant via Azure Translator | Yes — feature (10); **currently broken (endpoint decommissioned)** |
| `merge_waf_checklists.py` | Merge WAF / review / service-guide checklists, dedup via **local** embeddings (`sentence_transformers`) | Yes — already AI-assisted; **still works (local model)** |
| `create_master_checklist.py` / `compile_checklist.py` | Combine all checklists into a master JSON + macro-free XLSX | No — deterministic assembly |
| `verify_checklist.py` | Validate checklist correctness / schema | No — must stay deterministic (CI gate) |
| `sort_checklist.py`, `timestamp_checklist.py` | Housekeeping (ordering, timestamps) | No |
| `workbook_create.py` | Generate Azure Monitor workbook from a checklist | No — deterministic render |
| `update_excel_openpyxl.py`, `checklist_graph_update.py` | Populate Excel / import ARG results into spreadsheet | No |
| `checklist_graph.sh` | Run ARG queries with the user's credentials | No — the "no extra permission" core |
| `cl.py` | CLI: `analyze-v1/2`, `list/show-recos`, `v1tov2` (uses **Text Analytics**, **endpoint decommissioned**), `run-arg` | Partly — `v1tov2` AI-assisted but currently broken |
| `upload2cosmosdb.py`, `upload2tablestorage.py` | Publish corpus to Cosmos DB / Table Storage | No — relates to (11) API/package |

Takeaway: validation, assembly, and rendering stay **mechanical**. Automatic upstream
ingestion is deprecated in this branch; manual importer fallback does not replace
source-backed curation and review. The inventory above describes legacy tools,
not a claim that all their cloud dependencies have been restored.

---

## Open items / next steps

- [x] Confirm first-milestone scope: local prototype plus provider/MCP designs;
      initially defer Decision C. Corpus modernization is now approved as the
      follow-on phase; customer-hosted collaboration remains deferred.
- [x] Sketch the LLM provider abstraction; separate completion and optional
      embedding capabilities. See [integration contracts](../../review_checklists/docs/integration-design.md).
- [x] Prototype A.1: local CLI/web, pinned v2 recommendations, SQLite assessments,
      explicit ARG evidence, JSON/HTML export. No automatic compliance decisions.
- [x] Add severity/WAF/service/ARG-only filters, explicit selected-check query runs,
      and a filtered assessment donut with compliance/progress percentages.
- [x] Support multiple status/severity/WAF/service selections, using OR within a
      group and AND across groups, consistently in the UI, CLI and navigation.
- [x] Offer opt-in Azure CLI subscription lookup in query forms, with displayed-ID
      confirmation, manual scope override, and stale-form protection.
- [x] Add an always-visible current-CLI-subscription execution option, and real-browser
      form regression coverage for subscription lookup, query submission and assessment saves.
- [x] Consolidate CLI scope selection into one option with name/ID preview and change
      confirmation; explain disabled query actions with page/filtered query counts.
- [x] Design the MCP server over the checklist corpus + review state (feature 7).
- [x] Add editable review name/description metadata, retaining explicit filenames.
- [x] Make pagination optional and disabled by default; retain the 50-check run limit.
- [x] Migrate corpus metadata and implement deterministic versioned JSON bundles.
- [x] Complete the initial source-backed Cost refresh, conservative duplicate
      merges and importer deprecation; preserve the initial stage reports.
- [x] Account for the entire frozen corpus across five pillars and APRL, recording
      verified changes, source-supported unchanged guidance and explicit gaps.
      See the [all-pillar report](../../review_checklists/docs/corpus-refresh/full-refresh-2026-09-11/README.md).
- [x] Implement explicit review-refresh preview/apply, backup and history without
      overwriting assessments; changed guidance requires reassessment.
- [x] Implement read-only corpus administration and dated upstream inventories,
      with source-ID/hash reconciliation rather than inferred completeness.
- [x] Apply a bounded classification/Key Vault follow-up and two confirmed storage
      merges, preserving all identities and immutable source evidence. See the
      [September 13 report](../../review_checklists/docs/corpus-refresh/followup-2026-09-13.md).
- [x] Preserve distinct upstream mappings during merges and reject conflicts for
      the same source/ID; retain explicit priority/pillar/scope deferrals.
- [x] Improve large-list rendering without removing rows, native controls,
      no-JavaScript saving, print content or stale-edit protection.
- [ ] Validate the ARG path against explicitly authorized live subscription scope.
- [ ] Implement read-only stdio MCP with bounded output and explicit host-data disclosure.
- [ ] Implement and validate a first provider adapter with explicit remote-data approval.
- [ ] Design/implement trusted local approvals before enabling mutating MCP tools.

The provider and MCP documents are contracts, not working integrations. No paid AI
calls or live Azure queries were needed for the local prototype's automated tests.

## Decision summary

| ID | Decision | Status |
|----|----------|--------|
| A.1 | Local-first app (`DefaultAzureCredential`) as primary | **Chosen** |
| A.2 | Customer-deployed app + managed identity, Easy Auth + assignment-required | **Deferred, specced** |
| B.1 | LLM features optional; no-LLM baseline guaranteed; provider-pluggable | **Chosen** |
| B.2 | GitHub Copilot as recommended default for MS/partners | **Chosen** |
| C   | YAML authoring, versioned JSON bundles, schema/provenance/identity contract | **Implemented baseline; source-specific gaps recorded** |
| C.1 | LLM-assisted curated proposals; deprecated manual importers; deterministic validation and human review | **Chosen** |
