"""Shared, persistent review operations for the CLI and localhost UI."""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

from review_checklists.corpus import ReviewError
from review_checklists.filters import FilterValue, filter_items, filter_values


STATUSES = ("Not reviewed", "Compliant", "Non-compliant", "Not applicable")
SCHEMA_VERSION = 1


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
            if version != SCHEMA_VERSION:
                raise ReviewError(f"Unsupported review schema {version}; expected {SCHEMA_VERSION}")
            self.metadata = dict(connection.execute("SELECT key, value FROM metadata"))

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
    def create(cls, path: Path, name: str, recos: list[dict], corpus: Path):
        if not name.strip() or not recos:
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
                connection.executemany("INSERT INTO metadata VALUES (?, ?)", {
                    "name": name,
                    "created_at": utc_now(),
                    "corpus_path": str(corpus.resolve()),
                    "corpus_sha256": hashlib.sha256(snapshot.encode("utf-8")).hexdigest(),
                }.items())
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
    def item(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "recommendation": json.loads(row["recommendation"]),
            "status": row["status"],
            "comments": row["comments"],
            "revision": row["revision"],
        }

    def items(
        self, search: str = "", status: FilterValue = "", *,
        severity: FilterValue = "", waf: FilterValue = "", service: FilterValue = "",
        with_arg: bool = False,
    ) -> list[dict]:
        statuses = filter_values(status)
        if unknown := set(statuses) - set(STATUSES):
            raise ReviewError(f"Unknown status: {', '.join(sorted(unknown))}")
        with self.connection() as connection:
            rows = connection.execute("SELECT * FROM items ORDER BY id").fetchall()
        items = filter_items(
            [self.item(row) for row in rows], severity=severity, waf=waf, service=service,
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
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            raise ReviewError(f"Unknown recommendation ID: {item_id}")
        return self.item(row)

    def update(self, item_id: str, status: str, comments: str, revision: int) -> None:
        if status not in STATUSES:
            raise ReviewError(f"Unknown status: {status}")
        if not isinstance(comments, str) or len(comments) > 20000:
            raise ReviewError("Comments must be text of at most 20,000 characters")
        with self.connection() as connection:
            result = connection.execute(
                "UPDATE items SET status = ?, comments = ?, revision = revision + 1 "
                "WHERE id = ? AND revision = ?",
                (status, comments, item_id, revision),
            )
            if result.rowcount != 1:
                raise ReviewError("Item changed or no longer exists. Reload before saving.")

    def add_evidence(self, item_id: str, result: dict) -> None:
        self.get(item_id)
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO evidence (item_id, result) VALUES (?, ?)",
                (item_id, json.dumps(result, ensure_ascii=False)),
            )

    def evidence(self, item_id: str) -> list[dict]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT run_id, result FROM evidence WHERE item_id = ? ORDER BY run_id DESC",
                (item_id,),
            ).fetchall()
        return [dict(json.loads(row["result"]), run_id=row["run_id"]) for row in rows]

    def report(self) -> dict:
        items = self.items()
        with self.connection() as connection:
            rows = connection.execute("SELECT * FROM evidence ORDER BY run_id DESC").fetchall()
        by_item: dict[str, list] = {}
        for row in rows:
            by_item.setdefault(row["item_id"], []).append(
                dict(json.loads(row["result"]), run_id=row["run_id"])
            )
        return {
            "schema_version": SCHEMA_VERSION,
            "metadata": self.metadata,
            "summary": {status: sum(item["status"] == status for item in items) for status in STATUSES},
            "items": [dict(item, evidence=by_item.get(item["id"], [])) for item in items],
        }

    def export(self) -> str:
        return json.dumps(self.report(), ensure_ascii=False, indent=2) + "\n"
