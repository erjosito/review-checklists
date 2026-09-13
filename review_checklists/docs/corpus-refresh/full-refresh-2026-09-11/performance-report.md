# Performance refresh - 2026-09-11

The frozen **175 initial non-APRL Performance recommendations** have individual
guidance outcomes: **53 updated, 71 supported with unchanged guidance, and 51
requiring manual review**. Three justified curated practices were added, leaving **178 owned
canonical records and nine unchanged aliases**. No existing identity, name,
original source, primary pillar, classification, folder, or alias was moved,
merged, deleted, or replaced.

This completes accounting for the assigned slice, **not technical verification
of every baseline claim or every Azure performance best practice**. APRL records
remain outside ownership even if another refresh classifies them as Performance.
Other agents' changes are not attributed to this report.

## Durable evidence

| Artifact | Purpose |
| --- | --- |
| [performance-baseline.json](performance-baseline.json) | Frozen GUID/path list, complete initial records and original file-byte hashes. Selection is not rerun after APRL/pillar changes. |
| [performance-manifest.json](performance-manifest.json) | Every baseline outcome, reason and evidence references; before/after records, field differences, semantic hashes and file hashes; additions and overlap decisions. |
| [performance-sources.json](performance-sources.json) | 33 retrieved primary references, actual access dates, exact reading boundaries, failed/misdirected fetches and research limits. |
| [performance-queries.json](performance-queries.json) | Three exact inventory KQL texts across five assignments; two removed queries retained as historical evidence. |
| [performance-mapping-proposals.json](performance-mapping-proposals.json) | Explicit corpus-to-upstream ID semantic assessments, current item hashes, cross-owned proposals and deferred additions. |
| [performance-waf-inventory.json](performance-waf-inventory.json), [performance-advisor-inventory.json](performance-advisor-inventory.json) | Complete dated inventories of the respective single published checklist/catalog pages, with declared fingerprint representations. |
| [performance-waf-coverage.json](performance-waf-coverage.json), [performance-advisor-coverage.json](performance-advisor-coverage.json) | Computed, scoped coverage using the shared `review_checklists.source_coverage` API, not URL or KQL-GUID matching. |
| [performance-source-normalization.json](performance-source-normalization.json) | Explicit old-to-canonical source identities, before/after fingerprints and item hashes, and measured agreement with central snapshots. |
| [performance-lineage-validation.json](performance-lineage-validation.json) | Actual generated-bundle readback proving all 16 mappings and both coverage reports survive without external mapping arguments. |

Local recommendation semantic hashes use UTF-8 compact sorted-key JSON with
`ensure_ascii=False`. File hashes cover actual bytes. These are different from
upstream item hashes. The baseline GUID-set digest is
`6180f0661f5694948c61440d6a51730f4a11ae97ab7d40ee4384549e4f0fca92`
(SHA-256 of sorted GUIDs joined by newlines without a trailing newline).

## Meaningful corrections

- **AKS:** distinguish overlay, pod-subnet and legacy CNI defaults and IP
  consumption; include surge capacity; separate node autoscaling from pod
  autoscaling; replace autoscaler-profile presence as a configuration verdict;
  qualify ephemeral/Ultra Disk advice; retain legitimate stateful CSI workloads.
- **OpenAI:** distinguish TPM admission quota from achieved throughput and
  first-token latency from complete generation time. Remove unconditional PTU
  production mandates and maximum-latency guarantees. Replace the claim that
  provisioned overflow always requires a custom gateway with native spillover
  prerequisites, failure behavior, monitoring and cost caveats.
- **Application Gateway:** remove stale scale-up timing and ambiguous
  average/peak arithmetic, size v2 capacity with headroom, and replace optional
  migration language after v1's documented 2026-04-28 retirement. Distinguish
  increasing a configured maximum from billing for consumed capacity.
- **Firewall:** retain required observability while limiting expensive optional
  diagnostics, measure SNAT pressure, avoid assumed backend-instance capacity
  guarantees, and verify warm-up/observed capacity. Current prescaling guidance
  was incorporated into the existing warm-up/capacity check rather than added
  as an overlapping record.
- **ExpressRoute and virtual networks:** update FastPath eligibility for
  ErGwScale and topology/circuit restrictions; replace SKU and `/16` compliance
  heuristics with configuration inventory and workload-specific assessment.
- **Front Door:** remove unsupported `CdnResources` queries and null-as-pass
  probe logic. Qualify HEAD compatibility and single-origin probe decisions.
  Correct language implying that active probes collect health only on changes.
- **Storage and App Service:** qualify small-block hash-prefix advice; explicitly
  distinguish the general Blob checklist's 256 KiB statement from the developer
  checklist's standard/premium thresholds. Add Files metadata caching to the
  existing access-pattern check. Add initialization headroom, numerical/tail
  latency targets, baseline comparisons and load-test acceptance/stop criteria.

Updated YAML gains relevant source citations, deliberate content/automation edits
and the evaluated lineage described below. Source access dates are not copied to
`lastReviewed`, `upstreamRevision`, or `validatedAt`. Of the 71
supported-unchanged guidance records, **67 retain their original bytes and four
receive only upstream lineage metadata**. All 51 manual-review records retain
their original bytes, including unresolved guidance; they must not be treated
as newly endorsed.

### Final lineage integration

All **16 already-assessed mappings** are now embedded in
`provenance.upstreamRecommendations` on **16 owned YAML records**: 13 baseline
records and the three additions. Their source IDs, upstream IDs, URLs, hashes,
dates, notes and full/partial/supporting levels are copied exactly from the
assessed audit file. No semantic assessment was added or promoted, no network
access was used, and no unassessed or cross-owned proposal was embedded.

The manifest preserves each participant's pre-lineage record and file/content
hashes in `lineageMetadata`, updates its final hashes and field differences,
and separately records `lineageIntegration`. Guidance outcome counts remain
**53 / 71 / 51**. Including the four metadata-only baseline changes, **57 baseline
files differ and 118 remain byte-identical** to the frozen baseline.

## Additions and overlap

| Added stable ID | Practice and distinction |
| --- | --- |
| `5c8617a0-c1a5-5d95-9520-646263b48cd9` | `performance-FlowPerformanceTargets`: a workload-wide target register covering every flow, unlike existing VM, App Service and ML target checks. |
| `0f62530d-f4e5-5687-bba9-8da9e63af7cd` | `performance-OperationalTaskBudgets`: measured cross-task performance budgets, not another individual backup, antivirus or deployment check. |
| `730f27c7-3b7e-5c10-86e9-00d86105a898` | `performance-PerformanceIncidentTriage`: performance-specific diagnosis, restoration and recurrence prevention, distinct from security incident response and generic alerts. |

All names/IDs were checked against the entire corpus and aliases before writing.
The overlap search covered titles and descriptions for performance targets,
budgets, load tests, capacity, critical flows, prioritization, incidents, triage,
operational work, deployment effects, LocalDNS, metadata caching and prescaling.
The closest cross-owned records were read before deciding on additions.
The manifest retains the exact candidate GUIDs and individual decisions.

No separate generic critical-flow prioritization check was added. Existing
OpenAI prioritization and Reliability-owned App Service flow prioritization
support partial PE:09 mappings. Operations-owned release testing and blue/green
deployment controls are also proposed as cross-owned mappings, not duplicated,
edited or counted here. LocalDNS/high-scale Container Insights additions are
deferred pending feature-specific and overlap review; Files metadata caching
was incorporated into an existing check.

## Queries and evidence semantics

| Measure | Before | After |
| --- | ---: | ---: |
| Owned baseline records with primary ARG text | 7 | 5 |
| Distinct primary KQL texts | 7 | 3 |
| Added practices with ARG text | - | 0 |

Five existing primary assignments were replaced: three AKS checks share node-pool
inventory, one inventories gateway SKUs, and one inventories VNet address/subnet
configuration. Two Front Door queries were removed because the retrieved ARG
reference did not establish their table/child-resource support. Their original
texts remain in the reports; portal/service API evidence is required instead.

All five current queries declare **`inventory`**, with **`validatedAt: null`**.
None is a violations query or automatic compliance decision. Query text was not
compiled or executed against Azure. No latency, utilization, load-test result,
available capacity or service health is invented from configuration. Missing
fields, incomplete permissions, truncation, eventual consistency and empty
results cannot establish a pass. The app executes one primary query per check;
there are no hidden supplemental query assignments.

The App Service load-test guidance explicitly separates acceptance criteria
from auto-stop. The retrieved Load Testing documentation supports request-level
latency percentiles and notes that server-side failure criteria are not
configurable through Azure Pipelines/GitHub Actions. This is documentation-backed
manual evidence guidance, not live test execution.

## Upstream-ID coverage

The inventories use the shared `item_content_hash`, `validate_inventory` and
`coverage_report` implementation. WAF IDs come from all 12 current checklist
rows. Advisor IDs come from all **150 unique explicit Recommendation IDs** in
the fetched public Performance catalog. The catalog includes historical items
such as a 2021 Bastion recommendation; its presence is not a current adoption
recommendation.

The current WAF source is **`waf-performance-checklist`**. Its inventory now
copies the pipeline's verified `{id,code,recommendation}` payloads and
`item.contentHash` values exactly: **12 of 12 payloads and hashes agree** with
the central snapshot. All 13 WAF mapping entries use those exact target hashes
and URLs. The checklist statements were compared before rebinding; coverage
levels and rationale did not change.

The current Advisor source is **`advisor-performance-catalog`**. Renaming
preserves all **150 existing item payloads and hashes**. This inventory's
declared fingerprint uses digests of the actual normalized retrieved sections.
Central promotion and registration were requested from the pipeline owner;
the normalization record explicitly tracks that handoff as pending until a
central snapshot can be compared.

The earlier `azure-waf-performance` and `azure-advisor-performance` names are
recorded only as historical normalization inputs, not additional current
sources. The WAF fingerprint change is explicit, not a silent alias relabeling
of incompatible hashes. No new upstream fetch was needed. Neither this change
nor the lack of a comparable historical snapshot establishes upstream additions
or removals.

| Source scope | Denominator | Full | Partial | Supporting only | Unassessed |
| --- | ---: | ---: | ---: | ---: | ---: |
| WAF Performance checklist controls | 12 | 3 | 9 | 0 | 0 |
| Published Advisor Performance catalog IDs | 150 | 0 | 2 | 1 | 147 |

The three full WAF assessments concern **PE:01, PE:10 and PE:11**, limited to
their checklist control statements. The nine other controls have explicitly
limited service-specific mappings, not full workload-wide implementations.
The measured WAF full-coverage value is **25%**, with **75% partial**. These are
recorded semantic assessments, not independent human approval or proof that
every Performance best practice is represented.

Advisor mappings cover only parts of Application Gateway scaling and Firewall
network-rule optimization. Classic Front Door's HEAD-probe recommendation is
supporting-only because of the resource-scope mismatch. The computed catalog
result is **0% full, 1.33% partial**, with 147 IDs still unassessed. Catalog
retrieval and GUID presence are not semantic coverage.

Mappings now persist in the corpus and generated bundles. Call
`coverage_report(inventory, recommendations)` **without a separate mappings
argument**. The retained `performance-mapping-proposals.json` is audit evidence;
do not pass the same mappings again alongside embedded records. Duplicate
assessments are rejected rather than counted twice. Cross-owned proposals remain
external and uncounted. Embedded assessments are not inferred from links or
represented as independent human approval.

## Research boundaries and gaps

The verified reference set includes the complete WAF Performance checklist;
the target, testing, critical-flow, operational-task and live-incident guides;
a bounded scaling-guide read; and the **Performance sections only** of nine
service guides (VM, AKS, ML, App Service, Firewall, Application Gateway, Front
Door, Files and ExpressRoute). Additional reads cover OpenAI latency/spillover,
AKS networking/node/storage behavior, Blob transfer guidance, Load Testing
criteria, VNet planning, FastPath, retirement and ARG support.

The source inventory documents six failed or misdirected URLs and their
replacements. In particular, the old OpenAI service-guide URL returned a model
catalog, not its architecture guidance. That result was not counted as source
verification of gateway or fine-tuning recommendations.

The **51 explicit manual-review outcomes** include SAP/vendor diagnostic and
support assertions, AVS/HCX scaling and connectivity, APIM tier/topology details,
selected AKS feature/event/OS guidance, Firewall security/topology claims,
network architecture requirements and detailed Blob monitoring. Every affected
GUID and its exact inherited subject is preserved in the baseline/manifest.
For example, the Linux `tcp_timestamps = 0` instruction remains unverified,
not silently endorsed. Remaining source-supported recommendations can still
need workload-specific applicability evidence.

## Validation results

- **24 tests passed**: the thirteen-test Performance module plus eleven shared
  corpus-contract tests. Checks cover frozen IDs, all outcomes, aliases,
  unchanged bytes, exact KQL, metadata honesty, shared-schema/YAML round trips,
  stable additions, explicit source mappings, stale hashes and missing/empty
  inventory denominators. The normalization follow-up also verifies canonical
  source IDs, exact central WAF payload/hash agreement and unchanged Advisor
  item hashes. Final lineage tests prove metadata-only accounting, exact
  preservation of all assessed mappings, bundle round trips, sidecar-free
  coverage and rejection of duplicate sidecar-plus-embedded assessments.
- The shared application validator passed with **2,011 recommendations and
  aliases** at the observed integration snapshot.
- The folder validator passed with **2,011 recommendations and nine checklists**.
- A draft bundle was built in session artifacts, with content hash
  `sha256:fb986eb8a0e301d970bf3d47a083723437ab695621dbb8236ed4813de38d4d2c`.
  The real bundle was read back and its 178 owned records reproduced both
  recorded coverage reports without supplying a mappings argument.
  These whole-corpus counts/hash reflect concurrent owners' work at that moment,
  not a persistent global-count assertion in the Performance tests.

No live Azure, deployments, nested agents, commits or pushes were used. Global
dataset-count tests, core code, scripts, schema and historical reports were not
edited by this slice.
