# Service catalogue and classification normalization

`scripts/service_dictionary.json` is the single catalogue. Existing `service`,
`names` and `arm` values retain the legacy importer contract. Additive
`displayName` provides friendly English labels; old service keys and aliases
remain accepted case-insensitively in CLI filters and saved URLs.
`resourceTypes` optionally supplies many-to-many applicability, overriding the
legacy primary ARM field. Duplicate legacy entries are aggregated.
An optional `inferredResourceTypes` subset restricts which of those types can
suggest the service without additional configuration evidence. WAF uses this
distinction: it can apply to Front Door/Application Gateway hosts, but the host
type alone does not establish WAF enablement. Its policy types still suggest WAF.
The subset must contain unique types present in `resourceTypes`.

Explicit `services: []` remains **uncurated**, not automatically classified.
Shared types (including Web sites, storage accounts and virtual network gateways)
retain a technical display fallback rather than inventing a particular service.
Friendly service filters also accept catalogue candidates on uncurated records;
this is possible applicability, not curated evidence. A raw ARM filter always
matches actual resourceTypes, even when an explicit service is present.

Mechanical normalization lowercases types, trims outer whitespace, sorts and
deduplicates them. No type
is repaired, added or removed except identical case-insensitive duplicates.
Queries, recommendation IDs, sources, aliases and all guidance remain untouched.
Unknown service names remain visible and are reported, never silently assigned
to a default. Disjoint known service/resource scopes are reported for review;
an auxiliary resource or a shared type is not by itself a contradiction.
Advisor and Cost Management are explicitly cross-cutting catalogue entries.

## Auditable offline command

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m review_checklists.service_normalization `
  --report service-normalization-plan.json
# Inspect summary, changed fields, hashes and classification gaps before applying.
.\.venv\Scripts\python.exe -m review_checklists.service_normalization `
  --apply-plan service-normalization-plan.json `
  --report review_checklists\docs\corpus-refresh\service-normalization-next.json
```

Reports refuse overwrites. Apply regenerates/validates the entire plan and rejects
stale or modified inputs before any writes. Only classification YAML blocks are
rewritten. The report includes original/current file and document hashes,
protected-field hashes, reversible field edits, all IDs and classification gaps.
No Azure calls or live query validation occur.

The historical `corpus-refresh/service-normalization.json` stage covers 2,011
canonical records and 55 aliases: 335 resource-type normalizations, including
one service-list ordering change. The 1,990 empty classifications remain empty;
21 explicit classifications resolve to catalogue labels. No unknown service
names or known-scope contradictions were found. There are 569 records with shared
types, not 569 errors. Eleven records retain unresolved legacy ARM spellings:
six `microsoft.datafactory/datafactories` and five
`microsoft.network/frontdoorwebapplicationfirewalls`. Repairing those could change
applicability and needs a separate source-backed decision.

The subsequent [source-backed follow-up](corpus-refresh/followup-2026-09-13.md)
records that decision separately. It recognizes the real legacy
`microsoft.datafactory/datafactories` type alongside `factories`, without treating
them as aliases. Five recommendations now explicitly target v2; one missing-source
playbook remains unchanged. Five WAF applicability records and the Photon/Spark
requirement were reconciled. There are no remaining unknown ARM spellings in the
current corpus, but that is not proof of current provisioning availability or
complete service curation. Legacy importer `arm`/`names` fields retain their
compatibility role, not an exhaustive current applicability contract.

Checklist `serviceSelector` values accept the same friendly aliases as CLI/UI
filters. They still match explicit service metadata only; no new service
inference is introduced into checklist selection.

Added catalogue entries are grounded in the existing explicit Cost
classifications (Advisor, Cost Management, managed disks, SQL Managed Instance,
NAT Gateway and DDoS Protection). The CDN candidate prevents falsely identifying
every `Microsoft.Cdn/profiles` resource as Front Door. Catalogue candidates are
not an exhaustive ARM registry or a claim of live resource validation.

## Shared API and history

`scripts.modules.cl_services` exposes `normalize_service_name`,
`normalize_services`, `normalize_resource_types`, `semantic_classification`,
`classifications_equivalent`, `services_for_resource_type`,
`resource_types_for_service`, `service_catalogue` and `classify_applicability`.
Semantic comparison preserves missing versus explicitly empty fields and treats
only declared alias/case/order/duplicate normalization as equivalent.

Pinned review snapshots are never rewritten by this command. Historical pillar
manifests remain immutable. Their regression tests first verify/reverse any later
amendment ledgers, then verify normalization's file, document and protected-field
hashes and reverse its classification edits. All original guidance/query/identity/
hash assertions remain in place. Catalogue diagnostics are checked against the
hash-bound historical catalogue, not silently reinterpreted using newer mappings.
