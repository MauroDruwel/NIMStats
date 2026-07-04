<div align="center">

[![NIMStats Banner](https://capsule-render.vercel.app/api?type=waving&color=76b900&height=220&section=header&text=NIMStats&fontSize=90&fontColor=ffffff&animation=fadeIn&fontAlignY=38&desc=Real-Time%20NVIDIA%20NIM%20Benchmark%20Dashboard&descSize=22&descAlignY=60&descAlign=50)](https://nimstats.maurodruwel.be/)

[![CI](https://github.com/MauroDruwel/NIMStats/actions/workflows/benchmark.yml/badge.svg)](https://github.com/MauroDruwel/NIMStats/actions)
[![Live Dashboard](https://img.shields.io/badge/🌐%20live-nimstats.maurodruwel.be-76b900?style=flat-square)](https://nimstats.maurodruwel.be/)
[![Models](https://img.shields.io/badge/models-22-blue?style=flat-square)](https://build.nvidia.com/models)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow?style=flat-square)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square)](https://github.com/MauroDruwel/NIMStats/pulls)
[![Stars](https://img.shields.io/github/stars/MauroDruwel/NIMStats?style=flat-square&color=gold)](https://github.com/MauroDruwel/NIMStats/stargazers)

<br/>

> **Community-driven benchmarking of 22 NVIDIA NIM models — fully automated, zero infra cost, self-hostable in minutes.**

<br/>

**[🚀 View Live Dashboard](https://nimstats.maurodruwel.be/) · [📖 Docs](#-quick-start) · [🤝 Contribute](#-contributing) · [💬 Discussions](https://github.com/MauroDruwel/NIMStats/discussions)**

</div>

---

## ✨ What is NIMStats?

NIMStats automatically benchmarks **22 NVIDIA NIM models** every hour using GitHub Actions and publishes the results to a beautiful, interactive dashboard. No servers, no subscriptions — just fork, add your API key, and go.

<div align="center">

| 🏎️ Hourly Benchmarks | 📊 Interactive Charts | 🔁 Zero Infrastructure | 🌍 Fully Open-Source |
|:---:|:---:|:---:|:---:|
| Automatic via GitHub Actions | Response time, throughput & trends | Static site + free CI/CD | Fork and self-host in minutes |

</div>

---

## ⚡ Quick Start

> Get your own benchmarking dashboard running in under 5 minutes.

### 1. Fork & Clone

```bash
git clone https://github.com/MauroDruwel/NIMStats.git
cd NIMStats
```

### 2. Get a Free API Key

Visit **[build.nvidia.com](https://build.nvidia.com)** → Create a free account → Copy your API key.

### 3. Add the Secret

In your forked repo: **Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|------|-------|
| `NIM_API_KEY` | Your NVIDIA NIM API key |

### 4. Deploy the Dashboard

| Platform | Steps |
|----------|-------|
| **Cloudflare Pages** | Connect repo → auto-deploys on every push to `main` |
| **GitHub Pages** | Settings → Pages → Deploy from `main` |
| **Netlify / Vercel** | Connect repo for instant auto-deploy |

### 5. Run Your First Benchmark

**Actions → Benchmark NVIDIA NIM Models → Run workflow**

That's it — your dashboard auto-refreshes every hour. ✨

---

## 📊 Dashboard Features

<div align="center">

| Tab | What you get |
|-----|-------------|
| **📊 Overview** | 5 animated KPI cards · success trend charts · top-10 speed & throughput bars · model reliability pills |
| **🏆 Leaderboard** | Composite score rankings · sortable columns · SVG sparklines · trend indicators (↑↓→) · provider chips |
| **🔬 Explorer** | Per-model deep dive · response time history chart · error breakdown donut · availability heatmap |
| **⏱ Timeline** | Filterable run history (All / 24h / 48h / 7d) · expandable run cards with full per-model detail |
| **⚔️ Compare** | Head-to-head overlay chart · win-rate stats · side-by-side metric comparison |

</div>

---

## 🤖 Benchmarked Models

<details>
<summary><b>22 models across 11 providers — click to expand</b></summary>

<br/>

| Provider | Model | Highlight |
|----------|-------|-----------|
| **DeepSeek** | `deepseek-ai/deepseek-v4-flash` | Fast MoE, optimized for speed |
| **DeepSeek** | `deepseek-ai/deepseek-v4-pro` | Professional-grade reasoning |
| **Z-AI** | `z-ai/glm-5.2` | Superior code understanding |
| **MiniMax** | `minimaxai/minimax-m2.7` | Efficient inference model |
| **MiniMax** | `minimaxai/minimax-m3` | Latest MiniMax generation |
| **NVIDIA** | `nvidia/nemotron-3-super-120b-a12b` | NVIDIA's 120B flagship |
| **NVIDIA** | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | Compact omni reasoning model |
| **NVIDIA** | `nvidia/llama-3.3-nemotron-super-49b-v1.5` | Nemotron Super 49B v1.5 |
| **Moonshot** | `moonshotai/kimi-k2.6` | Context-optimized model |
| **OpenAI** | `openai/gpt-oss-120b` | Open-source 120B |
| **Google** | `google/gemma-4-31b-it` | Lightweight edge inference |
| **Qwen** | `qwen/qwen3.5-397b-a17b` | Flagship Qwen (397B) |
| **Qwen** | `qwen/qwen3.5-122b-a10b` | Mid-range Qwen 3.5 MoE |
| **Qwen** | `qwen/qwen3-next-80b-a3b-instruct` | Next-gen Qwen (80B MoE) |
| **Mistral** | `mistralai/mistral-large-3-675b-instruct-2512` | Largest Mistral (675B) |
| **Mistral** | `mistralai/mistral-medium-3.5-128b` | Efficient medium-scale Mistral |
| **Mistral** | `mistralai/mistral-small-4-119b-2603` | Mistral Small 4 (119B) |
| **Meta** | `meta/llama-3.3-70b-instruct` | Llama 3.3 70B |
| **Meta** | `meta/llama-4-maverick-17b-128e-instruct` | Llama 4 Maverick (128 experts) |
| **Meta** | `meta/llama-3.2-90b-vision-instruct` | Multimodal 90B vision model |
| **StepFun** | `stepfun-ai/step-3.5-flash` | Ultra-fast flash model |
| **StepFun** | `stepfun-ai/step-3.7-flash` | Latest high-performance flash |

</details>

---

## 🏗️ How It Works

````
┌──────────────────── GitHub Actions (every hour) ────────────────────┐
│                                                                       │
│   ┌─────────────────────┐        ┌─────────────────────┐              │
│   │  Job 1 — Group A    │        │  Job 2 — Group B    │ (parallel)  │
│   │  N/2 NIM models     │        │  N/2 NIM models     │              │
│   └──────────┬──────────┘        └──────────┬──────────┘              │
│              └──────────────┬───────────────┘                         │
│                    ┌────────▼────────┐                                 │
│                    │  Merge + commit │ → history.db committed to repo │
│                    └─────────────────┘                                 │
└───────────────────────────────────────────────────────────────────────┘
                              │
                   ┌──────────▼──────────┐
                   │  Cloudflare Pages     │ → auto-deploys on push
                   │  (static dashboard)  │   index.html + history.db
                   └──────────────────────┘
````

**Parallel jobs = ~50% faster benchmarks** ⚡

---

## 🛠️ Customization

<details>
<summary><b>Change the benchmark prompt</b></summary>

Edit `PROMPT` in `scripts/test_models.py`:
```python
PROMPT = "Your custom prompt here"
```
</details>

<details>
<summary><b>Add or remove models</b></summary>

Use the model management script:
```bash
# List models in DB vs test_models.py
python scripts/manage_models.py list

# Add a new model to ALL_MODELS
python scripts/manage_models.py add your/custom-model

# Remove a model from ALL_MODELS and purge its data from history.db
python scripts/manage_models.py remove your/custom-model

# Purge all DB models not in ALL_MODELS
python scripts/manage_models.py purge
```

Or manually edit `ALL_MODELS` in `scripts/test_models.py`:
```python
ALL_MODELS = [
    "your/custom-model",
    # ...
]
```
</details>

<details>
<summary><b>Change the schedule</b></summary>

Edit `.github/workflows/benchmark.yml`:
```yaml
- cron: '0 */6 * * *'  # Every 6 hours instead of every hour
```
</details>

<details>
<summary><b>Run locally</b></summary>

```bash
# Serve the dashboard
python3 -m http.server 8000
# Open http://localhost:8000

# Run benchmarks manually (requires NIM_API_KEY env var)
export NIM_API_KEY=your_key_here
python3 scripts/test_models.py
```
</details>

---

## 📦 Data Storage

`history.db` is a SQLite database persisted in the repo — the single source of truth. The browser loads it via [sql.js](https://sql.js.org/) (WebAssembly) and queries it entirely client-side. `scripts/results.json` is a temporary per-job artifact that is never committed.

**Schema:**

```sql
prompts       (id, text)
models        (id, name)
errors        (id, text)
runs          (id, timestamp, prompt_id, fastest_model_id, fastest_time)
model_results (run_id, model_id, success, error_id, response_time, tokens_generated, total_tokens)
```

**Benchmark parameters:** `temperature: 0.7` · `top_p: 0.9` · `max_tokens: 500` · OpenAI-compatible API

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
- [sql.js — SQLite in the browser](https://sql.js.org/)

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.

---

<div align="center">

Made with ❤️ for the ML community · [⭐ Star this repo](https://github.com/MauroDruwel/NIMStats) if you find it useful!

[![footer](https://capsule-render.vercel.app/api?type=waving&color=76b900&height=100&section=footer)](https://nimstats.maurodruwel.be/)

</div>
