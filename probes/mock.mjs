import { handleProbe } from "./worker.mjs";

export const MOCK_SIGNING_KEY = "0".repeat(64);

const encoder = new TextEncoder();

export function eventStream(...chunks) {
  const body = new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
  return new Response(body, { headers: { "Content-Type": "text/event-stream" } });
}

export function createMockFetcher(region) {
  return (url, init) => {
    const request = new Request(url, init);
    let time = 0;
    return handleProbe(
      request,
      { PROBE_REGION: region, PROBE_ENABLED: "true", PROBE_SIGNING_KEY: MOCK_SIGNING_KEY, NIM_API_KEY: "mock" },
      {
        now: () => (time += 25),
        upstream: async () => eventStream(
          'data: {"choices":[{"delta":{"reasoning_content":"thinking"}}]}\n\n',
          'data: {"choices":[{"delta":{"content":"Earth is tilted."},"finish_reason":"stop"}]}\n\n',
          'data: {"usage":{"completion_tokens":5}}\n\ndata: [DONE]\n\n',
        ),
      },
    );
  };
}
