#!/usr/bin/env python3
"""Manage models in the benchmark and database.

Usage:
  python scripts/manage_models.py list            # Show models in DB vs test_models.py
  python scripts/manage_models.py add <model_id>  # Add a model to ALL_MODELS
  python scripts/manage_models.py remove <model_id>  # Remove from ALL_MODELS + purge DB data
  python scripts/manage_models.py purge            # Remove all DB models not in ALL_MODELS
"""

import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db_utils import HISTORY_DB  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
TEST_MODELS_FILE = SCRIPT_DIR / "test_models.py"


def _read_all_models() -> list[str]:
    source = TEST_MODELS_FILE.read_text(encoding="utf-8")
    match = re.search(r"ALL_MODELS\s*=\s*\[(.*?)\]", source, re.DOTALL)
    if not match:
        raise RuntimeError("Could not find ALL_MODELS in test_models.py")
    return re.findall(r'"([^"]+)"', match.group(1))


def _write_all_models(models: list[str]) -> None:
    source = TEST_MODELS_FILE.read_text(encoding="utf-8")
    lines = ['    "' + m + '",' for m in models]
    block = "ALL_MODELS = [\n" + "\n".join(lines) + "\n]\n"
    source = re.sub(r"ALL_MODELS\s*=\s*\[.*?\n\]", block, source, count=1, flags=re.DOTALL)
    TEST_MODELS_FILE.write_text(source, encoding="utf-8")


def _db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(HISTORY_DB))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def cmd_list() -> int:
    configured = _read_all_models()
    print("=== Models in test_models.py ===")
    for i, m in enumerate(configured, 1):
        print(f"  {i:2}. {m}")
    print(f"  Total: {len(configured)}")

    conn = _db_connect()
    db_models = [r[0] for r in conn.execute("SELECT name FROM models ORDER BY name").fetchall()]
    print(f"\n=== Models in history.db ({len(db_models)}) ===")
    for m in db_models:
        in_cfg = "OK" if m in configured else "ORPHANED"
        count = conn.execute(
            "SELECT COUNT(*) FROM model_results mr JOIN models m ON mr.model_id = m.id WHERE m.name = ?",
            (m,),
        ).fetchone()[0]
        print(f"  {in_cfg:9} {m:50} {count} results")

    orphans = [m for m in db_models if m not in configured]
    if orphans:
        print(f"\n{len(orphans)} orphaned model(s) in DB not in test_models.py.")
        print("Run 'python scripts/manage_models.py purge' to clean them up.")
    else:
        print("\nAll DB models match test_models.py. Clean!")

    conn.close()
    return 0


def cmd_add(model_id: str) -> int:
    models = _read_all_models()
    if model_id in models:
        print(f"'{model_id}' is already in ALL_MODELS.")
        return 1
    models.append(model_id)
    _write_all_models(models)
    print(f"Added '{model_id}' to ALL_MODELS ({len(models)} total).")
    half = len(models) // 2 + len(models) % 2
    print(f"Groups auto-balanced: group1={half}, group2={len(models) - half}.")
    return 0


def cmd_remove(model_id: str) -> int:
    models = _read_all_models()
    if model_id not in models:
        print(f"'{model_id}' is not in ALL_MODELS.")
    else:
        models.remove(model_id)
        _write_all_models(models)
        print(f"Removed '{model_id}' from ALL_MODELS ({len(models)} total).")
        half = len(models) // 2 + len(models) % 2
        print(f"Groups auto-balanced: group1={half}, group2={len(models) - half}.")

    conn = _db_connect()
    row = conn.execute("SELECT id FROM models WHERE name = ?", (model_id,)).fetchone()
    if not row:
        print(f"'{model_id}' not found in history.db — nothing to purge.")
        conn.close()
        return 0

    model_id_db = row[0]
    count = conn.execute("SELECT COUNT(*) FROM model_results WHERE model_id = ?", (model_id_db,)).fetchone()[0]

    # Check if any run has this model as fastest_model_id
    fastest = conn.execute(
        "SELECT COUNT(*) FROM runs WHERE fastest_model_id = ?", (model_id_db,)
    ).fetchone()[0]
    if fastest:
        print(f"  Clearing fastest_model_id on {fastest} run(s)...")
        conn.execute(
            "UPDATE runs SET fastest_model_id = NULL, fastest_time = NULL WHERE fastest_model_id = ?",
            (model_id_db,),
        )

    conn.execute("DELETE FROM model_results WHERE model_id = ?", (model_id_db,))
    conn.execute("DELETE FROM models WHERE id = ?", (model_id_db,))
    conn.commit()
    conn.execute("VACUUM")
    conn.close()

    print(f"Purged {count} model_results and removed '{model_id}' from history.db.")
    return 0


def cmd_purge() -> int:
    configured = set(_read_all_models())
    conn = _db_connect()
    db_models = [r[0] for r in conn.execute("SELECT name FROM models ORDER BY name").fetchall()]
    orphans = [m for m in db_models if m not in configured]

    if not orphans:
        print("No orphaned models found. DB is clean!")
        conn.close()
        return 0

    print(f"Found {len(orphans)} orphaned model(s):")
    total = 0
    for m in orphans:
        row = conn.execute("SELECT id FROM models WHERE name = ?", (m,)).fetchone()
        mid = row[0]
        count = conn.execute("SELECT COUNT(*) FROM model_results WHERE model_id = ?", (mid,)).fetchone()[0]
        total += count
        print(f"  {m:50} {count} results")

    print(f"\nPurging {total} total model_results...")

    for m in orphans:
        row = conn.execute("SELECT id FROM models WHERE name = ?", (m,)).fetchone()
        mid = row[0]
        conn.execute(
            "UPDATE runs SET fastest_model_id = NULL, fastest_time = NULL WHERE fastest_model_id = ?",
            (mid,),
        )
        conn.execute("DELETE FROM model_results WHERE model_id = ?", (mid,))
        conn.execute("DELETE FROM models WHERE id = ?", (mid,))

    conn.commit()
    conn.execute("VACUUM")
    conn.close()

    print("Done! Purged orphaned models and VACUUMed history.db.")
    return 0


USAGE = """Usage:
  python scripts/manage_models.py list
  python scripts/manage_models.py add <model_id>
  python scripts/manage_models.py remove <model_id>
  python scripts/manage_models.py purge"""


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(USAGE)
        return 1

    cmd = args[0]
    if cmd == "list":
        return cmd_list()
    elif cmd == "add" and len(args) == 2:
        return cmd_add(args[1])
    elif cmd == "remove" and len(args) == 2:
        return cmd_remove(args[1])
    elif cmd == "purge":
        return cmd_purge()
    else:
        print(USAGE)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
