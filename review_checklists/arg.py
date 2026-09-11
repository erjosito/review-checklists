"""Explicit, read-only Azure Resource Graph execution. Never assigns compliance."""

from collections.abc import Callable
from uuid import UUID

from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential
from azure.mgmt.resourcegraph import ResourceGraphClient
from azure.mgmt.resourcegraph.models import QueryRequest, QueryRequestOptions

from review_checklists.corpus import ReviewError, has_arg_query
from review_checklists.review import Review, utc_now


MAX_ROWS = 10000
MAX_PAGES = 100
MAX_SELECTED = 50


def subscription_ids(text: str) -> list[str]:
    try:
        values = [str(UUID(value.strip())) for value in text.split(",")]
    except (ValueError, AttributeError) as exc:
        raise ReviewError("Specify explicit subscription GUIDs, separated by commas") from exc
    return list(dict.fromkeys(values))


def query_azure(query: str, subscriptions: list[str]) -> dict:
    # Restrict DefaultAzureCredential to the existing az login session, not an
    # ambient service principal/managed identity or an interactive consent flow.
    with DefaultAzureCredential(
        exclude_environment_credential=True,
        exclude_workload_identity_credential=True,
        exclude_managed_identity_credential=True,
        exclude_shared_token_cache_credential=True,
        exclude_visual_studio_code_credential=True,
        exclude_powershell_credential=True,
        exclude_developer_cli_credential=True,
        exclude_interactive_browser_credential=True,
        exclude_broker_credential=True,
    ) as credential, ResourceGraphClient(
        credential, connection_timeout=10, read_timeout=60, retry_total=2,
    ) as client:
        return collect_pages(client, query, subscriptions)


def collect_pages(client: ResourceGraphClient, query: str, subscriptions: list[str]) -> dict:
    rows = []
    token = None
    seen_tokens = set()
    for _ in range(MAX_PAGES):
        response = client.resources(QueryRequest(
            query=query,
            subscriptions=subscriptions,
            options=QueryRequestOptions(
                result_format="objectArray", top=1000, skip_token=token,
                allow_partial_scopes=False,
            ),
        ))
        if not isinstance(response.data, list) or not all(
            isinstance(row, dict) for row in response.data
        ):
            raise ReviewError("ARG returned an unexpected result shape; expected object rows")
        room = MAX_ROWS - len(rows)
        rows.extend(response.data[:room])
        token = response.skip_token
        truncated = response.result_truncated in (True, "true")
        if len(response.data) > room or (len(rows) >= MAX_ROWS and (token or truncated)):
            return {"rows": rows, "truncated": True}
        if not token:
            return {"rows": rows, "truncated": truncated}
        if token in seen_tokens:
            raise ReviewError("ARG repeated a pagination token; results are incomplete")
        seen_tokens.add(token)
    return {"rows": rows, "truncated": True}


def run_query(
    review: Review, item_id: str, scope: str,
    executor: Callable[[str, list[str]], dict] = query_azure,
) -> dict:
    item = review.get(item_id)
    query = item["recommendation"].get("queries", {}).get("arg", "").strip()
    if not query:
        raise ReviewError("This recommendation has no ARG query")
    subscriptions = subscription_ids(scope)
    evidence = {
        "started_at": utc_now(), "query": query, "subscriptions": subscriptions,
    }
    try:
        result = executor(query, subscriptions)
    except (AzureError, ReviewError) as exc:
        evidence.update(outcome="error", error=str(exc), completed_at=utc_now())
        review.add_evidence(item_id, evidence)
        raise ReviewError(f"ARG failed; failure saved in review evidence: {exc}") from exc
    evidence.update(result, outcome="success", completed_at=utc_now())
    review.add_evidence(item_id, evidence)
    return evidence


def run_selected(
    review: Review, item_ids: list[str], scope: str,
    executor: Callable[[str, list[str]], dict] = query_azure,
) -> dict:
    selected = list(dict.fromkeys(item_ids))
    if not 1 <= len(selected) <= MAX_SELECTED:
        raise ReviewError(f"Select between 1 and {MAX_SELECTED} checks with ARG queries")
    subscriptions = subscription_ids(scope)
    # Validate the entire selection before issuing even the first Azure request.
    items = [review.get(item_id) for item_id in selected]
    for item in items:
        if not has_arg_query(item["recommendation"]):
            raise ReviewError(f"Selected check has no ARG query: {item['id']}")
    results = []
    for item in items:
        result = {"id": item["id"], "title": item["recommendation"]["title"]}
        try:
            evidence = run_query(review, item["id"], scope, executor)
        except ReviewError as exc:
            result.update(outcome="error", error=str(exc))
        else:
            result.update(
                outcome="success", row_count=len(evidence["rows"]),
                truncated=evidence["truncated"],
            )
        results.append(result)
    return {
        "results": results, "subscriptions": subscriptions,
        "succeeded": sum(result["outcome"] == "success" for result in results),
        "failed": sum(result["outcome"] == "error" for result in results),
    }
