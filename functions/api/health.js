const STALE_AFTER_SECONDS = 2 * 60 * 60;

export async function onRequestGet({ env }) {
  const now = new Date();
  let latestRun;
  try {
    if (env.DB) {
      latestRun = await env.DB.prepare(`
        SELECT r.timestamp FROM runs r
        WHERE EXISTS (SELECT 1 FROM model_results WHERE run_id = r.id)
        ORDER BY r.timestamp DESC, r.id DESC
        LIMIT 1
      `).first("timestamp");
    }
  } catch (error) {
    console.error("Could not check benchmark freshness", error);
  }

  const latest = Date.parse(latestRun);
  const age = Number.isFinite(latest) ? Math.max(0, Math.floor((now.getTime() - latest) / 1000)) : null;
  let status = "unavailable";
  if (age !== null) status = age >= STALE_AFTER_SECONDS ? "stale" : "ok";

  return Response.json({
    status,
    timestamp: now.toISOString(),
    service: "nimstats-edge",
    latest_complete_run_at: age === null ? null : latestRun,
    age_seconds: age,
    stale_after_seconds: STALE_AFTER_SECONDS,
  }, {
    status: status === "ok" ? 200 : 503,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "no-store",
    },
  });
}
