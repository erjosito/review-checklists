# Operational Excellence bounded refresh - 2026-09-11

**The entire frozen 279-record non-APRL Operations slice has an explicit outcome:
38 updated, 38 supported unchanged, and 203 needing manual review.** Two
source-backed curated checks were added. This is a completed bounded pass with
visible gaps, not a claim that all 279 records have current verified guidance.

## Ownership and durable evidence

The selection was frozen before authoring: `waf: Operations` and
`source.type != aprl`. It contained 175 `revcl` and 104 `wafsg` records, with 11
aliases. All 279 canonical GUIDs, names, aliases, labels, original source objects,
severities, service/resource classifications and paths remain intact. No record
was moved, merged, deleted or reclassified by this worker. No newly classified
APRL record was written. Other pillars, APRL, core/schema/scripts and historical
reports were outside ownership.

- `operations-baseline.json`: exact frozen GUID list, original records and byte
  hashes. Sorted GUID-list SHA-256:
  `f181032b378471c61106a7f4fd0890242b0731dbf5f8372e63a87b815be7e363`.
- `operations-manifest.json`: one outcome per baseline GUID, reasons, evidence
  references, remaining gaps, changed fields with before/after values, semantic
  and byte hashes, additions, read scopes and exact upstream mappings.
- `operations-waf-inventory.json` and `operations-advisor-inventory.json`:
  dated primary-source inventories with meaningful-payload hashes.
- `operations-source-coverage.json`: reproducible unique upstream-ID accounting
  for this worker's mappings, plus a cross-owned proposal.
- `operations-sources.md`: reading boundaries and refresh caveats.

The 38 supported-unchanged records and all 203 manual-review records remain
byte-identical to the frozen baseline. Evidence supporting unchanged records is
in the manifest, not added as an implicit freshness stamp. The 38 updates have
current `provenance.sources`; original `source` still records origin. Existing
`lastReviewed`, `upstreamRevision` and query validation dates were not promoted
from documentation access. The two new checks have null review/revision/
validation metadata.

## Meaningful changes

The pass corrected retired WAD/LAD and Log Analytics agent deployment advice,
distinguished Azure Update Manager from monitoring-agent migration, modernized
AKS log/Prometheus/control-plane monitoring and Container insights authentication
guidance, and removed a blanket ban on governed external log export.

IaC, CI/CD, operational ownership, emergency fixes and testing now identify
inspectable process evidence rather than treating Azure configuration as proof
of human practices. Application Gateway affinity is conditional; copied Load
Balancer timeout advice was removed from an Application Gateway check. A Firewall
backup check now distinguishes Firewall Policy from Azure Policy artifacts.

Front Door guidance distinguishes Standard/Premium from retiring classic,
certificate offload from renewal prerequisites, and HTTP redirects from TLS
client compatibility. App Service guidance distinguishes free managed
certificates from Key Vault imports and qualifies deployment-slot capacity,
settings and stateful rollback. Network Watcher traffic monitoring now includes
NSG-to-virtual-network-flow-log migration.

## Query reconciliation

All four baseline query payloads were individually reviewed. **Two documented
configuration inventories replace two compliance heuristics; two unsafe queries
were removed.** No new query was invented for runbooks, incident processes or
monitoring effectiveness.

| Existing canonical GUID | Result |
| --- | --- |
| `eaa8dc4a-2436-47b3-9697-15b1752beee0` | AKS monitoring add-on inventory, with enabled state, workspace and managed-identity configuration. It does not measure actual delivery, alternate tools, alert quality or log retention. |
| `73b32a5a-67f7-4a9e-b5b3-1f38c3f39812` | AKS `nodeResourceGroup` inventory. The default `MC_` prefix is valid; custom naming is optional and creation-time only. |
| `c755562f-2b4e-4456-9b4d-874a748b662e` | Removed optional virtual-node enablement compliance test. Applicability depends on ACI, networking, OS and workload limitations. |
| `af95c92d-d723-4f4a-98d7-8722324efd4d` | Removed reversed managed-certificate predicate and unverified `CdnResources` query. A missing certificate type or `CustomerCertificate` does not prove use of a managed certificate. ARM schema evidence alone does not establish ARG indexing. |

Both remaining queries have `resultSemantics: inventory`, `validatedAt: null`
and explicit no-zero-row-pass caveats. Properties can be missing or stale;
permissions and selected scope can make inventories incomplete. No live ARG
execution, KQL compilation, Azure login, subscription change or deployment was
performed. The superseded KQL remains in baseline and field-change evidence,
not as an executable supplemental query.

## Additions and overlap decisions

| New stable UUIDv5 | Check |
| --- | --- |
| `482a84af-0360-55ab-be33-6d8e4706b580` | `operations-VersionedOperationalRunbooks` - standardize and exercise routine, ad-hoc and emergency procedures (OE:02). |
| `eac9d939-9c58-5bf4-aa1d-1c77d8068036` | `operations-ReliableLifecycleAutomation` - assess automation value, security, reliability, maintenance, ownership and lifecycle review (OE:10). |

Before adding these, the whole corpus was searched for runbooks, SOPs,
operational readiness, incident processes, quality gates, lifecycle automation,
reliable automation and related terms. Related AVS manual deployment, VM
bootstrapping/emergency patching, APIM PowerShell and AVS scaling-monitoring
records were read and retained: their service/task-specific requirements do not
replace workload-wide operating-procedure or automation-quality controls.
Exact shortlist GUIDs and decisions are in the additions manifest.

The Security-owned incident-response record
`b86ad884-08e3-4727-94b8-75ba18f20459` overlaps OE:08. A supporting cross-owned
mapping/enrichment proposal is recorded, **not applied or counted as coverage**.
No duplicate generic Operations incident-response record was added.

## Upstream-ID coverage, not citation counts

Both inventories were captured from complete nonempty published pages using
the shared public-reader and strict inventory/hash APIs. The WAF unit is one
numbered checklist row, not every linked guidance paragraph. OE:07 has two
guidance links in one code cell: both are retained in the fingerprint and the
row is counted once. The Advisor unit is one published recommendation GUID
section, not a customer-specific finding or all Advisor categories.

| Source ID | Inventory | Full | Partial | Unassessed | Full coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| `waf-operations-checklist` | 11 | 2 | 6 | 3 | 18.18% |
| `advisor-operations-catalog` | 122 | 3 | 2 | 117 | 2.46% |

These are **only this worker's explicit semantic mappings**, not integrated
all-corpus coverage. All counted full/partial mappings match the current item
hashes. Partial mappings are separate, never summed into full coverage.
Supporting, stale and outside-inventory counts are zero in these assessed
sources; unknown remains unknown, not evidence of absence from the corpus.

Mapped updated/new records carry `provenance.upstreamRecommendations`. Three
assessed mappings to supported-unchanged records are external report evidence,
so their YAML stays byte-identical. Hash payloads use the pipeline's
`item_content_hash`; the temporary WAF extractor handled the duplicate OE:07
links while preserving the adapter-defined payload. The shared pipeline owner
was notified of the parser case and source naming proposals. No fabricated IDs or
hashes were used.

After the pipeline snapshot became available, all 11 control IDs, payloads and
hashes were compared and matched
`waf-operations-checklist--2026-09-11--84fd234f106eacce573ee415497edd96436e6620--938e88b5449f.json`
exactly. Following the explicit coordination correction, our new references
and reports now use `waf-operations-checklist` and `advisor-operations-catalog`.
The earlier `azure-waf-operations` and `azure-advisor-operations` names were
parent proposals, not user requirements. No new upstream fetch was performed.

`operations-source-id-normalization.json` records the old/new names, 24 applied
reference changes in 23 owned records, three external-reference changes and
before/after record hashes. All 11 WAF and 122 Advisor item payloads and hashes
are unchanged. The frozen baseline and all unchanged YAML records remain
untouched; manifest after-state hashes and reproducible coverage are refreshed.
This is a metadata correction to the same 38-update/two-addition event, not
another refresh or additional covered controls. WAF central inventory agreement
is exact for all 11 items. The normalized Advisor inventory has been handed
to the pipeline owner for central registration and snapshot integration;
central Advisor agreement is pending until that owner completes integration.

## Remaining gaps and validation

The 203 manual-review outcomes identify their exact original requirement and
why the general OE checklist does not verify it. They include significant
SAP/ANF, AVS, identity, APIM, ML/OpenAI, VM lifecycle, storage and networking
details. Examples needing service-specific follow-up include ANF delegated
subnet restrictions, Virtual WAN throughput, AVS preview/route-limit/vSAN claims,
AKS patching and probe constraints, Log Analytics retention, Front Door wildcard
certificates and storage-tier claims. None received blanket freshness metadata.

The current Firewall service guide itself still states a categorical intra-VNet
restriction while describing east-west inspection elsewhere; that inherited
record remains a manual-review gap rather than silently asserting a resolution.
Some Advisor entries describe old retirements or potentially stale product
details. Catalog presence verifies an upstream ID and published action, not
every underlying service claim. Most Advisor IDs remain unassessed.

The focused Operations tests cover exact frozen identities, aliases, origin,
byte/content hashes, all outcomes, query payloads, honest metadata, additions,
strict round trips and reproducible inventory coverage. Shared-contract tests
and full-corpus validation are also run. A local deterministic bundle was built
in session storage, not published. Concurrent pillar work makes whole-corpus
counts transient; the authoritative accounting here is the frozen 279 plus two
additions. No global-count tests were loosened, and no commits or pushes were made.

The pre-normalization focused invocation passed **24 tests** across
`test_full_refresh_operations`, `test_corpus_contract` and
`test_upstream_references`. The contemporaneous integrated validation/build
contained **2,011 canonical records**. Bundle version
`operations-bounded-final-2026-09-11` had content hash
`sha256:c2b394d1fe427c163c1127afb0b3f7d026a59dee200a3bfa5fcc51a82ac140c8`.
That count/hash is a local validation snapshot, not the final result of other
workers' ongoing edits. The Operations evidence contains **24 applied upstream
references and three external unchanged-record references**; these reduce to
the unique upstream-ID counts above, not 27 fully covered controls.

After canonical source-ID normalization, **25 tests passed** across the same
three modules, including a regression that reconstructs pre-normalization
references, checks unchanged inventory fingerprints and verifies exact central
WAF item agreement. Integrated strict validation again accepted **2,011
recommendations and their aliases**. The earlier bundle hash above is historical
and does not describe the normalized working tree.
