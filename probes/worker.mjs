import {
  MAX_TOKENS, MODELS, PROBE_TIMEOUT_MS, PROFILE, REGIONS, SLOT_MS, currentSlot, validSigningKey,
  verifyProbe,
} from "./protocol.mjs";

const NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions";
const PROMPT = "In three short sentences, explain why Earth has seasons.";
const MAX_STREAM_BYTES = 48 * 1024;
const MAX_EVENT_COUNT = 256;

/**
 * @typedef {"ok" | "rate_limited" | "upstream_auth" | "upstream_http" |
 *   "upstream_error" | "timeout" | "network_error" | "invalid_stream" | "stream_limit" |
 *   "interrupted_stream" | "empty_output" | "truncated_output" | "unexpected_finish"} Outcome
 * @typedef {{
 *   statusCode: number | null,
 *   timeToFirstTokenMs: number | null,
 *   providerCompletionTokens: number | null,
 *   finishReason: string | null,
 * }} Measurement
 * @typedef {{
 *   error?: unknown,
 *   choices?: { delta?: { content?: unknown }, finish_reason?: unknown }[],
 *   usage?: { completion_tokens?: unknown },
 * }} ProviderEvent
 */

/** @param {unknown} body @param {number} status @param {Record<string, string>} extraHeaders */
function json(body, status = 200, extraHeaders = {}) {
  return Response.json(body, {
    status,
    headers: { "Cache-Control": "no-store", ...extraHeaders },
  });
}

/** @param {Request} request */
function placement(request) {
  const routed = /^(local|remote)-([A-Z]{3})$/.exec(request.headers.get("cf-placement") ?? "");
  const ingress = request.cf?.colo;
  return {
    executionColo: routed?.[2] ?? null,
    placementType: routed?.[1] ?? null,
    ingressColo: typeof ingress === "string" && /^[A-Z]{3}$/.test(ingress) ? ingress : null,
  };
}

/**
 * @param {ReadableStream<Uint8Array>} body
 * @param {Measurement} state
 * @param {() => number} now
 * @param {number} started
 * @returns {Promise<Outcome>}
 */
async function readCompletion(body, state, now, started) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let bytes = 0;
  let events = 0;
  let buffer = "";
  /** @type {string[]} */
  let data = [];
  let doneMarker = false;

  function readEvent() {
    if (++events > MAX_EVENT_COUNT) {
      return "stream_limit";
    }
    const payload = data.join("\n");
    data = [];
    if (payload === "[DONE]") {
      doneMarker = true;
      return null;
    }

    /** @type {ProviderEvent} */
    let event;
    try {
      event = JSON.parse(payload);
    } catch {
      return "invalid_stream";
    }
    if (!event || typeof event !== "object" || Array.isArray(event)) {
      return "invalid_stream";
    }
    if (event.error) {
      return "upstream_error";
    }

    const choice = Array.isArray(event.choices) ? event.choices[0] : undefined;
    const visibleText = choice?.delta?.content;
    if (state.timeToFirstTokenMs === null && typeof visibleText === "string" && visibleText.trim()) {
      state.timeToFirstTokenMs = Math.round(now() - started);
    }
    if (typeof choice?.finish_reason === "string") {
      state.finishReason = choice.finish_reason;
    }
    const completionTokens = event.usage?.completion_tokens;
    if (typeof completionTokens === "number" && Number.isSafeInteger(completionTokens) && completionTokens >= 0) {
      state.providerCompletionTokens = completionTokens;
    }
    return null;
  }

  try {
    while (!doneMarker) {
      const { value, done } = await reader.read();
      bytes += value?.byteLength ?? 0;
      if (bytes > MAX_STREAM_BYTES) {
        return "stream_limit";
      }
      buffer += decoder.decode(value, { stream: !done });
      if (done && (buffer || data.length)) {
        // Process a final data line if its blank separator was omitted at EOF.
        buffer += "\n\n";
      }
      let newline;
      while (!doneMarker && (newline = buffer.indexOf("\n")) !== -1) {
        const line = buffer.slice(0, newline).replace(/\r$/, "");
        buffer = buffer.slice(newline + 1);
        if (line.startsWith("data:")) {
          data.push(line.slice(5).replace(/^ /, ""));
        } else if (!line && data.length) {
          const outcome = readEvent();
          if (outcome) return outcome;
        }
      }
      if (done) break;
    }
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }

  if (!doneMarker && !state.finishReason) return "interrupted_stream";
  if (state.timeToFirstTokenMs === null) return "empty_output";
  if (state.finishReason === "length") return "truncated_output";
  if (state.finishReason && state.finishReason !== "stop") return "unexpected_finish";
  return "ok";
}

/**
 * @param {string} model
 * @param {string} apiKey
 * @param {AbortSignal} abortSignal
 * @param {typeof fetch} upstream
 * @param {() => number} now
 */
async function measure(model, apiKey, abortSignal, upstream, now) {
  const started = now();
  /** @type {Measurement} */
  const state = { statusCode: null, timeToFirstTokenMs: null, providerCompletionTokens: null, finishReason: null };
  const timeout = AbortSignal.timeout(PROBE_TIMEOUT_MS);
  const signal = AbortSignal.any([abortSignal, timeout]);
  /** @type {Outcome} */
  let outcome;

  try {
    const response = await upstream(NIM_URL, {
      method: "POST",
      redirect: "manual",
      signal,
      headers: {
        "Authorization": `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
      },
      body: JSON.stringify({
        model,
        messages: [{ role: "user", content: PROMPT }],
        temperature: 0.2,
        max_tokens: MAX_TOKENS,
        stream: true,
        stream_options: { include_usage: true },
      }),
    });
    state.statusCode = response.status;
    if (!response.ok) {
      outcome = response.status === 429 ? "rate_limited" : "upstream_http";
      if ([401, 403].includes(response.status)) outcome = "upstream_auth";
      if (response.body) await response.body.cancel().catch(() => {});
    } else if (!response.body || !/^text\/event-stream(?:\s*;|$)/i.test(response.headers.get("Content-Type") ?? "")) {
      outcome = "invalid_stream";
      if (response.body) await response.body.cancel().catch(() => {});
    } else {
      outcome = await readCompletion(response.body, state, now, started);
    }
  } catch {
    outcome = timeout.aborted ? "timeout" : "network_error";
  }

  return {
    outcome,
    statusCode: state.statusCode,
    timeToFirstTokenMs: state.timeToFirstTokenMs,
    durationMs: Math.round(now() - started),
    providerCompletionTokens: state.providerCompletionTokens,
  };
}

/**
 * @param {Request} request
 * @param {Env} env
 * @param {{ upstream?: typeof fetch, now?: () => number, clock?: () => number }} options
 */
export async function handleProbe(request, env, {
  upstream = fetch, now = () => performance.now(), clock = Date.now,
} = {}) {
  const region = env.PROBE_REGION;
  if (env.PROBE_ENABLED !== "true" || !region || !REGIONS.includes(region)) {
    return json({ error: "probe_disabled" }, 404);
  }

  const url = new URL(request.url);
  const route = /^\/probe\/(\d{1,10})\/([a-z]+)$/.exec(url.pathname);
  if (!route || url.search || !Object.hasOwn(MODELS, route[2])) {
    return json({ error: "unknown_probe" }, 404);
  }
  if (request.method !== "POST") {
    return json({ error: "method_not_allowed" }, 405, { Allow: "POST" });
  }
  // Workerd can represent an HTTP POST with Content-Length: 0 as an empty stream.
  if (request.body !== null && request.headers.get("Content-Length") !== "0") {
    return json({ error: "unexpected_request_body" }, 400);
  }
  if (!validSigningKey(env.PROBE_SIGNING_KEY)) {
    return json({ error: "probe_unconfigured" }, 503);
  }

  const slot = currentSlot(clock());
  const signature = request.headers.get("X-Nimstats-Probe-Signature");
  if (route[1] !== String(slot) || !await verifyProbe(env.PROBE_SIGNING_KEY, region, url.pathname, signature)) {
    return json({ error: "invalid_signature_or_slot" }, 403);
  }
  if (!env.NIM_API_KEY) {
    return json({ error: "probe_unconfigured" }, 503);
  }

  const model = MODELS[/** @type {keyof typeof MODELS} */ (route[2])];
  const sampledAt = new Date(clock()).toISOString();
  const sample = await measure(model, env.NIM_API_KEY, request.signal, upstream, now);
  return json({
    schemaVersion: 1,
    profile: PROFILE,
    region,
    slotStartedAt: new Date(slot * SLOT_MS).toISOString(),
    sampledAt,
    model,
    placement: placement(request),
    ...sample,
  });
}

/** @type {ExportedHandler<Env>} */
const worker = {
  fetch(request, env) {
    return handleProbe(request, env);
  },
};

export default worker;
