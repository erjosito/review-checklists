# APRL source-slice refresh - 2026-09-11

The frozen **333 APRL-source records** were assessed and updated without changing
their IDs, names, paths, aliases, original source objects, or legacy labels.
There were no moves, additions, deletions, or merges in this slice. The first-round
duplicate reports remain unchanged.

**332 records received a primary WAF classification:** 145 Reliability,
81 Operations, 60 Performance, 43 Security, and 3 Cost. The Photon-acceleration
title/Spark-recovery description conflict remains unclassified rather than being
assigned a pillar without coherent guidance.

The substantive dispositions are **128 updated, 46 supported unchanged, and
159 needs manual review**. Metadata can change even for supported-unchanged
guidance; a manual-review disposition can coexist with a supported correction.
There are 58 narrative updates, including 17 independently documented corrections.
Four statically reviewed upstream ARG changes were adopted, four misleading
queries withdrawn, and 156 empty/comment-only payloads represented honestly as
manual or candidate automation. No query was executed against Azure.

Verified corrections include unmanaged-disk and Application Gateway v1 retirement,
NSG flow-log migration, Key Vault and Backup retention ranges, NSG association
semantics, Databricks runtime support, Service Bus automatic zone support, SQL and
Load Balancer zone-versus-region scope, and Functions warmup restrictions.
Unresolved entries identify specific missing/disabled IDs, scope changes,
contradictory narratives, or unverified query differences. The changed Citrix VDA
limit was deliberately not adopted: the vendor URL did not return usable limit
evidence.

## Source inventory and coverage

The complete public repository snapshot is pinned to
`4ed61607223b49e3d0bdd9ce3127ef6e842b5463` (2026-09-07), retrieved on 2026-09-11.
The denominator includes **456 actual GUIDs: 393 Active and 63 Disabled** across
resource, specialized-workload, and WAF recommendations. Six archetype placeholders
are excluded.

Within the frozen slice, **252 IDs are Active, 59 Disabled, and 22 absent** from
that complete snapshot. Explicit assessments record **162 full, 77 partial,
72 supporting, and 22 unmapped**. Full coverage is 41.22% of the complete Active
denominator; partial coverage is separately 19.59%, not added to full coverage.
The other 141 Active IDs are unassessed by this slice, not proven absent from the
entire corpus. Disabled IDs have supporting evidence only. The 59 disabled
references listed outside the Active inventory still exist in the all-state
inventory; they are distinct from the 22 missing legacy GUIDs.

Hashes cover the complete parsed upstream recommendation metadata, with the
fingerprint scope declared in both inventories. KQL correspondence and its static
assessment are recorded separately. A GUID match alone is not semantic coverage.
`assessedAt` dates source assessment; `lastReviewed` and `validatedAt` remain
unchanged. Published APRL text and its `pgVerified` metadata are not independent
service certification.

## Durable evidence

- `aprl-baseline.json`: frozen records, original YAML bytes, and original hashes.
- `aprl-review.json`: every ID's classification, changes, evidence, gaps, and query disposition.
- `aprl-inventory-all.json` and `aprl-inventory-active.json`: complete dated denominators and payload hashes.
- `aprl-coverage-all.json` and `aprl-coverage-active.json`: reproducible explicit-ID coverage.
- `aprl-validation.json`: validation commands and checked invariants.
- `aprl-upstream-license.txt`: upstream MIT attribution and permission notice.

All 13 APRL regression tests passed. Full validation passed for 2,011
recommendations and nine checklists at the time of validation; concurrent
non-APRL additions can change the total.
