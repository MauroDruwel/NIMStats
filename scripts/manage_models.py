#!/usr/bin/env python3
"""Manage models in the benchmark and database.

Usage:
  python scripts/manage_models.py list            # Show models in DB vs test_models.py
  python scripts/manage_models.py add <model_id>  # Add a model to ALL_MODELS
  python scripts/manage_models.py remove <model_id>  # Remove from ALL_MODELS + purge DB data
  python scripts/manage_models.py purge            # Remove all DB models not in ALL_MODELS
"""

import ast
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db_utils import HISTORY_DB  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
TEST_MODELS_FILE = SCRIPT_DIR / "test_models.py"


def _find_all_models_node(source: str):
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "ALL_MODELS":
                    if isinstance(node.value, ast.List):
                        return node, node.value
    raise RuntimeError("Could not find ALL_MODELS in test_models.py")


def _read_all_models() -> list[str]:
    source = TEST_MODELS_FILE.read_text(encoding="utf-8")
    _, list_node = _find_all_models_node(source)
    return [
        elt.value
        for elt in list_node.elts
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
    ]


def _write_all_models(models: list[str]) -> None:
    source = TEST_MODELS_FILE.read_text(encoding="utf-8")
    assign_node, _ = _find_all_models_node(source)
    source_lines = source.splitlines(keepends=True)
    indent = " " * 4
    new_body = "\n".join(indent + f'"{m}",' for m in models)
    new_block = "ALL_MODELS = [\n" + new_body + "\n]\n"
    start = assign_node.lineno - 1
    end = assign_node.end_lineno
    source_lines[start:end] = [new_block]
    TEST_MODELS_FILE.write_text("".join(source_lines), encoding="utf-8")


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

    purged_models = 0
    total_results = 0

    if orphans:
        print(f"Found {len(orphans)} orphaned model(s):")
        for m in orphans:
            row = conn.execute("SELECT id FROM models WHERE name = ?", (m,)).fetchone()
            mid = row[0]
            count = conn.execute("SELECT COUNT(*) FROM model_results WHERE model_id = ?", (mid,)).fetchone()[0]
            total_results += count
            print(f"  {m:50} {count} results")

        print(f"\nPurging {total_results} total model_results...")

        for m in orphans:
            row = conn.execute("SELECT id FROM models WHERE name = ?", (m,)).fetchone()
            mid = row[0]
            conn.execute(
                "UPDATE runs SET fastest_model_id = NULL, fastest_time = NULL WHERE fastest_model_id = ?",
                (mid,),
            )
            conn.execute("DELETE FROM model_results WHERE model_id = ?", (mid,))
            conn.execute("DELETE FROM models WHERE id = ?", (mid,))
            purged_models += 1

    # Clean up orphaned errors and prompts
    cur_errors = conn.execute(
        "DELETE FROM errors WHERE id NOT IN (SELECT DISTINCT error_id FROM model_results WHERE error_id IS NOT NULL)"
    )
    cur_prompts = conn.execute(
        "DELETE FROM prompts WHERE id NOT IN (SELECT DISTINCT prompt_id FROM runs)"
    )

    any_changes = purged_models > 0 or cur_errors.rowcount > 0 or cur_prompts.rowcount > 0

    if any_changes:
        conn.commit()
        conn.execute("VACUUM")
        print("\nPurge complete:")
        if purged_models > 0:
            print(f"  - Purged {purged_models} orphaned model(s) and {total_results} results.")
        if cur_errors.rowcount > 0:
            print(f"  - Cleaned up {cur_errors.rowcount} orphaned error message(s).")
        if cur_prompts.rowcount > 0:
            print(f"  - Cleaned up {cur_prompts.rowcount} orphaned prompt(s).")
        print("Database VACUUMed and compacted successfully.")
    else:
        print("No orphaned models, errors, or prompts found. DB is clean!")

    conn.close()
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
