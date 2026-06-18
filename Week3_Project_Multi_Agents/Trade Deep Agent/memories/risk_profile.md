# Risk Profile — $100K Futures Portfolio

_Last updated: seed file, before first agent-run. The trade-review orchestrator overwrites
this note (step 6 of its workflow) after every reviewed trade, so future sessions can read
it back via `/memories/risk_profile.md` without re-deriving the rules from scratch._

**Account state:** $100,000 notional, no open positions yet recorded in memory. No flags
raised. Portfolio heat: 0% of the 6% cap.

**Standing risk rules this account trades under** (see `grounding/trading_playbook.md` for
full detail): risk 1.0% per MEDIUM-conviction trade, 1.5% per HIGH-conviction trade, never
exceed 2.0% on any single trade; cap total open risk ("portfolio heat") at 6% of portfolio
value; no more than 2 concurrent open positions in the same sector; minimum acceptable
reward:risk is 2.0:1 (target 2.0:1–3.5:1); every trade requires a hard stop and explicit
human approval before it is marked taken.

**Flags / lessons carried forward:** none yet — this is the first entry. Subsequent runs
should append a one-paragraph note here: which contract/sector was traded, the conviction
level and size used, any compliance issues hit (e.g. a FAIL that needed re-sizing), and
anything that should make the next review faster or stricter (e.g. "avoid stacking a third
equities position" or "NQ flagged for bearish divergence on 2026-05-31").
