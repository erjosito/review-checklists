# Legacy v1 JSON checklists

This directory retains the v1 checklist format used by the macro-enabled
spreadsheet, legacy ARG script and workbook renderers. It is **not the canonical
authoring location for the current local-first application**.

Current recommendations live in [`v2/recos`](../v2/recos), with selectors in
[`v2/checklists`](../v2/checklists). The [corpus contract](../review_checklists/docs/corpus-contract.md)
defines YAML authoring and deterministic versioned JSON bundles; these bundles
are a different format from the legacy checklist JSON here. Do not assume a v1
checklist JSON or spreadsheet export can be passed to the current app's `--bundle`.

For corrections or new guidance, follow [Contributing](../CONTRIBUTING.md)
and edit the canonical YAML, not generated JSON or translated copies.
Historical localizations were produced with Azure Translator. That dependency
is decommissioned; automatic translation is not a current supported workflow,
and retained translations can be stale.

See the [legacy spreadsheet guide](../docs/legacy-v1.md) for old import/export
mechanics, or the [application guide](../review_checklists/README.md) to start a
current review. Legacy assets and historical checklist maturity labels do not
establish current support, freshness or production readiness.
