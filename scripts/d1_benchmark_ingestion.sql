-- One prepared INSERT into this view publishes an entire benchmark run through
-- its trigger. The REST caller needs no multi-statement transaction support.
CREATE VIEW IF NOT EXISTS benchmark_ingest (
    run_timestamp, prompt_text, fastest_model, fastest_time, measurements
) AS SELECT NULL, NULL, NULL, NULL, NULL WHERE 0;

CREATE TRIGGER IF NOT EXISTS benchmark_ingest_run
INSTEAD OF INSERT ON benchmark_ingest
BEGIN
    SELECT CASE WHEN json_array_length(NEW.measurements) > 0
        AND json_type(NEW.measurements) = 'array' THEN 1
        ELSE RAISE(ABORT, 'Benchmark measurements must be a nonempty array') END;

    INSERT INTO prompts (text) VALUES (NEW.prompt_text)
    ON CONFLICT (text) DO NOTHING;

    INSERT INTO models (name)
    SELECT json_extract(value, '$.model') FROM json_each(NEW.measurements) WHERE TRUE
    ON CONFLICT (name) DO NOTHING;

    INSERT INTO errors (text)
    SELECT json_extract(value, '$.error') FROM json_each(NEW.measurements)
    WHERE json_extract(value, '$.error') IS NOT NULL
    ON CONFLICT (text) DO NOTHING;

    -- Matching by capture timestamp and prompt also supports replaying artifacts
    -- created before this migration. SQLite serializes writes to the database.
    INSERT INTO runs (timestamp, prompt_id, fastest_model_id, fastest_time)
    SELECT NEW.run_timestamp, prompts.id, models.id, NEW.fastest_time
    FROM prompts
    LEFT JOIN models ON models.name = NEW.fastest_model
    WHERE prompts.text = NEW.prompt_text
      AND NOT EXISTS (
          SELECT 1 FROM runs WHERE timestamp = NEW.run_timestamp AND prompt_id = prompts.id
      );

    INSERT INTO model_results (
        run_id, model_id, success, error_id, response_time,
        tokens_generated, total_tokens, time_to_first_token
    )
    SELECT
        matching_run.id, models.id, json_extract(measurement.value, '$.success'), errors.id,
        json_extract(measurement.value, '$.responseTime'),
        json_extract(measurement.value, '$.tokensGenerated'),
        json_extract(measurement.value, '$.totalTokens'),
        json_extract(measurement.value, '$.timeToFirstToken')
    FROM json_each(NEW.measurements) AS measurement
    JOIN models ON models.name = json_extract(measurement.value, '$.model')
    LEFT JOIN errors ON errors.text = json_extract(measurement.value, '$.error')
    CROSS JOIN (
        SELECT runs.id FROM runs
        JOIN prompts ON prompts.id = runs.prompt_id
        WHERE runs.timestamp = NEW.run_timestamp AND prompts.text = NEW.prompt_text
        ORDER BY runs.id DESC LIMIT 1
    ) AS matching_run
    WHERE TRUE
    ON CONFLICT (run_id, model_id) DO NOTHING;

    DELETE FROM runs WHERE id IN (
        SELECT id FROM runs ORDER BY timestamp DESC, id DESC LIMIT -1 OFFSET 720
    );
END;
