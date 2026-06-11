<div align="center">

[![CI](https://github.com/ahmedhabibo/NIMStats/actions/workflows/benchmark.yml/badge.svg)](https://github.com/ahmedhabibo/NIMStats/actions)
[![Models](https://img.shields.io/badge/models-8-blue?style=flat-square)](https://build.nvidia.com/models)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow?style=flat-square)](LICENSE)

<br/>

> **Ahmed Hassan's 3-Layer NIM Architecture Benchmarks — 8 models across Router, Worker, and Reasoning tiers.**

<br/>

**[🚀 View Live Dashboard](https://nimstats.maurodruwel.be/) · [📖 Docs](#-quick-start) · [🤝 Contribute](#-contributing) · [💬 Discussions](https://github.com/MauroDruwel/NIMStats/discussions)**

</div>

---

## ✨ What is NIMStats?

NIMStats automatically benchmarks **8 NVIDIA NIM models** every hour using GitHub Actions and publishes the results to a beautiful, interactive dashboard. No servers, no subscriptions — just fork, add your API key, and go.

### 🏗️ 3-Layer Architecture

| Tier | Models | Purpose |
|------|--------|---------|
| **Layer 1 — Router** | `minimax-m2.7` | Intent classification, memory management |
| **Layer 2 — Workers** | `v4-flash`, `nemotron-ultra`, `step-3.7-flash`, `qwen3.5-122b` | Fast, cheap — handles 90% of daily tasks |
| **Layer 3 — Reasoning** | `kimi-k2.6`, `v4-pro`, `qwen3.5-397b` | Complex reasoning, expensive — invoked only when needed |

**Cost win**: Cheaper models (V4 Flash @ ~139 t/s) handle day-to-day work. Kimi K2.6 and V4 Pro only invoked for difficult tasks.

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
| **Cloudflare Pages** | Connect repo in [Cloudflare Pages](https://pages.cloudflare.com/) |
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
<summary><b>20 models across 11 providers — click to expand</b></summary>

<br/>

| Provider | Model | Highlight |
|----------|-------|-----------|
| **DeepSeek** | `deepseek-ai/deepseek-v4-flash` | Fast MoE, optimized for speed |
| **DeepSeek** | `deepseek-ai/deepseek-v4-pro` | Professional-grade reasoning |
| **DeepSeek** | `deepseek-ai/deepseek-v3.2` | Latest with improved reasoning |
| **Z-AI** | `z-ai/glm-5.1` | Superior code understanding |
| **Z-AI** | `z-ai/glm-4.7` | Strong mathematical capabilities |
| **MiniMax** | `minimaxai/minimax-m2.7` | Efficient inference model |
| **MiniMax** | `minimaxai/minimax-m2.5` | Previous generation MiniMax |
| **NVIDIA** | `nvidia/nemotron-3-super-120b-a12b` | NVIDIA's 120B flagship |
| **NVIDIA** | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | Compact omni reasoning model |
| **Moonshot** | `moonshotai/kimi-k2.6` | Context-optimized model |
| **Moonshot** | `moonshotai/kimi-k2-instruct` | Instruction-tuned Kimi |
| **OpenAI** | `openai/gpt-oss-120b` | Open-source 120B |
| **Google** | `google/gemma-4-31b-it` | Lightweight edge inference |
| **Qwen** | `qwen/qwen3-coder-480b-a35b-instruct` | Specialized coding (480B MoE) |
| **Qwen** | `qwen/qwen2.5-coder-32b-instruct` | Lightweight Qwen coder |
| **Qwen** | `qwen/qwen3.5-397b-a17b` | Flagship Qwen (397B) |
| **Qwen** | `qwen/qwen3.5-122b-a10b` | Mid-range Qwen 3.5 MoE |
| **Mistral** | `mistralai/devstral-2-123b-instruct-2512` | Developer-focused (123B) |
| **Mistral** | `mistralai/mistral-large-3-675b-instruct-2512` | Largest Mistral (675B) |
| **Mistral** | `mistralai/mistral-medium-3.5-128b` | Efficient medium-scale Mistral |
| **Meta** | `meta/llama-3_3-70b-instruct` | Llama 3.3 70B |
| **Meta** | `meta/llama-4-maverick-17b-128e-instruct` | Llama 4 Maverick (128 experts) |
| **Meta** | `meta/llama-3.2-90b-vision-instruct` | Multimodal 90B vision model |
| **StepFun** | `stepfun-ai/step-3.5-flash` | Ultra-fast flash model |
| **StepFun** | `stepfun-ai/step-3.7-flash` | Latest high-performance flash |

</details>

---

## 🏗️ How It Works

```
┌──────────────────── GitHub Actions (every hour) ──────────────────────┐
│                                                                               │
│   ┌─────────────────────┐        ┌─────────────────────┐                    │
│   │  Job 1 — Group A    │        │  Job 2 — Group B    │  (run in parallel) │
│   │  10 NIM models      │        │  10 NIM models      │                    │
│   └──────────┬──────────┘        └──────────┬──────────┘                    │
│              └──────────────┬───────────────┘                               │
│                    ┌────────▼────────┐                                       │
│                    │  Merge + commit │  → history.db updated in repo         │
│                    └─────────────────┘                                       │
└───────────────────────────────────────────────────────────────────────────── ┘
                                     │
                          ┌──────────▼──────────┐
                          │  Static Dashboard   │  rebuilds on each push
                          │  (Pages / Netlify)  │
                          └─────────────────────┘
```

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

Edit `ALL_MODELS` in `scripts/test_models.py`:
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
runs          (id, timestamp, prompt, success_count, total_models, fastest_model, fastest_time)
model_results (run_id, model, success, error, response_time, tokens_generated, total_tokens, response)
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
