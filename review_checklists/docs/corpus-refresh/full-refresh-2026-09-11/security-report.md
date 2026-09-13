# Security slice - 2026-09-11

**49 existing recommendations received source-backed guidance changes; 35 more
were supported without guidance changes and received provenance only. The
remaining 481 recommendations are explicitly unverified and need manual
review.** This is a completed bounded implementation and accounting pass, not
a claim that the full Security corpus is source-verified.

The frozen ownership set is the **565 initial records with `waf: Security` and
`source.type != aprl`**. It remains 565 records with the same canonical IDs,
names, original import sources, classification, paths and **18 aliases**.
There were no additions, deletions, moves, merges or pillar changes. APRL is
excluded by the initial ownership rule even if its classification later changes.
No other pillar, application code, schema, shared scripts or previous completed
report was edited by this slice.

## Exact accounting and evidence

| Outcome | Records | Meaning |
| --- | ---: | --- |
| `updated` | 49 | Guidance and assessment metadata changed against the identified primary sources. |
| `supportedunchanged` | 35 | Existing requirement compared with identified source sections; only provenance changed. |
| `needsmanualreview` | 481 | Original file retained byte-for-byte, with a requirement-specific unverified gap. |
| Source-verified requirements | 84 | Updated plus supported unchanged; not all 565. |
| New guidance records | 0 | Existing IDs reused; no speculative new control added. |
| Primary source URLs read | 32 | Bounded sections are recorded; linked articles are not implicitly verified. |

Every baseline GUID has exactly one manifest outcome. The source review considered
the complete text of the selected requirements, not merely their source-family
labels. Whole-scope title/query triage is not counted as source verification.
All source access dates are documentation observations. `lastReviewed`,
`upstreamRevision` and legacy review fields retain their original values, and
`automation.validatedAt` remains null. No human approval or live Azure execution
is claimed.

| Artifact | Purpose |
| --- | --- |
| [security-baseline.json](security-baseline.json) | Immutable frozen GUID/path list, full original records and original file hashes. |
| [security-manifest.json](security-manifest.json) | All 565 outcomes, exact before/after changed fields, full after records, file/content hashes, per-GUID evidence or gaps, and service accounting. |
| [security-sources.json](security-sources.json) | All 32 verified primary URLs, titles and actual read scopes, plus unsuccessful attempts. |
| [security-query-audit.json](security-query-audit.json) | All 39 original exact KQL texts, seven withdrawals and 32 individualized unresolved query limitations. |
| [security-mapping-proposals.json](security-mapping-proposals.json) | Explicit semantic mapping decisions, now applied as draft provenance with canonical upstream hashes. |
| [security-source-id-normalization.json](security-source-id-normalization.json) | Source-family rename audit, per-record before/after hashes and exact agreement with all 12 central inventory payloads and hashes. No guidance changes. |
| [security-waf-inventory.json](security-waf-inventory.json) | Complete dated inventory of the 12 published SE checklist rows, using the shared adapter's fingerprint contract. |
| [security-waf-coverage.json](security-waf-coverage.json) | Computed ID coverage for this frozen slice, separating full, partial and unknown. |
| [security-advisor-inventory.json](security-advisor-inventory.json) and [security-advisor-coverage.json](security-advisor-coverage.json) | Explicit unsupported/unknown Advisor Security denominator; no fabricated IDs or percentages. |

File hashes cover the actual UTF-8 bytes. Record hashes cover sorted-key compact
JSON of the complete record, with Unicode preserved. These are not the upstream
row hashes: the latter use `source_coverage.item_content_hash` on the shared WAF
adapter's `{id, code, recommendation}` payload, including the trimmed Markdown
table cells and excluding retrieval metadata.

## Meaningful changes

- **Identity and privileged access:** distinguish managed identities from
  application-managed service-principal credentials; preserve protected emergency
  access when enforcing Conditional Access and PIM; require at least two
  cloud-only emergency accounts with phishing-resistant authentication, alerts
  and regular recovery exercises.
- **AKS and Container Registry:** remove stale Workload ID and kubelogin preview
  wording; document Cilium and the Windows/Linux NPM support deadlines; distinguish
  pod-network controls from API-server privacy. ACR role guidance now handles
  ABAC-enabled registries, where legacy `AcrPull`/`AcrPush` roles are not honored.
- **Key Vault:** separate soft delete from purge protection and their recovery
  implications; correct directory-role versus Azure data-plane role terminology;
  stop recommending Managed HSM as an arbitrary secret store; replace a
  vault-count compliance heuristic with application/environment boundary review.
- **Storage:** correct SFTP ACL and Microsoft Entra authentication support, NFS
  encryption-in-transit support, SAS expiration Log/Block behavior and exclusions,
  and service-SAS-only stored policies. Retention exceptions remain distinct from
  enablement checks: disabling soft delete is neither a per-container switch nor
  immediate erasure of already-retained data. Resource locks protect the control
  plane, not data-plane deletion.
- **App Service and workload operations:** distinguish Key Vault reference
  refresh from source-credential rotation; distinguish outbound VNet integration
  from inbound isolation; clarify HTTPS redirects and certificate validation.
  Expand owned incident response through exercised recovery and lessons learned,
  and strengthen the existing App Service security-testing requirement.

The free Foundational versus paid Defender CSPM distinction and the announced
October 27, 2026 opt-in change are recorded as guidance, not a recommendation to
buy every plan. Product-specific documentation takes precedence over stale
shorthand in service guides: in particular, Key Vault reference refresh does not
rotate the underlying credential.

## Upstream-ID coverage: narrow and explicitly draft

The `waf-security-checklist` inventory contains **all 12 numbered rows of the English
WAF Security checklist**, observed on September 11, 2026. The page-reported
revision is `1df1c6023e01032c7be0013b086379c176827b1c`; this is public page
metadata, not a claim that its private source repository was separately fetched.
The shared `source_audit.fetch_inventory` adapter parsed the public Markdown, and
the shared coverage API computed the report from the applied mappings.

**79 explicit local-to-upstream mappings** produce the following unique
upstream-control accounting:

| State | Upstream controls | Share of the 12-row checklist |
| --- | --- | ---: |
| Full draft semantic mapping | SE:12 | 8.33% |
| Partial draft semantic mapping | SE:01, SE:04, SE:05, SE:06, SE:07, SE:08, SE:09, SE:10, SE:11 | 75.00% |
| Unknown / no verified mapping in this slice | SE:02, SE:03 | 16.67% |

Only `b86ad884-08e3-4727-94b8-75ba18f20459` is mapped as full, for the owned,
tested, workload-wide incident-response requirement. Every other applied mapping
is partial: a service-specific or narrower control is not the entire SE
requirement. Multiple partial references are **not** promoted to full coverage.
All notes explicitly identify the mapping as LLM-assisted draft semantic
assessment, not human review, implementation evidence or compliance.

These percentages describe **checklist-row coverage in this slice**, not all
Microsoft security guidance, all service guides, the complete corpus, or the
security of an Azure environment. Unknown does not mean the control is absent
from the full corpus. No remote IDs were inferred from local GUIDs, query text
or general citations.

**Advisor Security coverage is not measurable.** The attempted
`advisor-reference-security-recommendations` URL could not be retrieved.
`advisor-security-recommendations` redirects to Defender for Cloud review
guidance, which did not provide a complete Advisor type-ID inventory. The
`advisor-security-catalog` gap artifact therefore has unknown status, an empty
observed item list, a null denominator and null coverage percentages. Defender
assessment IDs, policy IDs and Advisor type IDs have not been equated.

The parent clarified that the earlier `azure-waf-security` and
`azure-advisor-security` names were parent proposals, not user requirements.
The 79 new references and this slice's new inventories/reports now use
`waf-security-checklist` and `advisor-security-catalog`. The explicit
[normalization audit](security-source-id-normalization.json) records every
affected GUID and before/after hash. This is a source-name correction, not another
guidance refresh or 79 newly covered controls.

All **12 complete item objects, payloads and content hashes exactly match** the
pipeline-owned central inventory
`source-inventories/waf-security-checklist--2026-09-11--1df1c6023e01032c7be0013b086379c176827b1c--ed51828272ff.json`
in the parent corpus-refresh directory. No upstream refetch was needed; source
payloads, hashes and observation dates were preserved. The shared registry and
central snapshots remain pipeline-owned and unmodified. There is no newly
verified Advisor Security catalog to integrate centrally: its local artifact
records an unknown inventory, not a second source or an uncovered alias.

## Query safety and limits

The initial scope contained **39 ARG queries**. **Seven were removed** rather
than replaced with invented or unsupported KQL:

| Existing GUID | Withdrawal |
| --- | --- |
| `ce7f2a7c-297c-47c6-adea-a6ff838db665` | Private-cluster query did not assess Windows network policies. |
| `6c46b91a-1107-4485-ad66-3183e2a8c266` | DDoS query did not assess AKS HTTP proxy configuration. |
| `58d7c892-ddb1-407d-9769-ae669ca48e4a` | Network-policy engine presence did not prove policies or enforcement. |
| `a0477a20-9945-4bda-9333-4f2491163418` | Vault count other than one falsely represented application isolation. |
| `baf8e317-2397-4d49-b3d1-0dcc16d8778d` | Front Door query did not assess Application Gateway WAF. |
| `c115775c-2ea5-45b4-9ad4-8408ee72734b` | Numeric TLS comparison and exact ARG property/table semantics were not verified. |
| `d9bd3baf-cda3-4b54-bb2e-b03dd9a25827` | Remote-debugging field/table representation was not verified. |

The affected records use `manual` or `candidate` assessment instead of
`query_available`. No replacement or new KQL was introduced.

**The other 32 inherited queries remain unverified**, unchanged and explicitly
`resultSemantics: unknown`. They are not part of the 84 source-verified
requirements. Their original `compliant` expressions are not endorsed as correct:
the query audit identifies such concerns as inner joins dropping resources,
nonempty configuration being mistaken for enforcement, pool counts being
mistaken for scheduling isolation, and NSG presence being mistaken for ASG rules.
This bounded slice does not complete query remediation. Empty, missing,
permission-limited or partial results must not be read as a pass. No query was
executed against Azure or marked live-validated.

## Remaining scope and ownership proposals

The 481 unverified requirements include the detailed SAP/landing-zone practices,
VMs, VMware Solution, API Management, Azure Policy, Event Hubs/Service Bus, AI/ML,
most networking guidance and the unselected portions of AKS, Storage, App Service
and Key Vault. The manifest's `serviceScopeOutcomes` provides exact counts for
every folder; each deferred GUID retains the complete requirement and inherited
URLs explicitly labeled **not verified in this pass**.

Do not infer that a fetched generic article validates an entire service family.
In particular, the WAF App Service Security section was compared only with the
specific records listed as supported or updated, not used to stamp every App
Service record as reviewed.

The following taxonomy decisions are proposed for parent review only; their
records remain unchanged in the frozen Security slice:

| GUID | Deferred proposal |
| --- | --- |
| `ae28c84c-33b6-4b78-88b9-fe5c41049d40` | Review the primary pillar of the cost-management process requirement. |
| `5de32c19-9248-4160-9d5d-1e4e614658d3` | Review the primary pillar of billing/cost tags; a non-null tag map is not an allocation-quality assessment. |
| `c68e1d76-6673-413b-9f56-64b5e984a859` | Review the Cost classification and the inherited claim that Reserved Instances ensure capacity; obtain current primary evidence before rewriting. |

Potential new workload-wide SDL or classification records are **not added** just
because SE:02/SE:03 lack verified mappings here. Corpus-wide semantic overlap and
scope review is still needed before concluding that new GUIDs are justified.
The distinct retention-exception and protection-enablement records were not
merged, and repeated service/import records retain their identities and aliases.

## Local validation

`review_checklists.tests.test_full_refresh_security` verifies the immutable
565-record scope digest, exact changed GUIDs, original identities and 18 aliases,
strict schema and serialization, exact withdrawn and retained KQL, before/after
fields and hashes, source evidence versus gaps, and current explicit upstream
hash mappings. It also rejects a zero-coverage interpretation of the unknown
Advisor inventory.

The shared corpus validator and bundle builder succeeded against **2,011
recommendations at the observed integration point**; other owners are working
concurrently, so that is not a new global count assertion. The validation bundle
was written outside the repository. No global count tests were weakened. These
checks establish data-contract consistency, not source completeness or live
query correctness.
