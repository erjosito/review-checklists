# All-pillar source assessment - September 2026

This pass accounts for every one of the **2,005 canonical recommendations** after
the initial Cost refresh and duplicate merges. It adds six recommendations,
producing **2,011 canonicals with 55 preserved aliases**. It is a complete
accounting pass, **not verification that all legacy guidance is current**.
The [September 13 follow-up](../followup-2026-09-13.md) is a later, separately
recorded stage; the outcomes and checkpoint below remain historical.

## Frozen ownership and outcomes

| Slice | Baseline | Updated | Supported unchanged | Needs manual review | Added |
| --- | ---: | ---: | ---: | ---: | ---: |
| [Cost](cost-report.md) | 226 | 27 | 122 | 77 | 0 |
| [Security](security-report.md) | 565 | 49 | 35 | 481 | 0 |
| [Reliability](reliability-report.md) | 427 | 34 | 8 | 385 | 1 |
| [Performance](performance-report.md) | 175 | 53 | 71 | 51 | 3 |
| [Operations](operations-report.md) | 279 | 38 | 38 | 203 | 2 |
| [Initially unclassified APRL](aprl-summary.md) | 333 | 128 | 46 | 159 | 0 |
| **Total** | **2,005** | **329** | **320** | **1,356** | **6** |

These are recorded substantive dispositions, not counts of YAML files written.
Supported-unchanged records can receive provenance-only edits. A record with an
unresolved gap can still receive a verified, limited correction. Original
identities, names, import origins and retired aliases remain preserved.

The APRL slice is disjoint from the original five pillar slices. It classified
332 records: 145 Reliability, 81 Operations, 60 Performance, 43 Security and
three Cost. One contradictory Photon/Spark requirement remains unclassified.
Do not retrospectively count those three APRL records as part of the 226-record
Cost baseline or sum overlapping historical stages as new recommendations.

The resulting pillar counts are Cost 229, Security 608, Reliability 573,
Performance 238, Operations 362 and one unclassified record. The six additions
are three Performance, two Operations and one Reliability recommendation;
no additional duplicate merges occurred in this pass.

## What the evidence establishes

Each slice retains a frozen baseline and a machine-readable outcome ledger.
Source inventories retain actual upstream IDs, scope, date, revision, payload
and content hash. Evaluated mappings distinguish full, partial and supporting
relationships. A matching GUID or documentation link is not sufficient to
declare a requirement fully represented.

The WAF inventories cover **59 published checklist rows** across the five
pillars, not every recommendation in all WAF service guides. Advisor catalogs
are separate per-category units; incomplete inventories have no percentage.
APRL's Active, all-state and narrower resource inventories are distinct scopes.
Disabled upstream records are not automatically a deficit in Active coverage.

Use [source coverage](../../source-coverage.md) and the read-only
[corpus dashboard](../../corpus-admin.md) for recorded inventory reconciliation.
The dashboard computes current coverage from explicit corpus mappings rather
than equating supporting source counts with coverage. New/changed/removed IDs
can be compared programmatically without importing changes.

## Gaps are deliberate review work, not hidden success

The **1,356 needs-manual-review outcomes** identify unverified or conflicting
requirements, including vendor-specific SAP/AVS claims, service-specific behavior,
disabled or missing upstream IDs, licensing and billing context, and query
differences without sufficient evidence. The per-record ledgers retain the
reasons. No broad WAF article substitutes for missing service-specific evidence.

No live ARG execution, customer resource enumeration, savings verification or
human approval occurred. Inventory and statically reviewed queries are not
automatic compliance verdicts. `lastReviewed` and `validatedAt` were not invented.
Source access and mapping assessment dates are recorded separately.

## History and safe use

The [initial Cost/merge summary](../README.md) is a historical stage, not the
final all-pillar corpus. Its original reports and hashes remain evidence of that
stage. Any later service-label/resource-type normalization is a separate,
mechanical stage and must not change guidance, IDs, KQL or applicability.

Existing saved reviews do not change automatically. Use the explicit
[review refresh workflow](../../review-refresh.md) to preview a new bundle,
preserve assessments/comments/evidence, and mark changed guidance for reassessment.
Corpus administrators can inspect source statistics independently of customer
review state.

## Integrated checkpoint

The subsequent [service catalogue stage](../../service-catalog.md) normalized
classification fields on 335 records without changing guidance, query text or
identities. Its [mechanical change ledger](../service-normalization.json) is
separate from the six source assessments above. Ambiguous applicability remains
explicit: 1,990 records still have no curated service labels, and 11 legacy ARM
type spellings remain unresolved rather than being guessed.

The local bundle `dist/catalog-2026.09.12-checkpoint.json` contains the resulting
2,011 canonical recommendations and 55 aliases, version
`2026.09.12-checkpoint`, with recommendation content hash
`sha256:1a9879553910a9fdb7271e507973d717dee75862726f23ea7ba9f0af858ffe58`.
This generated local checkpoint is not a published or human-approved release.

The central APRL inventory retains all 456 GUIDs for hash and change tracking,
with an explicit coverage selection of 393 Active recommendations. The 63
Disabled entries are retained and disclosed separately, not silently dropped
or counted as Active coverage gaps. Historical reports without a selection keep
their original reconciliation format.

Five machine-local artifact paths in the initial duplicate audit were redacted.
The [redaction record](../report-redactions.json) preserves its original and
sanitized hashes; the APRL report still records the original historical hash.
