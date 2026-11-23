// Cloudflare Pages Function: /api/reliable
// Returns top reliable models (lowest error rate / highest uptime) from Cloudflare D1.
// Edge-cached globally on Cloudflare CDN to ensure 100% free-tier usage.
//
// Query parameters:
//   limit: integer (default: 5, max: 50)
//   window: integer (default: 100, max: 500)

import { onRequestGet as handleTopGet } from "./top.js";

export async function onRequestGet(context) {
  const url = new URL(context.request.url);
  if (!url.searchParams.has("sort")) {
    url.searchParams.set("sort", "reliability");
  }
  const modifiedRequest = new Request(url.toString(), context.request);
  return handleTopGet({ ...context, request: modifiedRequest });
}
