---
name: compliance-review-style
description: How to write a compliance/risk review of a trade ticket against the portfolio's hard risk rules — PASS/FAIL with specific citations.
---

# Compliance Review Style

## When to use
When reviewing a drafted trade ticket against the trading playbook's hard "never" rules
and position-sizing limits.

## Structure
1. **Verdict line first**: `PASS` or `FAIL` (or `FAIL — escalate` for ambiguous cases),
   in the very first line.
2. **Rule-by-rule check**: walk each applicable rule (single-trade risk cap, portfolio
   heat cap, same-sector limit, minimum R:R, stop present) and mark it ✓ or ✗ with the
   actual number next to the limit (e.g. "Single-trade risk: 1.5% ✓ (cap 2.0%)").
3. **Issues**: a bullet list of anything that failed, with the specific fix needed.
4. **Sign-off note**: one sentence on whether this ticket is ready for human approval
   as-is, or needs to be re-sized/re-drafted first.

## Voice
Blunt and citation-heavy. Every claim about pass/fail must point to a specific number
from the ticket and a specific rule from the trading playbook — no vague "looks fine."

## Rules
- Never soften a FAIL into a PASS because the trade idea is otherwise compelling.
- Never approve a ticket missing a stop price, regardless of conviction.
- If portfolio heat would exceed 6% including this trade, this is an automatic FAIL.
- Keep the review under ~150 words.
