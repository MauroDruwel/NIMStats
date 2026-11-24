import assert from "node:assert/strict";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";

import { reserveSlot } from "./dispatch.mjs";
import { eventStream, MOCK_SIGNING_KEY } from "./mock.mjs";
import { MAX_TOKENS, MODELS, SLOT_MS, currentSlot, probePath, signProbe } from "./protocol.mjs";
import { handleProbe } from "./worker.mjs";

const clock = () => Date.parse("2026-11-23T13:00:00Z");
const slot = currentSlot(clock());
const path = probePath(slot, "gemma");
const env = {
  PROBE_REGION: "eu",
  PROBE_ENABLED: "true",
  PROBE_SIGNING_KEY: MOCK_SIGNING_KEY,
  NIM_API_KEY: "mock",
};

async function signed(pathname = path, region = "eu", init = {}) {
  const signature = await signProbe(MOCK_SIGNING_KEY, region, pathname);
  const request = new Request(`https://probe.invalid${pathname}`, {
    method: "POST",
    headers: { "X-Nimstats-Probe-Signature": signature, "Cf-Placement": "remote-AMS" },
    ...init,
  });
  Object.defineProperty(request, "cf", { value: { colo: "IAD" } });
  return request;
}

test("samples visible text after reasoning and records Cloudflare execution versus ingress", async () => {
  let requests = 0;
  let time = 100;
  let firstTokenTime = 0;
  const upstream = async (url, init) => {
    requests += 1;
    assert.equal(url, "https://integrate.api.nvidia.com/v1/chat/completions");
    assert.equal(init.headers.Authorization, "Bearer mock");
    assert.equal(init.redirect, "manual");
    const parameters = JSON.parse(init.body);
    assert.equal(parameters.model, MODELS.gemma);
    assert.equal(parameters.max_tokens, MAX_TOKENS);
    assert.equal(parameters.stream, true);
    const encoder = new TextEncoder();
    const chunks = [
      'data: {"choices":[{"delta":{"reasoning_content":"thinking"}}]}\r\n\r\n',
      'data: {"choices":[{"delta":{"content":"   "}}]}\n\n',
      'data: {"choices":[{"delta":{"content":"Earth',
      ' is tilted"},"finish_reason":"stop"}]}\n\n',
      'data: {"usage":{"completion_tokens":8}}\ndata: \n\n',
      'data: [DONE]\n',
    ];
    let index = 0;
    return new Response(new ReadableStream({
      pull(controller) {
        if (index === chunks.length) {
          controller.close();
          return;
        }
        time += 50;
        if (index === 3) firstTokenTime = time;
        controller.enqueue(encoder.encode(chunks[index++]));
      },
    }, { highWaterMark: 0 }), { headers: { "Content-Type": "text/event-stream; charset=utf-8" } });
  };
  const response = await handleProbe(await signed(), env, { upstream, clock, now: () => time });
  const result = await response.json();
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.equal(requests, 1);
  assert.deepEqual(result.placement, { executionColo: "AMS", placementType: "remote", ingressColo: "IAD" });
  assert.equal(result.outcome, "ok");
  assert.equal(result.timeToFirstTokenMs, firstTokenTime - 100);
  assert.equal(result.timeToFirstTokenMs, 200);
  assert.equal(result.durationMs, 300);
  assert.equal(result.providerCompletionTokens, 8);
  assert.equal(result.slotStartedAt, new Date(slot * SLOT_MS).toISOString());
  assert.doesNotMatch(JSON.stringify(result), /thinking|Earth is tilted|Bearer mock/);
});

test("rejects disabled, unsigned, wrong-region, stale, unknown-model and parameterized requests", async () => {
  const requests = [
    [await signed(), { ...env, PROBE_ENABLED: "false" }, 404],
    [new Request(`https://probe.invalid${path}`, { method: "POST" }), env, 403],
    [await signed(path, "na"), env, 403],
    [await signed(probePath(slot - 1, "gemma")), env, 403],
    [await signed(probePath(slot, "custom")), env, 404],
    [await signed(`${path}?max_tokens=999`), env, 404],
    [await signed(path, "eu", { body: "{}" }), env, 400],
    [await signed(path, "eu", { method: "GET" }), env, 405],
    [await signed(), { ...env, NIM_API_KEY: "" }, 503],
  ];
  for (const [request, bindings, status] of requests) {
    let calls = 0;
    const response = await handleProbe(request, bindings, { clock, upstream: async () => { calls += 1; } });
    assert.equal(response.status, status);
    assert.equal(calls, 0);
  }
});

test("classifies HTTP failures, unreadable and partial streams, empty output, and length limits", async (t) => {
  const cases = [
    ["rate_limited", () => new Response("internal details", { status: 429 })],
    ["upstream_auth", () => new Response(null, { status: 403 })],
    ["upstream_http", () => new Response(null, { status: 302, headers: { Location: "https://redirect.invalid/" } })],
    ["upstream_http", () => new Response(null, { status: 500 })],
    ["network_error", () => { throw new TypeError("connection refused"); }],
    ["invalid_stream", () => new Response("not an SSE response")],
    ["invalid_stream", () => eventStream("data: {invalid}\n\n")],
    ["upstream_error", () => eventStream('data: {"error":{"message":"internal details"}}\n\n')],
    ["interrupted_stream", () => eventStream('data: {"choices":[{"delta":{"content":"Partial"}}]}\n\n')],
    ["empty_output", () => eventStream('data: {"choices":[{"delta":{"reasoning_content":"hidden"}}]}\n\ndata: [DONE]\n\n')],
    ["truncated_output", () => eventStream('data: {"choices":[{"delta":{"content":"Partial"},"finish_reason":"length"}]}\n\n')],
    ["unexpected_finish", () => eventStream('data: {"choices":[{"delta":{"content":"Partial"},"finish_reason":"content_filter"}]}\n\n')],
    ["stream_limit", () => eventStream("x".repeat(50 * 1024))],
    ["stream_limit", () => eventStream("data: {}\n\n".repeat(257))],
  ];
  for (const [outcome, upstream] of cases) {
    await t.test(outcome, async () => {
      const result = await handleProbe(await signed(), env, { upstream, clock });
      const sample = await result.json();
      assert.equal(sample.outcome, outcome);
      assert.doesNotMatch(JSON.stringify(sample), /internal details|Partial|connection refused/);
    });
  }
});

test("only one controller can reserve a slot in the same directory", async () => {
  const directory = await mkdtemp(join(tmpdir(), "nimstats-probe-test-"));
  try {
    const attempts = await Promise.allSettled([reserveSlot(directory, slot), reserveSlot(directory, slot)]);
    const acquired = attempts.find(({ status }) => status === "fulfilled").value;
    try {
      assert.equal(attempts.filter(({ status }) => status === "fulfilled").length, 1);
      assert.match(attempts.find(({ status }) => status === "rejected").reason.message, /already reserved/);
      await acquired.writeFile("first\n");
      await acquired.writeFile("second\n");
    } finally {
      await acquired.close();
    }
    assert.equal(await readFile(join(directory, `slot-${slot}.ndjson`), "utf8"), "first\nsecond\n");
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test("marks an expired upstream deadline as a timeout", async (t) => {
  t.mock.method(AbortSignal, "timeout", () => AbortSignal.abort(new DOMException("expired", "TimeoutError")));
  const response = await handleProbe(await signed(), env, {
    clock,
    upstream: async (_url, { signal }) => { signal.throwIfAborted(); },
  });
  assert.equal((await response.json()).outcome, "timeout");
});

test("accepts the empty stream representation of Content-Length zero", async () => {
  const request = await signed(path, "eu", {
    body: "",
    headers: {
      "Content-Length": "0",
      "X-Nimstats-Probe-Signature": await signProbe(MOCK_SIGNING_KEY, "eu", path),
    },
  });
  assert.notEqual(request.body, null);
  const response = await handleProbe(request, env, {
    clock,
    upstream: async () => eventStream('data: {"choices":[{"delta":{"content":"OK"},"finish_reason":"stop"}]}\n\n'),
  });
  assert.equal((await response.json()).outcome, "ok");
});
