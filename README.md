<div align="center">

[![NIMStats Banner](https://capsule-render.vercel.app/api?type=waving&color=76b900&height=220&section=header&text=NIMStats&fontSize=90&fontColor=ffffff&animation=fadeIn&fontAlignY=38&desc=Real-Time%20NVIDIA%20NIM%20Benchmark%20Dashboard&descSize=22&descAlignY=60&descAlign=50)](https://nimstats.maurodruwel.be/)

[![CI](https://github.com/MauroDruwel/NIMStats/actions/workflows/benchmark.yml/badge.svg)](https://github.com/MauroDruwel/NIMStats/actions)
[![Live Dashboard](https://img.shields.io/badge/🌐%20live-nimstats.maurodruwel.be-76b900?style=flat-square)](https://nimstats.maurodruwel.be/)
[![NVIDIA Model Catalog](https://img.shields.io/badge/NVIDIA-model_catalog-blue?style=flat-square)](https://build.nvidia.com/models)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow?style=flat-square)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square)](https://github.com/MauroDruwel/NIMStats/pulls)
[![Stars](https://img.shields.io/github/stars/MauroDruwel/NIMStats?style=flat-square&color=gold)](https://github.com/MauroDruwel/NIMStats/stargazers)

<br/>

> **Community-driven benchmarks for NVIDIA NIM models, with public reliability, latency, and throughput data.**

<br/>

**[🚀 View Live Dashboard](https://nimstats.maurodruwel.be/) · [📖 Docs](#-quick-start) · [🤝 Contribute](#-contributing) · [💬 Discussions](https://github.com/MauroDruwel/NIMStats/discussions)**

</div>

---

## ✨ What is NIMStats?

NIMStats runs hourly NVIDIA NIM benchmarks through GitHub Actions and stores the results in Cloudflare D1. The dashboard uses Cloudflare Pages Functions to read this shared history.

<div align="center">

| 🏎️ Hourly Benchmarks | 📊 Interactive Charts | 🔁 Cloudflare D1 | 🌍 Fully Open-Source |
|:---:|:---:|:---:|:---:|
| GitHub Actions | Response time, throughput & trends | Shared benchmark history | Fork and run your own probes |

</div>

---

## ⚡ Quick Start

### 1. Fork and clone

```bash
git clone https://github.com/YOUR_ACCOUNT/NIMStats.git
cd NIMStats
```

Get an NVIDIA NIM API key for the benchmark runner. [NVIDIA Build](https://build.nvidia.com)

### 2. Set up Cloudflare Pages and D1

Create a D1 database named `nimstats-db` in your account and update the project name and database ID in [`wrangler.jsonc`](wrangler.jsonc). Connect the repository to a Cloudflare Pages project. Use the repository's default branch for production and bind the same D1 database as `DB` for production and branch previews. Both dashboards read the same results through their Pages Functions. [Cloudflare Pages bindings](https://developers.cloudflare.com/pages/functions/bindings/#d1-databases)

For a new database, apply the base schema and then the benchmark ingestion migration. For an existing NIMStats D1 database, apply only the additive migration. It leaves existing measurements in place. [Wrangler D1 commands](https://developers.cloudflare.com/d1/wrangler-commands/)

```bash
# New databases only
npx wrangler d1 execute nimstats-db --remote --file=scripts/d1_schema.sql

# New and existing databases
npx wrangler d1 execute nimstats-db --remote --file=scripts/d1_benchmark_ingestion.sql
```

### 3. Configure GitHub Actions

- Add `NIM_API_KEY` as a repository Actions secret. `ARTIFICIAL_ANALYSIS_API_KEY` is optional and enables intelligence score updates.
- Set `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_D1_DATABASE_ID` as repository Actions variables for your account and database.
- Create the GitHub environment `nimstats-production` and restrict deployment branches to your repository's default branch. Add `CLOUDFLARE_API_TOKEN` **as an environment secret**, using the **D1 Edit** permission for the account hosting the database. [GitHub environment settings](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments) · [Create a D1 API token](https://developers.cloudflare.com/d1/tutorials/import-to-d1-with-rest-api/#1-create-a-d1-api-token)

### 4. Run the benchmark

Select the default branch in **Actions → Benchmark NVIDIA NIM Models → Run workflow**. The preflight job checks the secrets and ingestion migration before the benchmark jobs run. Both preflight and D1 ingestion are gated to the default branch. The production write token is available to the protected environment jobs, and all Pages dashboard endpoints are read-only.

The workflow uses `workflow_dispatch`. To reproduce the hosted hourly cadence, configure a scheduler to dispatch it on the default branch. After the first completed run, check `/api/health` on the public dashboard for the latest benchmark timestamp.

---

## 📊 Dashboard Features

<div align="center">

| Tab | What you get |
|-----|-------------|
| **📊 Overview** | 5 animated KPI cards · success trend charts · top-10 speed & throughput bars · model reliability pills |
| **🏆 Leaderboard** | Composite score rankings · sortable columns · SVG sparklines · trend indicators (↑↓→) · provider chips |
| **🔬 Explorer** | Per-model deep dive · response time history chart · error breakdown donut · availability heatmap |
| **⏱ Timeline** | Filterable run history (All / 24h / 48h / 7d) · expandable run cards with full per-model detail |
| **⚔️ Compare** | Head-to-head overlay chart · win-rate stats · side-by-side metric comparison · copyable backup suggestion based on matched runs |
| **🔗 Public APIs** | D1-backed history and rankings, plus compatibility ranking endpoints in JSON and plain text |

</div>

Every tab shows the latest benchmark timestamp and whether the data is current, stale, unavailable, or of unknown freshness. Data is marked stale after two hours. The dashboard requests up to 168 recent runs for its seven-day Timeline view.

The Compare tab suggests a backup for model A from models tested in the latest run. It uses the selected run window and counts only runs where model A failed and both models were tested. A suggestion requires at least five such matches and one observed backup success. The copy button exports the full model IDs as a JSON pair.

---

## 🔌 Developer APIs

The D1-backed endpoints include `/api/health`, `/api/history`, `/api/models`, `/api/top`, and `/api/reliable`. The OpenAPI documents describe request options and response fields. [OpenAPI YAML](openapi.yaml) · [OpenAPI JSON](openapi.json)

### Compatibility ranking endpoints

The workflow generates lightweight snapshots of the best models by category after each published run.

| Category | Endpoint (JSON) | Endpoint (Plain Text) | Scoring Balance |
| :--- | :--- | :--- | :--- |
| **⚖️ Balanced (Overall)** | [`/top`](https://nimstats.maurodruwel.be/top) | [`/top/model`](https://nimstats.maurodruwel.be/top/model) | **30%** Uptime + **30%** Intelligence + **20%** Avg Time + **20%** Throughput |
| **🏎️ Speed & Throughput** | [`/top/speed`](https://nimstats.maurodruwel.be/top/speed) | [`/top/speed/model`](https://nimstats.maurodruwel.be/top/speed/model) | **50%** Avg Response Time + **50%** Throughput (TPS) |
| **🧠 Model Intelligence** | [`/top/intelligence`](https://nimstats.maurodruwel.be/top/intelligence) | [`/top/intelligence/model`](https://nimstats.maurodruwel.be/top/intelligence/model) | **70%** Artificial Analysis Score + **30%** Uptime |

### JSON Response Schema

```json
{
  "best_model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
  "provider": "nvidia",
  "score": 71,
  "intelligence": 14.9,
  "uptime": 90.6,
  "avg_response_time_ms": 4736.7,
  "best_response_time_ms": 432.0,
  "avg_time_to_first_token_ms": 312.5,
  "avg_throughput_tps": 163.3,
  "total_runs": 720,
  "success_count": 652,
  "wins": 364,
  "last_seen": "2026-07-07T10:00:08Z",
  "generated_at": "2026-07-07T10:08:49Z"
}
```

---

## 🤖 Benchmarked Models

The active roster is `ALL_MODELS` in [`scripts/test_models.py`](scripts/test_models.py). The daily model sync proposes roster changes as GitHub pull requests. When a model leaves the roster, its earlier results stay in D1 until the regular retention window expires.

---

## 🏗️ How It Works

Two parallel GitHub Actions jobs collect measurements for different halves of the model roster. The protected default-branch job combines both artifacts and publishes the complete run to D1. Cloudflare Pages Functions serve the same history to production and preview deployments.

The regional pilot supports local mock runs and an opt-in manual deployment. It produces independent observations for offline comparison. [Regional probe pilot](probes/README.md)

---

## 🛠️ Customization

<details>
<summary><b>Change a benchmark prompt</b></summary>

Edit the corresponding profile in `PROFILE_PROMPTS` in `scripts/test_models.py`. The hourly workflow uses the default `code` profile.

</details>

<details>
<summary><b>Add or remove models</b></summary>

Use the model management script.

```bash
# List the configured roster and any retired models with history in D1
python scripts/manage_models.py list

# Add a new model to ALL_MODELS
python scripts/manage_models.py add your/custom-model

# Retire a model from future runs and keep its D1 history
python scripts/manage_models.py remove your/custom-model
```

The explicit maintenance command `python scripts/manage_models.py purge` deletes history for every model outside the roster in the targeted D1 database. Normal roster updates use `remove`.

You can also manually edit `ALL_MODELS` in `scripts/test_models.py`.
```python
ALL_MODELS = [
    "your/custom-model",
    # ...
]
```
</details>

<details>
<summary><b>Run benchmark profiles locally</b></summary>

With `NIM_API_KEY` set in your shell, select a workload profile. These commands collect results into JSON files under `scripts/` and leave the shared D1 database untouched.

```bash
python3 scripts/test_models.py --profile code
python3 scripts/test_models.py --profile json
python3 scripts/test_models.py --profile tool
```

`code` uses the standard coding prompt. `json` checks a structured answer, and `tool` checks the expected tool call and arguments. The profile reports are independent workloads.

</details>

<details>
<summary><b>Run the dashboard locally</b></summary>

Start Pages Functions with Wrangler and use a local D1 database. The dashboard displays an unavailable state until the local database contains data.

```bash
npx wrangler d1 execute nimstats-db --local --file=scripts/d1_schema.sql
npx wrangler d1 execute nimstats-db --local --file=scripts/d1_benchmark_ingestion.sql
npx wrangler pages dev .
```

</details>

---

## 📦 Data Storage

Cloudflare D1 stores benchmark runs and per-model results. The base schema defines the tables. The additive ingestion migration publishes each complete run in one statement and retains the latest 720 runs. Per-job benchmark JSON files are temporary artifacts. [Base schema](scripts/d1_schema.sql) · [Ingestion migration](scripts/d1_benchmark_ingestion.sql)

The scheduled freshness check fails when the production API reports stale or unavailable benchmark data. The health response includes the latest run timestamp and its age.

To recover results from a legacy snapshot, read the latest D1 timestamp from `/api/health` and pass it as `--after`. The export only creates a SQL file. It uses timestamps and model names so repeated imports preserve existing measurements.

```bash
python3 scripts/export_history_to_d1.py --input history.db --after "$LATEST_D1_TIMESTAMP"
```

**Default code profile parameters** · `temperature: 0.7` · `top_p: 0.9` · `max_tokens: 500` · OpenAI-compatible API. GLM-5.3 variants use `reasoning_effort: low` and `max_tokens: 2048` because thinking is always enabled.

---

## 🤝 Contributing

Contributions are what make the open-source community amazing. Any contribution you make is **greatly appreciated**!

1. **Fork** the repository
2. Create your feature branch: `git checkout -b feat/amazing-feature`
3. Commit your changes: `git commit -m 'feat: add amazing feature'`
4. Push to the branch: `git push origin feat/amazing-feature`
5. Open a **Pull Request**

**Ideas for contributions:**
- 🆕 Add new NIM models to the benchmark list
- 📊 New chart types or dashboard widgets
- 🌐 Internationalization / translations
- 🐛 Bug fixes and performance improvements
- 📖 Improve documentation

Please read through open [Issues](https://github.com/MauroDruwel/NIMStats/issues) before starting — someone might already be working on it!

---

## 🔗 Resources

- [NVIDIA NIM API Documentation](https://docs.api.nvidia.com/nim/)
- [NVIDIA Model Catalog](https://build.nvidia.com/models)
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Cloudflare D1 Documentation](https://developers.cloudflare.com/d1/)

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.

---

<div align="center">

Made with ❤️ for the ML community · [⭐ Star this repo](https://github.com/MauroDruwel/NIMStats) if you find it useful!

[![footer](https://capsule-render.vercel.app/api?type=waving&color=76b900&height=100&section=footer)](https://nimstats.maurodruwel.be/)

</div>
