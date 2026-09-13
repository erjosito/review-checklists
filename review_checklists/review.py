"""Shared, persistent review operations for the CLI and localhost UI."""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from review_checklists.corpus import ReviewError
from review_checklists.filters import FilterValue, filter_items, filter_values


STATUSES = ("Not reviewed", "Compliant", "Non-compliant", "Not applicable")
SCHEMA_VERSION = 2


class RevisionConflict(ReviewError):
    """An assessment changed since the submitted revision was read."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def assessment_summary(items: list[dict]) -> dict:
    counts = {status: sum(item["status"] == status for item in items) for status in STATUSES}
    total = len(items)
    assessed = counts["Compliant"] + counts["Non-compliant"]
    reviewed = total - counts["Not reviewed"]
    return {
        "counts": counts, "total": total, "assessed": assessed, "reviewed": reviewed,
        "compliance_percentage": round(100 * counts["Compliant"] / assessed, 1) if assessed else None,
        "progress_percentage": round(100 * reviewed / total, 1) if total else None,
    }


class Review:
    def __init__(self, path: Path):
        self.path = path.resolve()
        if not self.path.is_file():
            raise ReviewError(f"Review does not exist: {path}. Run 'init' first.")
        with self.connection() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in (1, SCHEMA_VERSION):
                raise ReviewError(f"Unsupported review schema {version}; expected 1 or {SCHEMA_VERSION}")

    @property
    def metadata(self) -> dict:
        with self.connection() as connection:
            metadata = dict(connection.execute("SELECT key, value FROM metadata"))
        return {"description": "", "metadata_revision": "0", **metadata}

    @contextmanager
    def connection(self):
        connection = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @classmethod
    def create(
        cls, path: Path, name: str, recos: list[dict], corpus: Path, *,
        description: str = "",
        corpus_version: str | None = None, corpus_content_hash: str | None = None,
        scope: dict | None = None,
    ):
        from review_checklists.refresh import ensure_schema, validate_scope
        scope = validate_scope(scope)
        cls.validate_metadata(name, description)
        if not recos:
            raise ReviewError("A review needs a name and at least one recommendation")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("xb"):
                pass
        except FileExistsError as exc:
            raise ReviewError(f"Refusing to overwrite existing review: {path}") from exc
        snapshot = json.dumps(recos, sort_keys=True, ensure_ascii=False)
        connection = sqlite3.connect(path)
        try:
            with connection:
                connection.executescript("""
                    CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                    CREATE TABLE items (
                        id TEXT PRIMARY KEY, recommendation TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'Not reviewed',
                        comments TEXT NOT NULL DEFAULT '', revision INTEGER NOT NULL DEFAULT 0
                    );
                    CREATE TABLE evidence (
                        run_id INTEGER PRIMARY KEY, item_id TEXT NOT NULL,
                        result TEXT NOT NULL
                    );
                    PRAGMA user_version = 1;
                """)
                ensure_schema(connection)
                created_at = utc_now()
                connection.executemany("INSERT INTO metadata VALUES (?, ?)", {
                    "name": name,
                    "description": description,
                    "review_id": str(uuid4()),
                    "created_at": created_at,
                    "metadata_updated_at": created_at,
                    "metadata_revision": "0",
                    "corpus_path": str(corpus.resolve()),
                    "corpus_sha256": hashlib.sha256(snapshot.encode("utf-8")).hexdigest(),
                    "review_scope": json.dumps(scope, ensure_ascii=False, sort_keys=True),
                }.items())
                extra = {}
                if corpus_version is not None:
                    extra["corpus_version"] = corpus_version
                if corpus_content_hash is not None:
                    extra["corpus_content_hash"] = corpus_content_hash
                connection.executemany("INSERT INTO metadata VALUES (?, ?)", extra.items())
                connection.executemany(
                    "INSERT INTO items (id, recommendation) VALUES (?, ?)",
                    [(reco["id"], json.dumps(reco, ensure_ascii=False)) for reco in recos],
                )
        except (sqlite3.Error, TypeError, ValueError):
            connection.close()
            path.unlink()
            raise
        finally:
            connection.close()
        return cls(path)

    @staticmethod
    def validate_metadata(name: str | None, description: str | None) -> None:
        if name is not None and (not isinstance(name, str) or not name.strip()):
            raise ReviewError("Review name must be nonempty text")
        if description is not None and (
            not isinstance(description, str) or len(description) > 20000
        ):
            raise ReviewError("Description must be text of at most 20,000 characters")

    def update_metadata(
        self, *, name: str | None = None, description: str | None = None,
        revision: int | None = None,
    ) -> None:
        if name is None and description is None:
            raise ReviewError("Specify a review name or description")
        self.validate_metadata(name, description)
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            metadata = dict(connection.execute("SELECT key, value FROM metadata"))
            current_revision = int(metadata.get("metadata_revision", "0"))
            if revision is not None and revision != current_revision:
                raise ReviewError("Review metadata changed. Reload before saving.")
            updates = {
                "review_id": metadata.get("review_id") or str(uuid4()),
                "description": metadata.get("description", "") if description is None else description,
                "metadata_revision": str(current_revision + 1),
                "metadata_updated_at": utc_now(),
            }
            if name is not None:
                updates["name"] = name
            connection.executemany(
                "INSERT INTO metadata (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                updates.items(),
            )

    @staticmethod
    def item(row: sqlite3.Row, refresh_state: dict | None = None) -> dict:
        item = {
            "id": row["id"],
            "recommendation": json.loads(row["recommendation"]),
            "status": row["status"],
            "comments": row["comments"],
            "revision": row["revision"],
        }
        if refresh_state is not None:
            item["refresh_state"] = refresh_state
        return item

    def items(
        self, search: str = "", status: FilterValue = "", *,
        severity: FilterValue = "", waf: FilterValue = "", service: FilterValue = "",
        with_arg: bool = False,
    ) -> list[dict]:
        from review_checklists.refresh import item_states
        statuses = filter_values(status)
        if unknown := set(statuses) - set(STATUSES):
            raise ReviewError(f"Unknown status: {', '.join(sorted(unknown))}")
        with self.connection() as connection:
            connection.execute("BEGIN")
            rows = connection.execute("SELECT * FROM items ORDER BY id").fetchall()
            states = item_states(connection)
        items = filter_items(
            [self.item(row, states[row["id"]]) for row in rows], severity=severity, waf=waf, service=service,
            with_arg=with_arg,
        )
        return [
            item for item in items
            if (not statuses or item["status"] in statuses)
            and (not search or search.casefold() in json.dumps(
                item["recommendation"], ensure_ascii=False
            ).casefold())
        ]

    def get(self, item_id: str) -> dict:
        from review_checklists.refresh import item_state
        with self.connection() as connection:
            connection.execute("BEGIN")
            row = connection.execute(
                "SELECT * FROM items WHERE id = ? COLLATE NOCASE", (item_id,),
            ).fetchone()
            if row is None:
                for candidate in connection.execute("SELECT * FROM items ORDER BY id"):
                    item = self.item(candidate)
                    if any(
                        alias["id"].casefold() == item_id.casefold()
                        for alias in item["recommendation"].get("aliases", [])
                    ):
                        return dict(item, refresh_state=item_state(connection, item["id"]))
            if row is None:
                raise ReviewError(f"Unknown recommendation ID: {item_id}")
            return self.item(row, item_state(connection, row["id"]))

    def update(
        self, item_id: str, status: str, comments: str, revision: int, *,
        confirm_current_assessment: bool = False,
    ) -> None:
        from review_checklists.refresh import acknowledge_assessment
        if status not in STATUSES:
            raise ReviewError(f"Unknown status: {status}")
        if not isinstance(comments, str) or len(comments) > 20000:
            raise ReviewError("Comments must be text of at most 20,000 characters")
        if not isinstance(confirm_current_assessment, bool):
            raise ReviewError("Assessment confirmation must be a boolean")
        item_id = self.get(item_id)["id"]
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            previous = connection.execute("SELECT status FROM items WHERE id = ?", (item_id,)).fetchone()
            result = connection.execute(
                "UPDATE items SET status = ?, comments = ?, revision = revision + 1 "
                "WHERE id = ? AND revision = ?",
                (status, comments, item_id, revision),
            )
            if result.rowcount != 1:
                raise RevisionConflict("Item changed or no longer exists. Reload before saving.")
            if confirm_current_assessment or previous["status"] != status:
                acknowledge_assessment(connection, item_id)

    def add_evidence(self, item_id: str, result: dict) -> None:
        item_id = self.get(item_id)["id"]
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO evidence (item_id, result) VALUES (?, ?)",
                (item_id, json.dumps(result, ensure_ascii=False)),
            )

    def evidence(self, item_id: str) -> list[dict]:
        item_id = self.get(item_id)["id"]
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT run_id, result FROM evidence WHERE item_id = ? ORDER BY run_id DESC",
                (item_id,),
            ).fetchall()
        return [dict(json.loads(row["result"]), run_id=row["run_id"]) for row in rows]

    def refresh_history(self) -> list[dict]:
        from review_checklists.refresh import refresh_history
        with self.connection() as connection:
            return refresh_history(connection)

    def report(self) -> dict:
        from review_checklists.refresh import item_states, refresh_history
        with self.connection() as connection:
            connection.execute("BEGIN")
            metadata = {"description": "", "metadata_revision": "0", **dict(
                connection.execute("SELECT key, value FROM metadata")
            )}
            states = item_states(connection, metadata)
            items = [
                self.item(row, states[row["id"]])
                for row in connection.execute("SELECT * FROM items ORDER BY id")
            ]
            rows = connection.execute("SELECT * FROM evidence ORDER BY run_id DESC").fetchall()
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            history = refresh_history(connection)
        by_item: dict[str, list] = {}
        for row in rows:
            by_item.setdefault(row["item_id"], []).append(
                dict(json.loads(row["result"]), run_id=row["run_id"])
            )
        return {
            "schema_version": version,
            "metadata": metadata,
            "refresh_history": history,
            "summary": {status: sum(item["status"] == status for item in items) for status in STATUSES},
            "items": [dict(item, evidence=by_item.get(item["id"], [])) for item in items],
        }

    def export(self) -> str:
        return json.dumps(self.report(), ensure_ascii=False, indent=2) + "\n"
