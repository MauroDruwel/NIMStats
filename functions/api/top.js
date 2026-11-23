// Cloudflare Pages Function: /api/top
// Returns top models sorted by reliability, composite score, speed, intelligence, or throughput.
// Edge-cached on Cloudflare CDN to ensure 100% free-tier usage.
//
// Query parameters:
//   sort: 'reliability' | 'uptime' | 'composite' | 'speed' | 'latency' | 'intelligence' | 'tps' (default: 'reliability')
//   limit: integer 1..50 (default: 5)
//   window: integer 10..500 (default: 100)

export async function onRequestGet({ request, env }) {
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
    const url = new URL(request.url);
    const rawLimit = parseInt(url.searchParams.get("limit") || "5", 10);
    const limit = isNaN(rawLimit) ? 5 : Math.max(1, Math.min(rawLimit, 50));

    const rawWindow = parseInt(url.searchParams.get("window") || "100", 10);
    const windowRuns = isNaN(rawWindow) ? 100 : Math.max(10, Math.min(rawWindow, 500));

    const sortParam = (url.searchParams.get("sort") || "reliability").toLowerCase();

    // Query aggregated stats over trailing window from D1
    const { results } = await env.DB.prepare(
      `SELECT m.id as model_id,
              m.name as model,
              COALESCE(m.intelligence_score, 50.0) as intelligence,
              COUNT(mr.run_id) as total_tests,
              SUM(CASE WHEN mr.success = 1 THEN 1 ELSE 0 END) as successful_tests,
              ROUND(CAST(SUM(CASE WHEN mr.success = 1 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(mr.run_id), 4) as uptime,
              ROUND(1.0 - (CAST(SUM(CASE WHEN mr.success = 1 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(mr.run_id)), 4) as error_rate,
              ROUND(AVG(CASE WHEN mr.success = 1 AND mr.response_time > 0 THEN mr.response_time END), 1) as avg_time,
              MIN(CASE WHEN mr.success = 1 AND mr.response_time > 0 THEN mr.response_time END) as best_time,
              ROUND(AVG(CASE WHEN mr.success = 1 AND mr.time_to_first_token > 0 THEN mr.time_to_first_token END), 1) as avg_ttft,
              ROUND(AVG(CASE WHEN mr.success = 1 AND mr.response_time > 0 THEN (mr.tokens_generated * 1000.0 / mr.response_time) END), 1) as avg_tps
       FROM model_results mr
       JOIN models m ON mr.model_id = m.id
       JOIN (SELECT id FROM runs ORDER BY timestamp DESC LIMIT ?) r ON mr.run_id = r.id
       GROUP BY mr.model_id, m.name, m.intelligence_score`
    ).bind(windowRuns).all();

    const rows = results || [];

    // Calculate speed scores and composite ranking (50% Intelligence, 25% Speed, 25% Reliability)
    const validTimes = rows.filter((r) => r.avg_time != null).map((r) => r.avg_time);
    const validTps = rows.filter((r) => r.avg_tps != null).map((r) => r.avg_tps);
    const minTime = validTimes.length ? Math.min(...validTimes) : 0;
    const maxTime = validTimes.length ? Math.max(...validTimes) : 1;
    const minTps = validTps.length ? Math.min(...validTps) : 0;
    const maxTps = validTps.length ? Math.max(...validTps) : 1;

    const scored = rows.map((r) => {
      const speedScore = r.avg_time != null
        ? (1 - (r.avg_time - minTime) / Math.max(maxTime - minTime, 1)) * 100
        : 0;
      const tpsScore = r.avg_tps != null
        ? ((r.avg_tps - minTps) / Math.max(maxTps - minTps, 1)) * 100
        : 0;
      const combinedSpeed = (speedScore * 0.6) + (tpsScore * 0.4);
      const compositeScore = Math.round((r.intelligence * 0.50) + (combinedSpeed * 0.25) + (r.uptime * 100 * 0.25));

      return {
        model: r.model,
        uptime: r.uptime,
        uptime_pct: `${(r.uptime * 100).toFixed(1)}%`,
        error_rate: r.error_rate,
        error_rate_pct: `${(r.error_rate * 100).toFixed(1)}%`,
        avg_time_ms: r.avg_time,
        best_time_ms: r.best_time,
        avg_ttft_ms: r.avg_ttft,
        avg_tps: r.avg_tps,
        intelligence: r.intelligence,
        composite_score: compositeScore,
        total_tests: r.total_tests,
        successful_tests: r.successful_tests,
        failed_tests: r.total_tests - r.successful_tests,
      };
    });

    // Sort according to requested parameter
    if (sortParam === "composite") {
      scored.sort((a, b) => b.composite_score - a.composite_score || b.uptime - a.uptime);
    } else if (sortParam === "speed" || sortParam === "latency") {
      scored.sort((a, b) => {
        const at = a.avg_time_ms ?? Infinity;
        const bt = b.avg_time_ms ?? Infinity;
        return at - bt || b.uptime - a.uptime;
      });
    } else if (sortParam === "intelligence") {
      scored.sort((a, b) => b.intelligence - a.intelligence || b.uptime - a.uptime);
    } else if (sortParam === "tps" || sortParam === "throughput") {
      scored.sort((a, b) => (b.avg_tps ?? 0) - (a.avg_tps ?? 0) || b.uptime - a.uptime);
    } else {
      // Default: reliability / uptime
      scored.sort((a, b) => b.uptime - a.uptime || (a.avg_time_ms ?? Infinity) - (b.avg_time_ms ?? Infinity));
    }

    const topModels = scored.slice(0, limit).map((m, idx) => ({
      rank: idx + 1,
      ...m,
    }));

    return new Response(
      JSON.stringify({
        sort: sortParam,
        limit,
        window_runs: windowRuns,
        timestamp: new Date().toISOString(),
        models: topModels,
      }),
      {
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
          "Cache-Control": "public, max-age=300, s-maxage=300",
        },
      }
    );
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
