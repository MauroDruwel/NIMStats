export const REGIONS = Object.freeze(["na", "eu", "apac"]);
export const MODELS = Object.freeze({
  gemma: "google/gemma-4-31b-it",
  lightning: "nvidia/nemotron-3.5-lightning-30b-a3b",
  mistral: "mistralai/mistral-large-4-1t-a52b",
});

export const SLOT_MS = 2 * 60 * 60 * 1000;
export const MAX_TOKENS = 128;
export const PROBE_TIMEOUT_MS = 25_000;
export const PROFILE = "seasons-short-v1";

const encoder = new TextEncoder();
const hmac = { name: "HMAC", hash: "SHA-256" };

export function currentSlot(now = Date.now()) {
  return Math.floor(now / SLOT_MS);
}

/** @param {number} slot @param {string} model */
export function probePath(slot, model) {
  return `/probe/${slot}/${model}`;
}

/** @param {unknown} secret @returns {secret is string} */
export function validSigningKey(secret) {
  return typeof secret === "string" && /^[a-f0-9]{64}$/.test(secret);
}

/** @param {string} region @param {string} path */
function signingMessage(region, path) {
  return encoder.encode(`nimstats-regional-v1\n${region}\nPOST\n${path}`);
}

/** @param {string} secret @param {string} region @param {string} path */
export async function signProbe(secret, region, path) {
  const key = await crypto.subtle.importKey("raw", encoder.encode(secret), hmac, false, ["sign"]);
  const digest = await crypto.subtle.sign("HMAC", key, signingMessage(region, path));
  return btoa(String.fromCharCode(...new Uint8Array(digest)));
}

/** @param {string} secret @param {string} region @param {string} path @param {string | null} signature */
export async function verifyProbe(secret, region, path, signature) {
  if (!signature || !/^[A-Za-z0-9+/]{43}=$/.test(signature)) {
    return false;
  }

  const key = await crypto.subtle.importKey("raw", encoder.encode(secret), hmac, false, ["verify"]);
  const bytes = Uint8Array.from(atob(signature), (character) => character.charCodeAt(0));
  return crypto.subtle.verify("HMAC", key, bytes, signingMessage(region, path));
}
