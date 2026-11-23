# Regional NIM pilot

The pilot measures requests to the NVIDIA API Catalog from Cloudflare Workers placed near three regions. The reference points are Northern Virginia (`na`), Belgium (`eu`), and Singapore (`apac`). Each result records the `cf-placement` processing location when Cloudflare supplies it, and records ingress separately. Treat placement as an observed Cloudflare execution location. NVIDIA's inference location is unknown.

## Local demo

Run from the repository root with Node.js 22 or newer. The demo uses in-process stream fixtures and prints nine NDJSON records with simulated timings.

```sh
node --test probes/worker.test.mjs
node probes/dispatch.mjs --mock
```

Wrangler can bundle each environment locally. This command uses the version verified with the pilot.

```sh
for region in na eu apac; do
  npx wrangler@4.166.0 deploy --config probes/wrangler.jsonc --env "$region" --dry-run
done
```

## Commissioning

The checked-in config disables execution and public routes across all three environments. The pilot has no scheduler and no database binding. Keep it separate from the hourly benchmark and the D1 database shared by the Pages preview and production.

1. When ready for a live trial, confirm the selected models and catalog limits in your NVIDIA account. The [API Catalog FAQ](https://forums.developer.nvidia.com/t/nvidia-nim-faq/300317) describes model-specific trial limits.
2. Configure separate Worker secrets named `PROBE_SIGNING_KEY` and `NIM_API_KEY` in each regional environment. Give each region a distinct 32-byte random signing key encoded as 64 lowercase hex characters. Keep the NVIDIA key in Worker secrets. On the controller, use only the regional signing keys.
3. Commission explicitly by setting `workers_dev` and each environment's `PROBE_ENABLED` to true (`"true"` for the variable) in the probe config and deploying the three named environments. The dispatcher accepts their default `nimstats-regional-probe-<region>.<account>.workers.dev` hostnames.
4. Set `PROBE_URL_NA`, `PROBE_URL_EU`, and `PROBE_URL_APAC` to those HTTPS origins. Supply `PROBE_SIGNING_KEY_NA`, `PROBE_SIGNING_KEY_EU`, and `PROBE_SIGNING_KEY_APAC` from the controller's secret manager. Set `PROBE_RESULTS_DIRECTORY` to a persistent, private directory outside the repository.
5. Run `node probes/dispatch.mjs --run` on one controller. Confirm three distinct, geographically plausible execution locations and inspect Cloudflare CPU time before deciding whether to schedule it.

The controller reserves each two-hour UTC slot in its local result directory before sending requests. One run compares each model across all three regions, with one model in flight per region. It makes at most nine inference calls per slot, without retries, with a 25-second deadline and a 128-token output cap per call. A full 12-slot day uses up to 108 inference calls. These limits assume a single controller and persistent directory. The HMAC authorizes a specific region, model, and current slot. The Workers are stateless, so use one dispatcher and keep the signing keys private. Persistent deduplication across controllers would be needed before scheduling from distributed runners.

## Results

Successful Worker replies include the schema and test profile, model, probe region, UTC sample and slot timestamps, placement metadata, upstream status, time to first visible content, total duration, and reported completion tokens when available. A failed inference produces a sample with an outcome such as `rate_limited`, `timeout`, `truncated_output`, or `empty_output`. Dispatcher and Worker failures are recorded separately as `probe_*`. The probe discards model responses and upstream error bodies.

Inspect the Cloudflare CPU measurements against the [Workers Free limits](https://developers.cloudflare.com/workers/platform/limits/). Track the pilot as a separate series because its fixed prompt and token budget differ from the hourly benchmark. Review per-region coverage, failure categories, and latency percentiles together. The controller exits with an error when a live response has unknown placement or a dispatch error. Results already written still describe what the run observed.
