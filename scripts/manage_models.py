#!/usr/bin/env python3
"""Manage models in the benchmark and database.

Usage:
  python scripts/manage_models.py list              # Show configured and retired models
  python scripts/manage_models.py add <model_id>    # Add a model to ALL_MODELS
  python scripts/manage_models.py remove <model_id> # Retire a model and retain its history
  python scripts/manage_models.py purge             # Delete all retired-model history from D1
"""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from push_run_to_d1 import execute_d1_sql, get_auth_token

SCRIPT_DIR = Path(__file__).resolve().parent
TEST_MODELS_FILE = SCRIPT_DIR / "test_models.py"


def _find_all_models_node(source: str):
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "ALL_MODELS" and isinstance(node.value, ast.List):
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


def cmd_list() -> int:
    configured = _read_all_models()
    print("=== Models in test_models.py ===")
    for i, m in enumerate(configured, 1):
        print(f"  {i:2}. {m}")
    print(f"  Total: {len(configured)}")

    token = get_auth_token()
    if not token:
        print("Warning: No Cloudflare API token found to inspect D1.")
        return 0

    response = execute_d1_sql(
        "SELECT m.name, COUNT(mr.run_id) AS result_count FROM models m "
        "LEFT JOIN model_results mr ON mr.model_id = m.id GROUP BY m.id ORDER BY m.name;",
        token,
    )
    db_models = response.get("result", [{}])[0].get("results", [])
    print(f"\n=== Models in Cloudflare D1 ({len(db_models)}) ===")
    configured_names = set(configured)
    for row in db_models:
        name = row["name"]
        status = "ACTIVE" if name in configured_names else "RETIRED"
        print(f"  {status:9} {name:50} {row['result_count']} results")

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
        return 0

    models.remove(model_id)
    _write_all_models(models)
    print(f"Retired '{model_id}' from ALL_MODELS ({len(models)} total). D1 history retained.")
    half = len(models) // 2 + len(models) % 2
    print(f"Groups auto-balanced: group1={half}, group2={len(models) - half}.")
    return 0


def cmd_purge() -> int:
    configured = set(_read_all_models())
    token = get_auth_token()
    if not token:
        print("Warning: No Cloudflare API token found; DB purge skipped in Cloudflare D1.")
        return 0

    resp = execute_d1_sql("SELECT id, name FROM models ORDER BY name;", token)
    db_rows = resp.get("result", [{}])[0].get("results", [])
    retired = [r for r in db_rows if r["name"] not in configured]

    if not retired:
        print("No retired models found in Cloudflare D1.")
        return 0

    print(f"Found {len(retired)} retired model(s) in Cloudflare D1:")
    stmts = []
    total_results = 0
    for r in retired:
        mid = r["id"]
        m = r["name"]
        c_resp = execute_d1_sql(f"SELECT COUNT(*) as count FROM model_results WHERE model_id = {mid};", token)
        cnt = c_resp.get("result", [{}])[0].get("results", [{}])[0].get("count", 0)
        total_results += cnt
        print(f"  {m:50} {cnt} results")
        stmts.append(f"UPDATE runs SET fastest_model_id = NULL, fastest_time = NULL WHERE fastest_model_id = {mid};")
        stmts.append(f"DELETE FROM model_results WHERE model_id = {mid};")
        stmts.append(f"DELETE FROM models WHERE id = {mid};")

    stmts.append("DELETE FROM errors WHERE id NOT IN (SELECT DISTINCT error_id FROM model_results WHERE error_id IS NOT NULL);")
    stmts.append("DELETE FROM prompts WHERE id NOT IN (SELECT DISTINCT prompt_id FROM runs);")
    execute_d1_sql(" ".join(stmts), token)
    print(f"\nPurge complete: Removed {len(retired)} retired models and {total_results} results from Cloudflare D1.")
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
