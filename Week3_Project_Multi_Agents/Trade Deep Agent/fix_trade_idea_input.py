import nbformat

PATH = "trade_deep_agent.ipynb"

nb = nbformat.read(PATH, as_version=4)

new_code = '''# Clear scratch artifacts from any previous run so the demo starts clean.
# write_file refuses to overwrite an existing file (by design — it forces an
# explicit edit_file instead of silent clobbering), so stale /research, /drafts,
# /review, /final files from a prior run cause the orchestrator to burn steps on
# failed writes/edits and retries under new filenames — easily exhausting
# recursion_limit before the pipeline finishes. /memories/ is left alone since
# that's the intentional cross-session store.
import shutil
for d in ["research", "drafts", "review", "final"]:
    p = Path(d)
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True, exist_ok=True)

config = {"configurable": {"thread_id": "trade-demo-1"}, "recursion_limit": 60}

# Enter the trade idea by hand. Press Enter on Symbol to fall back to the
# built-in NG example instead of typing all four.
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

nb.cells[25].source = new_code
nb.cells[25].outputs = []
nb.cells[25].execution_count = None

nbformat.validate(nb)
nbformat.write(nb, PATH)
print("done")
