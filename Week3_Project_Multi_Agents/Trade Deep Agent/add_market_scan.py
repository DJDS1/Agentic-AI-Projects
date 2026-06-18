import nbformat

PATH = "trade_deep_agent.ipynb"
nb = nbformat.read(PATH, as_version=4)

# --- cell 23: markdown header for "Run a trade idea" section ---------------------
nb.cells[23].source = '''## 8. Run a trade idea

Before you type in a setup, we run a quick **market scan** across the watchlist (ES,
NQ, GC, CL, NG): the market-analyst subagent gives each one a CURRENT read (live search
when Tavily is enabled) and proposes a candidate setup that honors the strategy
dashboard's entry rules — or says no setup qualifies right now. These scans are
single-subagent, throwaway-thread calls; they never touch `/research`, `/drafts`, etc.
used by the real review pipeline below.

Then **you** pick the contract and enter the setup (symbol/entry/stop/target) you want
the full pipeline to research, size, and review. Watch the message stream on the real
run: you'll see the orchestrator's `task` calls and each subagent's **final report** —
but *not* the subagents' internal back-and-forth. That hidden churn is the
context-isolation benefit.

`recursion_limit` caps the agent loop — the hard backstop against runaway loops.'''

# --- cell 25: scan + interactive trade-idea entry ----------------------------------
nb.cells[25].source = '''# Clear scratch artifacts from any previous run so the demo starts clean.
# write_file refuses to overwrite an existing file (by design — it forces an
# explicit edit_file instead of silent clobbering), so stale /research, /drafts,
# /review, /final files from a prior run cause the orchestrator to burn steps on
# failed writes/edits and retries under new filenames — easily exhausting
# recursion_limit before the pipeline finishes. /memories/ is left alone since
# that's the intentional cross-session store.
import shutil
from langgraph.errors import GraphRecursionError

for d in ["research", "drafts", "review", "final"]:
    p = Path(d)
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True, exist_ok=True)

config = {"configurable": {"thread_id": "trade-demo-1"}, "recursion_limit": 60}

# --- Market scan: ask market-analyst for ONE candidate setup on each watched
# contract, grounded in the CURRENT market trend (web_search, when Tavily is
# enabled) plus the strategy dashboard's entry rules. Each scan runs on its own
# throwaway thread with a tight recursion limit so it never touches /research,
# /drafts, /review, /final used by the real review pipeline below.
WATCHLIST = ["ES", "NQ", "GC", "CL", "NG"]

def scan_contract(symbol: str) -> str:
    scan_config = {"configurable": {"thread_id": f"scan-{symbol}"}, "recursion_limit": 20}
    prompt = (
        "OVERRIDE — for this message only, skip your standing 7-step workflow. "
        f"ONLY delegate to 'market-analyst' to get a CURRENT read on {symbol} futures. "
        "Do not delegate to risk-sizer, compliance-checker, or trade-critic, and do not "
        "call execute_trade. Based on the market-analyst's brief and the strategy "
        "dashboard's entry rules (timeframe confirmation, MACD direction, RSI bounds, "
        "volume, no setups within 30 min of a major release), propose ONE candidate "
        "setup as a single line in exactly this format:\\n"
        f"{symbol} | LONG-or-SHORT | entry=X | stop=X | target=X | HIGH-or-MEDIUM | "
        "one-line why\\n"
        "If nothing qualifies right now, reply with exactly:\\n"
        f"{symbol} | NO QUALIFYING SETUP | one-line why"
    )
    try:
        res = agent.invoke({"messages": [{"role": "user", "content": prompt}]}, config=scan_config)
        return res["messages"][-1].content
    except GraphRecursionError:
        return f"{symbol} | SCAN INCOMPLETE — recursion limit hit, size this one manually."

print("=" * 70)
print("MARKET SCAN — candidate setups across the watchlist")
print("=" * 70)
for sym in WATCHLIST:
    idea = scan_contract(sym)
    print(f"\\n[{sym}]")
    print(idea)
print("\\n" + "=" * 70)

# Enter the trade idea by hand, using the scan above as a guide. Press Enter on
# Symbol to fall back to the built-in NG example instead of typing all four.
DEFAULT_SYMBOL, DEFAULT_ENTRY, DEFAULT_STOP, DEFAULT_TARGET = "NG", 3.30, 3.18, 3.66

symbol = input(f"Symbol (e.g. ES, NQ, GC, CL, NG) [{DEFAULT_SYMBOL}]: ").strip().upper() or DEFAULT_SYMBOL

def _ask_price(label, default):
    raw = input(f"{label} [{default}]: ").strip()
    return float(raw) if raw else default

entry = _ask_price("Entry", DEFAULT_ENTRY)
stop = _ask_price("Stop", DEFAULT_STOP)
target = _ask_price("Target", DEFAULT_TARGET)

direction = "LONG" if target > entry else "SHORT"

trade_idea = (
    f"Trade idea: {direction} {symbol}, entry {entry}, stop {stop}, target {target}. "
    "Evaluate the current macro/technical backdrop from grounding and/or research, and "
    "decide HIGH or MEDIUM conviction yourself based on the setup."
)
print(f"\\n--> Trade idea: {trade_idea}")

result = agent.invoke({"messages": [{"role": "user", "content": trade_idea}]}, config=config)
#try streaming the output to see how the agent is executing

for m in result["messages"]:
    m.pretty_print()
'''
nb.cells[25].outputs = []
nb.cells[25].execution_count = None

nbformat.validate(nb)
nbformat.write(nb, PATH)
print("done")
