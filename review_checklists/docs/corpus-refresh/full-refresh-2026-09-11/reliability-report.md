# Reliability slice - 2026-09-11

This bounded slice updates **34 existing recommendations**, adds **one
workload-wide design-simplicity check**, and documents **eight supported,
guidance-unchanged recommendations**. Seven remain byte-unchanged; one gained
only its previously assessed upstream mapping. **385 baseline recommendations remain
needsmanualreview**. This is not a completed technical refresh of all
Reliability guidance or a blanket source-freshness claim.

The frozen scope is exactly **427 initially Reliability, non-APRL GUIDs**.
The resulting owned set contains 428 canonical GUIDs. APRL is excluded by source
type regardless of subsequent pillar classification. No identifiers, names,
aliases, original source objects, resource classifications, severities or folder
locations were changed. No deletes or merges occurred. Existing review databases
were not opened or modified; no live Azure query, recovery drill, commit or push
was performed.

## Durable accounting

| Artifact | Contents |
| --- | --- |
| `reliability-baseline.json` | Frozen GUIDs, original paths, complete before documents and byte/canonical-content SHA256 hashes |
| `reliability-manifest.json` | One explicit outcome for every baseline GUID, evidence or honest gap, changed before/after fields, final hashes, exact queries, sources and reading limits, addition overlap decisions |
| `reliability-waf-inventory.json` | Complete dated inventory of the ten published RE checklist rows, page-reported revision and shared-parser item hashes |
| `reliability-waf-coverage.json` | Reproducible hash-matched semantic coverage of those rows |
| `reliability-advisor-inventory.json` | Nine explicitly identified and read Advisor catalog items; **partial**, not a whole-catalog denominator |
| `reliability-advisor-coverage.json` | Three full and six partial assessments of the observed items; whole-catalog percentages deliberately unavailable |

Canonical content hashes use UTF-8 JSON with sorted keys, compact separators
and unescaped Unicode. File hashes cover exact bytes. Upstream item hashes
are a separate contract supplied by `review_checklists.source_coverage` and
the shared source parser; they are not hashes of paraphrases or URLs.

All 427 records were triaged from their frozen title, identity, source and
resource scope. The 34 updates and eight supported-unchanged decisions received
the specific source comparisons described in the manifest. The other 385
records did **not** receive complete current service-level verification.
Their individual entries say so, preserve original bytes and identify the
inherited requirement and scope. A generic WAF citation does not approve them.

## Meaningful corrections

- **Key Vault:** correct configurable 7-90-day retention rather than fixed
  90 days; include missing RBAC/Event Grid recovery dependencies; qualify
  best-effort regional failover, read-only behavior and unsupported regions;
  remove the blanket fixed-distance replication promise.
- **Application Gateway:** remove the retired v1 deployment exception.
  Current v2 default zone redundancy means an omitted `zones` array is not
  noncompliance. Separate configured autoscale minimum from internal platform
  instance count and actual surviving-zone capacity.
- **Cosmos DB:** distinguish service-managed replicas from user-selected
  account regions; describe per-region zone settings, continuous backup
  7/30/35-day windows and restore exclusions, consistency/conflict tradeoffs,
  and real failover delays rather than a zero-downtime guarantee.
- **Storage and Backup:** distinguish zone availability, geographic
  durability and backups. Correct Azure Files secondary-read claims and require
  RA-GRS/RA-GZRS for supported Blob reads before failover. Qualify Backup
  secure-by-default rollout, retention and operational/log-recovery exclusions.
- **App Service and workload design:** include eligible Premium v4 plans,
  scale-unit constraints and best-effort replacement capacity; reject deprecated
  linked-database backups; replace component-SLA-as-SLO-ceiling wording with
  business targets and measured evidence; strengthen scoped failure analysis,
  scaling, recovery, testing and retained monitoring telemetry.

## Upstream coverage is not source-link coverage

| Source and inventory scope | Denominator | Full | Partial | Whole-scope percentage |
| --- | ---: | ---: | ---: | --- |
| `waf-reliability-checklist`: published RE checklist rows | 10 | 1 | 9 | 10% full; 90% partial |
| `advisor-reliability-catalog`: published Reliability catalog | **Unknown** | 3 observed | 6 observed | **Unavailable** |

The new workload-wide simplicity check fully addresses the **RE:01 control
row**, not every paragraph in its linked guide. RE:02-RE:10 map to existing
App Service or VM checks with explicit **partial** coverage because those
service scopes do not cover every workload, dependency and critical flow.
No supporting-only, stale or unverified mapping is promoted to full coverage.
There is no claim of 100% full WAF Reliability coverage.

The Advisor legacy high-availability URL redirects to the canonical
`advisor-reference-reliability-recommendations` page. The anonymous shared
reader refused the redirect; the canonical URL was then fetched explicitly.
The shared complete-catalog parser rejected the ID-less **Avoid placing
Traffic Manager behind Front Door** section. A later identically titled
section has a different resource scope and an actual GUID; that GUID was
**not** assigned to the ID-less section. Nine previously read, explicitly
identified sections were captured with the shared section parser in a
**partial** inventory. The omitted catalog remains unverified; nine is not
the denominator for a catalog percentage.

Advisor conflicts are visible in mapping notes: its Cosmos service-managed
failover text promises no downtime, while the current service reliability
guide describes possible hour-or-longer account failover. The service guide
controls the paraphrase. Catalog backup wording mentions 30 days, while
current backup documentation includes 7/30/35-day options. Zone redundancy is
not presented as protection from an entire regional outage.

All **19 evaluated mappings** now persist in YAML
`provenance.upstreamRecommendations`, so corpus and bundle coverage work without
an external mappings argument. The previously external, partial Advisor
health-check assessment was embedded unchanged as a **mapping-only metadata
change**; the eight supported-guidance outcomes are unchanged, while seven of
those records remain byte-identical. Exact notes, coverage status, source ID,
hash and assessment date were preserved. The note's original external-assessment
wording is historical context, not its current storage location.
The external mapping remains in the manifest as audit evidence only and must
not also be supplied as an active mapping, which would duplicate the assessment.
Final hashes and mapping-only accounting are in `mappingOnlyMetadataChanges`
and `lineageIntegration`. No new semantic assessment or network access occurred.
All 13 focused tests pass after embedding, including serialized bundle
round-trip coverage with no separate mappings argument.
`assessedAt` dates identify this source comparison, not a human review or
deployment validation. Source `accessedAt` dates identify actual page access;
`lastReviewed`, recommendation `upstreamRevision` and `validatedAt` remain null.
Inventory revisions are page-reported upstream revisions, separately scoped.

## Query semantics and limits

The owned baseline and result each have **15 wired ARG queries**. Exactly
two payloads were replaced, both Application Gateway heuristics, with the
same supported-property configuration inventory. No first-time query was
added. The inventory projects resource identity, location, reported zones,
SKU/capacity and autoscale min/max values; it neither measures runtime
instances nor certifies zone resilience, backend health, SLOs or recovery.
Null properties, missing permissions, partial scope and zero rows are never
a compliance pass. No live execution or KQL compilation was performed.

The **13 inherited AKS/networking queries remain byte-unchanged and explicitly
unverified**, with unknown semantics. This includes the obsolete AKS
`sku.tier == 'Paid'` heuristic, zone-SKU heuristics, rule-count thresholds,
peering/circuit coverage and outbound-rule inference. They must not be treated
as reliable compliance automation merely because their payloads contain a
column named `compliant`. The manifest retains every exact before/after query.

## Addition and overlap boundaries

New GUID `c6c87882-4b54-5f08-9950-5a8b7ac0f546`
(`reliability-WorkloadSimplicityDecisionReview`) requires architecture/code
review of complexity against functional and nonfunctional business needs.
It has no ARG query and does not duplicate a service configuration switch.

The global overlap search included all pillars, APRL, aliases, titles,
descriptions and other serialized fields. Seven candidates are recorded
with their existing GUIDs and decisions. Function storage isolation and
App Service affinity are narrower implementations. ML curated environments,
SAP subscription placement, authentication, Firewall service tags and model
complexity have different scopes or pillar objectives. Cross-owned records
remain intact; related Operations references were proposed to their owner,
not copied into new duplicate controls.

## Remaining verification work

The 385 individually recorded gaps include SAP/vendor support matrices,
APIM tiers, Spring Apps lifecycle, AVS/HCX limits, Redis lifecycle, AKS
networking and ingress, AI services, Data Factory, relational databases,
IoT, Event Hubs, Kusto, Machine Learning, detailed networking, Purview and
other Storage/Functions/Logic Apps requirements. Existing contradictory,
obsolete or unsupported assertions in that set are **not approved by this
pass**. No folder or pillar correction was used to conceal a gap.

The manifest records 18 accessed sources and exactly which portions were
read. Fetching a long page did not establish reading of every section or its
linked documents. App Service/Storage service and SKU matrices, real SLA
contracts, tenant-specific Advisor findings, runtime measurements and actual
restores require separate evidence.

The focused regression module is
`review_checklists.tests.test_full_refresh_reliability`. It pins the frozen
baseline, identity/alias/source preservation, each outcome, exact content and
query payloads, provenance, scoped additions and shared-schema validity,
without weakening unrelated global-count assertions.

Local validation completed with **11 focused tests passing**, shared corpus
validation and a successful bundle build. The concurrent corpus contained
2,011 recommendations at that observation; this is not a fixed global-count
claim or a Reliability-only total. The build stayed in the session artifact
directory, not the authoring tree or any review database. These checks validate
data contracts and audit reproducibility, not Azure behavior or human approval.
