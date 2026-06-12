"""
Financial RAG Intelligence Pipeline — Streamlit App
====================================================
Runs both n8n workflows and adds local chunking strategy comparison + reranking analysis.

Endpoints used:
  POST /webhook/rag-ingest   { ticker }
  POST /webhook/rag-query    { ticker, question }
  GET  /webhook/stock-valuation?ticker=TICKER

Run:
  pip install -r requirements.txt
  streamlit run app.py
"""

import math
import time
from collections import Counter

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import streamlit as st
from openai import OpenAI

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Financial RAG Intelligence Pipeline",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
N8N_BASE   = "https://djn8n1122.app.n8n.cloud/webhook"
FMP_KEY    = "VXWoHKuKG6qlMl21v2LGhTJ3n4nfPS94"
TIMEOUT    = 60          # seconds for n8n calls
FMP_TIMEOUT = 15

CHUNKING_STRATEGIES = [
    {"name": "Fine-grained",  "size": 256,  "overlap": 25,  "color": "#636EFA"},
    {"name": "Balanced ✓",    "size": 512,  "overlap": 50,  "color": "#00CC96"},   # current n8n setting
    {"name": "Context-rich",  "size": 1024, "overlap": 100, "color": "#EF553B"},
]

SAMPLE_QUESTIONS = [
    "What are the main business segments and revenue drivers?",
    "What are the key risk factors for this company?",
    "How does the company describe its competitive advantages?",
    "What is the company's dividend policy and financial health?",
    "Who is the CEO and how many employees does the company have?",
    "Is the stock considered undervalued or overvalued per the FMP DCF model?",
]

# ── CUSTOM CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* ── FONTS ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* ── GLOBAL BACKGROUND — NYSE trading floor photo + dark overlay + grid ── */
    .stApp {
        background-color: #060c18;
        background-image:
            linear-gradient(rgba(0, 204, 150, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 204, 150, 0.03) 1px, transparent 1px),
            linear-gradient(rgba(4, 8, 20, 0.82), rgba(4, 8, 20, 0.92)),
            url("https://upload.wikimedia.org/wikipedia/commons/4/4e/NYSE_Advanced_Trading_Floor.jpg");
        background-size: 48px 48px, 48px 48px, cover, cover;
        background-position: center, center, center, center;
        background-attachment: fixed, fixed, fixed, fixed;
        font-family: 'Inter', sans-serif;
    }

    /* ── SIDEBAR ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(8,14,28,0.96) 0%, rgba(4,8,20,0.98) 100%) !important;
        border-right: 1px solid rgba(0, 204, 150, 0.15) !important;
        backdrop-filter: blur(12px);
    }
    [data-testid="stSidebar"] .stButton > button {
        background: linear-gradient(135deg, #00CC96 0%, #00a878 100%) !important;
        color: #000 !important;
        font-weight: 700 !important;
        letter-spacing: 0.04em !important;
        border: none !important;
        border-radius: 8px !important;
        box-shadow: 0 0 20px rgba(0, 204, 150, 0.35) !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        box-shadow: 0 0 32px rgba(0, 204, 150, 0.6) !important;
        transform: translateY(-1px) !important;
    }

    /* ── TABS ── */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(13, 21, 38, 0.8) !important;
        border-bottom: 1px solid rgba(0, 204, 150, 0.2) !important;
        gap: 4px;
        border-radius: 10px 10px 0 0;
        padding: 6px 6px 0 6px;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: #6b7a99 !important;
        font-weight: 500 !important;
        font-size: 0.88rem !important;
        border-radius: 8px 8px 0 0 !important;
        padding: 8px 18px !important;
        border: 1px solid transparent !important;
        transition: all 0.2s ease !important;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(0, 204, 150, 0.12) !important;
        color: #00CC96 !important;
        border-color: rgba(0, 204, 150, 0.3) !important;
        border-bottom-color: transparent !important;
    }
    .stTabs [data-baseweb="tab-panel"] {
        background: rgba(10, 16, 30, 0.7) !important;
        border: 1px solid rgba(0, 204, 150, 0.12) !important;
        border-top: none !important;
        border-radius: 0 0 10px 10px !important;
        padding: 1.5rem !important;
        backdrop-filter: blur(8px);
    }

    /* ── METRIC CARDS ── */
    [data-testid="stMetric"] {
        background: rgba(13, 21, 38, 0.85) !important;
        border: 1px solid rgba(0, 204, 150, 0.15) !important;
        border-radius: 10px !important;
        padding: 1rem 1.2rem !important;
        backdrop-filter: blur(8px);
        transition: border-color 0.2s ease;
    }
    [data-testid="stMetric"]:hover {
        border-color: rgba(0, 204, 150, 0.4) !important;
    }
    [data-testid="stMetricLabel"] {
        color: #6b7a99 !important;
        font-size: 0.75rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        font-weight: 500 !important;
    }
    [data-testid="stMetricValue"] {
        color: #e8edf5 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 1.3rem !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetricDelta"] svg { display: none; }

    /* ── GLASSMORPHISM CHUNK CARDS ── */
    .chunk-card {
        background: rgba(13, 21, 38, 0.75);
        border: 1px solid rgba(0, 204, 150, 0.18);
        border-left: 3px solid #00CC96;
        border-radius: 8px;
        padding: 0.9rem 1.1rem;
        margin: 0.5rem 0;
        font-size: 0.84rem;
        color: #b8c5d6;
        line-height: 1.6;
        backdrop-filter: blur(6px);
        transition: border-color 0.2s ease, background 0.2s ease;
    }
    .chunk-card:hover {
        background: rgba(13, 21, 38, 0.95);
        border-color: rgba(0, 204, 150, 0.45);
    }

    /* ── HERO HEADER ── */
    .hero-header {
        background: linear-gradient(135deg, rgba(0,204,150,0.08) 0%, rgba(0,100,255,0.06) 100%);
        border: 1px solid rgba(0, 204, 150, 0.2);
        border-radius: 14px;
        padding: 1.4rem 1.8rem;
        margin-bottom: 1.2rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        backdrop-filter: blur(10px);
    }
    .hero-ticker {
        font-family: 'JetBrains Mono', monospace;
        font-size: 2.2rem;
        font-weight: 700;
        color: #00CC96;
        letter-spacing: 0.06em;
        text-shadow: 0 0 20px rgba(0,204,150,0.4);
    }
    .hero-label {
        font-size: 0.8rem;
        color: #6b7a99;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 2px;
    }

    /* ── TICKER BADGE ── */
    .ticker-badge {
        display: inline-block;
        background: rgba(0,204,150,0.12);
        border: 1px solid rgba(0,204,150,0.35);
        border-radius: 6px;
        padding: 2px 10px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        color: #00CC96;
        font-weight: 600;
        letter-spacing: 0.05em;
    }

    /* ── DATAFRAMES ── */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(0, 204, 150, 0.15) !important;
        border-radius: 10px !important;
        overflow: hidden !important;
    }

    /* ── INFO / WARNING / ERROR BOXES ── */
    [data-testid="stAlert"] {
        border-radius: 10px !important;
        border-left-width: 4px !important;
        backdrop-filter: blur(6px) !important;
    }

    /* ── CODE BLOCKS ── */
    .stCode {
        background: rgba(6, 12, 24, 0.9) !important;
        border: 1px solid rgba(0, 204, 150, 0.15) !important;
        border-radius: 8px !important;
    }

    /* ── INPUTS ── */
    [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {
        background: rgba(13, 21, 38, 0.9) !important;
        border: 1px solid rgba(0, 204, 150, 0.2) !important;
        border-radius: 8px !important;
        color: #e8edf5 !important;
        font-family: 'Inter', sans-serif !important;
    }
    [data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus {
        border-color: rgba(0, 204, 150, 0.6) !important;
        box-shadow: 0 0 0 2px rgba(0, 204, 150, 0.12) !important;
    }

    /* ── SELECT BOX ── */
    [data-testid="stSelectbox"] > div > div {
        background: rgba(13, 21, 38, 0.9) !important;
        border: 1px solid rgba(0, 204, 150, 0.2) !important;
        border-radius: 8px !important;
        color: #e8edf5 !important;
    }

    /* ── DIVIDERS ── */
    hr {
        border-color: rgba(0, 204, 150, 0.12) !important;
    }

    /* ── EXPANDER ── */
    [data-testid="stExpander"] {
        background: rgba(13, 21, 38, 0.7) !important;
        border: 1px solid rgba(0, 204, 150, 0.15) !important;
        border-radius: 10px !important;
    }

    /* ── CANDLESTICK DECORATIVE BAR (top of page) ── */
    .top-bar {
        height: 3px;
        background: linear-gradient(90deg, #00CC96, #0070f3, #00CC96, #ef553b, #00CC96);
        background-size: 200% 100%;
        animation: shimmer 4s linear infinite;
        border-radius: 2px;
        margin-bottom: 1.2rem;
    }
    @keyframes shimmer {
        0%   { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }

    /* ── RANK BADGES ── */
    .rank-up   { color: #00CC96; font-weight: 700; }
    .rank-down { color: #EF553B; font-weight: 700; }
    .rank-same { color: #6b7a99; }
    .status-badge-ok  { background: rgba(0,204,150,0.15); color: #00CC96; border: 1px solid rgba(0,204,150,0.4); padding: 2px 10px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; letter-spacing: 0.06em; }
    .status-badge-err { background: rgba(239,85,59,0.15); color: #EF553B; border: 1px solid rgba(239,85,59,0.4); padding: 2px 10px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; }

    /* ── SCROLLBAR ── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #060c18; }
    ::-webkit-scrollbar-thumb { background: rgba(0,204,150,0.25); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(0,204,150,0.5); }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════

def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Recursive character text splitter — mirrors LangChain behaviour."""
    chunks, start = [], 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end]
        if end < len(text):
            for sep in ["\n\n", "\n", ". ", " "]:
                pos = chunk.rfind(sep)
                if pos > chunk_size * 0.5:
                    end = start + pos + len(sep)
                    chunk = text[start:end]
                    break
        chunk = chunk.strip()
        if len(chunk) > 20:
            chunks.append(chunk)
        start = end - overlap
        if start >= len(text):
            break
    return chunks


class BM25:
    """Okapi BM25 — pure Python, no extra deps."""
    def __init__(self, corpus: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b  = b
        self.tokenized = [doc.lower().split() for doc in corpus]
        N = len(corpus)
        self.avgdl = sum(len(d) for d in self.tokenized) / max(N, 1)
        df: dict[str, int] = {}
        for doc in self.tokenized:
            for w in set(doc):
                df[w] = df.get(w, 0) + 1
        self.idf = {w: math.log((N - f + 0.5) / (f + 0.5) + 1) for w, f in df.items()}

    def scores(self, query: str) -> list[float]:
        tokens = query.lower().split()
        out = []
        for doc in self.tokenized:
            tf_map = Counter(doc)
            dl = len(doc)
            s = 0.0
            for t in tokens:
                if t not in self.idf:
                    continue
                tf = tf_map.get(t, 0)
                s += self.idf[t] * (tf * (self.k1 + 1)) / (
                    tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                )
            out.append(s)
        return out


def cosine(a: list, b: list) -> float:
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))


def get_embeddings(client: OpenAI, texts: list[str]) -> list[list[float]]:
    """Batch embed; respects 2048-token limit by batching 20 at a time."""
    results = []
    for i in range(0, len(texts), 20):
        resp = client.embeddings.create(input=texts[i:i+20], model="text-embedding-3-small")
        results.extend([e.embedding for e in resp.data])
    return results


@st.cache_data(ttl=300, show_spinner=False)
def fetch_fmp_profile(ticker: str) -> dict:
    try:
        r = requests.get(
            "https://financialmodelingprep.com/stable/profile",
            params={"symbol": ticker, "apikey": FMP_KEY},
            timeout=FMP_TIMEOUT,
        )
        raw = r.json()
        return raw[0] if isinstance(raw, list) and raw else (raw or {})
    except Exception:
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def fetch_fmp_dcf(ticker: str) -> dict:
    try:
        r = requests.get(
            "https://financialmodelingprep.com/stable/discounted-cash-flow",
            params={"symbol": ticker, "apikey": FMP_KEY},
            timeout=FMP_TIMEOUT,
        )
        raw = r.json()
        return raw[0] if isinstance(raw, list) and raw else (raw or {})
    except Exception:
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def fetch_sec_cik(ticker: str) -> str:
    try:
        r = requests.get(
            "https://efts.sec.gov/LATEST/search-index",
            params={"q": ticker, "forms": "10-K", "dateRange": "custom", "startdt": "2023-01-01"},
            headers={"User-Agent": "streamlit-rag-app contact@example.com"},
            timeout=10,
        )
        hits = r.json().get("hits", {}).get("hits", [])
        return hits[0].get("_source", {}).get("entity_id", "") if hits else ""
    except Exception:
        return ""


def build_financial_doc(ticker: str) -> tuple[str, dict]:
    prof = fetch_fmp_profile(ticker)
    dcf_data = fetch_fmp_dcf(ticker)
    cik  = fetch_sec_cik(ticker)

    # Merge DCF into profile so the rest of the app has one dict to work with
    if dcf_data:
        prof["dcf"]     = dcf_data.get("dcf")
        prof["dcfPrice"] = dcf_data.get("Stock Price")
        price = float(prof.get("price") or 0)
        dcf_v = float(dcf_data.get("dcf") or 0)
        prof["dcfDiff"] = round((dcf_v - price) / price * 100, 2) if price else None

    fmt  = lambda n: str(n) if n is not None else "N/A"
    fmtB = lambda n: f"${float(n)/1e9:.2f}B" if n else "N/A"
    beta     = float(prof.get("beta", 1) or 1)
    dcf_diff = float(prof.get("dcfDiff") or 0)

    lines = [
        f"# {fmt(prof.get('companyName'))} ({ticker}) — Financial Intelligence Document",
        "",
        "## Company Overview",
        f"Ticker: {ticker}",
        f"Company Name: {fmt(prof.get('companyName'))}",
        f"Exchange: {fmt(prof.get('exchange') or prof.get('exchangeFullName'))}",
        f"Sector: {fmt(prof.get('sector'))}",
        f"Industry: {fmt(prof.get('industry'))}",
        f"Country: {fmt(prof.get('country'))}",
        f"CEO: {fmt(prof.get('ceo'))}",
        f"Full-Time Employees: {fmt(prof.get('fullTimeEmployees'))}",
        f"Website: {fmt(prof.get('website'))}",
        f"IPO Date: {fmt(prof.get('ipoDate'))}",
        f"SEC CIK: {cik}",
        "",
        "## Business Description",
        prof.get("description") or "No description available.",
        "",
        "## Market and Valuation Data",
        f"Current Price: ${fmt(prof.get('price'))}",
        f"Market Capitalization: {fmtB(prof.get('marketCap'))}",
        f"Beta (market sensitivity): {fmt(prof.get('beta'))}",
        f"Volume Average: {fmt(prof.get('averageVolume'))}",
        f"Last Dividend Paid: ${fmt(prof.get('lastDividend'))}",
        f"DCF Fair Value (FMP model): ${fmt(prof.get('dcf'))}",
        f"DCF vs Market Price Differential: {fmt(prof.get('dcfDiff'))}%",
        "",
        "## SEC Filing References",
        f"CIK: {cik}",
        f"10-K Filings: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-K",
        f"XBRL Facts: https://data.sec.gov/api/xbrl/companyfacts/CIK{str(cik).zfill(10)}.json",
        "",
        "## Investment Risk Context",
        f"{fmt(prof.get('companyName'))} operates in the {fmt(prof.get('sector'))} sector "
        f"({fmt(prof.get('industry'))}).",
        f"Beta of {fmt(prof.get('beta'))} indicates "
        f"{'above-average' if beta > 1 else 'below-average'} market sensitivity.",
        f"Dividend policy: last dividend ${fmt(prof.get('lastDividend'))} per share.",
        f"FMP DCF model implies {'undervaluation' if dcf_diff > 0 else 'overvaluation'} "
        f"of {abs(dcf_diff):.1f}% vs current price.",
    ]
    return "\n".join(lines), prof


def normalize(arr: list[float]) -> list[float]:
    mn, mx = min(arr), max(arr)
    if mx == mn:
        return [0.5] * len(arr)
    return [(x - mn) / (mx - mn) for x in arr]


# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="padding:1rem 0 0.5rem 0">
      <div style="font-size:1.6rem;margin-bottom:4px">📈</div>
      <div style="font-size:1.1rem;font-weight:700;color:#e8edf5;letter-spacing:0.02em">Financial RAG</div>
      <div style="font-size:0.72rem;color:#00CC96;letter-spacing:0.1em;text-transform:uppercase;margin-top:2px">Intelligence Pipeline</div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    ticker_input = st.text_input(
        "📌 Stock Ticker",
        value="AAPL",
        max_chars=10,
        help="Enter any US stock ticker, e.g. MSFT, NVDA, TSLA",
    ).strip().upper()

    openai_key = st.text_input(
        "🔑 OpenAI API Key",
        type="password",
        placeholder="sk-...",
        help="Required for Chunking Comparison and Reranking tabs",
    )

    st.divider()
    st.subheader("RAG Questions")
    selected_q = st.selectbox("Choose a preset", SAMPLE_QUESTIONS, index=0)
    custom_q   = st.text_area("Or type your own", placeholder="Ask anything about the company…", height=80)
    question   = custom_q.strip() if custom_q.strip() else selected_q

    st.divider()
    rerank_query = st.text_input(
        "🎯 Reranking test query",
        value="competitive advantage and market position",
        help="Used in the Reranking tab to compare retrieval approaches",
    )

    run_btn = st.button("🚀 Run Full Analysis", type="primary", use_container_width=True)
    st.caption("Runs ingest → valuation → Q&A → local analysis")

# ════════════════════════════════════════════════════════════════════════════
# MAIN TABS
# ════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="top-bar"></div>', unsafe_allow_html=True)
st.markdown(f"""
<div class="hero-header">
  <div>
    <div class="hero-label">Financial Intelligence Pipeline</div>
    <div class="hero-ticker">📈 {ticker_input}</div>
  </div>
  <div style="margin-left:auto;text-align:right">
    <div class="hero-label">Powered by</div>
    <div style="color:#6b7a99;font-size:0.82rem;margin-top:2px">n8n · GPT-4o · SEC EDGAR · FMP</div>
  </div>
</div>
""", unsafe_allow_html=True)

tab_val, tab_rag, tab_chunk, tab_rerank = st.tabs([
    "📊 Valuation Report",
    "🔍 RAG Q&A",
    "📐 Chunking Strategy Comparison",
    "🎯 Reranking Impact Analysis",
])

# ── SESSION STATE ─────────────────────────────────────────────────────────
if "doc_text" not in st.session_state:
    st.session_state.doc_text = None
if "profile"  not in st.session_state:
    st.session_state.profile  = {}
if "rag_answer" not in st.session_state:
    st.session_state.rag_answer = None
if "ingest_ok" not in st.session_state:
    st.session_state.ingest_ok = False
if "chunk_results" not in st.session_state:
    st.session_state.chunk_results = None
if "rerank_results" not in st.session_state:
    st.session_state.rerank_results = None
if "last_ticker" not in st.session_state:
    st.session_state.last_ticker = ""
if "val_pdf" not in st.session_state:
    st.session_state.val_pdf = None
if "val_error" not in st.session_state:
    st.session_state.val_error = None

# ════════════════════════════════════════════════════════════════════════════
# RUN BUTTON LOGIC
# ════════════════════════════════════════════════════════════════════════════
if run_btn:
    if not ticker_input:
        st.error("Please enter a ticker symbol.")
        st.stop()

    st.session_state.last_ticker = ticker_input

    # ── 1. Fetch FMP profile + build local doc ───────────────────────────
    with st.spinner(f"Fetching company profile for {ticker_input}…"):
        doc_text, profile = build_financial_doc(ticker_input)
        st.session_state.doc_text = doc_text
        st.session_state.profile  = profile

    # ── 2. n8n RAG Ingest ────────────────────────────────────────────────
    with st.spinner("Ingesting documents into n8n vector store…"):
        try:
            t0 = time.time()
            r = requests.post(
                f"{N8N_BASE}/rag-ingest",
                json={"ticker": ticker_input},
                timeout=TIMEOUT,
            )
            ingest_ms = int((time.time() - t0) * 1000)
            if r.status_code == 200:
                st.session_state.ingest_ok = True
                try:
                    idata = r.json() if r.text.strip() else {}
                except Exception:
                    idata = {}
                # Ensure memoryKey always reflects the actual ticker
                if not idata.get("memoryKey") or "undefined" in str(idata.get("memoryKey", "")):
                    idata["memoryKey"] = f"financial_rag_{ticker_input}"
                st.session_state.ingest_data = idata
                st.session_state.ingest_ms   = ingest_ms
            else:
                st.session_state.ingest_ok    = False
                st.session_state.ingest_error = f"HTTP {r.status_code}: {r.text[:300]}"
        except Exception as e:
            st.session_state.ingest_ok    = False
            st.session_state.ingest_error = str(e)

    # ── 3. n8n RAG Query ─────────────────────────────────────────────────
    if st.session_state.ingest_ok:
        with st.spinner(f'Querying RAG agent: "{question[:60]}..."'):
            try:
                t0 = time.time()
                r = requests.post(
                    f"{N8N_BASE}/rag-query",
                    json={"ticker": ticker_input, "question": question},
                    timeout=TIMEOUT,
                )
                query_ms = int((time.time() - t0) * 1000)
                if r.status_code == 200:
                    try:
                        answer_data = r.json() if r.text.strip() else None
                    except Exception:
                        answer_data = None
                    if answer_data:
                        st.session_state.rag_answer = answer_data
                        st.session_state.query_ms   = query_ms
                        st.session_state.rag_error  = None
                    else:
                        st.session_state.rag_answer = None
                        st.session_state.rag_error  = (
                            "RAG workflow returned an empty response. "
                            "Check that the RAG Query workflow (NZcW470MuDrUKjMH) is active and returning output in n8n."
                        )
                else:
                    st.session_state.rag_answer  = None
                    st.session_state.rag_error   = f"HTTP {r.status_code}: {r.text[:300]}"
            except Exception as e:
                st.session_state.rag_error  = str(e)
                st.session_state.rag_answer = None

    # ── 4. Valuation Report ──────────────────────────────────────────────
    with st.spinner("Fetching WACC-Based valuation report…"):
        try:
            t0 = time.time()
            r = requests.get(
                f"{N8N_BASE}/stock-valuation",
                params={"ticker": ticker_input},
                timeout=TIMEOUT,
            )
            val_ms = int((time.time() - t0) * 1000)
            if r.status_code == 200 and "application/pdf" in r.headers.get("Content-Type", ""):
                st.session_state.val_pdf   = r.content
                st.session_state.val_ms    = val_ms
                st.session_state.val_error = None
            elif r.status_code == 200:
                # Sometimes returns JSON or redirect — store raw
                st.session_state.val_pdf   = None
                st.session_state.val_raw   = r.text[:2000]
                st.session_state.val_ms    = val_ms
                st.session_state.val_error = None
            else:
                st.session_state.val_pdf   = None
                st.session_state.val_error = f"HTTP {r.status_code}: {r.text[:300]}"
        except Exception as e:
            st.session_state.val_pdf   = None
            st.session_state.val_error = str(e)

    # ── 5. Local chunking comparison (needs OpenAI key) ──────────────────
    if openai_key and doc_text:
        with st.spinner("Running chunking strategy comparison (embedding chunks)…"):
            try:
                client  = OpenAI(api_key=openai_key, timeout=30.0)
                results = []
                # Embed question once — reused across all strategies
                q_emb = get_embeddings(client, [question])[0]
                for strat in CHUNKING_STRATEGIES:
                    chunks     = chunk_text(doc_text, strat["size"], strat["overlap"])
                    embeddings = get_embeddings(client, chunks)
                    sims       = [cosine(q_emb, e) for e in embeddings]
                    top_idx    = sorted(range(len(sims)), key=lambda i: -sims[i])[:3]
                    results.append({
                        "strategy"       : strat["name"],
                        "chunk_size"     : strat["size"],
                        "overlap"        : strat["overlap"],
                        "num_chunks"     : len(chunks),
                        "avg_chunk_len"  : int(np.mean([len(c) for c in chunks])),
                        "top1_score"     : round(sims[top_idx[0]], 4) if top_idx else 0,
                        "top3_avg_score" : round(np.mean([sims[i] for i in top_idx[:3]]), 4),
                        "top_chunks"     : [chunks[i] for i in top_idx[:3]],
                        "top_scores"     : [round(sims[i], 4) for i in top_idx[:3]],
                        "color"          : strat["color"],
                        "all_chunks"     : chunks,
                        "all_embeddings" : embeddings,
                    })
                st.session_state.chunk_results = results
                st.session_state.chunk_error   = None
                # Re-use balanced strategy chunks for reranking tab
                balanced = next(r for r in results if "Balanced" in r["strategy"])
                st.session_state._balanced_chunks = balanced["all_chunks"]
                st.session_state._balanced_embs   = balanced["all_embeddings"]
            except Exception as e:
                st.session_state.chunk_results = None
                st.session_state.chunk_error   = str(e)

    # ── 6. Reranking analysis ─────────────────────────────────────────────
    if openai_key and st.session_state.get("_balanced_chunks"):
        with st.spinner("Running reranking analysis (dense vs BM25+semantic hybrid)…"):
            try:
                client  = OpenAI(api_key=openai_key, timeout=30.0)
                chunks  = st.session_state._balanced_chunks
                embs    = st.session_state._balanced_embs
                q_emb   = get_embeddings(client, [rerank_query])[0]

                sem_scores = [cosine(q_emb, e) for e in embs]
                bm25_obj   = BM25(chunks)
                bm25_raw   = bm25_obj.scores(rerank_query)

                sem_norm  = normalize(sem_scores)
                bm25_norm = normalize(bm25_raw)
                hybrid    = [0.6 * s + 0.4 * b for s, b in zip(sem_norm, bm25_norm)]

                top_k = 8
                dense_rank  = sorted(range(len(sem_scores)),  key=lambda i: -sem_scores[i])[:top_k]
                hybrid_rank = sorted(range(len(hybrid)),      key=lambda i: -hybrid[i])[:top_k]

                rerank_rows = []
                for new_pos, idx in enumerate(hybrid_rank[:5]):
                    old_pos = dense_rank.index(idx) if idx in dense_rank else top_k
                    rerank_rows.append({
                        "rank_dense"  : old_pos + 1,
                        "rank_hybrid" : new_pos + 1,
                        "delta"       : old_pos - new_pos,
                        "sem_score"   : round(sem_scores[idx], 4),
                        "bm25_score"  : round(bm25_raw[idx], 4),
                        "hybrid_score": round(hybrid[idx], 4),
                        "chunk_preview": chunks[idx][:200] + "…",
                    })

                st.session_state.rerank_results = rerank_rows
                st.session_state.rerank_all = {
                    "dense_top5" : [chunks[i][:180] for i in dense_rank[:5]],
                    "dense_scores": [round(sem_scores[i], 4) for i in dense_rank[:5]],
                    "hybrid_top5": [chunks[i][:180] for i in hybrid_rank[:5]],
                    "hybrid_scores": [round(hybrid[i], 4) for i in hybrid_rank[:5]],
                }
                st.session_state.rerank_error = None
            except Exception as e:
                st.session_state.rerank_results = None
                st.session_state.rerank_error   = str(e)

    st.success(f"✅ Analysis complete for **{ticker_input}**")


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — VALUATION REPORT
# ════════════════════════════════════════════════════════════════════════════
with tab_val:
    if not st.session_state.last_ticker:
        st.info("👈 Enter a ticker in the sidebar and click **Run Full Analysis**.")
    else:
        prof  = st.session_state.profile
        ticker = st.session_state.last_ticker

        st.subheader(f"WACC Intrinsic Valuation — {ticker}")

        # Key metrics row
        if prof:
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            price    = prof.get("price")
            mktcap   = prof.get("marketCap")
            dcf      = prof.get("dcf")
            dcfdiff  = prof.get("dcfDiff")
            beta_v   = prof.get("beta")
            div      = prof.get("lastDividend")

            def mcard(col, label, value, delta=None):
                col.metric(label, value, delta)

            mcard(c1, "Price",          f"${float(price):.2f}" if price else "N/A")
            mcard(c2, "Market Cap",     f"${float(mktcap)/1e9:.1f}B" if mktcap else "N/A")
            mcard(c3, "FMP DCF Value",  f"${float(dcf):.2f}" if dcf else "N/A",
                  delta=f"{float(dcfdiff):+.1f}%" if dcfdiff is not None else None)
            mcard(c4, "Beta",           f"{float(beta_v):.3f}" if beta_v else "N/A")
            mcard(c5, "Last Dividend",  f"${float(div):.2f}" if div else "N/A")
            mcard(c6, "Sector",         prof.get("sector", "N/A"))

            st.divider()

            col_left, col_right = st.columns([1, 1])
            with col_left:
                st.markdown("**Company Details**")
                details = {
                    "CEO"        : prof.get("ceo", "N/A"),
                    "Employees"  : f"{int(prof.get('fullTimeEmployees', 0)):,}" if prof.get("fullTimeEmployees") else "N/A",
                    "Industry"   : prof.get("industry", "N/A"),
                    "Exchange"   : prof.get("exchange") or prof.get("exchangeFullName", "N/A"),
                    "Country"    : prof.get("country", "N/A"),
                    "IPO Date"   : prof.get("ipoDate", "N/A"),
                    "Website"    : prof.get("website", "N/A"),
                }
                for k, v in details.items():
                    st.markdown(f"- **{k}:** {v}")

            with col_right:
                st.markdown("**Business Description**")
                desc = prof.get("description", "No description available.")
                st.markdown(f'<div style="font-size:0.88rem;color:#cdd5e0;line-height:1.6">{desc[:800]}{"…" if len(desc) > 800 else ""}</div>', unsafe_allow_html=True)

        st.divider()

        # Valuation PDF / response
        if st.session_state.val_error:
            st.error(f"Valuation workflow error: {st.session_state.val_error}")
            st.info("Make sure the WACC-Based workflow (ID: 94LnAeM8PpFn4Xob) is **active** in n8n.")
        elif st.session_state.val_pdf:
            st.success(f"✅ Valuation PDF received in {st.session_state.get('val_ms', '?')}ms")
            st.download_button(
                label="📥 Download Full Valuation Report (PDF)",
                data=st.session_state.val_pdf,
                file_name=f"{ticker}_valuation_report.pdf",
                mime="application/pdf",
                type="primary",
            )
        elif hasattr(st.session_state, "val_raw") and st.session_state.val_raw:
            st.success(f"✅ Valuation workflow responded in {st.session_state.get('val_ms', '?')}ms")
            try:
                import json as _json
                val_data = _json.loads(st.session_state.val_raw)
                pdf_url  = val_data.get("pdfUrl") or val_data.get("pdf_url") or val_data.get("url")
                if pdf_url:
                    st.markdown(
                        f"""
                        <div style="background:rgba(0,204,150,0.07);border:1px solid rgba(0,204,150,0.3);
                                    border-radius:10px;padding:1.2rem 1.5rem;margin-top:0.5rem;display:flex;
                                    align-items:center;gap:1rem">
                          <span style="font-size:1.6rem">📄</span>
                          <div>
                            <div style="color:#6b7a99;font-size:0.72rem;text-transform:uppercase;
                                        letter-spacing:0.08em;margin-bottom:4px">Valuation Report</div>
                            <a href="{pdf_url}" target="_blank"
                               style="color:#00CC96;font-weight:600;font-size:1rem;text-decoration:none;
                                      letter-spacing:0.01em">
                              📥 Open Full Valuation Report (PDF) ↗
                            </a>
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    # Show remaining fields as a clean table
                    other = {k: v for k, v in val_data.items() if k not in ("pdfUrl", "pdf_url", "url")}
                    if other:
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.dataframe(
                            pd.DataFrame(list(other.items()), columns=["Field", "Value"]),
                            use_container_width=True,
                            hide_index=True,
                        )
                else:
                    st.code(st.session_state.val_raw, language="json")
            except Exception:
                st.code(st.session_state.val_raw, language="json")
        else:
            st.info("Run the analysis to fetch the valuation report.")

        # DCF signal chart
        if prof and prof.get("dcf") and prof.get("price") and st.session_state.last_ticker:
            try:
                dcf_val   = float(prof["dcf"])
                mkt_price = float(prof["price"])
                margin    = (dcf_val - mkt_price) / mkt_price * 100

                fig = go.Figure(go.Bar(
                    x=["Market Price", "FMP DCF Intrinsic Value"],
                    y=[mkt_price, dcf_val],
                    marker_color=["#636EFA", "#00CC96" if dcf_val > mkt_price else "#EF553B"],
                    text=[f"${mkt_price:.2f}", f"${dcf_val:.2f}"],
                    textposition="outside",
                ))
                fig.update_layout(
                    title=f"{ticker} — Market Price vs DCF Intrinsic Value",
                    yaxis_title="USD ($)",
                    plot_bgcolor="#0e1117",
                    paper_bgcolor="#0e1117",
                    font_color="#fafafa",
                    height=350,
                )
                st.plotly_chart(fig, use_container_width=True)
                signal = "🟢 Undervalued" if margin > 0 else "🔴 Overvalued"
                st.markdown(f"**DCF Signal:** {signal} by {abs(margin):.1f}% relative to market price")
            except Exception:
                pass


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — RAG Q&A
# ════════════════════════════════════════════════════════════════════════════
with tab_rag:
    if not st.session_state.last_ticker:
        st.info("👈 Enter a ticker in the sidebar and click **Run Full Analysis**.")
    else:
        ticker = st.session_state.last_ticker
        st.subheader(f"RAG Q&A — {ticker}")

        # Ingest status
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.ingest_ok:
                idata = st.session_state.get("ingest_data", {})
                st.success(
                    f"✅ Documents indexed in {st.session_state.get('ingest_ms', '?')}ms  \n"
                    f"Vector store key: `{idata.get('memoryKey', f'financial_rag_{ticker}')}`  \n"
                    f"Embedding model: `{idata.get('embeddingModel', 'text-embedding-3-small')}`  \n"
                    f"Chunking: `{idata.get('chunking', 'recursive_512_50')}`"
                )
            else:
                st.error(f"Ingest failed: {st.session_state.get('ingest_error', 'Unknown error')}")
                st.info("Ensure the RAG workflow (ID: NZcW470MuDrUKjMH) is **active** in n8n.")

        with col2:
            if st.session_state.rag_answer:
                st.success(f"✅ Answer generated in {st.session_state.get('query_ms', '?')}ms  \n"
                           f"Model: `{st.session_state.rag_answer.get('model', 'gpt-4o')}`")
            elif st.session_state.get("rag_error"):
                st.error(f"Query failed: {st.session_state.rag_error}")

        st.divider()

        # Answer display
        if st.session_state.rag_answer:
            ans = st.session_state.rag_answer
            st.markdown(f"**❓ Question:** {ans.get('question', question)}")
            st.markdown("**💬 Answer:**")
            st.markdown(
                f'<div style="background:#1e2130;border-left:3px solid #636EFA;padding:1rem 1.2rem;'
                f'border-radius:6px;color:#cdd5e0;line-height:1.7;font-size:0.92rem">'
                f'{ans.get("answer","").replace(chr(10),"<br>")}</div>',
                unsafe_allow_html=True,
            )
            st.divider()

            # RAG pipeline metadata
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Retrieval Source",  ans.get("retrievalSource", f"financial_rag_{ticker}"))
            c2.metric("Generation Model",  ans.get("model", "gpt-4o"))
            c3.metric("Embedding Model",   ans.get("embeddingModel", "text-embedding-3-small"))
            c4.metric("Latency",           f"{st.session_state.get('query_ms', '?')} ms")

        # Show doc preview
        if st.session_state.doc_text:
            with st.expander("📄 View indexed document (first 2000 chars)"):
                st.code(st.session_state.doc_text[:2000], language="markdown")

        # Quick re-query without re-ingesting
        st.divider()
        st.markdown("**Ask another question** (uses already-indexed docs):")
        col_q, col_btn = st.columns([5, 1])
        with col_q:
            quick_q = st.text_input("Question", placeholder="Type a financial question…", label_visibility="collapsed")
        with col_btn:
            ask_btn = st.button("Ask", type="secondary")

        if ask_btn and quick_q.strip() and st.session_state.ingest_ok:
            with st.spinner("Querying RAG agent…"):
                try:
                    t0 = time.time()
                    r  = requests.post(
                        f"{N8N_BASE}/rag-query",
                        json={"ticker": ticker, "question": quick_q.strip()},
                        timeout=TIMEOUT,
                    )
                    ms = int((time.time() - t0) * 1000)
                    if r.status_code == 200:
                        try:
                            data = r.json() if r.text.strip() else None
                        except Exception:
                            data = None
                        if data:
                            st.markdown(f"**❓ {quick_q}**")
                            st.markdown(
                                f'<div style="background:#1e2130;border-left:3px solid #00CC96;padding:1rem 1.2rem;'
                                f'border-radius:6px;color:#cdd5e0;line-height:1.7;font-size:0.92rem">'
                                f'{data.get("answer","").replace(chr(10),"<br>")}</div>',
                                unsafe_allow_html=True,
                            )
                            st.caption(f"Answered in {ms}ms · model: gpt-4o")
                        else:
                            st.error("RAG workflow returned an empty response. Check the n8n workflow is active.")
                    else:
                        st.error(f"HTTP {r.status_code}: {r.text[:300]}")
                except Exception as e:
                    st.error(str(e))


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — CHUNKING STRATEGY COMPARISON
# ════════════════════════════════════════════════════════════════════════════
with tab_chunk:
    if not st.session_state.last_ticker:
        st.info("👈 Enter a ticker in the sidebar and click **Run Full Analysis**.")
    elif not openai_key:
        st.warning("⚠️ Enter your **OpenAI API Key** in the sidebar to enable local chunking analysis.")
    elif st.session_state.get("chunk_error"):
        st.error(f"Chunking analysis failed: {st.session_state.chunk_error}")
    elif not st.session_state.chunk_results:
        st.info("Click **Run Full Analysis** to generate chunking comparison.")
    else:
        results = st.session_state.chunk_results
        ticker  = st.session_state.last_ticker

        st.subheader("Chunking Strategy Comparison")
        st.caption(
            f"Evaluating 3 strategies on the {ticker} financial document against the query: "
            f'*"{question[:80]}…"*'
        )

        # ── Summary table ────────────────────────────────────────────────
        df = pd.DataFrame([{
            "Strategy"       : r["strategy"],
            "Chunk Size"     : r["chunk_size"],
            "Overlap"        : r["overlap"],
            "# Chunks"       : r["num_chunks"],
            "Avg Length (chars)": r["avg_chunk_len"],
            "Top-1 Score"    : r["top1_score"],
            "Top-3 Avg Score": r["top3_avg_score"],
        } for r in results])

        st.dataframe(
            df.style.highlight_max(subset=["Top-1 Score", "Top-3 Avg Score"], color="#1a3a2a"),
            use_container_width=True,
            hide_index=True,
        )

        # ── Bar chart: retrieval scores ──────────────────────────────────
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Top-1 Score",
            x=[r["strategy"] for r in results],
            y=[r["top1_score"] for r in results],
            marker_color=[r["color"] for r in results],
            text=[f'{r["top1_score"]:.4f}' for r in results],
            textposition="outside",
        ))
        fig.add_trace(go.Bar(
            name="Top-3 Avg Score",
            x=[r["strategy"] for r in results],
            y=[r["top3_avg_score"] for r in results],
            marker_color=[r["color"] for r in results],
            opacity=0.5,
            text=[f'{r["top3_avg_score"]:.4f}' for r in results],
            textposition="outside",
        ))
        fig.update_layout(
            title="Semantic Similarity Score by Chunking Strategy",
            yaxis_title="Cosine Similarity (text-embedding-3-small)",
            barmode="group",
            plot_bgcolor="#0e1117",
            paper_bgcolor="#0e1117",
            font_color="#fafafa",
            height=380,
            legend=dict(bgcolor="#1e2130"),
        )
        st.plotly_chart(fig, use_container_width=True)

        # ── Chunk count comparison ───────────────────────────────────────
        fig2 = go.Figure(go.Bar(
            x=[r["strategy"] for r in results],
            y=[r["num_chunks"] for r in results],
            marker_color=[r["color"] for r in results],
            text=[r["num_chunks"] for r in results],
            textposition="outside",
        ))
        fig2.update_layout(
            title="Number of Chunks Produced by Each Strategy",
            yaxis_title="Chunk Count",
            plot_bgcolor="#0e1117",
            paper_bgcolor="#0e1117",
            font_color="#fafafa",
            height=300,
        )
        st.plotly_chart(fig2, use_container_width=True)

        st.divider()

        # ── Per-strategy top chunks ──────────────────────────────────────
        st.markdown("### Top Retrieved Chunks per Strategy")
        tabs_strat = st.tabs([r["strategy"] for r in results])
        for tab, r in zip(tabs_strat, results):
            with tab:
                st.caption(
                    f"Chunk size: {r['chunk_size']} | Overlap: {r['overlap']} | "
                    f"Total chunks: {r['num_chunks']} | Avg length: {r['avg_chunk_len']} chars"
                )
                for rank, (chunk, score) in enumerate(zip(r["top_chunks"], r["top_scores"]), 1):
                    st.markdown(
                        f'<div class="chunk-card">'
                        f'<strong>Rank {rank}</strong> — Score: <strong>{score}</strong><br><br>'
                        f'{chunk}</div>',
                        unsafe_allow_html=True,
                    )

        # ── Recommendation ───────────────────────────────────────────────
        st.divider()
        best = max(results, key=lambda r: r["top3_avg_score"])
        st.markdown("### 📋 Chunking Strategy Recommendation")
        st.info(
            f"**Recommended strategy: {best['strategy']}** "
            f"(chunk_size={best['chunk_size']}, overlap={best['overlap']})  \n"
            f"Achieves the highest Top-3 average cosine similarity ({best['top3_avg_score']}) "
            f"for this query and document.  \n\n"
            f"The n8n workflow uses **Balanced 512/50** — a strong default that trades "
            f"granularity for sufficient context per chunk. For financial documents "
            f"with multi-sentence descriptions and risk disclosures, 512-char chunks "
            f"preserve enough semantic coherence for reliable retrieval."
        )


# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — RERANKING IMPACT ANALYSIS
# ════════════════════════════════════════════════════════════════════════════
with tab_rerank:
    if not st.session_state.last_ticker:
        st.info("👈 Enter a ticker in the sidebar and click **Run Full Analysis**.")
    elif not openai_key:
        st.warning("⚠️ Enter your **OpenAI API Key** in the sidebar to enable reranking analysis.")
    elif st.session_state.get("rerank_error"):
        st.error(f"Reranking analysis failed: {st.session_state.rerank_error}")
    elif not st.session_state.rerank_results:
        st.info("Click **Run Full Analysis** to generate reranking analysis.")
    else:
        rows   = st.session_state.rerank_results
        rall   = st.session_state.rerank_all
        ticker = st.session_state.last_ticker

        st.subheader("Reranking Impact Analysis")
        st.caption(
            f"Query: *\"{rerank_query}\"*  \n"
            "Comparing **Dense Retrieval only** vs **Hybrid BM25 + Semantic Reranking** "
            "(weights: 0.6 semantic · 0.4 BM25)"
        )

        # ── Side-by-side top-5 ───────────────────────────────────────────
        col_dense, col_hybrid = st.columns(2)

        with col_dense:
            st.markdown("#### 🔵 Dense Retrieval (semantic only)")
            for i, (chunk, score) in enumerate(zip(rall["dense_top5"], rall["dense_scores"]), 1):
                st.markdown(
                    f'<div class="chunk-card">'
                    f'<strong>#{i}</strong> · Score: {score}<br><br>'
                    f'{chunk}…</div>',
                    unsafe_allow_html=True,
                )

        with col_hybrid:
            st.markdown("#### 🟢 Hybrid Reranked (BM25 + semantic)")
            for i, (chunk, score) in enumerate(zip(rall["hybrid_top5"], rall["hybrid_scores"]), 1):
                st.markdown(
                    f'<div class="chunk-card" style="border-left-color:#00CC96">'
                    f'<strong>#{i}</strong> · Score: {score}<br><br>'
                    f'{chunk}…</div>',
                    unsafe_allow_html=True,
                )

        st.divider()

        # ── Rank change table ────────────────────────────────────────────
        st.markdown("### Rank Change Summary (Top 5 after reranking)")

        rank_df = pd.DataFrame([{
            "Dense Rank"  : r["rank_dense"],
            "Hybrid Rank" : r["rank_hybrid"],
            "Δ Rank"      : r["delta"],
            "Sem Score"   : r["sem_score"],
            "BM25 Score"  : r["bm25_score"],
            "Hybrid Score": r["hybrid_score"],
            "Chunk Preview": r["chunk_preview"],
        } for r in rows])

        st.dataframe(
            rank_df.style.map(
                lambda v: "color: #00CC96; font-weight:bold" if isinstance(v, (int, float)) and v > 0
                else ("color: #EF553B" if isinstance(v, (int, float)) and v < 0 else ""),
                subset=["Δ Rank"]
            ),
            use_container_width=True,
            hide_index=True,
        )

        # ── Score comparison chart ───────────────────────────────────────
        fig = go.Figure()
        labels = [f"#{r['rank_hybrid']}" for r in rows]
        fig.add_trace(go.Bar(name="Semantic Score",  x=labels, y=[r["sem_score"]   for r in rows], marker_color="#636EFA"))
        fig.add_trace(go.Bar(name="BM25 Score",      x=labels, y=[r["bm25_score"]  for r in rows], marker_color="#FFA15A"))
        fig.add_trace(go.Bar(name="Hybrid Score",    x=labels, y=[r["hybrid_score"] for r in rows], marker_color="#00CC96"))
        fig.update_layout(
            title="Score Components for Top-5 Hybrid-Reranked Chunks",
            yaxis_title="Score (normalized for hybrid)",
            barmode="group",
            plot_bgcolor="#0e1117",
            paper_bgcolor="#0e1117",
            font_color="#fafafa",
            height=380,
            legend=dict(bgcolor="#1e2130"),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.divider()
        st.markdown("### 📋 Reranking Methodology")
        st.markdown("""
**Stage 1 — Dense Retrieval:**
All chunks embedded with `text-embedding-3-small`. Query embedded identically.
Cosine similarity ranks candidates purely by semantic closeness.

**Stage 2 — BM25 Keyword Scoring:**
Each chunk scored with Okapi BM25 (k₁=1.5, b=0.75) for the same query.
Captures exact keyword matches that semantic search may miss (e.g. proper nouns, ticker symbols).

**Hybrid Reranking Formula:**
`hybrid_score = 0.6 × norm(semantic) + 0.4 × norm(BM25)`
Both scores min-max normalized before combining.

**Why hybrid beats dense-only for financial docs:**
Financial text contains specific terminology (e.g. "WACC", "beta", "10-K") where
BM25 exact-match significantly boosts precision for keyword-heavy queries.
        """)


# ── FOOTER ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Financial RAG Intelligence Pipeline · Gen Academy Week 2 Project  \n"
    "n8n workflows: RAG [NZcW470MuDrUKjMH] · Valuation [94LnAeM8PpFn4Xob]  \n"
    "Data: Financial Modeling Prep API · SEC EDGAR · OpenAI · GPT-4o"
)
