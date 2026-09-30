# HW4 — Pi Memory System

> **課程作業 4：為本地 Coding Agent 打造記憶機制（Pi Memory）**  

A persistent, retrieval-augmented memory layer for the [Pi coding agent](https://github.com/earendil-works/pi).  
Implements the **Capture → Store → Retrieve → Inject** pipeline in pure Python.

---

## 系統設計概述

| 階段 | 模組 | 說明 |
|---|---|---|
| Capture | `memory/core.py` (provided) | 攔截 agent 互動，擷取觀察 |
| Store | `memory/store.py` | id 去重、JSON 原子寫入（fsync）、壞檔隔離 |
| Retrieve | `memory/bm25.py` | 標準 BM25 Okapi 確定性排序 |
| Inject | `memory/core.py` (provided) | Token 預算截斷，注入 context |
| Hybrid (Task 2) | `memory/hybrid.py` | BM25 + local sentence-transformers 融合檢索 |

---

## 環境需求

| 項目 | 版本 / 說明 |
|---|---|
| **Python** | **>= 3.10**（作業要求；開發驗證版本：3.10+） |
| 本地模型 (demo 用) | Ollama + llama3.2（或任意 OpenAI-compatible endpoint） |
| Embedding 模型 (hybrid) | `paraphrase-multilingual-MiniLM-L12-v2`（sentence-transformers 首次執行自動從 HuggingFace 下載，約 120 MB；之後離線可用，不呼叫雲端推論 API） |
| 推論後端 | CPU-only（CUDA 非必要） |
| RAM | 純 BM25：< 100 MB；Hybrid：約 500 MB |
| VRAM | 不需要（CPU inference） |

> ⚠️ 本作業**完全本地執行**，不呼叫任何雲端 LLM / Embedding API。

---

## 安裝

```bash
# Python >= 3.10 required
pip install -r requirements.txt
```

`requirements.txt` 中的 PyTorch 為 CPU-only 版本，由 `--extra-index-url` 自動指向正確來源。  
若網路受限，請手動安裝 `torch` 後再執行 `pip install sentence-transformers hypothesis pytest`。

---

## 測試

```bash
# Linux / macOS
PYTHONPATH=. pytest -q

# Windows PowerShell
$env:PYTHONPATH = "."; pytest -q
```

預期：**13 passed, 0 failed**（公開測試集；隱藏測試格式相同，換資料）。

---

## Benchmark

```bash
# Linux / macOS
# 標準 30 筆語料（BM25 基準）
PYTHONPATH=. python benchmark/run_benchmark.py --k 5 --per-query

# 大語料 100 筆（自行探索）
PYTHONPATH=. python benchmark/run_benchmark.py \
  --corpus benchmark/corpus_large.jsonl \
  --queries benchmark/queries_large.jsonl \
  --k 5 --per-query

# Hybrid benchmark（需先 pip install sentence-transformers）
PYTHONPATH=. python benchmark/run_benchmark_hybrid.py --k 5 --per-query

# Windows PowerShell
$env:PYTHONPATH = "."; python benchmark/run_benchmark.py --k 5 --per-query
$env:PYTHONPATH = "."; python benchmark/run_benchmark_hybrid.py --k 5 --per-query
```

實測結果（純 BM25，30 筆語料）：

| Recall@5 | MRR   | nDCG@5 |
|---|---|---|
| **0.810** | **0.810** | **0.802** |

---

## Task 2 進階功能：Hybrid Retrieval

實作位置：`memory/hybrid.py` → `hybrid_search()`  
Embedding 模型：`paraphrase-multilingual-MiniLM-L12-v2`（支援中英跨語言查詢）

**Python API 呼叫方式：**

```python
from memory.hybrid import hybrid_search

results = hybrid_search(
    query="pnpm test",
    docs=[{"id": "d1", "text": "this project uses pnpm test"}, ...],
    k=5,
    alpha=0.5,   # 0.5 = BM25 與 cosine 各佔 50%
)
```

> ⚠️ CLI (`python -m memory.cli`) **不支援 `--hybrid` 旗標**，hybrid 功能僅透過 Python API 或 `benchmark/run_benchmark_hybrid.py` 使用。  
> 純 BM25 路徑不 import `sentence_transformers`，hybrid 未安裝時純 BM25 測試仍可正常執行。

---

## 接到 Pi 執行

```bash
# Linux / macOS
PYTHONPATH=. pi -e ./pi-bridge/extension.ts

# Windows PowerShell
$env:PYTHONPATH = "."; pi -e ./pi-bridge/extension.ts
```

Pi 需要本地模型設定，請先複製並修改：

```bash
# 複製設定檔到 Pi 讀取的位置
cp models.json.example ~/.pi/agent/models.json
# Windows: copy models.json.example %USERPROFILE%\.pi\agent\models.json
```

---

## CLI 指令參考

```bash
# Capture（寫入記憶）
PYTHONPATH=. python -m memory.cli capture --summary "這個專案使用 pnpm，不要使用 npm。"

# Retrieve（查詢記憶）
PYTHONPATH=. python -m memory.cli retrieve --query "怎麼跑測試" --k 5

# Inject（取得注入字串）
PYTHONPATH=. python -m memory.cli inject --query "怎麼跑測試" --budget 2000
```

---

## 安全性

- 本作業不使用任何雲端 API，不需要 API key。
- 請勿 commit `.env` 或任何真實 API key（CI 自動檢查）。
- `memory.json` 和 `.pi-memory.json` 已加入 `.gitignore`。
- `models.json` 已加入 `.gitignore`（含本地 endpoint 設定，不應 commit）。

---

## Demo

Demo 展示跨 session 記憶生效（Session A 告訴 agent pnpm 規範，Session B 不重述即記得）。

Demo video: https://youtu.be/Yhh-RkFCPe0

詳細步驟見 `demo/README.md`。

最短版操作（Windows PowerShell）：

```powershell
# 清除舊記憶
Remove-Item "$env:USERPROFILE\.pi-memory.json" -ErrorAction SilentlyContinue

# Session A
$env:PYTHONPATH = "."; pi -e ./pi-bridge/extension.ts
# 輸入: 請記住：這個專案使用 pnpm，不要使用 npm。測試指令是 pnpm test。
# 然後: /exit

# Session B（重新啟動，不提 pnpm）
$env:PYTHONPATH = "."; pi -e ./pi-bridge/extension.ts
# 輸入: 如果我要執行這個專案的測試，應該使用什麼指令？
# 預期: agent 回答 pnpm test ✅
```

---

## 安全性

- 本作業不使用任何雲端 API，不需要 API key。
- 請勿 commit `.env` 或任何真實 API key（CI 自動檢查）。
- `memory.json` 和 `.pi-memory.json` 已加入 `.gitignore`。
- `models.json` 已加入 `.gitignore`（含本地 endpoint 設定，不應 commit）。

---

## 檔案結構

```
AIASE2026-HW4/
├── memory/
│   ├── __init__.py
│   ├── bm25.py           ← BM25 Okapi 實作（主戰場）
│   ├── store.py          ← JSON 持久層
│   ├── hybrid.py         ← Task 2：hybrid retrieval
│   ├── core.py           ← 已提供，不修改
│   └── cli.py            ← 已提供，不修改
├── tests/
│   └── test_memory.py    ← 公開單元測試（13 tests）
├── benchmark/
│   ├── run_benchmark.py         ← 純 BM25 benchmark
│   ├── run_benchmark_hybrid.py  ← Hybrid benchmark
│   ├── corpus.jsonl / queries.jsonl
│   └── corpus_large.jsonl / queries_large.jsonl
├── pi-bridge/
│   └── extension.ts      ← 已提供，不修改
├── fixtures/
│   └── observations.json
├── demo/
│   └── README.md
├── requirements.txt
├── README.md
├── REPORT.md
└── models.json.example
```
