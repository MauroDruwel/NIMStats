import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import { test } from "node:test";
import { onRequestGet as getHealth } from "../functions/api/health.js";
import { onRequestGet as getHistory } from "../functions/api/history.js";

function openFixture(t) {
  const sqlite = new DatabaseSync(":memory:");
  t.after(() => sqlite.close());
  sqlite.exec(readFileSync(new URL("../scripts/d1_schema.sql", import.meta.url), "utf8"));
  sqlite.exec(`
    INSERT INTO prompts (id, text) VALUES (1, 'Fixture prompt');
    INSERT INTO models (id, name, intelligence_score) VALUES (1, 'fixture/first', 75), (2, 'fixture/second', NULL);
  `);

  const addRun = sqlite.prepare("INSERT INTO runs (id, timestamp, prompt_id) VALUES (?, ?, 1)");
  const addResult = sqlite.prepare("INSERT INTO model_results (run_id, model_id, success) VALUES (?, ?, ?)");
  const DB = {
    prepare(sql) {
      const stmt = sqlite.prepare(sql);
      return {
        all: () => ({ results: stmt.all() }),
        bind: (...args) => ({ all: () => ({ results: stmt.all(...args) }) }),
        first: (column) => stmt.get()?.[column] ?? null,
      };
    },
    batch: (statements) => Promise.all(statements.map((stmt) => stmt.all())),
  };
  return { env: { DB }, addRun, addResult };
}

test("history limits recent runs by time and excludes empty run headers", async (t) => {
  const { env, addRun, addResult } = openFixture(t);
  const start = Date.parse("2026-11-01T00:00:00Z");
  for (let i = 1; i <= 170; i++) {
    addRun.run(i, new Date(start + i * 3_600_000).toISOString());
    addResult.run(i, 1, 1);
  }
  addResult.run(170, 2, 0);
  addRun.run(171, new Date(start + 180 * 3_600_000).toISOString());
  addRun.run(172, new Date(start).toISOString());
  addResult.run(172, 1, 1);

  const read = (query = "") => getHistory({ env, request: new Request("https://nimstats.test/api/history" + query) });
  const expanded = await (await read("?limit=168")).json();
  assert.equal(expanded.runs.length, 168);
  assert.equal(expanded.runs[0]._dbId, 170);
  assert.equal(expanded.runs.at(-1)._dbId, 3);
  assert.equal(expanded.runs[0].summary.successCount, 1);
  assert.equal(expanded.runs[0].summary.totalModels, 2);
  assert.deepEqual(expanded.modelIntel, { "fixture/first": 75, "fixture/second": 50 });
  assert.equal((await (await read()).json()).runs.length, 100);
  for (const limit of ["0", "169", "1.5", "nope"]) {
    assert.equal((await read("?limit=" + limit)).status, 400);
  }
});

test("health distinguishes missing, stale, and fresh results", async (t) => {
  const { env, addRun, addResult } = openFixture(t);
  const read = async (bindings = env) => {
    const response = await getHealth({ env: bindings });
    assert.equal(response.headers.get("Cache-Control"), "no-store");
    return { status: response.status, data: await response.json() };
  };

  const fresh = new Date(Date.now() - 1_000).toISOString();
  const stale = new Date(Date.now() - 3 * 3_600_000).toISOString();
  addRun.run(1, stale);
  addRun.run(2, fresh);
  assert.equal((await read({})).data.status, "unavailable");
  assert.equal((await read()).data.status, "unavailable");

  addResult.run(1, 1, 0);
  const staleResult = await read();
  assert.equal(staleResult.status, 503);
  assert.equal(staleResult.data.status, "stale");
  assert.equal(staleResult.data.latest_complete_run_at, stale);

  addResult.run(2, 1, 1);
  const freshResult = await read();
  assert.equal(freshResult.status, 200);
  assert.equal(freshResult.data.status, "ok");
  assert.equal(freshResult.data.latest_complete_run_at, fresh);
});
