-- Cloudflare D1 Schema for NIMStats
-- Run with: npx wrangler d1 execute nimstats-db --file=scripts/d1_schema.sql

CREATE TABLE IF NOT EXISTS prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    intelligence_score REAL DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    prompt_id INTEGER NOT NULL REFERENCES prompts(id),
    fastest_model_id INTEGER REFERENCES models(id),
    fastest_time INTEGER
);

CREATE TABLE IF NOT EXISTS model_results (
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    model_id INTEGER NOT NULL REFERENCES models(id),
    success INTEGER NOT NULL DEFAULT 0,
    error_id INTEGER REFERENCES errors(id),
    response_time INTEGER,
    tokens_generated INTEGER,
    total_tokens INTEGER,
    time_to_first_token INTEGER,
    PRIMARY KEY (run_id, model_id)
);

CREATE INDEX IF NOT EXISTS idx_runs_ts ON runs(timestamp);
CREATE INDEX IF NOT EXISTS idx_mr_model ON model_results(model_id);
CREATE INDEX IF NOT EXISTS idx_mr_run ON model_results(run_id);
