// ─── SQLite Data Loader ───────────────────────────────────────────────────────
function loadFromDb(db) {
  const runsQ = db.exec(
    `SELECT r.id, r.timestamp, p.text, m.name, r.fastest_time
     FROM runs r
     JOIN prompts p ON r.prompt_id = p.id
     LEFT JOIN models m ON r.fastest_model_id = m.id
     ORDER BY r.timestamp DESC`
  );
  if (!runsQ.length || !runsQ[0].values.length) return { runs: [], modelIntel: {} };

  const runs = runsQ[0].values.map(([id, timestamp, prompt, fm, ft]) => ({
    _dbId: id,
    timestamp,
    prompt,
    models: [],
    summary: { fastestModel: fm || 'N/A', fastestTime: ft || 0 }
  }));

  const runById = new Map(runs.map((r, i) => [r._dbId, i]));

  const resQ = db.exec(
    `SELECT mr.run_id, m.name, mr.success, e.text, mr.response_time, mr.tokens_generated, mr.total_tokens
     FROM model_results mr
     JOIN models m ON mr.model_id = m.id
     LEFT JOIN errors e ON mr.error_id = e.id
     ORDER BY mr.run_id ASC`
  );
  if (resQ.length && resQ[0].values.length) {
    for (const [run_id, model, success, error, rt, tg, tt] of resQ[0].values) {
      const idx = runById.get(run_id);
      if (idx !== undefined) {
        runs[idx].models.push({
          model,
          success: success === 1,
          error: error || null,
          responseTime: rt,
          tokensGenerated: tg,
          totalTokens: tt,
        });
      }
    }
  }

  // Load model intelligence
  const modelIntel = {};
  try {
    const intelQ = db.exec("SELECT name, intelligence_score FROM models");
    if (intelQ.length && intelQ[0].values.length) {
      for (const [name, intel] of intelQ[0].values) {
        modelIntel[name] = intel != null ? intel : 50.0;
      }
    }
  } catch (err) {
    console.warn("Failed to read intelligence_score from database, using fallback:", err);
  }

  // Derive success count and total models per run
  for (const run of runs) {
    run.summary.successCount = run.models.filter(m => m.success).length;
    run.summary.totalModels = run.models.length;
  }

  return { runs, modelIntel };
}

// ─── Data Processing ──────────────────────────────────────────────────────────
function processData(data) {
  const runs = [...data.runs].reverse(); // chronological
  const modelNames = [...new Set(runs.flatMap(r => r.models.map(m => m.model)))];
  const modelStats = {};
  const modelIntel = data.modelIntel || {};

  for (const model of modelNames) {
    const results = runs.map(run => run.models.find(m => m.model === model) || null);
    const successes = results.filter(r => r && r.success);
    const testedResults = results.filter(r => r !== null);
    const times = successes.map(r => r.responseTime).filter(t => t > 0);
    const tpsArr = successes
      .filter(r => r.responseTime > 0)
      .map(r => r.tokensGenerated / (r.responseTime / 1000));

    modelStats[model] = {
      results,
      totalRuns: testedResults.length,
      successCount: successes.length,
      uptime: testedResults.length ? successes.length / testedResults.length : 0,
      responseTimes: results.map(r => (r && r.success && r.responseTime > 0) ? r.responseTime : null),
      throughputs: results.map(r => (r && r.success && r.responseTime > 0)
        ? r.tokensGenerated / (r.responseTime / 1000) : null),
      avgTime: times.length ? avg(times) : null,
      bestTime: times.length ? Math.min(...times) : null,
      avgTps: tpsArr.length ? avg(tpsArr) : null,
      wins: 0,
      errors: {},
      lastSeen: null,
      intelligence: modelIntel[model] != null ? modelIntel[model] : null,
    };

    // Last seen
    for (let i = results.length - 1; i >= 0; i--) {
      if (results[i] && results[i].success) {
        modelStats[model].lastSeen = runs[i]?.timestamp || null;
        break;
      }
    }

    // Errors
    results.filter(r => r && !r.success && r.error).forEach(r => {
      const t = categorizeError(r.error);
      modelStats[model].errors[t] = (modelStats[model].errors[t] || 0) + 1;
    });
  }

  // Wins
  runs.forEach(run => {
    const fm = run.summary?.fastestModel;
    if (fm && modelStats[fm]) modelStats[fm].wins++;
  });

  // Scores
  const validTimes = modelNames.filter(m => modelStats[m].avgTime != null).map(m => modelStats[m].avgTime);
  const validTps = modelNames.filter(m => modelStats[m].avgTps != null).map(m => modelStats[m].avgTps);
  const maxTime = validTimes.length ? Math.max(...validTimes) : 1;
  const minTime = validTimes.length ? Math.min(...validTimes) : 0;
  const maxTps = validTps.length ? Math.max(...validTps) : 1;
  const minTps = validTps.length ? Math.min(...validTps) : 0;

  for (const model of modelNames) {
    const s = modelStats[model];
    const speedScore = s.avgTime != null
      ? (1 - (s.avgTime - minTime) / Math.max(maxTime - minTime, 1)) * 100 : 0;
    const tpsScore = s.avgTps != null
      ? ((s.avgTps - minTps) / Math.max(maxTps - minTps, 1)) * 100 : 0;
    s.speedScore = speedScore;
    s.tpsScore = tpsScore;
    // Revised 4-factor scoring: reliability (30%) + intelligence (30%) + speed (20%) + throughput (20%)
    s.score = Math.round(s.uptime * 30 + speedScore * 0.2 + tpsScore * 0.2 + (s.intelligence / 100) * 30);

    // Trend
    const half = Math.floor(s.responseTimes.length / 2);
    const firstHalf = s.responseTimes.slice(0, half).filter(v => v != null);
    const secondHalf = s.responseTimes.slice(half).filter(v => v != null);
    if (firstHalf.length && secondHalf.length) {
      const diff = avg(secondHalf) - avg(firstHalf);
      s.trend = diff < -500 ? 'up' : diff > 500 ? 'down' : 'flat';
    } else {
      s.trend = 'flat';
    }
  }

  return { runs, modelNames, modelStats };
}

function recomputeStats() {
  const limit = state.limit;
  let runsSubset = [...state.rawRuns]; // rawRuns is in chronological order (oldest first)
  if (limit !== 'all') {
    const n = parseInt(limit, 10);
    runsSubset = state.rawRuns.slice(-n); // gets the latest n runs
  }
  state.runs = runsSubset;
  
  // Recalculate stats for the current subset of runs
  const modelNames = state.modelNames;
  const modelStats = {};

  for (const model of modelNames) {
    const results = state.runs.map(run => run.models.find(m => m.model === model) || null);
    const successes = results.filter(r => r && r.success);
    const testedResults = results.filter(r => r !== null);
    const times = successes.map(r => r.responseTime).filter(t => t > 0);
    const tpsArr = successes
      .filter(r => r.responseTime > 0)
      .map(r => r.tokensGenerated / (r.responseTime / 1000));

    modelStats[model] = {
      results,
      totalRuns: testedResults.length,
      successCount: successes.length,
      uptime: testedResults.length ? successes.length / testedResults.length : 0,
      responseTimes: results.map(r => (r && r.success && r.responseTime > 0) ? r.responseTime : null),
      throughputs: results.map(r => (r && r.success && r.responseTime > 0)
        ? r.tokensGenerated / (r.responseTime / 1000) : null),
      avgTime: times.length ? avg(times) : null,
      bestTime: times.length ? Math.min(...times) : null,
      avgTps: tpsArr.length ? avg(tpsArr) : null,
      wins: 0,
      errors: {},
      lastSeen: null,
      intelligence: (state.modelIntel && state.modelIntel[model] != null) ? state.modelIntel[model] : null,
    };

    // Last seen
    for (let i = results.length - 1; i >= 0; i--) {
      if (results[i] && results[i].success) {
        modelStats[model].lastSeen = state.runs[i]?.timestamp || null;
        break;
      }
    }

    // Errors
    results.filter(r => r && !r.success && r.error).forEach(r => {
      const t = categorizeError(r.error);
      modelStats[model].errors[t] = (modelStats[model].errors[t] || 0) + 1;
    });
  }

  // Wins
  state.runs.forEach(run => {
    const fm = run.summary?.fastestModel;
    if (fm && modelStats[fm]) modelStats[fm].wins++;
  });

  // Scores
  const validTimes = modelNames.filter(m => modelStats[m].avgTime != null).map(m => modelStats[m].avgTime);
  const validTps = modelNames.filter(m => modelStats[m].avgTps != null).map(m => modelStats[m].avgTps);
  const maxTime = validTimes.length ? Math.max(...validTimes) : 1;
  const minTime = validTimes.length ? Math.min(...validTimes) : 0;
  const maxTps = validTps.length ? Math.max(...validTps) : 1;
  const minTps = validTps.length ? Math.min(...validTps) : 0;

  for (const model of modelNames) {
    const s = modelStats[model];
    const speedScore = s.avgTime != null
      ? (1 - (s.avgTime - minTime) / Math.max(maxTime - minTime, 1)) * 100 : 0;
    const tpsScore = s.avgTps != null
      ? ((s.avgTps - minTps) / Math.max(maxTps - minTps, 1)) * 100 : 0;
    s.speedScore = speedScore;
    s.tpsScore = tpsScore;
    // Revised 4-factor scoring: reliability (30%) + intelligence (30%) + speed (20%) + throughput (20%)
    s.score = Math.round(s.uptime * 30 + speedScore * 0.2 + tpsScore * 0.2 + (s.intelligence / 100) * 30);

    // Trend
    const half = Math.floor(s.responseTimes.length / 2);
    const firstHalf = s.responseTimes.slice(0, half).filter(v => v != null);
    const secondHalf = s.responseTimes.slice(half).filter(v => v != null);
    if (firstHalf.length && secondHalf.length) {
      const diff = avg(secondHalf) - avg(firstHalf);
      s.trend = diff < -500 ? 'up' : diff > 500 ? 'down' : 'flat';
    } else {
      s.trend = 'flat';
    }
  }

  state.modelStats = modelStats;
}
