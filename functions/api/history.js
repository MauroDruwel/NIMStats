// Cloudflare Pages Function: /api/history
// Returns trailing benchmark runs and model intelligence scores from Cloudflare D1.
// Edge-cached globally on Cloudflare CDN to ensure 100% free-tier usage.

export async function onRequestGet({ env }) {
  if (!env.DB) {
    return new Response(
      JSON.stringify({
        error: "Cloudflare D1 database binding 'DB' is not configured yet.",
        docs: "Bind 'DB' in Cloudflare Dashboard -> Pages -> Settings -> Functions -> D1 Database Bindings",
      }),
      {
        status: 503,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
      }
    );
  }

  try {
    // 1. Fetch recent runs (limit to trailing 100 runs)
    const runsResult = await env.DB.prepare(
      `SELECT r.id, r.timestamp, p.text as prompt, m.name as fastest_model, r.fastest_time
       FROM runs r
       JOIN prompts p ON r.prompt_id = p.id
       LEFT JOIN models m ON r.fastest_model_id = m.id
       ORDER BY r.timestamp DESC
       LIMIT 100`
    ).all();

    const rawRuns = runsResult.results || [];
    if (!rawRuns.length) {
      return new Response(JSON.stringify({ runs: [], modelIntel: {} }), {
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
          "Cache-Control": "public, max-age=300, s-maxage=3600",
        },
      });
    }

    const runIds = rawRuns.map((r) => r.id);
    const minRunId = Math.min(...runIds);
    const maxRunId = Math.max(...runIds);

    // 2. Fetch model results within the ID range of the fetched runs
    const resultsQ = await env.DB.prepare(
      `SELECT mr.run_id, m.name as model, mr.success, e.text as error, mr.response_time, mr.tokens_generated, mr.total_tokens, mr.time_to_first_token
       FROM model_results mr
       JOIN models m ON mr.model_id = m.id
       LEFT JOIN errors e ON mr.error_id = e.id
       WHERE mr.run_id BETWEEN ? AND ?
       ORDER BY mr.run_id ASC`
    ).bind(minRunId, maxRunId).all();

    // 3. Fetch model intelligence scores
    const intelQ = await env.DB.prepare(
      "SELECT name, intelligence_score FROM models"
    ).all();

    const modelIntel = {};
    for (const row of intelQ.results || []) {
      modelIntel[row.name] = row.intelligence_score != null ? row.intelligence_score : 50.0;
    }

    // 4. Assemble runs structure matching frontend expectation
    const runs = rawRuns.map((r) => ({
      _dbId: r.id,
      timestamp: r.timestamp,
      prompt: r.prompt,
      models: [],
      summary: {
        fastestModel: r.fastest_model || "N/A",
        fastestTime: r.fastest_time || 0,
      },
    }));

    const runMap = new Map(runs.map((r) => [r._dbId, r]));

    for (const mr of resultsQ.results || []) {
      const run = runMap.get(mr.run_id);
      if (run) {
        run.models.push({
          model: mr.model,
          success: mr.success === 1,
          error: mr.error || null,
          responseTime: mr.response_time,
          tokensGenerated: mr.tokens_generated,
          totalTokens: mr.total_tokens,
          timeToFirstToken: mr.time_to_first_token,
        });
      }
    }

    for (const run of runs) {
      run.summary.successCount = run.models.filter((m) => m.success).length;
      run.summary.totalModels = run.models.length;
    }

    return new Response(JSON.stringify({ runs, modelIntel }), {
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "public, max-age=300, s-maxage=3600",
      },
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      },
    });
  }
}
