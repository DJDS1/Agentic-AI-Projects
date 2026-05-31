import json, random, math
from datetime import date, timedelta

random.seed(42)

# ── Trading days Jan 2 – May 29 2026 ─────────────────────────────────────────
def trading_days(start, end):
    days = []
    d = start
    while d <= end:
        if d.weekday() < 5:  # Mon-Fri
            # Skip US holidays (approx)
            holidays_2026 = {date(2026,1,1), date(2026,1,19), date(2026,2,16),
                             date(2026,4,3), date(2026,5,25)}
            if d not in holidays_2026:
                days.append(d)
        d += timedelta(days=1)
    return days

all_days = trading_days(date(2026,1,2), date(2026,5,29))

# ── Contract universe ─────────────────────────────────────────────────────────
contracts = {
    # contract: (sector, multiplier, tick_val, typical_risk_per_trade)
    "ES":  ("Equity",  50,    12.50, 1500),
    "NQ":  ("Equity",  20,    5.00,  1200),
    "YM":  ("Equity",  5,     5.00,  1000),
    "GC":  ("Metals",  100,   10.00, 1500),
    "SI":  ("Metals",  5000,  25.00, 1000),
    "CL":  ("Energy",  1000,  10.00, 1500),
    "NG":  ("Energy",  10000, 10.00, 1000),
    "ZB":  ("Bonds",   1000,  31.25, 1200),
    "ZN":  ("Bonds",   1000,  15.625,1000),
    "ZF":  ("Bonds",   1000,  7.8125,800),
}

# Monthly bias weights — which contracts are favored each month
# (contract, direction, weight) — reflects real market narrative Jan-May 2026
monthly_setup = {
    1: [("ES","LONG",3),("NQ","LONG",3),("YM","LONG",2),("GC","LONG",2),("CL","SHORT",2),("ZB","SHORT",2),("ZN","SHORT",1)],
    2: [("ES","LONG",2),("NQ","LONG",2),("GC","LONG",3),("CL","SHORT",2),("ZB","SHORT",2),("NG","LONG",2),("YM","LONG",1)],
    3: [("ES","SHORT",2),("NQ","SHORT",2),("GC","LONG",3),("CL","SHORT",2),("ZB","SHORT",2),("SI","LONG",2),("NG","SHORT",1)],
    4: [("ES","SHORT",3),("NQ","SHORT",3),("GC","LONG",2),("CL","SHORT",2),("ZB","LONG",2),("YM","SHORT",2),("NG","LONG",1)],
    5: [("ES","LONG",3),("NQ","LONG",3),("YM","LONG",2),("GC","NEUTRAL",1),("CL","SHORT",3),("ZB","SHORT",2),("NG","LONG",2)],
}

# ── 40% win rate with hot/cold streak simulation ──────────────────────────────
# We'll use a Markov chain: after win, slightly higher chance of next win (momentum)
# After loss, slightly lower. But overall baseline = 40%
def next_outcome(prev_wins, streak):
    # Base 40% win rate, slight streak bias
    base = 0.40
    if streak >= 3:   base = min(0.52, base + 0.04)  # hot streak
    elif streak <= -3: base = max(0.30, base - 0.04)  # cold streak
    return random.random() < base

# ── Generate trades ───────────────────────────────────────────────────────────
trades = []
portfolio = 100000.0
streak = 0
trade_id = 1

conviction_map = {"HIGH": 2.0, "MEDIUM": 1.5, "LOW": 1.0}

for day in all_days:
    month = day.month
    setups = monthly_setup[month]
    
    # 1-3 trades per day, weighted toward 2
    n_trades = random.choices([1, 2, 3], weights=[25, 50, 25])[0]
    
    # Pick contracts for the day (no duplicate contracts same day)
    day_contracts = []
    available = [s for s in setups if s[2] > 0 and s[1] != "NEUTRAL"]
    random.shuffle(available)
    
    pool = []
    for c, d, w in available:
        pool.extend([(c, d)] * w)
    random.shuffle(pool)
    
    seen = set()
    day_trades = []
    for c, d in pool:
        if c not in seen and len(day_trades) < n_trades:
            seen.add(c)
            day_trades.append((c, d))
    
    if not day_trades:
        day_trades = [("ES", "LONG")]
    
    for contract, direction in day_trades[:n_trades]:
        sector, mult, tick_val, base_risk = contracts[contract]
        
        # Conviction based on month + contract
        if month in [1, 5] and contract in ["ES", "NQ", "YM"]:
            conviction = "HIGH"
        elif month in [3, 4] and contract in ["ES", "NQ"]:
            conviction = "HIGH"
        elif contract in ["GC", "SI"]:
            conviction = "MEDIUM"
        else:
            conviction = random.choice(["HIGH", "MEDIUM", "MEDIUM"])
        
        # Risk sizing: 1% of portfolio for MEDIUM, 1.5% for HIGH
        risk_pct = 0.015 if conviction == "HIGH" else 0.010
        risk_amt = round(portfolio * risk_pct, 0)
        risk_amt = max(800, min(2500, risk_amt))  # cap between $800-$2500
        
        # R:R ratio: 2:1 to 3.5:1 range
        rr = round(random.uniform(2.0, 3.5), 1)
        
        # Outcome
        won = next_outcome(streak > 0, streak)
        streak = (streak + 1) if won else (streak - 1)
        
        if won:
            pnl = round(risk_amt * rr, 0)
            outcome = "WIN"
        else:
            # Occasional scratch (break-even)
            if random.random() < 0.08:
                pnl = round(random.uniform(-150, 50), 0)
                outcome = "BE"
                streak = 0
            else:
                pnl = -risk_amt
                outcome = "LOSS"
        
        portfolio += pnl
        roi_pct = ((portfolio - 100000) / 100000) * 100
        
        # Generate realistic-looking prices
        price_bases = {
            "ES": 5800, "NQ": 20500, "YM": 42000, "GC": 2650, "SI": 30,
            "CL": 72, "NG": 2.80, "ZB": 115, "ZN": 109, "ZF": 105
        }
        # Drift prices over time (bull market Jan-Feb, correction Mar-Apr, recovery May)
        day_offset = (day - date(2026,1,2)).days
        if day.month <= 2:
            drift = day_offset * 0.3
        elif day.month <= 4:
            drift = 40 - (day_offset - 40) * 0.4
        else:
            drift = 20 + (day_offset - 85) * 0.5
        
        base = price_bases[contract]
        entry = round(base + drift * (base/5800) + random.uniform(-base*0.002, base*0.002), 2)
        
        stop_dist = risk_amt / (mult * 0.1) if mult > 100 else risk_amt / mult
        if direction == "LONG":
            stop = round(entry - stop_dist, 2)
            target = round(entry + stop_dist * rr, 2)
        else:
            stop = round(entry + stop_dist, 2)
            target = round(entry - stop_dist * rr, 2)
        
        # Notes
        notes_map = {
            "WIN": ["Clean breakout entry", "Trend continuation", "Support held perfectly",
                    "MACD confirmation on entry", "Volume surge confirmed move"],
            "LOSS": ["Stop triggered on news spike", "False breakout", "Spread wider than expected",
                     "Reversal at resistance", "Gap through stop level"],
            "BE": ["Moved stop to break-even", "Exited early on reversal signal", "Managed to scratch"]
        }
        note = random.choice(notes_map[outcome])
        
        trades.append({
            "id": trade_id,
            "date": day.strftime("%Y-%m-%d"),
            "day_of_week": day.strftime("%a"),
            "month": day.strftime("%b %Y"),
            "contract": contract,
            "sector": sector,
            "direction": direction,
            "conviction": conviction,
            "entry": entry,
            "stop": stop,
            "target": target,
            "rr": rr,
            "risk_amt": risk_amt,
            "outcome": outcome,
            "pnl": pnl,
            "portfolio_value": round(portfolio, 2),
            "roi_pct": round(roi_pct, 2),
            "note": note
        })
        trade_id += 1

# ── Daily portfolio series ────────────────────────────────────────────────────
daily_portfolio = {}
for t in trades:
    daily_portfolio[t["date"]] = t["portfolio_value"]

# Forward fill for chart
portf_series = []
last_val = 100000
for d in all_days:
    ds = d.strftime("%Y-%m-%d")
    if ds in daily_portfolio:
        last_val = daily_portfolio[ds]
    portf_series.append({"date": ds, "value": last_val})

# ── Monthly stats ─────────────────────────────────────────────────────────────
from collections import defaultdict
monthly_stats = defaultdict(lambda: {"trades":0,"wins":0,"losses":0,"be":0,"pnl":0.0,"start_val":0,"end_val":0})
month_order = []
prev_month = None
month_start_val = 100000

for t in trades:
    m = t["month"]
    if m not in monthly_stats:
        monthly_stats[m]["start_val"] = month_start_val
        month_order.append(m)
    monthly_stats[m]["trades"] += 1
    monthly_stats[m]["pnl"] += t["pnl"]
    if t["outcome"] == "WIN":   monthly_stats[m]["wins"] += 1
    elif t["outcome"] == "LOSS":monthly_stats[m]["losses"] += 1
    else:                       monthly_stats[m]["be"] += 1
    monthly_stats[m]["end_val"] = t["portfolio_value"]
    if prev_month and prev_month != m:
        monthly_stats[m]["start_val"] = monthly_stats[prev_month]["end_val"]
    prev_month = m

# ── Contract performance ──────────────────────────────────────────────────────
contract_stats = defaultdict(lambda: {"trades":0,"wins":0,"losses":0,"be":0,"pnl":0.0,"total_risk":0.0,"total_reward":0.0})
for t in trades:
    c = t["contract"]
    contract_stats[c]["trades"] += 1
    contract_stats[c]["pnl"] += t["pnl"]
    contract_stats[c]["total_risk"] += t["risk_amt"]
    if t["outcome"] == "WIN":
        contract_stats[c]["wins"] += 1
        contract_stats[c]["total_reward"] += t["pnl"]
    elif t["outcome"] == "LOSS":
        contract_stats[c]["losses"] += 1

# ── Peak & drawdown series ────────────────────────────────────────────────────
peak = 100000
drawdown_series = []
for p in portf_series:
    peak = max(peak, p["value"])
    dd = ((p["value"] - peak) / peak) * 100
    drawdown_series.append(round(dd, 2))

# ── Summary stats ─────────────────────────────────────────────────────────────
total_trades = len(trades)
total_wins = sum(1 for t in trades if t["outcome"]=="WIN")
total_losses = sum(1 for t in trades if t["outcome"]=="LOSS")
total_be = sum(1 for t in trades if t["outcome"]=="BE")
win_rate = round(total_wins/total_trades*100, 1)
final_value = trades[-1]["portfolio_value"]
total_pnl = round(final_value - 100000, 2)
total_roi = round((final_value - 100000)/100000*100, 2)
max_dd = round(min(drawdown_series), 2)
avg_win = round(sum(t["pnl"] for t in trades if t["outcome"]=="WIN")/max(total_wins,1), 0)
avg_loss = round(sum(abs(t["pnl"]) for t in trades if t["outcome"]=="LOSS")/max(total_losses,1), 0)
avg_rr_actual = round(avg_win/avg_loss, 2) if avg_loss else 0
profit_factor = round(sum(t["pnl"] for t in trades if t["pnl"]>0) / abs(sum(t["pnl"] for t in trades if t["pnl"]<0)), 2)

summary = {
    "total_trades": total_trades,
    "total_wins": total_wins,
    "total_losses": total_losses,
    "total_be": total_be,
    "win_rate": win_rate,
    "final_value": round(final_value, 2),
    "total_pnl": total_pnl,
    "total_roi": total_roi,
    "max_drawdown": max_dd,
    "avg_win": avg_win,
    "avg_loss": avg_loss,
    "avg_rr_actual": avg_rr_actual,
    "profit_factor": profit_factor,
    "roi_target": 20.0,
    "on_target": total_roi >= 20.0
}

output = {
    "summary": summary,
    "trades": trades,
    "portf_series": portf_series,
    "drawdown_series": drawdown_series,
    "monthly_stats": {k: dict(v) for k,v in monthly_stats.items()},
    "month_order": month_order,
    "contract_stats": {k: dict(v) for k,v in contract_stats.items()},
}

with open("/sessions/inspiring-cool-cannon/mnt/outputs/sim_data.json", "w") as f:
    json.dump(output, f)

print(f"Simulation complete: {total_trades} trades | Win rate: {win_rate}% | Final ROI: {total_roi}% | Max DD: {max_dd}%")
