"""Read the selected subscription from the user's existing Azure CLI profile."""

import json
import os
import shutil
import subprocess
from uuid import UUID

from review_checklists.corpus import ReviewError


def get_cli_subscription() -> dict[str, str]:
    executable = shutil.which("az")
    if executable is None:
        raise ReviewError("Azure CLI was not found. Install it and run 'az login', or enter IDs manually.")
    try:
        result = subprocess.run(
            [
                executable, "account", "show", "--query", "{id:id,name:name}",
                "--output", "json", "--only-show-errors",
            ],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8",
            timeout=15, check=False, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
    except subprocess.TimeoutExpired as exc:
        raise ReviewError("Azure CLI subscription lookup timed out. Retry or enter IDs manually.") from exc
    except (OSError, UnicodeError) as exc:
        raise ReviewError(f"Cannot read the Azure CLI subscription: {exc}") from exc
    if result.returncode:
        detail = result.stderr.strip()[:1000] or f"exit code {result.returncode}"
        raise ReviewError(
            f"Azure CLI subscription lookup failed: {detail}. "
            "Check 'az login' and 'az account show', or enter IDs manually."
        )
    try:
        account = json.loads(result.stdout)
    except ValueError as exc:
        raise ReviewError("Azure CLI returned invalid subscription JSON. Retry 'az account show'.") from exc
    if not isinstance(account, dict) or not all(
        isinstance(account.get(field), str) and account[field].strip()
        for field in ("id", "name")
    ):
        raise ReviewError("Azure CLI returned no valid subscription ID/name. Check 'az account show'.")
    try:
        subscription_id = str(UUID(account["id"]))
    except ValueError as exc:
        raise ReviewError("Azure CLI returned an invalid subscription GUID.") from exc
    return {"id": subscription_id, "name": account["name"]}
