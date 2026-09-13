# Second-round Cost sources and refresh procedure

**Access date: 2026-09-11.** This is the separate 226-canonical Cost round, not a rewrite of the [first-round 30-source index](../cost-sources.md). Nineteen primary pages were read in this round; some were already used historically and are not nineteen newly discovered sources. Source access does not mean human review, live KQL validation, applicability to a tenant or realized savings.

The outcome is **27 content updates, 122 supported-unchanged guidance decisions and 77 explicit manual-review gaps**. Eighteen supported-unchanged records received mapping-only metadata, so 45 YAML files changed. There are no additions, deletions or merges. The [report](cost-report.md) lists all 226 GUIDs; the [manifest](cost-refresh-manifest.json) preserves exact decisions, before references, after documents and hashes.

## Primary reading inventory

Counts identify records whose written guidance was compared with the reading. They are not coverage percentages or live resource checks. Mapping evidence is counted separately in JSON. Reading scopes explicitly identify partial articles rather than implying every section was reviewed.

| ID | Article and public URL | Accessed | What was read / supported | Guidance records |
| --- | --- | --- | --- | ---: |
| `waf` | [Design review checklist for Cost Optimization](https://learn.microsoft.com/azure/well-architected/cost-optimization/checklist) | 2026-09-11 | Full 14-row CO:01 through CO:14 checklist. | 6 |
| `advisor` | [Cost recommendations - Azure Advisor](https://learn.microsoft.com/azure/advisor/advisor-reference-cost-recommendations) | 2026-09-11 | Full catalog read in three consecutive sections, including published IDs and resource scopes. | 10 |
| `finops` | [FinOps best practices for general resource management](https://learn.microsoft.com/cloud-computing/finops/best-practices/general) | 2026-09-11 | Full article; documented AdvisorResources Cost inventory and projected properties. | 4 |
| `ai-cost` | [Plan and Manage Costs - Microsoft Foundry](https://learn.microsoft.com/azure/foundry/concepts/manage-costs) | 2026-09-11 | Prerequisites, estimates, reconciliation, billing models, fine-tuned deployment hosting and cost monitoring; portal walkthrough not exhaustively read. | 9 |
| `ai-reasoning` | [Azure OpenAI reasoning models](https://learn.microsoft.com/azure/foundry/openai/how-to/reasoning) | 2026-09-11 | How reasoning works, context, cost control, incomplete responses and model-dependent effort; not the full API matrix. | 5 |
| `ai-batch` | [How to use global batch processing with Azure OpenAI in Microsoft Foundry Models](https://learn.microsoft.com/azure/foundry/openai/how-to/batch) | 2026-09-11 | Introduction, turnaround target, cancellation charging, residency, model availability and feature constraints. | 1 |
| `files` | [Understand Azure Files Billing](https://learn.microsoft.com/azure/storage/files/understanding-billing) | 2026-09-11 | Billing/media/resource models, TCO, provisioned v2 recommendations/availability/guardrails, soft-delete meters, provisioned v1 and PAYG access-tier guidance. | 12 |
| `appgw` | [Architecture best practices for Azure Application Gateway](https://learn.microsoft.com/azure/well-architected/service-guides/azure-application-gateway) | 2026-09-11 | Cost Optimization checklist and configuration recommendations. | 5 |
| `firewall` | [Architecture best practices for Azure Firewall](https://learn.microsoft.com/azure/well-architected/service-guides/azure-firewall) | 2026-09-11 | Cost Optimization checklist and configuration recommendations. | 13 |
| `frontdoor` | [Architecture best practices for Azure Front Door](https://learn.microsoft.com/azure/well-architected/service-guides/azure-front-door) | 2026-09-11 | Cost Optimization checklist and configuration recommendations. | 9 |
| `blob` | [Architecture best practices for Azure Blob Storage](https://learn.microsoft.com/azure/well-architected/service-guides/azure-blob-storage) | 2026-09-11 | Cost checklist from meter-unit example onward, lifecycle/feature costs, guardrails, monitoring and full configuration recommendations. | 24 |
| `ml` | [Architecture best practices for Azure Machine Learning](https://learn.microsoft.com/azure/well-architected/service-guides/azure-machine-learning) | 2026-09-11 | Complete Cost Optimization checklist and configuration recommendations. | 13 |
| `aks` | [Architecture best practices for Azure Kubernetes Service](https://learn.microsoft.com/azure/well-architected/service-guides/azure-kubernetes-service) | 2026-09-11 | Cost Optimization checklist/configuration; adjacent Operational Excellence KEDA recommendation. | 15 |
| `vm` | [Architecture best practices for Azure Virtual Machines](https://learn.microsoft.com/azure/well-architected/service-guides/virtual-machines) | 2026-09-11 | Complete Cost Optimization checklist and configuration recommendations. | 12 |
| `er` | [Plan to manage costs for Azure ExpressRoute](https://learn.microsoft.com/azure/expressroute/plan-manage-cost) | 2026-09-11 | Full article including SKUs, Direct/Global Reach, gateway residual charges, budgets and exports. | 8 |
| `spot` | [About Azure Spot Virtual Machines](https://learn.microsoft.com/azure/virtual-machines/spot-vms) | 2026-09-11 | Overview through pricing/eviction history and documented SpotResources queries; FAQ not fully read. | 1 |
| `disk-ri` | [Optimize costs for Azure Disk Storage with reservations](https://learn.microsoft.com/azure/virtual-machines/disks-reserved-capacity) | 2026-09-11 | Overview, per-SKU consumption, eligibility table, purchase considerations/restrictions; purchase walkthrough only partially read. | 1 |
| `app` | [Architecture best practices for App Service Web Apps](https://learn.microsoft.com/azure/well-architected/service-guides/app-service-web-apps) | 2026-09-11 | Complete Cost Optimization checklist and configuration recommendations. | 11 |
| `frontdoor-probes` | [Health Probes - Azure Front Door](https://learn.microsoft.com/azure/frontdoor/health-probes) | 2026-09-11 | Full article, including HEAD recommendation, 200-only healthy status, all-origin failure and single-origin probe disabling. | 2 |

## Service/theme coverage and limits

The source set covers broad WAF financial governance, cost models, guardrails, rates, component/data/scaling costs and consolidation; the published Advisor Cost opportunity catalog and ARG projection; Foundry/OpenAI billing, reasoning and Batch; Azure Files models; Blob lifecycle/feature costs; VM/Spot/disk commitments; AKS and ML capacity; App Service; and Application Gateway, Firewall, Front Door and ExpressRoute cost guidance.

It is **not exhaustive**. Dedicated SAP/HANA support matrices, commerce/licensing programs, Functions plan billing, backup/ASR constraints, Monitor table plans and certain AKS operational features remain material follow-up areas. The exact 77 gaps are recorded per GUID; old research remains evidence of its own stage, not proof that all assertions were freshly checked here. Inherited service/resource aliases were preserved rather than guessed. In particular, Front Door Classic and Standard/Premium indexing must not be conflated.

The requested old Azure OpenAI guide URL `https://learn.microsoft.com/azure/well-architected/service-guides/azure-openai` now redirects to `https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure`. This freshness issue is recorded separately; a model catalog is not the former cost guide. The prior AI Foundry manage-cost URL also resolves to the current Foundry cost article in the table.

## What the upstream measurement means

The source pipeline supplies dated, complete inventories **within two narrow scopes**: 14 WAF Cost checklist rows and 66 published Advisor Cost catalog entries. The 24 mappings on 22 local canonicals were compared semantically with exact item payloads. Full and partial mappings contain the shared `item_content_hash` fingerprint; unmatched, changed or missing evidence must not silently become coverage.

WAF: **1 full, 11 partial, 2 unknown** (CO:09 and CO:13). Advisor: **4 full, 6 partial, 56 unknown**. These are distinct upstream IDs, not local row counts or citation counts. Partial percentages are reported separately, and an unknown mapping does not prove that another pillar has no matching control. The generic Advisor backlog query does not count as coverage of all 66 recommendations.

Cost mappings and snapshot copies use the central registry IDs `waf-cost-checklist` and `advisor-cost-catalog`. The earlier draft names were parent proposals, not user requirements, and have been corrected. The explicit normalization record in [cost-sources.json](cost-sources.json) retains previous draft names and central paths/file hashes. Both inventories now equal the central snapshots exactly: all 14 WAF and 66 Advisor item payloads and content hashes agree. No duplicate source or false uncovered count is introduced. Retrieval metadata and page-reported revisions are unchanged; page revision is not an invented local `provenance.upstreamRevision` or human `lastReviewed` date.

No previous complete dated inventory exists in this work, so newly observed upstream IDs are not labelled newly introduced. The new snapshots allow a later exact new/changed/removed comparison.

## Query evidence and execution boundary

The three new primary queries are documented in full below and in the structured catalog. They extend the current documented AdvisorResources projection with exact published type IDs. All are unexecuted inventory, with null validation dates and no compliance columns. A returned Advisor row is a review opportunity, not a verified violation or guaranteed saving. Required scope/permissions, paging, telemetry freshness, dismissals and billing assumptions remain reviewer obligations.

Cost now has **34 primary assignments / 31 unique primary texts**. The six historical supplemental-only variants are still documentation-only; this round creates no supplemental variants or multi-query app support. The first-round 34-variant catalog and new three-query catalog together preserve 37 distinct variants.

### `a6bcca2b-4fea-41db-b3dd-95d48c7c891d`

Published Advisor ID: `0eb54047-acd9-4f26-8ffb-8cec713782d6`. Primary only; inventory; liveExecuted=false; validatedAt=null.

```kusto
AdvisorResources
| where type =~ 'microsoft.advisor/recommendations'
| where properties.category =~ 'Cost'
| where tostring(properties.recommendationTypeId) in~ ('0eb54047-acd9-4f26-8ffb-8cec713782d6')
| project id, subscriptionId, resourceGroup,
    targetResourceId = tostring(properties.resourceMetadata.resourceId),
    impactedField = tostring(properties.impactedField),
    recommendationTypeId = tostring(properties.recommendationTypeId),
    impact = tostring(properties.impact),
    problem = tostring(properties.shortDescription.problem),
    solution = tostring(properties.shortDescription.solution),
    lastUpdated = tostring(properties.lastUpdated),
    extendedProperties = properties.extendedProperties
```

### `544451e1-92d3-4442-a3c7-628637a551c5`

Published Advisor ID: `e10b1381-5f0a-47ff-8c7b-37bd13d7c974`. Primary only; inventory; liveExecuted=false; validatedAt=null.

```kusto
AdvisorResources
| where type =~ 'microsoft.advisor/recommendations'
| where properties.category =~ 'Cost'
| where tostring(properties.recommendationTypeId) in~ ('e10b1381-5f0a-47ff-8c7b-37bd13d7c974')
| project id, subscriptionId, resourceGroup,
    targetResourceId = tostring(properties.resourceMetadata.resourceId),
    impactedField = tostring(properties.impactedField),
    recommendationTypeId = tostring(properties.recommendationTypeId),
    impact = tostring(properties.impact),
    problem = tostring(properties.shortDescription.problem),
    solution = tostring(properties.shortDescription.solution),
    lastUpdated = tostring(properties.lastUpdated),
    extendedProperties = properties.extendedProperties
```

### `f397a438-b320-46f8-a41a-f94545db3412`

Published Advisor ID: `1c7fc5ab-f776-4aee-8236-ab478519f68f`. Primary only; inventory; liveExecuted=false; validatedAt=null.

```kusto
AdvisorResources
| where type =~ 'microsoft.advisor/recommendations'
| where properties.category =~ 'Cost'
| where tostring(properties.recommendationTypeId) in~ ('1c7fc5ab-f776-4aee-8236-ab478519f68f')
| project id, subscriptionId, resourceGroup,
    targetResourceId = tostring(properties.resourceMetadata.resourceId),
    impactedField = tostring(properties.impactedField),
    recommendationTypeId = tostring(properties.recommendationTypeId),
    impact = tostring(properties.impact),
    problem = tostring(properties.shortDescription.problem),
    solution = tostring(properties.shortDescription.solution),
    lastUpdated = tostring(properties.lastUpdated),
    extendedProperties = properties.extendedProperties
```

## Future-refresh procedure

1. Freeze the current Cost canonicals, aliases and exact source/query/provenance fields before changes. Keep earlier manifests immutable and coordinate cross-pillar ownership.
2. Revisit the authoritative sources above and source-specific eligibility/support documents for each target assertion. Follow redirects, inspect publication changes and record the actual reading scope and access date. Prioritize the explicit per-GUID gaps rather than assuming this index is exhaustive.
3. Fetch a new dated inventory with the shared source-audit adapters and canonical registry source IDs. Preserve scope, unit and fingerprint definition; integrate newly verified inventories centrally rather than inventing pillar-local source names. Use `diff_inventories` to distinguish exact new, changed and removed IDs; incomplete/undated baselines mean not measured, not zero or new.
4. Compare each upstream item with existing canonical GUIDs and aliases across pillars. Record full/partial/supporting rationale using the actual item ID and `item_content_hash`; a citation or matching query filter is not a semantic mapping. Report cross-owned matches rather than editing them.
5. Paraphrase verified guidance and preserve canonical identity/import origin. Add a new control only after a concrete gap and overlap review; use stable collision-checked IDs. Do not create speculative ARG queries, fabricate remote IDs or claim service indexing that was not verified.
6. Keep one primary `queries.arg`; record supplemental variants separately. Use inventory semantics unless a real violation/compliance contract is established. Keep live validation dates null without actual authorized execution; obtain independent review for consequential claims.
7. Record every baseline GUID as updated, supported unchanged or an explicit unresolved gap, separately from mapping status. Recompute coverage only for complete scopes, run the Cost/history/schema/merge tests and corpus/full-folder validators, then report actual changes, gaps and source/query counts.
