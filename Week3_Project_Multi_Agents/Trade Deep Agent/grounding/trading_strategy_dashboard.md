# Grounding: Trading Strategy — Financial Portfolio Intelligence System Dashboard

> Source: `Financial Portfolio Intelligence System Dashboard.html` (Futures Portfolio
> Dashboard — YTD 2026), the "🎯 Trading Plan" tab. This is the detailed rulebook behind
> the high-level risk caps in `trading_playbook.md` — the trade-critic subagent validates
> every reviewed trade against these specific rules before it is marked READY FOR HUMAN
> REVIEW. The agent must never invent strategy rules beyond this file + the playbook.

## Strategy objective
Generate **>20% annual ROI** on the $100,000 futures portfolio trading ES, NQ, YM, GC,
SI, CL, NG, ZB, ZN, ZF. Risk 1-2% per trade. Minimum 2:1 R:R. Trade only HIGH and MEDIUM
conviction setups confirmed on at least 2 of 3 timeframes. (YTD stress test: 32.5% win
rate still produced +78.3% ROI on a 2.73:1 actual R:R — the strategy is built to survive
a low win rate, not to chase one.)

## Trade entry rules (all must hold before a trade is sized)
1. Confirm on Daily + Weekly timeframe before entry.
2. Wait for a pullback to support — never chase an all-time high.
3. MACD must be trending in the trade's direction on the Daily.
4. RSI must not be overbought (>75) for longs, or oversold (<25) for shorts.
5. Volume must be above the 20-period average on the entry candle.
6. No trades within 30 minutes of a major economic release.
7. Max 3 concurrent open positions across all contracts.

## Stop loss & exit rules
1. A hard stop is always set at order entry — no mental stops.
2. Move the stop to break-even once the trade reaches 1:1 R:R.
3. Take 50% off at the 2:1 target; trail the remainder with ATR.
4. Full exit if price closes against the trade on the Daily.
5. Time-based exit: close any trade open more than 5 days.
6. Daily loss limit: if down 3% for the day, stop trading for the day.
7. Weekly loss limit: if down 5% for the week, review before trading again.

## Position sizing rules
- HIGH conviction: 1.5-2% risk ($1,500-$2,000 on a $100K account).
- MEDIUM conviction: 1% risk ($1,000).
- LOW conviction: avoid entirely if possible.
- After 3 consecutive losses: halve size for the next 5 trades.
- Max total risk across all open positions: 5% of portfolio (note: tighter than the 6%
  portfolio-heat cap in `trading_playbook.md` — when the two differ, use the **stricter**
  number).

## Strategy review triggers (flag, don't block, unless asked)
- Win rate drops below 25% over a rolling 30-trade window.
- Drawdown exceeds 10% from the portfolio peak.
- Monthly ROI is below 0% for 2 consecutive months.
- Any contract is graded D for 2 consecutive months → pause trading it.
- Profit factor drops below 1.2 over a rolling 50-trade window.

## Contract performance scorecard (YTD 2026 — use the grade/action as a live input)
| Contract | Sector | Win rate | Net P&L | Grade | Action |
|---|---|---|---|---|---|
| ES | Equity | 37.5% | +$26,684 | B | Keep trading |
| NG | Energy | 52.9% | +$23,021 | A | Keep trading |
| CL | Energy | 36.4% | +$17,523 | B | Keep trading |
| ZB | Bonds | 30.8% | +$10,790 | B | Keep trading |
| GC | Metals | 30.4% | +$5,402 | B | Keep trading |
| ZN | Bonds | 100.0% | +$5,045 | A | Keep trading (small sample) |
| NQ | Equity | 25.0% | +$4,464 | C | Reduce size |
| SI | Metals | 12.5% | -$5,410 | D | Review / pause |
| YM | Equity | 17.6% | -$9,188 | D | Review / pause |

**Hard rule for the critic:** if the proposed contract is graded **D**, flag it as a
strategy-compliance issue even if it otherwise passes the playbook's hard risk rules —
recommend the human treat it as Review/Pause rather than an automatic green light. A
**C**-graded contract should be flagged to confirm size was reduced per the scorecard.

## Daily pre-market routine (context for why a "current market trend" read matters)
Review overnight gaps → check the economic calendar → run the pre-market report and
update the bias scorecard → identify the top 2-3 HIGH-conviction setups → set entry/stop/
target → no trades in the first 5 minutes after the open. The market-analyst subagent's
job mirrors the first three steps: get a *current* read on the contract, not a stale one.
