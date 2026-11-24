import { mkdir, open } from "node:fs/promises";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

import { createMockFetcher, MOCK_SIGNING_KEY } from "./mock.mjs";
import {
  MODELS, PROBE_TIMEOUT_MS, PROFILE, REGIONS, SLOT_MS, currentSlot, probePath, signProbe, validSigningKey,
} from "./protocol.mjs";

const CONTROLLER_TIMEOUT_MS = PROBE_TIMEOUT_MS + 5_000;
const SLOT_END_BUFFER_MS = Object.keys(MODELS).length * CONTROLLER_TIMEOUT_MS + 10_000;

function liveTargets(env) {
  const targets = [];
  for (const region of REGIONS) {
    const configKey = region.toUpperCase();
    const rawUrl = env[`PROBE_URL_${configKey}`] ?? "";
    const originPattern = new RegExp(`^https://nimstats-regional-probe-${region}\\.[a-z0-9-]+\\.workers\\.dev/?$`);
    const key = env[`PROBE_SIGNING_KEY_${configKey}`];
    if (!originPattern.test(rawUrl) || !validSigningKey(key)) {
      throw new Error(`Supply the Worker URL and 64-digit hex signing key for ${configKey}.`);
    }
    targets.push({ region, origin: new URL(rawUrl).origin, key, fetcher: fetch });
  }
  if (new Set(targets.map(({ key }) => key)).size !== REGIONS.length) {
    throw new Error("Use a different signing key for each region.");
  }
  return targets;
}

export async function reserveSlot(directory, slot) {
  await mkdir(directory, { recursive: true, mode: 0o700 });
  const path = join(directory, `slot-${slot}.ndjson`);
  try {
    return await open(path, "wx", 0o600);
  } catch (error) {
    if (error.code !== "EEXIST") throw error;
    throw new Error(`Slot ${slot} already reserved at ${path}.`);
  }
}

async function executeProbe({ region, origin, key, fetcher }, model, slot) {
  const path = probePath(slot, model);
  const slotStartedAt = new Date(slot * SLOT_MS).toISOString();
  const fallback = { region, model: MODELS[model], slotStartedAt };
  try {
    const signature = await signProbe(key, region, path);
    const response = await fetcher(origin + path, {
      method: "POST",
      redirect: "error",
      signal: AbortSignal.timeout(CONTROLLER_TIMEOUT_MS),
      headers: { "X-Nimstats-Probe-Signature": signature },
    });
    if (!response.ok) {
      if (response.body) await response.body.cancel().catch(() => {});
      return { ...fallback, outcome: "probe_http", probeStatusCode: response.status };
    }
    const sample = await response.json();
    if (sample?.schemaVersion !== 1 || sample.profile !== PROFILE || sample.region !== region
        || sample.model !== MODELS[model] || sample.slotStartedAt !== slotStartedAt) {
      return { ...fallback, outcome: "probe_invalid_response" };
    }
    return sample;
  } catch (error) {
    return {
      ...fallback,
      outcome: error.name === "TimeoutError" ? "probe_timeout" : "probe_request_failed",
    };
  }
}

async function main(mode, env) {
  if (mode !== "--mock" && mode !== "--run") {
    throw new Error("Usage: node probes/dispatch.mjs --mock or --run");
  }
  const mock = mode === "--mock";
  const now = Date.now();
  const slot = currentSlot(now);
  const targets = mock ? REGIONS.map((region) => ({
    region, origin: "https://nimstats.invalid", key: MOCK_SIGNING_KEY, fetcher: createMockFetcher(region),
  })) : liveTargets(env);
  let ledger;
  if (!mock) {
    if (now >= (slot + 1) * SLOT_MS - SLOT_END_BUFFER_MS) {
      throw new Error("The slot is about to end. Wait for the next two-hour UTC slot.");
    }
    if (!env.PROBE_RESULTS_DIRECTORY) {
      throw new Error("Supply a persistent result directory outside the repository via PROBE_RESULTS_DIRECTORY.");
    }
    ledger = await reserveSlot(env.PROBE_RESULTS_DIRECTORY, slot);
  }

  let incomplete = false;
  try {
    for (const model of Object.keys(MODELS)) {
      // Compare regions in one time window, with one model in flight per region.
      const records = await Promise.all(targets.map((target) => executeProbe(target, model, slot)));
      for (const record of records) {
        const output = JSON.stringify(record) + "\n";
        if (ledger) await ledger.writeFile(output);
        process.stdout.write(output);
        incomplete ||= record.outcome.startsWith("probe_") || (!mock && !record.placement?.executionColo);
      }
    }
  } finally {
    if (ledger) await ledger.close();
  }
  if (incomplete) process.exitCode = 1;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    await main(process.argv[2], process.env);
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
