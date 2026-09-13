# Cost content refresh - 2026-09-11

> Historical first-refresh and merge-stage results below are preserved. The separate
> [second Cost round](full-refresh-2026-09-11/cost-report.md) accounts for all 226
> post-merge canonicals, subsequent content changes, upstream mappings and explicit gaps.

The content-refresh stage applied **48 existing-GUID updates and eight
additions**, with **zero deferred additions** and no merges during that stage:
Cost records increased from **227 to 235**. A separately approved follow-on
stage applied **nine Cost duplicate merges**, leaving **226 canonical Cost
records and nine Cost aliases**. All 235 original-plus-added Cost identities
remain addressable.

The merges involved 18 of the 179 records untouched by the source refresh:
nine remain canonical and nine are aliases. **161 original records remain
truly untouched**. All 56 refreshed or added records remain byte-unchanged by
the merges. Duplicate confirmation is not source verification of inherited
guidance. This bounded work does not complete a corpus-wide audit.

## Durable evidence and exact changes

- [cost-sources.md](cost-sources.md) is the readable inventory of all 30 verified
  URLs, titles and access dates, service/theme coverage, gaps and future-refresh
  procedure for reviewers and subsequent LLM sessions.
- [cost-refresh-manifest.json](cost-refresh-manifest.json) lists all 56 affected
  GUIDs and repository-relative YAML filenames, application reasons, addition
  overlap decisions, changed fields, before-update snapshots, source references,
  primary/supplemental query assignments, and Cost-only baseline counts. It is
  immutable historical evidence of the 235-record pre-merge refresh stage.
- [cost-alias-migration.json](cost-alias-migration.json) records the actual
  follow-on merge results, approved and actual content hashes, original file
  hashes and full record snapshots, resulting file hashes, all retired-to-
  canonical mappings, and measured before/after counts. It references the
  separate [nine-group approval manifest](post-cost-safe-merge-manifest.json).
- [cost-research.json](cost-research.json) preserves the completed research:
  30 verified public primary sources, all 48 update proposals, all eight addition
  proposals and their duplicate shortlists, all 34 exact KQL variants, source
  references, required scopes/data, false-positive caveats, rejected samples,
  and coverage limits. It is a research snapshot, not a claim that every variant
  is executed by the application.

All proposed content fields matched the existing name, title, description and
query evidence before application. Byte hashes from research were not used as
the conflict gate because the additive schema migration changed file bytes.
Existing canonical IDs, names, labels, source objects, legacy review metadata,
links, severity and other unrelated fields were preserved. Before snapshots
retain the superseded content for audit purposes, not as current guidance.

## Follow-on Cost merges

The hardened merge tool matched all nine approval `beforeContentHash` values,
completed a dry-run, then applied exactly the same groups. All nonparticipating
files were byte-identical, including non-Cost files. The original refresh
manifest and research JSON were not overwritten. The measured whole-corpus
transition was **2,014 to 2,005 canonical recommendations**, and **46 to 55
aliases**; this stage added only the nine Cost aliases.

| Retired ID (retained as alias) | Surviving canonical ID |
| --- | --- |
| 96bcda1b-240a-4d4b-93fa-6872b549d711 | d0c4b44f-7b43-428c-93f2-dedd7bf00799 |
| 30cbe437-b17d-45ad-a42e-a26bef6f4b77 | 6f1432ef-61d2-4037-8f85-58e005d16b8c |
| 0ce550b6-f2ed-428c-b8c2-b224c065a0db | ac8bb190-71ba-48ec-9fef-351c1cd5501f |
| 7327aac3-008f-4878-bf49-a6c3f76746a1 | edd459fa-3105-4a03-b009-4f983d23da5a |
| 96599299-4653-4e94-989b-8c7fe64cb2bd | 92eec823-61dd-486c-b46e-0339fc02987e |
| 5473960a-7ac3-44a0-8d01-695132b782cd | 18f1f2f6-de79-405d-b7a1-65fb571c0493 |
| f0c38fed-fc9f-458d-aab7-9b03b8a0dfea | a5675d94-de9f-44b1-8b21-f8032cdf3f3d |
| 2d710fcf-b8bc-461d-81a1-895193ce91cc | 73967d95-39ff-47bb-b4f4-33ddade69d1f |
| a36bac4f-bf10-44c6-a51e-0d845162b3af | 3c5f0966-3c57-4e15-a6b0-6cb73405bbf1 |

The exact original names, sources and labels are retained in aliases, with
the original recommendation bodies preserved in the migration artifact.
Survivor guidance, empty queries and `unknown` automation remain unchanged;
links are combined without dropping evidence. No source access, review,
upstream revision or live validation claims were added to these records.
In particular, equivalence of the two inherited Application Gateway stop/start
records does not independently certify their billing statement.

**Two groups remain technically deferred**, as recorded in the
[post-refresh duplicate review](post-cost-duplicate-review.json):

- Application Gateway `7947e534-c9a8-435b-9e03-d300143b5f74` and
  `74ad737c-cbb8-4e91-84b7-2aa937b37ede`: the refreshed zero-backend-target
  inventory and safeguards are narrower than general utilization review.
  The second record has no equivalent query/automation contract.
- ExpressRoute `c36e0c83-11b4-409a-a4a6-2118b52a380f` and
  `271b6cfe-4507-4afa-a1e5-000e3be105ac`: the refreshed `NotProvisioned`
  inventory does not measure general inactivity. Expanded provider, gateway,
  residual-charge and recovery guidance cannot be silently reduced to the
  older deprovisioning control or donated to its unknown automation.

## Query accounting and safety

| Measure | Count |
| --- | ---: |
| Cost records with a wired primary `queries.arg`, before / after | 2 / 31 |
| Existing primary queries replaced | 2 |
| Existing records gaining their first primary query | 23 |
| Added records with a primary query | 6 |
| Wired primary assignments / unique KQL texts | 31 / 28 |
| Supplemental-only assignments / unique KQL texts | 6 / 6 |
| Full research query catalog | 34 |
| Verified sources / distinct sources in applied provenance | 30 / 30 |
| Refreshed statuses: query_available / candidate / manual | 31 / 14 / 11 |

These query and source counts are unchanged by the nine merges: **31 primary
assignments, 28 unique primary queries, six supplemental-only variants, 34
catalog variants and 30 sources**. The final Cost automation distribution is
31 `query_available`, 14 `candidate`, 11 `manual` and 170 `unknown`. The
`unknown` count fell from 179 only because nine duplicate canonicals became
aliases, not because their automation or guidance was verified.

Both ExpressRoute SKU/data-plan compliance heuristics were replaced with the
supplied configuration inventory query, not merely relabelled:
`f4e7926a-ec35-476e-a412-5dd17136bd62` and
`7025b442-f6e9-4af6-b11f-c9574916016f`.

The supplemental-only variants are `advisor-aks-autoscale`, `advisor-aks-spot`,
`aged-snapshots`, `ddos-unassociated`, `lb-empty`, and `nat-unassociated`. Their
complete KQL and evidence remain in the catalog. For the broad orphan-networking
recommendation, the app executes only the proposed public-IP primary query;
NAT, DDoS and load-balancer variants are documentation-only. Similarly, the two
AKS pool controls use pool inventory as primary, and the snapshot control uses
Premium snapshot inventory rather than the supplemental age query.

Every wired query has `resultSemantics: inventory` and `validatedAt: null`.
No live Azure execution or KQL compilation was performed. Query availability
does not mean compliance automation, realized savings, deletion approval, or
complete resource coverage. Empty, partial or permission-limited results are
not a pass. Billing, utilization, ownership, retention, dependencies and
workload requirements still require separate evidence.

Source `accessedAt: 2026-09-11` records documentation access, not human approval
or live validation. `provenance.upstreamRevision` and `lastReviewed` remain null.
The original catalog's proposal-stage wording about validation before
integration remains historical evidence; the applied corpus deliberately
exposes unvalidated inventory rather than claiming validated automation.

## Additions and overlap decisions

| Added name | Stable UUIDv5 |
| --- | --- |
| cost-AdvisorActionBacklog | 570cc0b7-8bcc-54bc-b0a3-abf24374c97b |
| cost-WorkloadCostModelUnitEconomics | ccf66d9e-1364-576b-9b40-16f91a5b52b7 |
| cost-SqlDatabaseComputeModel | 4f3e4c7b-78e3-5170-8ef9-903de93cd563 |
| cost-SqlEmptyElasticPools | 82a6242d-ee75-51c0-bf02-bd357c422c30 |
| cost-CosmosThroughputEconomics | ed807702-4e85-5b2e-b191-3fc76fe70a60 |
| cost-CosmosIdleContainers | 577a5f04-5ce3-5bf2-be7b-28c1ec86f362 |
| cost-ManagedDiskSnapshotLifecycle | 28856508-bfa7-5f94-82d8-7f6b53817bfe |
| cost-AppServiceEmptyPlans | fe224a34-ae94-57de-8570-e8bae87812f7 |

All eight shortlists were inspected. Similar wording resolved to different
resource scopes or decisions: OpenAI provisioned throughput is not Cosmos RU
economics; Synapse pools are not Azure SQL elastic pools; AKS node-pool and Files
snapshots are not managed disk snapshots; App Service density/sizing differs
from retiring a zero-app plan. The workload-wide model and Advisor backlog
cover cross-service decisions absent from the inspected service-specific
records. No uncertain overlap remained, so none were deferred. Related records
were not merged or retired. New IDs and names were checked against canonical
records and aliases, and new records use `source.type: curated` with public URLs.
These addition decisions describe the source-refresh stage; the later nine
merges involve only other, previously untouched records.

## Scope boundaries and remaining concerns

Only explicitly proposed service labels were applied; empty service lists remain
uncurated. No alias taxonomy was inferred. Thirteen proposed `resourceTypes`
corrections align the records with their actual target resources, including
VMSS, disks, SQL databases/managed instances, networking, workspaces, backup
vaults and App Service plans. Their exact before/after scope is recoverable from
the manifest and research. Legacy links were preserved even when unrelated or
mistargeted; the newly recorded provenance is the refresh evidence.

This is not an exhaustive refresh of all Cost rules, Advisor types or Azure
services. In particular, OpenAI/Foundry pricing and token controls,
MySQL/PostgreSQL, Data Factory, Data Explorer, Databricks, Fabric, Container
Apps, detailed Functions billing, service-specific licensing and sovereign
offers remain outside the verified coverage. The full limits and the failed
ExpressRoute page fetch with its verified replacement are in the catalog.

The application/schema, non-Cost duplicate merges and corpus-wide audit remain
outside this change. No multiple-query execution support, Azure queries,
deployments, commits or pushes were introduced.

## Targeted validation

`review_checklists.tests.test_cost_refresh` checks the exact expected IDs,
unchanged legacy metadata and truly untouched Cost records, honest provenance,
source references, exact primary KQL, inventory semantics, supplemental
separation, collision-free curated additions, shared-schema validity, YAML
serialization, sanitized artifacts and measured Cost/query increases. Its
counts do not depend on simultaneous non-Cost merges. Follow-on checks compare
the 18 original merge participants to the historical refresh hashes and the
approved merge hashes, verify exact surviving records and alias source/name/
label metadata, confirm retired files are absent, and verify final file hashes.
All original Cost identities remain covered, not merely the surviving IDs.

After the follow-on merges, **48 targeted Cost, shared-contract and hardened
merge tests passed**, and the full corpus passed `corpus validate` with
2,005 recommendations and their aliases. The full-folder validator also
passed with **2,005 recommendations and nine checklists**. These are local
content/schema checks, not live Azure validation.

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest review_checklists.tests.test_cost_refresh review_checklists.tests.test_corpus_contract review_checklists.tests.test_corpus_merges
.\.venv\Scripts\python.exe -m review_checklists corpus validate
.\.venv\Scripts\python.exe -m scripts.validate_corpus --root v2
```
