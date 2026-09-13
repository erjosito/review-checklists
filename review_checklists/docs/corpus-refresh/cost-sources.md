# Cost research sources and coverage

> This is the historical first-round source index. See the separate
> [second-round sources](full-refresh-2026-09-11/cost-sources.md) and
> [complete Cost outcome ledger](full-refresh-2026-09-11/cost-report.md)
> for subsequent readings, changes, mapping coverage and unresolved gaps.

This is the reviewer and future-refresh index for the **bounded 2026-09-11 Cost
refresh**, not an exhaustive Azure cost assessment. It records which primary
documentation was consulted, what it supports, what actually changed, and what
still needs investigation. Source verification here means successful retrieval
and reading of the recorded article or section during research. It does **not**
mean human approval, current subscription applicability, live KQL validation,
or proof of savings.

## Evidence files and actual application

| Artifact | Use |
| --- | --- |
| [cost-research.json](cost-research.json) | Structured inventory of all 30 sources, exact read scopes, 48 existing-GUID update proposals, eight addition proposals and overlap shortlists, 34 complete KQL variants, supporting references, rejected samples and coverage limits. |
| [cost-refresh-manifest.json](cost-refresh-manifest.json) | Historical refresh-stage application: affected GUIDs and repository-relative YAML filenames, before-update snapshots, changed fields, reasons, addition decisions, primary/supplemental assignments and the 179 then-unchanged Cost record hashes. Preserved unchanged after follow-on merges. |
| [cost-alias-migration.json](cost-alias-migration.json) | Actual follow-on application of nine approved Cost merges: original records/file hashes, approved and actual content hashes, resulting file hashes, exact retired-to-canonical mappings and measured stage counts. |
| [cost-refresh-report.md](cost-refresh-report.md) | Implementation results, the eight new stable IDs, query accounting, safety boundaries and local validation results. |

The research artifact contains **48 update proposals and eight addition
proposals**. The application manifest confirms that **all 48 updates and all
eight additions were applied** after comparison with existing content and
inspection of addition overlap candidates. **Zero additions were deferred;
zero existing Cost records were merged during the refresh stage.** These are separate facts:
the presence of a proposal in research is not, by itself, evidence of application.

At the end of that stage, the original **227 Cost checks** consisted of **48
updated checks and 179 unchanged checks**. The eight additions brought the
pre-merge Cost corpus to **235**; 56 records were refreshed or added.

A separately approved follow-on stage merged **nine confirmed duplicate
groups**, reducing Cost to **226 canonical records plus nine aliases**. All
235 original-plus-added identities and names survive as canonicals or aliases.
The 18 participating records were outside the source refresh: nine survive
canonically and nine are retained as aliases. **161 original records are still
truly untouched**, and all 56 refreshed/added records remain byte-unchanged by
the merges. The final canonical partition is **56 refreshed/added + nine
previously untouched merge survivors + 161 truly untouched = 226**.

Neither unchanged nor merely duplicate-merged checks are **implicitly
source-verified**. The historical refresh manifest identifies the original
179-record set; the separate migration artifact identifies the 18 later merge
participants and their full original content. Its mapping and hashes allow
reviewers to distinguish inherited evidence from new research. The measured
whole-corpus follow-on transition was **2,014 to 2,005 canonicals and 46 to 55
aliases**. Older whole-corpus counts in research are historical, not current.

Only the [nine-group approval](post-cost-safe-merge-manifest.json) was applied.
The App Gateway underutilization and ExpressRoute retirement pairs remain
technically deferred: narrower/expanded refreshed guidance and inventory queries
conflict with the other records' generic controls and unknown automation.
They require explicit semantic and query-contract reconciliation, not automatic
query donation. See the [refresh report](cost-refresh-report.md) for exact
pair IDs and the [post-refresh audit](post-cost-duplicate-review.json) for
technical blockers. These two merge deferrals are distinct from the zero
deferred addition proposals.

Existing canonical IDs, names, source objects and legacy metadata were retained.
New recommendations use collision-checked UUIDv5 IDs and `source.type: curated`.
Only explicit proposed service classifications were applied; empty service
lists were not filled with guessed aliases. Thirteen proposed resource-type
corrections are recorded in the manifest and research.

## Verified primary source inventory

All access dates below are **documentation access dates**, not publication or
last-modified dates. The IDs match `sourceInventory`, proposal `sourceRefs`, and
query `sourceRefs` in the structured research. All 30 sources appear in applied
provenance, including sources supporting associated supplemental variants.
An article supporting a topic does not establish that every sample in that
article is safe, adopted, or available in ARG.

| Source ID | Article title and verified URL | Accessed | What it supports in this refresh |
| --- | --- | --- | --- |
| `advisor-catalog` | [Cost recommendations](https://learn.microsoft.com/azure/advisor/advisor-reference-cost-recommendations) | 2026-09-11 | Published Advisor recommendation type IDs, supported recommendation topics and actions; exact type-ID filters for Advisor inventory. |
| `advisor-vm` | [Optimize virtual machine (VM) or virtual machine scale set (VMSS) spend by resizing or shutting down underutilized instances](https://learn.microsoft.com/azure/advisor/advisor-cost-recommendations) | 2026-09-11 | VM/VMSS rightsizing methodology, lookback, utilization evidence and limitations of estimated discounts/savings. |
| `finops-general` | [FinOps best practices for general resource management](https://learn.microsoft.com/cloud-computing/finops/best-practices/general) | 2026-09-11 | Cross-service Advisor Cost inventory and ongoing owner-led review. |
| `finops-compute` | [FinOps best practices for compute](https://learn.microsoft.com/cloud-computing/finops/best-practices/compute) | 2026-09-11 | VM, VMSS, AKS and licensing inventory; distinction between ARG configuration and non-ARG commitment/cost analytics. |
| `finops-storage` | [FinOps best practices for Storage](https://learn.microsoft.com/cloud-computing/finops/best-practices/storage) | 2026-09-11 | Disk, snapshot, backup and storage inventory candidates; lifecycle review rather than automatic deletion or savings assertions. |
| `finops-network` | [FinOps best practices for Networking](https://learn.microsoft.com/cloud-computing/finops/best-practices/networking) | 2026-09-11 | Networking inventory and orphan candidates, including public IPs, NAT gateways, DDoS plans, load balancers and ExpressRoute. |
| `finops-database` | [FinOps best practices for Databases](https://learn.microsoft.com/cloud-computing/finops/best-practices/databases) | 2026-09-11 | Cosmos DB Advisor opportunities and Azure SQL empty elastic-pool inventory. |
| `waf-checklist` | [Design review checklist for Cost Optimization](https://learn.microsoft.com/azure/well-architected/cost-optimization/checklist) | 2026-09-11 | CO:01 through CO:14 as an organizing framework; not a claim that every control was fully refreshed. |
| `waf-model` | [Architecture strategies for creating a cost model](https://learn.microsoft.com/azure/well-architected/cost-optimization/cost-model) | 2026-09-11 | Workload total cost, business unit economics, growth and resilience scenarios. |
| `waf-review` | [Architecture strategies for collecting and reviewing cost data](https://learn.microsoft.com/azure/well-architected/cost-optimization/collect-review-cost-data) | 2026-09-11 | Cost ownership, actual/amortized views, allocation, forecasts, anomalies and review actions. |
| `waf-data` | [Architecture strategies for optimizing data costs](https://learn.microsoft.com/azure/well-architected/cost-optimization/optimize-data-costs) | 2026-09-11 | Data lifecycle, replication, backup, compression and transfer tradeoffs. |
| `waf-guardrails` | [Architecture strategies for setting spending guardrails](https://learn.microsoft.com/azure/well-architected/cost-optimization/set-spending-guardrails) | 2026-09-11 | Policies, provisioning access, deployment approval gates and commitment utilization. |
| `commitments` | [Decide between a savings plan and a reservation](https://learn.microsoft.com/azure/cost-management-billing/savings-plan/decide-between-savings-plan-reservation) | 2026-09-11 | Rightsizing before commitments; stable baselines, eligibility and flexibility comparisons. |
| `exports` | [Tutorial: Create and manage Cost Management exports](https://learn.microsoft.com/azure/cost-management-billing/costs/tutorial-export-acm-data) | 2026-09-11 | Scheduled exports, supported datasets including FOCUS, prerequisites and run-history checks. |
| `focus` | [FinOps Open Cost and Usage Specification](https://learn.microsoft.com/cloud-computing/finops/focus/what-is-focus) | 2026-09-11 | BilledCost versus EffectiveCost, currencies, charge/commitment semantics and scope mappings. |
| `toolkit` | [FinOps toolkit overview](https://learn.microsoft.com/cloud-computing/finops/toolkit/finops-toolkit-overview) | 2026-09-11 | Available FinOps hubs, reports, workbooks and optimization workflow options; no toolkit deployment was performed. |
| `workbook` | [Optimization workbook](https://learn.microsoft.com/cloud-computing/finops/toolkit/workbooks/optimization) | 2026-09-11 | Rate and usage optimization review workflow supporting the Advisor action backlog. |
| `budgets` | [Tutorial: Create and manage budgets](https://learn.microsoft.com/azure/cost-management-billing/costs/tutorial-acm-create-budgets) | 2026-09-11 | Actual/forecast alerts, supported scopes and latency; budgets notify rather than automatically stopping spend. |
| `files-billing` | [Understand Azure Files billing](https://learn.microsoft.com/azure/storage/files/understanding-billing) | 2026-09-11 | Provisioned v2, provisioned v1 and PAYG distinctions; independent capacity, IOPS and throughput where supported. |
| `monitor` | [Cost optimization in Azure Monitor](https://learn.microsoft.com/azure/azure-monitor/fundamentals/best-practices-cost) | 2026-09-11 | Ingestion, retention, table plans, daily-cap risks and duplicate telemetry. |
| `sql-serverless` | [Serverless compute tier for Azure SQL Database](https://learn.microsoft.com/azure/azure-sql/database/serverless-tier-overview) | 2026-09-11 | Serverless versus provisioned compute and pooling decisions, minimum billing and auto-pause restrictions. |
| `windows-ahb` | [Explore Azure Hybrid Benefit for Windows VMs](https://learn.microsoft.com/azure/virtual-machines/windows/hybrid-use-benefit-licensing) | 2026-09-11 | License eligibility, core allocations, expiry and VM/VMSS license configuration; flags do not prove entitlement. |
| `sql-ahb` | [Azure Hybrid Benefit - Azure SQL Database & SQL Managed Instance](https://learn.microsoft.com/azure/azure-sql/azure-hybrid-benefit) | 2026-09-11 | SQL license eligibility and provisioned vCore applicability, including serverless/DTU exclusions. |
| `functions` | [Azure Functions hosting options](https://learn.microsoft.com/azure/azure-functions/functions-scale) | 2026-09-11 | Plan-dependent scaling, per-function/group boundaries, cold starts and always-ready capacity tradeoffs. |
| `expressroute` | [Plan and manage costs for Azure ExpressRoute](https://learn.microsoft.com/azure/expressroute/plan-manage-cost) | 2026-09-11 | Local/Standard/Premium, metered/unlimited, Direct, Global Reach and residual gateway/provider charges. |
| `aks-cost` | [Azure Kubernetes Service (AKS) cost analysis](https://learn.microsoft.com/azure/aks/cost-analysis) | 2026-09-11 | Native allocation, idle/unallocated costs, eligibility, prerequisites and limitations. |
| `aks-vpa` | [Vertical pod autoscaling in Azure Kubernetes Service (AKS)](https://learn.microsoft.com/azure/aks/vertical-pod-autoscaler) | 2026-09-11 | Recommendation mode, update modes, workload limitations and interaction with HPA. |
| `arg-power` | [Advanced Resource Graph query samples](https://learn.microsoft.com/azure/governance/resource-graph/samples/advanced#summarize-virtual-machine-by-the-power-states-extended-property) | 2026-09-11 | Documented VM instance-view `powerState.code`; the stopped-but-allocated inventory uses the explicit stopped code. |
| `arg-language` | [Understanding the Azure Resource Graph query language](https://learn.microsoft.com/azure/governance/resource-graph/concepts/query-language) | 2026-09-11 | ARG tables, supported joins/aggregations, extended properties and expansion limits; not live compilation of these queries. |
| `disk-state` | [Disks - Get](https://learn.microsoft.com/rest/api/compute/disks/get#diskstate) | 2026-09-11 | Official disk-state enumeration and disk SKU schema used to qualify unattached-disk inventory. |

### Depth of source reading

The structured inventory records `readScope` for every source. Most entries
record a full article read, but that never implies exhaustive traversal of
related links. The bounded reads were:

| Source ID | Recorded reading boundary |
| --- | --- |
| `waf-review` | Main guidance through Azure facilitation; related links not exhaustively followed. |
| `waf-data` | Main guidance through Optimize file formats. |
| `exports` | Introduction, functionality, prerequisites, create exports, firewall and manage exports sections. |
| `budgets` | Introduction and prerequisites through Create a budget. |
| `files-billing` | Billing, media, redundancy, resource models, TCO and provisioned v2 through provisioning. |
| `monitor` | Logs, resource logs, alerts, VM and Container cost optimization. |
| `functions` | Hosting options, plan overview, OS support, scale and cold start sections. |
| `arg-power` | Power-state sample discovered through code sample search; article fetched and focused section read. |
| `arg-language` | Resource Graph tables, extended properties and supported KQL language elements. |
| `disk-state` | DiskState enumeration and disk SKU schema. |

## Coverage by service and theme

These are the themes addressed, not a checklist of fully covered services.
Source IDs refer to the inventory above; per-recommendation evidence is mapped
in the JSON files.

| Service/theme | Applied scope | Main source IDs |
| --- | --- | --- |
| Governance and FinOps | Budget alerts, reporting, exports/FOCUS and guardrails updated; cross-service Advisor action backlog and workload cost model added. | `waf-checklist`, `waf-model`, `waf-review`, `waf-guardrails`, `budgets`, `exports`, `focus`, `finops-general`, `toolkit`, `workbook` |
| VM/VMSS and commitments | Rightsizing, Advisor lookback, deallocation, nonproduction schedules, commitment utilization and Windows licensing guidance updated. | `advisor-vm`, `advisor-catalog`, `finops-compute`, `commitments`, `windows-ahb`, `arg-power` |
| Managed disks and snapshots | Unattached-disk and tier-selection guidance updated; snapshot SKU/retention review added. | `finops-storage`, `disk-state`, `waf-data` |
| Networking | Orphan chargeable resources, ExpressRoute economics/retirement and empty Application Gateways updated. Both unsupported ExpressRoute compliance heuristics replaced. | `finops-network`, `expressroute`, `arg-language` |
| AKS | Node autoscaling, VPA, cost allocation, Spot and duplicate telemetry guidance updated. | `finops-compute`, `advisor-catalog`, `aks-cost`, `aks-vpa`, `monitor` |
| Azure Monitor | DCR filtering, ingestion/table-plan/retention choices and safe log lifecycle guidance updated. | `monitor`, `advisor-catalog`, `waf-data` |
| Azure SQL | Hybrid Benefit guidance updated; compute-model choice and empty elastic-pool review added. | `sql-ahb`, `sql-serverless`, `finops-database` |
| Cosmos DB | Throughput economics and inactive-container review added as separate decisions. | `finops-database`, `advisor-catalog` |
| Blob Storage and Azure Files | Blob transaction/tiering/recovery-history economics and Files billing/provisioning/commitment guidance updated. | `finops-storage`, `waf-data`, `files-billing`, `advisor-catalog` |
| Backup | SQL/HANA backup schedules and retained backups without visible source resources updated. | `finops-storage`, `waf-data`, `advisor-catalog` |
| App Service and Functions | App Service sizing/commitments and Functions hosting/scaling/always-ready guidance updated; empty App Service plan review added. | `advisor-catalog`, `commitments`, `functions` |
| Synapse Spark and AVS | Spark auto-pause/autoscaling and AVS commitment review updated; not a complete service sizing audit. | `advisor-catalog`, `finops-compute`, `commitments` |

## Primary versus supplemental KQL

The research preserves **34 unique KQL variants**. The app supports **one
primary `queries.arg` per recommendation**: **31 primary assignments using 28
unique queries** are wired. These comprise 25 updated records (two replacements
and 23 first queries) and six additions. Cost checks with primary queries
therefore increased from **2 to 31**.

The nine follow-on merges changed none of these queries or source references.
All merge members had empty queries and `unknown` automation. Final Cost
coverage remains 31 query-bearing canonicals out of 226, with the same 30
verified sources and the same primary/supplemental catalog. Final automation
counts are 31 `query_available`, 14 `candidate`, 11 `manual` and 170 `unknown`;
the reduction in unknown canonicals reflects deduplication, not validation.

**Six additional unique variants are supplemental-only**, with six supplemental
assignments. They remain documented evidence and are not executed by the UI:

| Supplemental query ID | Associated recommendation | Primary query actually wired |
| --- | --- | --- |
| `nat-unassociated` | `64f9a19a-f29c-495d-94c6-c7919ca0f6c5` | `publicip-unassociated` |
| `ddos-unassociated` | `64f9a19a-f29c-495d-94c6-c7919ca0f6c5` | `publicip-unassociated` |
| `lb-empty` | `64f9a19a-f29c-495d-94c6-c7919ca0f6c5` | `publicip-unassociated` |
| `advisor-aks-autoscale` | `c1b1cd52-1e54-4a29-a9de-39ac0e7c28dc` | `aks-pools` |
| `advisor-aks-spot` | `357e61fe-86e6-41c6-b446-3f0def6d8bcf` | `aks-pools` |
| `aged-snapshots` | `28856508-bfa7-5f94-82d8-7f6b53817bfe` | `premium-snapshots` |

All 34 catalog variants are **inventory**, including Advisor recommendations.
All 31 wired queries have `resultSemantics: inventory` and `validatedAt: null`.
`query_available` means query text is available, not that it has been executed
or technically validated against Azure. The remaining refreshed checks are
14 `candidate` and 11 `manual`; they do not have invented ARG substitutes for
financial, utilization, licensing or business evidence.

No live Azure query or KQL compilation was performed. Empty results, missing fields,
incomplete permissions, eventual consistency or truncated output cannot
establish compliance or zero waste. Inventory is not realized savings or
permission to delete resources. `provenance.upstreamRevision` and
`lastReviewed` remain null; source access dates must not be copied into them.

## Non-exhaustiveness, rejected evidence and known gaps

The 30 sources are a bounded starting set, not a census of authoritative Azure
cost guidance. A verified source does not validate every existing Cost check,
every service feature, every resource property or every offer/region. The
research explicitly leaves these areas without exhaustive treatment:

| Gap | Outstanding investigation |
| --- | --- |
| Original Cost corpus | The 179 checks outside the source refresh: 161 still untouched and 18 subsequently involved in duplicate merges, not source revalidation. Also all Advisor types, changing recommendation IDs and API/schema versions. |
| MySQL/PostgreSQL | Flexible Server sizing, stop/start limits, storage/autogrow and burstable credits. |
| Analytics platforms | Data Factory failed-pipeline cost, Data Explorer cache/autoscale, Databricks jobs/serverless/SQL, Fabric capacities and OneLake. |
| OpenAI/Foundry | Current model pricing, prompt caching, batch/provisioned commitments and token-control APIs; suspicious existing image-count claims need a dedicated verified refresh. |
| Application platforms | Container Apps, Container Registry, detailed Functions billing/Durable Functions edge cases and current App Service SKU eligibility matrices. |
| Storage indexing and data-plane evidence | SFTP/encryption-scope ARG coverage, per-blob tier/last-access analytics and top-level Microsoft.FileShares ARG support. |
| Networking economics | Firewall throughput/features, Front Door SKU economics, DDoS plan/IP comparisons and VPN P2S dependencies. |
| Specialized compute, backup and licensing | SAP certification, all database backup constraints, AVS sizing limits, Linux licensing, SQL VM extension registration and centralized SQL license assignments. |
| Pricing and access | Negotiated prices, discounts, sovereign regions, offer-specific billing scopes and actual subscription/billing permissions. |
| Live ARG behavior | Syntax/runtime compatibility, indexed property completeness, pagination, expansion limits, eventual consistency and permissions. |

The attempted fetch of
<https://learn.microsoft.com/azure/expressroute/expressroute-about-local-circuits>
failed; it is **not** one of the 30 verified sources. The verified replacement
was the `expressroute` cost-planning article in the inventory. Public search
was used for discovery, not as proof; unsupported generated claims were not
adopted.

The structured `rejectedOrQualifiedSourceSamples` explains important exclusions
and adaptations. Examples include malformed stopped-VM sample syntax,
unsupported processor-architecture inference from SKU names, and treating old
backup timestamps as proof that source resources were deleted. Review those
decisions before reintroducing an official sample: being published does not
make a sample suitable for this recommendation's semantics. Legacy unrelated
links retained for compatibility are not endorsed as refresh evidence.

## Procedure for a future refresh

1. Read this coverage index, the structured research, the historical refresh
   manifest, the actual alias-migration artifact and the current repository
   instructions. Choose a bounded service/theme or
   known gap. Establish current Cost counts and inspect existing GUIDs, names,
   aliases, constraints and queries; do not assume the historical baseline is
   still current.
2. Revisit authoritative Microsoft Learn service documentation, the Advisor
   catalog, WAF and relevant FinOps guidance. Verify actual article content,
   current eligibility, recommendation IDs and documented property paths.
   Record the real access date, title, URL and sections read, plus failures or
   unresolved freshness concerns. An old access date or a search snippet is
   not fresh verification.
3. Compare proposed guidance with canonical records and aliases by technical
   decision, resource/service scope, pillar, severity and query meaning.
   Prefer an existing-GUID update. Add only clearly distinct requirements,
   check ID/name collisions, and explicitly defer ambiguous overlaps. Preserve
   identity and legacy provenance; reconcile concurrent content changes before
   writing. A duplicate shortlist is not authorization to merge.
4. Use only supported, source-backed queries and the intended execution engine.
   Do not invent ARG properties or substitute inventory for billing, metrics,
   entitlements or business judgment. Keep uncertain automation `candidate`,
   `manual` or `unknown` with reasons. Record exact KQL, semantics, required
   scopes/data, limits and false positives. Wire only one primary `queries.arg`;
   retain supplemental variants in research without implying app execution.
5. Apply reviewed content through the shared corpus helpers and authoritative
   schema. Keep unknown `upstreamRevision`, `lastReviewed` and `validatedAt`
   null. Source retrieval or an LLM edit is not human approval or live
   validation. Do not execute Azure queries or publish changes without explicit
   authorization and scope.
6. Review the semantic diff and source evidence, then run targeted regression
   tests, `corpus validate` and the repository's deterministic bundle checks
   as applicable. Local schema/tests do not prove Azure technical correctness.
   Record actual applied/deferred counts, unchanged coverage, primary versus
   supplemental counts, validation outcomes and remaining gaps. Preserve
   structured evidence and a readable report for human review and the next
   refresh rather than relying on conversation history.
