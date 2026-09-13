# Support

For the current local-first prototype, start with the
[application guide](review_checklists/README.md). Spreadsheet, workbook and old
MySQL/ACI app instructions are in the [legacy guide](docs/legacy-v1.md).
This sample is not supported under a Microsoft standard support program; see
the [project disclaimer](README.md#disclaimer).

Search the [issues for this repository](https://github.com/erjosito/review-checklists/issues) before opening a bug report
or feature request. Include the branch/commit, Python and OS versions, sanitized
steps to reproduce, expected behavior, actual error, and whether the issue affects
the local CLI/UI, corpus, or a legacy asset.

For content issues, identify the canonical recommendation ID and repository-relative
YAML filename under `v2/recos`, the affected checklist selector if relevant, and
supporting source URLs. For bundle-only reproduction, include the corpus version
and hash. Mention an `.en.json` filename only when reporting a legacy JSON issue.
See [Contributing](CONTRIBUTING.md) for source-backed fixes.

Do not attach customer review databases, reports, raw ARG evidence, tokens or
other sensitive data to public issues. Use synthetic examples and redact logs.
Report security vulnerabilities through [SECURITY.md](SECURITY.md), not public issues.
