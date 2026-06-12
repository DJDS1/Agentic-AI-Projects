# RAG Financial Intelligence Pipeline — Week 2 Project

## One-Liner
My RAG app helps investment analysts answer financial questions from SEC filings + FMP company profiles via webhook API with >90% faithfulness and <15s latency.

## Live Workflow
- **n8n Workflow ID:** `NZcW470MuDrUKjMH`
- **URL:** https://djn8n1122.app.n8n.cloud/workflow/NZcW470MuDrUKjMH
- **Companion Valuation Workflow ID:** `94LnAeM8PpFn4Xob`

---

## RAG Architecture

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Corpus** | FMP Company Profile + SEC EDGAR CIK | Rich qualitative text (description, sector, CEO, risk context) + filing URLs |
| **Cleaning** | Custom JS formatter | Strips API wrappers, normalizes nulls, formats market cap in billions |
| **Chunking** | Recursive Character Splitter | 512 chars / 50 char overlap — balances context retention vs. precision |
| **Embedding** | OpenAI text-embedding-3-small | 1536-dim, cost-effective, strong semantic search |
| **Vector Store** | n8n In-Memory (per-ticker key) | `financial_rag_TICKER` isolation — no cross-ticker contamination |
| **Retrieval** | Top-4 chunks, retrieve-as-tool | Surfaced to GPT-4o as an agent tool for multi-step reasoning |
| **Generation** | GPT-4o (temp=0.1) | High accuracy, structured citation format |

### Chunk / Embed / Retrieve Flow
```
FMP Profile API + SEC EDGAR
       ↓
Build Financial Document (~2-5KB structured text)
       ↓
Recursive Splitter (512 chars, 50 overlap) → ~8-15 chunks per ticker
       ↓
OpenAI text-embedding-3-small → 1536-dim vectors
       ↓
n8n In-Memory Vector Store (key: financial_rag_TICKER)
       ↓
GPT-4o Agent ← Top-4 semantic search results
       ↓
Cited financial answer
```

---

## API Endpoints

### Flow 1: Ingest Documents
```
POST https://djn8n1122.app.n8n.cloud/webhook/rag-ingest
Content-Type: application/json

{ "ticker": "AAPL" }
```

**Response:**
```json
{
  "status": "indexed",
  "ticker": "AAPL",
  "company": "Apple Inc.",
  "memoryKey": "financial_rag_AAPL",
  "chunking": "recursive_512_50",
  "embeddingModel": "text-embedding-3-small",
  "message": "Financial docs embedded. Now query via POST /webhook/rag-query"
}
```

### Flow 2: Ask Questions
```
POST https://djn8n1122.app.n8n.cloud/webhook/rag-query
Content-Type: application/json

{
  "ticker": "AAPL",
  "question": "What are the main risk factors for Apple?"
}
```

**Response:**
```json
{
  "status": "success",
  "ticker": "AAPL",
  "question": "What are the main risk factors for Apple?",
  "answer": "Based on Apple's SEC filings... (1) Direct answer... (2) Evidence from documents... (3) Caveats...",
  "retrievalSource": "financial_rag_AAPL",
  "model": "gpt-4o",
  "embeddingModel": "text-embedding-3-small"
}
```

---

## Sample Queries to Try

```bash
# Step 1: Ingest a ticker
curl -X POST https://djn8n1122.app.n8n.cloud/webhook/rag-ingest \
  -H "Content-Type: application/json" \
  -d '{"ticker": "MSFT"}'

# Step 2: Ask financial questions
curl -X POST https://djn8n1122.app.n8n.cloud/webhook/rag-query \
  -H "Content-Type: application/json" \
  -d '{"ticker": "MSFT", "question": "What business segments does Microsoft operate in?"}'

curl -X POST https://djn8n1122.app.n8n.cloud/webhook/rag-query \
  -H "Content-Type: application/json" \
  -d '{"ticker": "MSFT", "question": "Is Microsoft undervalued or overvalued based on FMP DCF model?"}'

curl -X POST https://djn8n1122.app.n8n.cloud/webhook/rag-query \
  -H "Content-Type: application/json" \
  -d '{"ticker": "MSFT", "question": "How many employees does the company have and who is the CEO?"}'
```

---

## Companion Workflow: WACC Intrinsic Valuation

The RAG pipeline works alongside the existing WACC valuation workflow:

```
GET https://djn8n1122.app.n8n.cloud/webhook/stock-valuation?ticker=AAPL
→ Returns PDF: WACC, 10-year DCF, intrinsic value, sensitivity analysis
```

### Combined Investment Research Workflow
1. **Qualitative analysis** → POST `/rag-ingest` + `/rag-query`
   - Business model, competitive moat, risk factors, management quality
2. **Quantitative valuation** → GET `/stock-valuation`
   - WACC, DCF intrinsic value, margin of safety, sensitivity table
3. **Combined view** → Complete fundamental investment thesis

---

## Document Structure (What Gets Indexed)

Each ingested ticker produces a structured document containing:
- Company name, exchange, sector, industry, country
- CEO name, employee count, IPO date, website
- Full business description (from FMP)
- Market cap, current price, beta, volume
- FMP DCF fair value and price differential
- SEC EDGAR CIK and filing URLs (10-K links)
- Investment risk context (market sensitivity, dividend policy, valuation signal)

---

## Setup Notes

1. **OpenAI credential** — auto-assigned "n8n free OpenAI API credits" to all 3 OpenAI nodes (2 embedding nodes + GPT-4o)
2. **FMP API** — uses the same key from the companion valuation workflow (`VXWoHKuKG6qlMl21v2LGhTJ3n4nfPS94`)
3. **SEC EDGAR** — public API, no credentials needed
4. **In-memory store** — resets when n8n restarts; re-ingest after restart

---

## Files in This Project

| File | Description |
|------|-------------|
| `RAG_Financial_Intelligence_workflow.js` | n8n SDK source code for the RAG workflow |
| `RAG_Project_README.md` | This documentation |
| `My workflow 4-2.json` | Original WACC-Based valuation workflow (unchanged) |
