const DEFAULT_LIMIT = 100;
const MAX_LIMIT = 168;

const HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Cache-Control": "public, max-age=60, s-maxage=300",
};

const RECENT_RESULTS = `
  WITH recent_runs AS (
    SELECT r.id, r.timestamp, r.prompt_id, r.fastest_model_id, r.fastest_time
    FROM runs r
    WHERE EXISTS (SELECT 1 FROM model_results WHERE run_id = r.id)
    ORDER BY r.timestamp DESC, r.id DESC
    LIMIT ?
  )
  SELECT r.id, r.timestamp, p.text AS prompt, fastest.name AS fastest_model, r.fastest_time,
         m.name AS model, mr.success, e.text AS error, mr.response_time,
         mr.tokens_generated, mr.total_tokens, mr.time_to_first_token
  FROM recent_runs r
  JOIN prompts p ON p.id = r.prompt_id
  JOIN model_results mr ON mr.run_id = r.id
  JOIN models m ON m.id = mr.model_id
  LEFT JOIN models fastest ON fastest.id = r.fastest_model_id
  LEFT JOIN errors e ON e.id = mr.error_id
  ORDER BY r.timestamp DESC, r.id DESC, mr.model_id ASC
`;

export async function onRequestGet(context) {
  if (!context.env.DB) {
    return unavailable();
  }

  const url = new URL(context.request.url);
  const requested = url.searchParams.get("limit");
  const limit = requested === null ? DEFAULT_LIMIT : Number(requested);
  if (!Number.isInteger(limit) || limit < 1 || limit > MAX_LIMIT) {
    return Response.json({ error: "limit must be an integer from 1 to 168" }, {
      status: 400,
      headers: { ...HEADERS, "Cache-Control": "no-store" },
    });
  }

  const cache = globalThis.caches?.default;
  // All equivalent requests share a key. Bump the version if the response shape changes.
  url.search = new URLSearchParams({ limit: String(limit), v: "2" });
  const cacheKey = new Request(url);
  if (cache) {
    try {
      const cached = await cache.match(cacheKey);
      if (cached) return cached;
    } catch (error) {
      console.warn("History cache read failed", error);
    }
  }

  try {
    const db = context.env.DB;
    const [measurements, scores] = await db.batch([
      db.prepare(RECENT_RESULTS).bind(limit),
      db.prepare("SELECT name, intelligence_score FROM models"),
    ]);

    const runs = new Map();
    for (const row of measurements.results) {
      let run = runs.get(row.id);
      if (!run) {
        run = {
          _dbId: row.id,
          timestamp: row.timestamp,
          prompt: row.prompt,
          models: [],
          summary: {
            fastestModel: row.fastest_model ?? "N/A",
            fastestTime: row.fastest_time ?? 0,
            successCount: 0,
            totalModels: 0,
          },
        };
        runs.set(row.id, run);
      }
      const success = row.success === 1;
      run.models.push({
        model: row.model,
        success,
        error: row.error ?? null,
        responseTime: row.response_time,
        tokensGenerated: row.tokens_generated,
        totalTokens: row.total_tokens,
        timeToFirstToken: row.time_to_first_token,
      });
      run.summary.successCount += Number(success);
      run.summary.totalModels += 1;
    }

    const modelIntel = runs.size ? Object.fromEntries(
      scores.results.map((row) => [row.name, row.intelligence_score ?? 50]),
    ) : {};
    const response = Response.json({ runs: [...runs.values()], modelIntel }, { headers: HEADERS });
    if (cache && runs.size) {
      context.waitUntil(cache.put(cacheKey, response.clone()).catch((error) => {
        console.warn("History cache write failed", error);
      }));
    }
    return response;
  } catch (error) {
    console.error("Could not read benchmark history from D1", error);
    return unavailable();
  }
}

function unavailable() {
  return Response.json({ error: "Benchmark history is unavailable" }, {
    status: 503,
    headers: { ...HEADERS, "Cache-Control": "no-store" },
  });
}
