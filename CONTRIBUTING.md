# Contributing to Azure Review Checklists

Contributions are welcome from reviewers, customers, partners and Microsoft
employees. Report incorrect or missing guidance, propose source-backed content
changes, or improve the local application. Start with the [project README](README.md),
[AGENTS.md](AGENTS.md), and the [corpus contract](review_checklists/docs/corpus-contract.md).
For bug reports use [Support](SUPPORT.md); follow [SECURITY.md](SECURITY.md) for
security reports rather than a public issue.

## Work against the current implementation

The current v3 work is a local-first Python CLI/localhost UI prototype, not a
hosted service or a generally available team product. Check the target branch
before opening a PR: development-branch changes belong against that branch, not
automatically against an upstream `main` with a different implementation.
The package remains `review_checklists`; `v2/recos` is the intentional historical
path of the current YAML corpus.

Fork or create a working branch, keep the change focused, and request review from
the applicable [CODEOWNERS](CODEOWNERS). Include the motivation, affected IDs and
files, sources, semantic changes, validation results, and any unresolved limits.
Do not include review databases, customer evidence, credentials, virtual
environments, generated bundles, or machine-local paths.

The [legacy guide](docs/legacy-v1.md) preserves spreadsheet/JSON authoring history.
It is not the current contribution workflow. Historical GA/Preview labels and
spreadsheet releases do not establish the maturity of this prototype.

## Author recommendations in YAML

Edit individual files in [`v2/recos`](v2/recos), not generated JSON in
[`checklists`](checklists/README.md), release bundles, translated files, or workbooks.
Use the single [recommendation schema](v2/schema/recommendation.schema.json);
the app and authoring tools share parsing and validation through
`scripts/modules/cl_corpus.py`. Do not add a competing schema or rely on the
legacy loader to fill in missing authored metadata.

1. **Find the existing requirement first.** Search canonical IDs, names, aliases,
   services and resource scopes. Prefer updating the existing recommendation
   over adding overlapping guidance.
2. **Make the requirement actionable, verifiable and scoped.** State the setting
   or decision to assess, applicability, and necessary evidence. Use primary
   guidance to justify numerical limits or service-specific constraints; do not
   turn context-dependent advice into an unconditional rule.
3. **Preserve identity.** Keep existing canonical lowercase UUIDs, names and legacy
   GUID labels. New recommendations need unique stable IDs and normally
   `source.type: curated`. Include the required `schemaVersion`, service,
   automation and provenance metadata described in the corpus contract.
4. **Classify only supported facts.** Use canonical names from the
   [service dictionary](scripts/service_dictionary.json). Empty `services` means
   no explicit classification, not permission to guess specialization from a
   generic resource type. Review resource types, WAF pillar and severity together.
5. **Record evidence honestly.** Include public source URLs, titles, actual access
   dates, what changed and why in the PR and applicable provenance/report.
   Unknown `upstreamRevision`, `lastReviewed` and `validatedAt` stay null.
   Source access is not human approval, an upstream commit, or live query testing.

For a new checklist, add a YAML selector under [`v2/checklists`](v2/checklists);
use [app_delivery.yaml](v2/checklists/app_delivery.yaml) and existing definitions
as examples. Reuse canonical recommendations rather than copying them into
another corpus. Verify root/area/subarea inclusion and exclusion behavior,
including aliases and expected memberships, before submitting.

### ARG queries provide evidence

The application executes one primary `queries.arg` per recommendation.
Set `automation.status` and, for an available query, `resultSemantics` according
to the [contract](review_checklists/docs/corpus-contract.md#required-metadata).
`query_available` is not a validation claim. `compliance` semantics require
`complianceColumn`; the current app does not require every query to return the
legacy `id`/`compliant` pair.

Explain required scope, permissions, missing data, expected output, false positives,
and interpretation. Inventory and Advisor findings are evidence, not automatic
non-compliance or realized savings. Zero rows do not establish compliance.
Do not invent ARG access to utilization, billing, licensing or business context.
Keep additional researched query variants and caveats in the source/refresh
report; do not imply that the UI runs them or invent schema fields for them.
Live query testing requires separately authorized Azure scope.

### Confirm duplicates before merging

Merge only equivalent technical requirements. Keep an existing survivor ID and
retain retired IDs, names, original source and labels as aliases using the
manifest/dry-run process described in [AGENTS.md](AGENTS.md).
Reconcile or defer conflicts in scope, severity, WAF pillar, KQL and provenance.
Similar titles are not sufficient evidence for deletion.

Check selector compatibility and area/subarea membership after a merge.
Existing SQLite reviews remain pinned snapshots: never rewrite or combine
their assessments, comments or evidence as part of a corpus cleanup.

## Source-backed refreshes, not autonomous imports

Scheduled APRL, AKS-checklist and WAF service-guide ingestion is deprecated.
The importers are manual fallbacks whose output still requires reconciliation,
validation and human review. LLM-assisted research/editing produces proposals,
not automatic publication. Deterministic parsing, validation, assembly and
rendering remain required even when an LLM helped draft the change.

Read [Cost sources and coverage](review_checklists/docs/corpus-refresh/cost-sources.md)
and the [Cost refresh report](review_checklists/docs/corpus-refresh/cost-refresh-report.md)
for the established evidence/coverage pattern. Record untouched areas, rejected
proposals and gaps; a bounded refresh is not an exhaustive audit.

Azure Translator and Text Analytics endpoints used by the old pipelines are
decommissioned. Fork setup does **not** require provisioning them or adding their
secrets. Historical translations are not guaranteed to reflect current YAML.
See [scripts/README.md](scripts/README.md) for the retained deterministic tools
and manual adapters; optional future AI integrations are not implemented.

## Validate before requesting review

Use Python 3.11+ from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r review_checklists\requirements.txt
.\.venv\Scripts\python.exe -m review_checklists corpus validate
.\.venv\Scripts\python.exe -m review_checklists corpus build `
    --version "local-review" --output dist\catalog-local-review-a.json
.\.venv\Scripts\python.exe -m review_checklists corpus build `
    --version "local-review" --output dist\catalog-local-review-b.json
Get-FileHash dist\catalog-local-review-a.json, dist\catalog-local-review-b.json
```

For identical source and version, both SHA-256 hashes must match. Build commands
refuse overwrites: choose fresh output names rather than deleting unknown files.
Review the semantic diff, identities/aliases, provenance and selector membership
as well as schema results. Passing validation is not proof of technically correct
guidance or valid live KQL.

For application changes, run the relevant test modules first, then the needed
integration coverage; the full local suite is:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s review_checklists\tests -v
```

For script/legacy-adapter changes, use the dependencies and checks in the
[scripts guide](scripts/README.md). Documentation-only changes need relative-link
and command/configuration checks, not live Azure execution or a full app test run.
See the [application guide](review_checklists/README.md) for optional browser tests.
Never target a user's active review database in tests.

Human review remains required before merge. Do not equate validation success or
an LLM-generated diff with approval, production readiness, or an architecture sign-off.
