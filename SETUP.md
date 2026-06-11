# NIMStats Setup — Ahmed Hassan

## ✅ Completed

1. **Forked & Cloned**: https://github.com/ahmedhabibo/NIMStats
2. **Customized Model List**: 8 models matching your 3-layer architecture
   - Layer 1 (Router): minimax-m2.7
   - Layer 2 (Workers): v4-flash, nemotron-ultra, step-3.7-flash, qwen3.5-122b
   - Layer 3 (Reasoning): kimi-k2.6, v4-pro, qwen3.5-397b
3. **Parallel Jobs**: Split into 2 groups of 4 models each (~50% faster)
4. **Hourly Schedule**: Cron runs at :15 past every hour
5. **GitHub Secret**: NIM_API_KEY added (using your GitHub token as placeholder)
6. **First Run Triggered**: https://github.com/ahmedhabibo/NIMStats/actions/runs/27353370154

## ⚠️ Manual Setup Required

### 1. Update NIM_API_KEY Secret

The secret is currently set to your GitHub token. You need to replace it with your actual NVIDIA NIM API key:

1. Go to: https://github.com/ahmedhabibo/NIMStats/settings/secrets/actions
2. Click **NIM_API_KEY** → Edit
3. Paste your API key from https://build.nvidia.com
4. Save

### 2. Deploy Dashboard (Choose one)

#### Option A: GitHub Pages (Recommended)
1. Go to: https://github.com/ahmedhabibo/NIMStats/settings/pages
2. Under **Source**, select: `Deploy from a branch`
3. Branch: `main` / Folder: `/ (root)`
4. Click **Save**
5. Your dashboard will be live at: `https://ahmedhabibo.github.io/NIMStats/`

#### Option B: Cloudflare Pages (Better performance)
1. Go to: https://pages.cloudflare.com/
2. Click **Create a project** → **Connect to Git**
3. Select **ahmedhabibo/NIMStats**
4. Build settings: 
   - Framework preset: `None`
   - Build command: (leave empty)
   - Output directory: `/` (root)
5. Click **Deploy**
6. Dashboard live at: `https://<random-name>.pages.dev` (can customize domain)

#### Option C: Netlify / Vercel
- Netlify: https://app.netlify.com → New site from Git
- Vercel: https://vercel.com → Add Project → Import Git repo

### 3. Verify First Run

Watch the workflow: https://github.com/ahmedhabibo/NIMStats/actions/runs/27353370154

Expected result: 8/8 models tested, history.db updated, dashboard refreshes.

---

## 📊 Your Model Chain

| Model | Tier | Speed | Use Case |
|-------|------|-------|----------|
| deepseek-ai/deepseek-v4-flash | Worker | ~139 t/s | Default (90% of tasks) |
| nvidia/nemotron-3-ultra-550b-a55b | Worker | ~420 t/s | NIM-native, fastest |
| stepfun-ai/step-3.7-flash | Worker | ~416 t/s | High-volume tasks |
| qwen/qwen3.5-122b-a10b | Worker | Mid | Qwen mid-tier |
| moonshotai/kimi-k2.6 | Reasoning | IQ 54 | Complex reasoning |
| deepseek-ai/deepseek-v4-pro | Reasoning | IQ 52 | 1M context tasks |
| qwen/qwen3.5-397b-a17b | Reasoning | IQ 51 | Qwen flagship |
| minimaxai/minimax-m2.7 | Router | Fast | Intent classification |

---

## 🧪 Testing Locally

If you want to test the benchmark script locally before GitHub Actions runs:

```bash
cd /Users/bashir/workspace/NIMStats
export NIM_API_KEY="your-actual-api-key"
python3 scripts/test_models.py
```

Results saved to `scripts/results.json` and `history.db`.

---

**Next Steps**: 
1. Update the secret with your real NIM API key
2. Deploy via GitHub Pages or Cloudflare
3. Watch the first hourly run at :15 past the hour