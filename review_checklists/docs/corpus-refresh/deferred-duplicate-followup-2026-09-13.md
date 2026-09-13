# Follow-up: the seventeen technically deferred duplicate groups

**Proposal only — no corpus changes or merges applied.** Assessed 2026-09-13
against **2,011 canonical recommendations and 55 aliases**, after the later
source refresh and classification normalization. This is not the historical
2,005-record initial Cost/merge stage.

The [machine-readable report](deferred-duplicate-followup-2026-09-13.json)
contains exact group/member GUIDs, current metadata and membership observations,
canonical-first before hashes, source evidence, exact upstream-item checks,
survivor before snapshots, complete after deltas, and an embedded merge manifest.

## Exact scope and result

`duplicate-audit.json.finalTechnicalDeferrals` and
`alias-migration.json.finalTechnicalDeferrals` agree exactly. The original
71 confirmed groups minus 45 applied non-Cost groups and nine applied Cost groups
leave **17 groups / 37 current canonical members**. All historical manifests
remain unchanged. Their byte hashes are recorded in the JSON.

| Decision | Groups | Proposed retirements |
| --- | ---: | ---: |
| Equivalent and current-engine mergeable | 2 | 3 |
| Related but distinct: reject merge | 1 | 0 |
| Unresolved explicit technical/policy conflicts | 14 | 0 |
| **Total** | **17** | **3, not applied** |

“Unresolved” does not mean that fourteen groups were left unread. Several are
clearly the same action, but current merge semantics cannot preserve both live
WAF classifications, conflicting priorities, source types or selector labels.
Documentation corroboration does not authorize silently changing those fields.

## Per-group adjudication

GUIDs below retain the exact original group membership order. That order is
**not necessarily survivor-first**.

### confirmed-001 — unresolved: ASR monitoring

- `d89fd98d-23e4-4b40-a92e-32db9365522c`
- `07e5ed53-3d96-43d8-87ea-631b77da5aba`

The identical SAP application-server ASR-monitoring action is supported by the
current [ASR monitoring page][asr]. Operations/severity 0 versus
Reliability/severity 1 remains unresolved. Retiring the Reliability member into
the historical Operations survivor would remove live Reliability discovery,
including `waf_resiliency.yaml`. The latter's storage links do not define a
different monitoring requirement. Both have no query and unknown automation.

### confirmed-002 — unresolved: Virtual WAN global transit

- `7d4bc7d2-c34a-452e-8f1d-6ae3c8eafcc3`
- `e73de7d5-6f36-4217-a526-e1a621ecddde`

Identical conditional global-transit guidance; Operations versus Performance
remains a scalar WAF conflict. [Virtual WAN][vwan] supports this use case in
**Standard**, not Basic. The other member's Front Door links are tangential:
Front Door is not interchangeable with private-network transit. Matching
file-based checklist memberships does not prove matching live pillar filters.

### confirmed-003 — unresolved: encryption key ownership

- `16183687-a047-47a2-8994-5bda43334f24`
- `eeaa3592-829e-42ed-a217-3676aff6691b`

Identical platform-managed-by-default/customer-managed-when-required guidance,
supported by [encryption at rest][encryption]. The ALZ member has `G02.10`,
Security / Encryption and keys labels; the other does not. The current engine
rejects that label difference. Retaining the existing ALZ survivor looks
plausible for a future reviewed selector-preservation mechanism, but adding
labels to the other authored record merely to bypass the gate is not proposed.

### confirmed-006 — unresolved: VM availability zones

- `e514548d-2447-4ec6-9138-b8200f1ce16e`
- `826c5c45-bb79-4951-a812-e3bfbfd7326b`

Same conditional VM-zone requirement. Preserve the richer description's
replication of dependency arrangements across zones: a single zonal VM is not
zone-resilient ([source][zones]). Severity 1 versus 0 remains unresolved; the
second GUID also supplies ALZ Management / Fault Tolerance membership.
Conservative priority 0 could be a separately authorized decision, not an
implicit merge.

### confirmed-008 — unresolved: AKS multiregion clusters

- `8dd12fab-e3cb-4b39-9ebf-3609a3de2e34`
- `57d11e53-f830-4930-9d74-2ce5435cd971`

Titles and descriptions match: separate regional clusters and global routing
for Internet-facing workloads ([current architecture][aks-regions]).
Operations versus Reliability remains unresolved. This is not a zone-spread
check or a classic/modern ingress migration. Historical survivor is the
**second** GUID.

### confirmed-009 — unresolved: modernized AKS observability

- `bdab324d-7736-4444-a03e-a1ec180f3699`
- `1b92e639-a727-409c-a343-17109a2861f2`

The refreshed Operations member now separates containerized Azure Monitor Agent,
managed Prometheus, control-plane logs and application traces, with actual
data-arrival/alert verification. The Reliability member still has older combined
Container insights wording. [Current monitoring documentation][aks-monitoring]
supports the separation. WAF and manual/unknown automation differ.

There is an additional concrete lineage trap: `merge.py` retains the survivor's
`upstreamRecommendations`, not their union. The historical survivor has no
mapping; it would lose the other member's hash-matched partial **OE:07** mapping.
First decide whether to retain a narrower check or explicitly supersede it with
layered observability. Do not merely concatenate stale monitoring architecture.

### confirmed-012 — reject merge: empty targets are not underutilization

- `7947e534-c9a8-435b-9e03-d300143b5f74`
- `74ad737c-cbb8-4e91-84b7-2aa937b37ede`

**Retain both.** The first now checks Application Gateways with no configured
backend targets; the second still reviews underutilized resources. A populated,
low-traffic gateway is a concrete counterexample to equivalence.

The [FinOps empty-target scenario][finops] supports a specific inventory aid.
Preserve the existing leftouter query, bounded backend-pool expansion and
human/visibility/provisioning/standby caveats. Neither empty results nor empty
backend metadata establishes utilization, savings or deletion authority.
Classic gateway migration remains a separate requirement.

### confirmed-034 — unresolved: ExpressRoute maintenance and Disabled APRL

- `26cb547f-aabc-dc40-be02-d0a9b6b04b1a`
- `41687924-ef94-411f-b71a-c8ec2543dbb7`

Current [Service Health instructions][er-maintenance] still support
**planned-maintenance** alerts. The exact pinned APRL item was fetched and is
**Disabled**, `automationAvailable:false`; its matching inventory hash and
supporting-only lineage must survive. Do not imply advance notice of every
unplanned event or reactivate Disabled upstream coverage.

Operations/Reliability, severity 0/1, APRL/WAFSG source types, labels,
`arg:''`/`{}` and candidate/unknown automation conflict. The old comment-only
ARG is no longer executable evidence. A supported, deliberately scoped
replacement/reconciliation proposal is needed, not an alias-only merge.

### confirmed-049 — unresolved: DNS proxy and an incorrect constraint

- `94f3eede-9aa3-4088-92a3-bb9a56509fad`
- `eb9ee852-eda8-41a8-917d-4a5a25a6d866`
- `35c2f653-acd6-471c-91a9-f7e4a3fcce3e`

Same DNS proxy intent, but the historical survivor says custom upstream DNS
**must** be used and implies enabling proxy redirects clients automatically.
[Current DNS settings documentation][firewall-dns] says custom upstream DNS is
optional; client/VNet DNS configuration is a separate step. Correct that
constraint before even considering a WAFSG-only submerge.

The full group also crosses `revcl`/`wafsg` source types. Preserve WAF, WAF
service-guide Security and ALZ Network Topology and Connectivity / Firewall
membership. Do not rewrite import type to satisfy the engine.

### confirmed-050 — mergeable: identical refreshed storage locks

- `3195423b-0513-45e2-951b-87f9c5d534b0`
- **Survivor:** `5efa7ffa-1cc0-4a74-bd15-c809185ccb58`
- `0148ed98-3b9a-4b7f-81c2-8b550f56f793`

The later refresh removed the original description conflict: all three now
have identical source-backed control-plane lock guidance, classification,
priority, manual automation and exact partial **SE:08** mapping.
[Current lock documentation][locks] verifies CanNotDelete/ReadOnly differences
and the data-plane limitation.

**Only add two aliases.** Keep the survivor's existing name, title, description,
sources, mapping and null review/validation timestamps unchanged. The JSON
contains its entire before snapshot and exact after delta. Current-engine
dry run passed: **2,011 → 2,009**, two retirements.

### confirmed-051 — unresolved: blob soft delete

- `9ada4666-7e13-4c10-96b9-153d89f89dc7`
- `a274faa1-abfe-49d5-9d04-c3c4919cb1b3`
- `503547c1-447e-4c66-828a-7100f1ce16dd`

The generic “Enable Soft Delete” member links specifically to blobs. All three
address [blob soft delete][blob-delete], not container/account deletion.
Reliability/Security and severity 2/1 still differ; even a Reliability-only
submerge has a severity conflict. Preserve retention/snapshot/version details
and do not imply every metadata overwrite is protected.

### confirmed-052 — unresolved: container soft delete

- `a3992c2d-e6e2-4065-a3a7-6af4a691e893`
- `43a58a9c-2289-4c3d-9b57-d0c655462f2a`

Same whole-container recovery feature, corroborated by
[container soft delete][container-delete]. Reliability/Security and severity
2/0 remain unresolved; descriptions need deliberate preservation. Keep
container recovery separate from blob recovery and account control-plane locks.

### confirmed-058 — unresolved: Functions Always On

- `17232891-f89f-4eaa-90f1-3b34bf798ed5`
- `c7b5f3d1-0569-4fd2-9f32-c0b64e9c0c5e`

Same setting for Function Apps on **dedicated App Service plans**
([source][always-on]). Severity 0/1 is the remaining engine conflict. Do not
expand to Consumption/Flex/Premium hosting or every `microsoft.web/sites`
resource. An explicit priority decision could unlock a future merge.

### confirmed-066 — unresolved: regional service/feature availability

- `e6e20617-3686-4af4-9791-f8935ada4332`
- `4c27d42e-8bba-4c75-9155-9ab9153e8908`

Same region-capability check; ANF and zones are examples, not a separate scope
([current region-selection guidance][regions]). Operations/Reliability,
severity 0/1 and ALZ `C03.03` labels conflict. Preserve ALZ Resource Organization
/ Regions and WAF Reliability discovery; do not retain those only in an audit.

### confirmed-067 — unresolved: circuit retirement with a partial detector

- `271b6cfe-4507-4afa-a1e5-000e3be105ac`
- `c36e0c83-11b4-409a-a4a6-2118b52a380f`

Both retain unused-circuit retirement intent, so this is not conclusively a
different requirement. The refreshed survivor additionally requires provider
coordination, redundancy/migration/recovery review and residual charges
([ExpressRoute cost guidance][er-cost]). Its inventory query finds
`NotProvisioned`, not all unused or low-traffic circuits ([FinOps][finops]).

Unknown/no-query versus query-available/inventory still conflicts. Parent must
explicitly decide whether a manual retirement requirement plus a partial
inventory aid may supersede the original, retaining all caveats and import
origins. Circuit, Direct port and gateway costs are not interchangeable.

### confirmed-068 — mergeable: Last Sync Time assessment

- `f436bbde-bfd0-4be2-85a6-c13f0d79cee1`
- **Survivor:** `af07c8fb-ba63-41e5-b924-3bc6759ad671`

The two descriptions paraphrase the same geo-redundant-storage data-loss
assessment. Current [Last Sync Time][last-sync] and
[failover guidance][storage-failover] support equivalence, with important
qualification: later writes **might** have replicated, and planned failover/
failback expects no loss while both regions stay available.

The exact proposed description preserves both original paragraphs verbatim
(required by current merge semantics), then adds that qualification and makes
read-access variants explicit. Add the single retired-ID/name/source/labels
alias; leave other fields unchanged. Source evidence lives in this report, not
invented approval/validation timestamps. Current-engine dry run passed:
**2,011 → 2,010**, one retirement.

### confirmed-071 — unresolved: Firewall Policy Analytics

- `8ad68872-c312-4c23-9f23-be376493dfdb`
- `e104f2f7-c376-4ed8-b536-a10a16be484d`

Same dashboard review with identical descriptions, supported by
[Policy Analytics][policy-analytics]. Operations/Performance remains a live
classification conflict. Preserve logging/Log Analytics prerequisites and
time-window limitations; an inventory of rules or this dashboard is not
authorization for automatic rule deletion.

## Exact executable proposal and compatibility

Only the JSON report's `proposedMergeManifest` object has the strict shape
accepted by `review_checklists.merge`. The report itself is **not** a manifest.
If parent approves, extract that object into a **new** parent-owned file and
rerun the dry run against the then-current corpus. Never overwrite or rerun
the historical manifests.

| Retired GUID | Existing survivor GUID |
| --- | --- |
| `3195423b-0513-45e2-951b-87f9c5d534b0` | `5efa7ffa-1cc0-4a74-bd15-c809185ccb58` |
| `0148ed98-3b9a-4b7f-81c2-8b550f56f793` | `5efa7ffa-1cc0-4a74-bd15-c809185ccb58` |
| `f436bbde-bfd0-4be2-85a6-c13f0d79cee1` | `af07c8fb-ba63-41e5-b924-3bc6759ad671` |

Combined expected outcome, **not an applied count**: **2,008 canonical / 58
aliases**. `all_recos.yaml` decreases by three; `waf_sg_security.yaml` by two.
Other current checklist counts and areas/subareas are expected to remain
unchanged after retired-to-canonical resolution. ALZ remains 236, application
delivery 38, APRL 333 and WAF Reliability 299.

All original names, IDs, import sources and labels are specified in the alias
delta. Current merge behavior preserves existing aliases and source selectors;
the parent must retain the full original-member snapshots in its application
audit. Saved-review assessments remain separate pinned records.

## Evidence and validation boundaries

- **Read-only validation passed:** strict report JSON, exact ledger subtraction,
  all 37 current member metadata/query/membership checks, all seventeen
  canonical-first hashes, immutable historical-file hashes and the five exact
  upstream mappings. The **combined two-group current-engine dry run** passed.
- Both complete survivor-before snapshots and reconstructed after snapshots
  match the merge engine's hashes. The entire simulated corpus passes schema/
  identity validation; all ten checklist ID/area/subarea sets and all three
  retired GUID/name/guid-label selectors preserve expected resolution.
  The simulated (not written) result has content hash
  `sha256:dbb6bdefea44f401fbb85005698847d462e091b7f1b4a29d2cc7c677250996a4`.
- All linked primary sources above were actually fetched on **2026-09-13**
  (session UTC+03:00 date). The JSON records titles, reading boundaries and one
  failed URL corrected by fetching the right Last Sync Time page.
- Five members have existing upstream mappings: the Disabled APRL item, one
  partial OE:07 mapping, and the three identical partial SE:08 mappings. Their
  exact hashes match the frozen 2026-09-11 inventories. The other 32 members
  remain unmapped; no remote GUIDs or coverage percentages are fabricated.
- `merge.py` does **not** union distinct `upstreamRecommendations`. Proposed
  groups are safe on that dimension only because 050's maps are identical and
  068's are absent. This matters particularly for deferred group 009.
- The two existing executable queries are retained unchanged on their current
  records. All `validatedAt`, `lastReviewed` and unknown revision values remain
  null. No live ARG, subscriptions, customer reviews or paid services were used.
- Zero baseline selections for `alz.json` and `no-service.yaml` are explicitly
  recorded, not hidden as newly successful populated checklists.
- No members overlap the separately owned Data Factory/Front Door WAF type
  spellings or Photon/Spark record. Parent retains stage integration and tests.
- Stop here: the 22 uncertain groups and 393 candidate pairs are outside scope.

[asr]: https://learn.microsoft.com/en-us/azure/site-recovery/site-recovery-monitor-and-troubleshoot
[vwan]: https://learn.microsoft.com/en-us/azure/virtual-wan/virtual-wan-about
[encryption]: https://learn.microsoft.com/en-us/azure/security/fundamentals/encryption-atrest
[zones]: https://learn.microsoft.com/en-us/azure/reliability/availability-zones-overview
[aks-regions]: https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/containers/aks-multi-region/aks-multi-cluster
[aks-monitoring]: https://learn.microsoft.com/en-us/azure/azure-monitor/containers/kubernetes-monitoring-overview
[finops]: https://learn.microsoft.com/en-us/cloud-computing/finops/best-practices/networking
[er-maintenance]: https://learn.microsoft.com/en-us/azure/expressroute/maintenance-alerts
[firewall-dns]: https://learn.microsoft.com/en-us/azure/firewall/dns-settings
[locks]: https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/lock-resources
[blob-delete]: https://learn.microsoft.com/en-us/azure/storage/blobs/soft-delete-blob-overview
[container-delete]: https://learn.microsoft.com/en-us/azure/storage/blobs/soft-delete-container-overview
[always-on]: https://learn.microsoft.com/en-us/azure/azure-functions/dedicated-plan#always-on
[regions]: https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-setup-guide/regions
[er-cost]: https://learn.microsoft.com/en-us/azure/expressroute/plan-manage-cost
[last-sync]: https://learn.microsoft.com/en-us/azure/storage/common/last-sync-time-get
[storage-failover]: https://learn.microsoft.com/en-us/azure/storage/common/storage-disaster-recovery-guidance
[policy-analytics]: https://learn.microsoft.com/en-us/azure/firewall/policy-analytics
