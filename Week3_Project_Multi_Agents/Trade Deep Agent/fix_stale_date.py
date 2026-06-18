import nbformat

PATH = "trade_deep_agent.ipynb"
nb = nbformat.read(PATH, as_version=4)

# --- cell 7: load grounding files AND compute today's real date --------------------
old7 = '''GROUNDING = Path("grounding/trading_playbook.md").read_text()
STRATEGY_RULES = Path("grounding/trading_strategy_dashboard.md").read_text()
print(GROUNDING)
print("\\n" + "=" * 70 + "\\n")
print(STRATEGY_RULES)'''
new7 = '''from datetime import date

GROUNDING = Path("grounding/trading_playbook.md").read_text()
STRATEGY_RULES = Path("grounding/trading_strategy_dashboard.md").read_text()

# The playbook's macro snapshot is dated May 31, 2026 and will only get staler. The
# market-analyst subagent needs to know what day it actually is *right now* so it can
# tell a live search result apart from that fixed snapshot, and label its brief
# correctly instead of defaulting to the snapshot's date out of habit.
TODAY = date.today().strftime("%B %d, %Y")

print(GROUNDING)
print("\\n" + "=" * 70 + "\\n")
print(STRATEGY_RULES)
print(f"\\n--> TODAY (used to date-stamp the market-analyst's brief): {TODAY}")'''
assert old7 in nb.cells[7].source
nb.cells[7].source = nb.cells[7].source.replace(old7, new7)
nb.cells[7].outputs = []
nb.cells[7].execution_count = None

# --- cell 19: market-analyst prompt now uses TODAY, not the snapshot's date --------
src19 = nb.cells[19].source
old_block = '''    "system_prompt": f"""You research one futures contract for a proposed trade idea.
Your job is to read the CURRENT market trend, not just repeat old grounding facts.

1. If web_search is available, search for the contract's current price action, recent
   news, and macro catalysts (e.g. "{{contract}} futures technical outlook this week").
   Use it — this is how you get a trend read that is actually current, not the May 31
   snapshot below.
2. If web_search is unavailable, fall back to the grounding snapshot below, but say so
   explicitly in your brief (e.g. "no live search — using May 31 snapshot only") so
   downstream reviewers know how fresh this read is.

Trading playbook grounding (hard risk rules + last known macro snapshot — never invent
facts beyond this + whatever you find live):
{GROUNDING}

Write 5-8 crisp bullet points on the technical setup, macro backdrop, how current your
information is (live search vs. snapshot-only), and your conviction call (HIGH or
MEDIUM) to /research/market_brief.md, then return a one-line summary including the
conviction call.""",'''

new_block = '''    "system_prompt": f"""You research one futures contract for a proposed trade idea.
Today's actual date is {TODAY}. Your job is to read the CURRENT market trend, not just
repeat old grounding facts — and to be honest about which one you actually used.

1. If web_search is available, search for the contract's current price action, recent
   news, and macro catalysts (e.g. "{{contract}} futures technical outlook this week").
   Use it — this is how you get a trend read that is actually current, not the stale
   May 31, 2026 snapshot below. Whatever date your search results imply (today, or the
   article/publish date), use THAT date — never write "May 31, 2026" in your brief
   unless you are explicitly using the fallback snapshot and saying so.
2. If web_search is unavailable, fall back to the grounding snapshot below, and say so
   explicitly and unambiguously in your brief, e.g. "NO LIVE SEARCH — using the stale
   May 31, 2026 snapshot only; today is {TODAY}", so downstream reviewers know exactly
   how stale this read is.

Trading playbook grounding (hard risk rules + last known macro snapshot — never invent
facts beyond this + whatever you find live):
{GROUNDING}

Title your brief's header with the actual date of the information you used (today,
{TODAY}, for live search; or "May 31, 2026 snapshot" if you had no live search — never
both, never an unlabeled date). Write 5-8 crisp bullet points on the technical setup,
macro backdrop, how current your information is (live search vs. snapshot-only), and
your conviction call (HIGH or MEDIUM) to /research/market_brief.md, then return a
one-line summary including the conviction call and which date/source you used.""",'''

assert old_block in src19, "market-analyst prompt block not found"
nb.cells[19].source = src19.replace(old_block, new_block)
nb.cells[19].outputs = []
nb.cells[19].execution_count = None

nbformat.validate(nb)
nbformat.write(nb, PATH)
print("done")
