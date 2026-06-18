import cairosvg, os

PURPLE = "#6d28d9"
PURPLE_DARK = "#5b21b6"
TEXT_DARK = "#1f2937"
TEXT_GRAY = "#6b7280"
BLUE_BORDER = "#2563eb"
BLUE_FILL = "#eff6ff"
GREEN_BORDER = "#16a34a"
GREEN_FILL = "#f0fdf4"
AMBER_BORDER = "#d97706"
AMBER_FILL = "#fffbeb"
PURPLE_FILL = "#f5f3ff"
BANNER_FILL = "#ede9fe"
GRAY_BORDER = "#9ca3af"

def esc(s):
    return s.replace("&", "and")

def box(x, y, w, h, title, lines, border=PURPLE, fill="white", title_size=16, line_size=13):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" stroke="{border}" stroke-width="2.5"/>'
    if title:
        s += f'<text x="{x+16}" y="{y+28}" font-family="Arial, sans-serif" font-size="{title_size}" font-weight="bold" fill="{TEXT_DARK}">{esc(title)}</text>'
        ty = y + 50
    else:
        ty = y + 24
    for line in lines:
        s += f'<text x="{x+16}" y="{ty}" font-family="Arial, sans-serif" font-size="{line_size}" fill="{TEXT_GRAY}">{esc(line)}</text>'
        ty += 20
    return s

def circle_num(x, y, n, r=15):
    return (f'<circle cx="{x}" cy="{y}" r="{r}" fill="{PURPLE}"/>'
            f'<text x="{x}" y="{y+5}" font-family="Arial, sans-serif" font-size="14" font-weight="bold" '
            f'fill="white" text-anchor="middle">{n}</text>')

def arrow(x1, y1, x2, y2, color=PURPLE, dashed=False, sw=2.5):
    dash = ' stroke-dasharray="6,4"' if dashed else ''
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}" '
            f'marker-end="url(#arrow)"{dash}/>')

def label(x, y, text, size=12.5, color=TEXT_GRAY, anchor="middle", weight="normal"):
    return (f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{size}" '
            f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{esc(text)}</text>')

def title(text, x=600, y=42, size=28):
    return (f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{size}" font-weight="bold" '
            f'fill="{PURPLE}" text-anchor="middle">{esc(text)}</text>')

def subtitle(text, x=600, y=66, size=15):
    return (f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{size}" '
            f'fill="{TEXT_GRAY}" text-anchor="middle">{esc(text)}</text>')

def banner(x, y, w, h, text, fill=BANNER_FILL, border=PURPLE, color=PURPLE_DARK, size=15):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2}" fill="{fill}" stroke="{border}" stroke-width="2.5"/>'
    s += f'<text x="{x+w/2}" y="{y+h/2+5}" font-family="Arial, sans-serif" font-size="{size}" font-weight="bold" fill="{color}" text-anchor="middle">{esc(text)}</text>'
    return s

DEFS = f'''<defs>
<marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
<path d="M0,0 L0,6 L9,3 z" fill="{PURPLE}"/>
</marker>
<marker id="arrowblue" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
<path d="M0,0 L0,6 L9,3 z" fill="{BLUE_BORDER}"/>
</marker>
<marker id="arrowgreen" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
<path d="M0,0 L0,6 L9,3 z" fill="{GREEN_BORDER}"/>
</marker>
</defs>'''


# ======================================================================
# 1. ARCHITECTURE DIAGRAM
# ======================================================================
def architecture_diagram():
    W, H = 1300, 980
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="white"/>', DEFS]
    p.append(title("Trade Review Deep Agent — Architecture", x=650))
    p.append(subtitle("Orchestrator + 4 specialist subagents on LangGraph, with shared filesystem state and a mandatory human gate", x=650))

    # Human / trader row
    p.append(box(40, 95, 260, 100, "TRADER (HUMAN)", ["Enters trade idea", "Approves / rejects execute_trade"], border=AMBER_BORDER, fill=AMBER_FILL))

    # Orchestrator (center, prominent) -- sits right next to trader, no boxes in between
    p.append(box(340, 95, 460, 130, "ORCHESTRATOR  (create_deep_agent)",
                  ["system_prompt = 7-step workflow", "tools = [execute_trade]  (only risky tool)",
                   "interrupt_on = {'execute_trade': True}", "skills = [trade-ticket-style, compliance-review-style, ...]"],
                  border=BLUE_BORDER, fill=BLUE_FILL, title_size=16))

    # Skills
    p.append(box(840, 95, 420, 100, "SKILLS  (progressive disclosure)",
                  ["trade-ticket-style", "compliance-review-style"]))

    # Arrows: trader <-> orchestrator (short, clear of any box, labelled via one caption below)
    p.append(arrow(300, 130, 340, 130))
    p.append(arrow(340, 160, 300, 160, color=AMBER_BORDER))
    p.append(arrow(800, 145, 840, 145, color=GRAY_BORDER))

    p.append(label(320, 235, "trade idea in  /  critic verdict + pending approval request out", size=12.5, anchor="middle"))

    # Model strip -- own row, feeds the orchestrator + every subagent (avoids overlapping the arrows above)
    p.append(box(40, 255, 1220, 56, "", ["MODEL: gpt-4.1 (configurable) — shared by the orchestrator and all 4 subagents"], line_size=14))
    p.append(arrow(570, 255, 570, 225, color=GRAY_BORDER))

    # 4 subagents row
    subs = [
        (40, "market-analyst", ["Tools: web_search (Tavily)", "Reads CURRENT trend +", "GROUNDING. Writes", "/research/market_brief.md"]),
        (350, "risk-sizer", ["Tools: portfolio_state,", "risk_calculator. Skill:", "trade-ticket-style. Writes", "/drafts/trade_ticket.md"]),
        (660, "compliance-checker", ["Tools: portfolio_state,", "compliance_check. Skill:", "compliance-review-style. Writes", "/review/compliance_report.md"]),
        (970, "trade-critic", ["Tools: risk_calculator,", "compliance_check. Validates", "vs. STRATEGY_RULES (4 axes).", "Writes /review/critic_verdict.md"]),
    ]
    for x, name, lines in subs:
        p.append(box(x, 365, 290, 130, name, lines))
        p.append(arrow(570, 311, x + 145, 365))
    p.append(label(570, 340, "task(...) — isolated context per delegation", size=12.5))

    # Tools row
    p.append(box(40, 545, 290, 90, "TOOL: web_search", ["TavilySearch(max_results=3)", "optional — falls back to", "grounding snapshot if no key"]))
    p.append(box(350, 545, 290, 90, "TOOL: portfolio_state", ["Mocked broker API", "(swap for real API later)"]))
    p.append(box(660, 545, 290, 90, "TOOL: risk_calculator /", ["compliance_check", "Deterministic Python functions"]))
    p.append(box(970, 545, 290, 90, "TOOL: execute_trade", ["SIMULATED order only", "gated by interrupt_on"], border=AMBER_BORDER, fill=AMBER_FILL))

    # Backend / store / checkpointer row
    p.append(box(40, 685, 380, 110, "BACKEND  (CompositeBackend)",
                  ["default: FilesystemBackend(root='.')", "  -> /research /drafts /review /final", "/memories/ routed to StoreBackend"],
                  border=PURPLE, fill=PURPLE_FILL))
    p.append(box(450, 685, 270, 110, "STORE", ["InMemoryStore", "cross-session memory", "(PostgresStore in production)"], border=PURPLE, fill=PURPLE_FILL))
    p.append(box(750, 685, 270, 110, "CHECKPOINTER", ["MemorySaver", "per-thread state;", "required for HITL resume"], border=GREEN_BORDER, fill=GREEN_FILL))
    p.append(box(1050, 685, 210, 110, "GROUNDING FILES", ["trading_playbook.md", "trading_strategy_", "dashboard.md"]))

    for x in [180, 585, 885]:
        p.append(arrow(x, 655, x, 685, color=GRAY_BORDER))

    p.append(banner(40, 845, 1220, 60, "Reads (research, sizing, compliance) are autonomous. The write action that takes the trade always needs a human."))
    p.append(f'<text x="650" y="930" font-family="Arial, sans-serif" font-size="13" fill="{TEXT_GRAY}" text-anchor="middle">'
              f'Decision-support only -- execute_trade is simulated; nothing is ever sent to a real broker.</text>')
    p.append('</svg>')
    return "".join(p)


# ======================================================================
# 2. DATA FLOW DIAGRAM
# ======================================================================
def data_flow_diagram():
    W, H = 1300, 880
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="white"/>', DEFS]
    p.append(title("Trade Review Deep Agent — Data Flow", x=650))
    p.append(subtitle("From source data, through subagent processing, to the consolidated ticket the human reviews", x=650))

    # Column 1: data sources
    p.append(label(170, 100, "DATA SOURCES", size=15, color=PURPLE_DARK, weight="bold"))
    p.append(box(40, 115, 260, 90, "grounding/trading_playbook.md", ["Hard risk caps (never-rules) +", "May 31, 2026 macro snapshot"]))
    p.append(box(40, 220, 260, 90, "grounding/trading_strategy_", ["dashboard.md", "Entry/exit/sizing rules +", "live per-contract grade (A-D)"]))
    p.append(box(40, 325, 260, 90, "Live web search (Tavily)", ["Current price action, news,", "macro catalysts -- optional"]))
    p.append(box(40, 430, 260, 90, "portfolio_state tool", ["Mocked broker API:", "portfolio value + open positions"]))
    p.append(box(40, 535, 260, 90, "Human input", ["Symbol / Entry / Stop / Target", "(or market-scan suggestion)"], border=AMBER_BORDER, fill=AMBER_FILL))

    # Column 2: processing (subagents)
    p.append(label(620, 100, "PROCESSING  (subagents, isolated context)", size=15, color=PURPLE_DARK, weight="bold"))
    proc = [
        (140, "market-analyst", "current trend + conviction call"),
        (245, "risk-sizer", "entry/stop/target -> ticket + sizing"),
        (350, "compliance-checker", "ticket vs. hard risk rules -> PASS/FAIL"),
        (455, "trade-critic", "4-axis review incl. strategy-dashboard validation"),
        (560, "orchestrator", "consolidates ticket + both verdicts"),
    ]
    for y, name, desc in proc:
        p.append(box(460, y, 380, 85, name, [desc]))
    for x0, y0 in [(300, 160), (300, 265), (300, 370), (300, 475), (300, 475)]:
        pass
    p.append(arrow(300, 160, 460, 182, color=BLUE_BORDER))
    p.append(arrow(300, 265, 460, 287, color=BLUE_BORDER))
    p.append(arrow(300, 370, 460, 392, color=BLUE_BORDER))
    p.append(arrow(300, 475, 460, 497, color=BLUE_BORDER))
    p.append(arrow(300, 580, 460, 602, color=AMBER_BORDER))
    # chain between subagents
    p.append(arrow(650, 225, 650, 245))
    p.append(arrow(650, 330, 650, 350))
    p.append(arrow(650, 435, 650, 455))
    p.append(arrow(650, 540, 650, 560))

    # Column 3: artifacts
    p.append(label(1120, 100, "ARTIFACTS  (shared filesystem)", size=15, color=PURPLE_DARK, weight="bold"))
    p.append(box(960, 140, 320, 60, "/research/market_brief.md", [], border=BLUE_BORDER, fill=BLUE_FILL, title_size=13.5))
    p.append(box(960, 245, 320, 60, "/drafts/trade_ticket.md", [], border=BLUE_BORDER, fill=BLUE_FILL, title_size=13.5))
    p.append(box(960, 350, 320, 60, "/review/compliance_report.md", [], border=BLUE_BORDER, fill=BLUE_FILL, title_size=13.5))
    p.append(box(960, 455, 320, 60, "/review/critic_verdict.md", [], border=BLUE_BORDER, fill=BLUE_FILL, title_size=13.5))
    p.append(box(960, 560, 320, 60, "/final/trade_ticket.md  (consolidated)", [], border=GREEN_BORDER, fill=GREEN_FILL, title_size=13.5))
    for y in [170, 275, 380, 485, 590]:
        p.append(arrow(840, y, 960, y, color=GRAY_BORDER))

    # bottom: human decision + memory
    p.append(box(960, 660, 320, 80, "/memories/risk_profile.md", ["Cross-session note (StoreBackend)", "-- persists across new threads"], border=PURPLE, fill=PURPLE_FILL, title_size=13.5))
    p.append(arrow(1120, 620, 1120, 660, color=GRAY_BORDER))

    p.append(box(40, 660, 850, 110, "HUMAN DECISION",
                  ["Critic verdict + pending execute_trade request are printed for the human.",
                   "Approve -> trade marked TAKEN (simulated).  Reject + feedback -> resumes the",
                   "graph from checkpoint and loops back into processing for revision."],
                  border=AMBER_BORDER, fill=AMBER_FILL, title_size=15))
    p.append(arrow(960, 690, 890, 690, color=AMBER_BORDER))
    p.append('</svg>')
    return "".join(p)


# ======================================================================
# 3. WORKFLOW DIAGRAM
# ======================================================================
def workflow_diagram():
    W, H = 1300, 1000
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="white"/>', DEFS]
    p.append(title("Trade Review Deep Agent — End-to-End Workflow", x=650))
    p.append(subtitle("One run, from market scan to a human go/no-go decision", x=650))

    steps = [
        (0, "Market scan", "Throwaway-thread market-analyst call per watchlist contract (ES, NQ, GC, CL, NG); each proposes ONE candidate setup or 'no qualifying setup', printed for the trader to skim.", BLUE_BORDER, BLUE_FILL),
        (1, "Trader picks a setup", "input(): Symbol / Entry / Stop / Target -- either typed from scratch or based on the scan above.", AMBER_BORDER, AMBER_FILL),
        (2, "Orchestrator plans", "write_todos lays out the 7-step workflow for this run.", PURPLE, "white"),
        (3, "Delegate: market-analyst", "Live search (if available) for current price action/news; falls back to grounding snapshot with explicit disclosure. Writes /research/market_brief.md.", PURPLE, "white"),
        (4, "Delegate: risk-sizer", "Sizes the position via risk_calculator (1.0-2.0% risk by conviction); drafts /drafts/trade_ticket.md.", PURPLE, "white"),
        (5, "Delegate: compliance-checker", "Runs compliance_check against the hard risk rules; PASS/FAIL to /review/compliance_report.md.", PURPLE, "white"),
        (6, "Delegate: trade-critic", "4-axis review: consistency, grounding, completeness, strategy-dashboard validation (contract grade, sizing bands, R:R, live-vs-stale check). Writes /review/critic_verdict.md.", PURPLE, "white"),
        (7, "Revision loop (if needed)", "If the critic says NEEDS REVISION, the orchestrator re-delegates to the relevant subagent and re-runs the critic.", GRAY_BORDER, "white"),
        (8, "Save final + memory", "Consolidated ticket + both verdicts -> /final/trade_ticket.md. One-paragraph risk-profile note -> /memories/risk_profile.md.", PURPLE, "white"),
        (9, "Call execute_trade", "The ONLY risky tool call. interrupt_on pauses the graph here -- nothing is taken yet.", AMBER_BORDER, AMBER_FILL),
        (10, "Human-in-the-loop", "Critic verdict + pending request printed. Trader approves (-> trade marked TAKEN, simulated) or rejects with feedback (-> resumes for revision).", GREEN_BORDER, GREEN_FILL),
    ]

    y = 110
    row_h = 76
    for n, name, desc, border, fill in steps:
        p.append(circle_num(60, y + 24, n))
        p.append(box(95, y, 1165, row_h - 10, name, [desc], border=border, fill=fill, title_size=15, line_size=12.5))
        if n < 10:
            p.append(arrow(60, y + row_h - 10 + 6, 60, y + row_h + 10, sw=2))
        y += row_h

    p.append('</svg>')
    return "".join(p)


jobs = {
    "architecture_diagram": architecture_diagram(),
    "data_flow_diagram": data_flow_diagram(),
    "workflow_diagram": workflow_diagram(),
}

os.makedirs("diagrams", exist_ok=True)
for name, svg in jobs.items():
    out = f"diagrams/{name}.png"
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=out, output_width=1300)
    print("wrote", out)
