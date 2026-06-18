import cairosvg

PURPLE = "#6d28d9"
PURPLE_DARK = "#5b21b6"
TEXT_DARK = "#1f2937"
TEXT_GRAY = "#6b7280"
BLUE_BORDER = "#2563eb"
BLUE_FILL = "#eff6ff"
GREEN_BORDER = "#16a34a"
GREEN_FILL = "#f0fdf4"
PURPLE_FILL = "#f5f3ff"
BANNER_FILL = "#ede9fe"

def box(x, y, w, h, title, lines, border=PURPLE, fill="white", title_size=17):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" stroke="{border}" stroke-width="2.5"/>'
    s += f'<text x="{x+18}" y="{y+34}" font-family="Arial, sans-serif" font-size="{title_size}" font-weight="bold" fill="{TEXT_DARK}">{title}</text>'
    ty = y + 60
    for line in lines:
        s += f'<text x="{x+18}" y="{ty}" font-family="Arial, sans-serif" font-size="14.5" fill="{TEXT_GRAY}">{line}</text>'
        ty += 22
    return s

def circle_num(x, y, n):
    return (f'<circle cx="{x}" cy="{y}" r="16" fill="{PURPLE}"/>'
            f'<text x="{x}" y="{y+5}" font-family="Arial, sans-serif" font-size="15" font-weight="bold" '
            f'fill="white" text-anchor="middle">{n}</text>')

def arrow(x1, y1, x2, y2, color=PURPLE):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="2.5" '
            f'marker-end="url(#arrow)"/>')

def title(text, x=600, y=42, size=30):
    return (f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{size}" font-weight="bold" '
            f'fill="{PURPLE}" text-anchor="middle">{text}</text>')

def banner(x, y, w, h, text, fill=BANNER_FILL, border=PURPLE, color=PURPLE_DARK, size=17):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2}" fill="{fill}" stroke="{border}" stroke-width="2.5"/>'
    s += f'<text x="{x+w/2}" y="{y+h/2+6}" font-family="Arial, sans-serif" font-size="{size}" font-weight="bold" fill="{color}" text-anchor="middle">{text}</text>'
    return s

DEFS = '''<defs>
<marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
<path d="M0,0 L0,6 L9,3 z" fill="%s"/>
</marker>
</defs>''' % PURPLE


# ============================================================ 05: Specialist subagents
def img05():
    W, H = 1200, 680
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="white"/>', DEFS]
    parts.append(title("Specialist Subagents: Focused Workers, Isolated Context"))

    parts.append(box(395, 65, 410, 90, "SUBAGENT TEMPLATE",
                      ["{name, description, system_prompt,", "tools, skills} -- stateless per task() call"],
                      fill=PURPLE_FILL))

    cols = [(28, "market-analyst", ["Tools: web_search.", "Reads CURRENT trend (live", "search) + GROUNDING."]),
            (313, "risk-sizer", ["Tools: portfolio_state,", "risk_calculator. Skill:", "trade-ticket-style"]),
            (598, "compliance-checker", ["Tools: portfolio_state,", "compliance_check. Skill:", "compliance-review-style"]),
            (883, "trade-critic", ["Tools: risk_calculator,", "compliance_check. Validates", "vs. STRATEGY_RULES (4 axes)."])]
    cw = 290
    for x, name, lines in cols:
        parts.append(box(x, 200, cw, 140, name, lines))
        parts.append(arrow(600, 155, x + cw / 2, 200))

    parts.append(box(28, 370, cw, 86, "market-analyst writes", ["/research/market_brief.md"]))
    parts.append(box(883, 370, cw, 86, "trade-critic writes", ["/review/critic_verdict.md"], border=BLUE_BORDER, fill=BLUE_FILL))

    parts.append(box(28, 480, 1144, 86, "SHARED FILE WORKSPACE (single source of truth)",
                      ["/research/market_brief.md  /drafts/trade_ticket.md  /review/compliance_report.md  /review/critic_verdict.md  /final/trade_ticket.md"],
                      fill=PURPLE_FILL))

    parts.append(banner(60, 596, 1080, 56, "The orchestrator delegates work. Specialists stay focused. The filesystem carries the handoff."))
    parts.append('</svg>')
    return "".join(parts)


# ============================================================ 06: Assemble the deep agent
def img06():
    W, H = 1200, 800
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="white"/>', DEFS]
    parts.append(title("Assembling the Deep Agent: Configuration, Not Plumbing"))

    top = [(28, "MODEL", ["e.g. gpt-4.1"]),
           (318, "BACKEND", ["Filesystem", "+ Store"]),
           (608, "STORE", ["long-term", "memory"]),
           (898, "SKILLS", ["style", "guides"])]
    for x, name, lines in top:
        parts.append(box(x, 65, 272, 120, name, lines))
        parts.append(arrow(x + 136, 185, 600 + (x - 463) * 0.35, 265))

    parts.append(box(28, 265, 358, 360,
                      "ORCHESTRATOR_PROMPT",
                      ["7-step workflow:", "1 CURRENT trend research", "2 size  3 compliance check", "4 critic + STRATEGY_RULES", "   validation (re-loop if",
                       "   NEEDS REVISION)", "5 save final + verdict", "6 save memory  7 execute"]))

    parts.append(box(390, 265, 420, 360,
                      "agent = create_deep_agent(",
                      ["model=MODEL,", "system_prompt=ORCH_PROMPT,", "tools=[execute_trade],",
                       "subagents=[...4 specialists],", "backend=backend, store=store,",
                       "skills=SKILLS,", "interrupt_on={'execute_trade':", "  True},",
                       "checkpointer=checkpointer)"], border=BLUE_BORDER, fill=BLUE_FILL))

    parts.append(box(842, 265, 330, 360, "4 SUBAGENTS",
                      ["market-analyst (live trend)", "risk-sizer", "compliance-checker",
                       "trade-critic (dashboard-", "  validated, writes verdict)"]))

    parts.append(box(28, 650, 562, 110, "INTERRUPT GATE", ["{'execute_trade': True}"], border=GREEN_BORDER, fill=GREEN_FILL))
    parts.append(box(610, 650, 562, 110, "CHECKPOINTER", ["pauses and resumes across the interrupt"], border=GREEN_BORDER, fill=GREEN_FILL))
    parts.append('</svg>')
    return "".join(parts)


# ============================================================ 07: Run a trade idea (market scan + interactive input)
def img07():
    W, H = 1200, 800
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="white"/>', DEFS]
    parts.append(title("Running a Trade Idea: Scan -> Pick -> Delegate -> Review", size=27))

    parts.append(box(28, 64, 1144, 96, "STEP A -- MARKET SCAN ACROSS THE WATCHLIST (throwaway threads)",
                      ["For each of ES, NQ, GC, CL, NG: a single isolated market-analyst call proposes ONE candidate setup",
                       "(or 'NO QUALIFYING SETUP'), grounded in a live read + the strategy dashboard's entry rules. Printed for you to skim."],
                      border=BLUE_BORDER, fill=BLUE_FILL, title_size=16))

    rows = [
        (1, "You pick a contract and enter the setup", "input(): Symbol / Entry / Stop / Target (defaults provided)"),
        (2, "Trade idea enters", "agent.invoke({'messages':[...]})"),
        (3, "Orchestrator plans", "write_todos"),
        (4, "Delegates research", "task -> market-analyst (CURRENT trend, web_search)"),
        (5, "Delegates sizing", "task -> risk-sizer"),
        (6, "Delegates compliance", "task -> compliance-checker"),
        (7, "Delegates critique", "task -> trade-critic (validates vs. strategy dashboard, writes critic_verdict.md)"),
        (8, "Saves final ticket + verdict", "/final/trade_ticket.md"),
        (9, "Calls execute_trade", "-> interrupt fires"),
    ]
    y = 200
    for n, name, sub in rows:
        parts.append(circle_num(56, y + 24, n))
        parts.append(box(86, y, 760, 48, "", [], fill="none"))
        parts.append(f'<rect x="86" y="{y}" width="760" height="48" rx="10" fill="white" stroke="{PURPLE}" stroke-width="2"/>')
        parts.append(f'<text x="104" y="{y+20}" font-family="Arial, sans-serif" font-size="14.5" font-weight="bold" fill="{TEXT_DARK}">{name}</text>')
        parts.append(f'<text x="104" y="{y+38}" font-family="Arial, sans-serif" font-size="12.5" fill="{TEXT_GRAY}">{sub}</text>')
        y += 58

    parts.append(box(880, 200, 292, 150, "What you SEE",
                      ["orchestrator plans/status,", "each subagent's FINAL report", "(not internal back-and-forth),", "the printed market scan"],
                      border=BLUE_BORDER, fill=BLUE_FILL))
    parts.append(box(880, 366, 292, 130, "What you DON'T see",
                      ["internal subagent reasoning,", "chain-of-thought, tool calls", "-> that churn stays isolated"]))

    parts.append(banner(60, 716, 1080, 56, "The scan suggests; you decide. The pipeline then researches, sizes, and reviews your pick."))
    parts.append('</svg>')
    return "".join(parts)


# ============================================================ 08: Shared state
def img08():
    W, H = 800, 800  # not used as canvas size; will fix at end via param
    W, H = 1200, 800
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="white"/>', DEFS]
    parts.append(title("Shared State: Files and Todos Tell the Story"))

    parts.append(box(28, 65, 352, 500, "Who wrote what",
                      ["market-analyst writes", "/research/market_brief.md", "",
                       "risk-sizer + compliance-", "checker write", "/drafts/trade_ticket.md", "/review/compliance_report.md", "",
                       "trade-critic writes", "/review/critic_verdict.md", "(4-axis review, incl.",
                       "strategy-dashboard grade)", "",
                       "orchestrator saves", "/final/trade_ticket.md", "(ticket + both verdicts)"]))

    parts.append(box(408, 65, 352, 500, "SHARED STATE",
                      ["/research/", "market_brief.md", "/drafts/", "trade_ticket.md", "/review/",
                       "compliance_report.md", "critic_verdict.md", "/final/", "trade_ticket.md"],
                      fill=PURPLE_FILL))
    parts.append(arrow(380, 300, 408, 300))

    parts.append(box(788, 65, 384, 500, "TODO LIST",
                      ["[done] research trade idea", "[done] size position", "[done] check compliance",
                       "[done] critique + validate vs.", "       strategy dashboard",
                       "[done] save final ticket", "[pending] human approval", "  (sees critic_verdict.md)"],
                      border=BLUE_BORDER, fill=BLUE_FILL))

    parts.append(banner(60, 600, 1080, 56, "Shared artifacts are often more useful than shared chat history."))
    parts.append(f'<text x="60" y="690" font-family="Arial, sans-serif" font-size="14" fill="{TEXT_GRAY}">'
                  f'for p in [...]: print(Path(p).read_text())  |  for t in result[\'todos\']: print(t[\'status\'], t[\'content\'])</text>')
    parts.append('</svg>')
    return "".join(parts)


# ============================================================ 09: HITL (minor refresh: mention critic_verdict.md)
def img09():
    W, H = 1200, 720
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="white"/>', DEFS]
    parts.append(title("Human-in-the-Loop: Critic Verdict, Then Approve or Reject"))

    row1 = [(1, "Ticket + verdict ready", "/final/trade_ticket.md"),
            (2, "Calls execute_trade", "the only risky tool"),
            (3, "Interrupt fires", "interrupt_on={...:True}"),
            (4, "Verdict + request printed", "critic_verdict.md, then pending_requests()")]
    row2 = [(5, "Human reviews", "axes + D/C-grade flag"),
            (6, "Approve / reject", "input(): y/n + reason if no"),
            (7, "Resume run", "Command(resume={...})"),
            (8, "Trade marked TAKEN", "[SIMULATED] order")]

    cw = 268
    x0 = 28
    for i, (n, name, sub) in enumerate(row1):
        x = x0 + i * (cw + 18)
        parts.append(circle_num(x + cw / 2, 110, n))
        parts.append(box(x, 130, cw, 110, name, [sub]))
        if i < 3:
            parts.append(arrow(x + cw + 4, 185, x + cw + 14, 185))
    for i, (n, name, sub) in enumerate(row2):
        x = x0 + i * (cw + 18)
        border = GREEN_BORDER if n == 8 else PURPLE
        fill = GREEN_FILL if n == 8 else "white"
        parts.append(circle_num(x + cw / 2, 280, n))
        parts.append(box(x, 300, cw, 110, name, [sub], border=border, fill=fill))
        if i < 3:
            parts.append(arrow(x + cw + 4, 355, x + cw + 14, 355))

    parts.append(banner(50, 460, 1100, 56, "The graph does not restart. It resumes from the saved checkpoint after review."))
    parts.append(f'<text x="60" y="552" font-family="Arial, sans-serif" font-size="15" fill="{TEXT_GRAY}">'
                  f"Reject with feedback: {{'type': 'reject', 'message': '...'}} sends the ticket back for revision (critic re-runs, verdict file updates).</text>")
    parts.append('</svg>')
    return "".join(parts)


jobs = {
    "trade_05_img": img05(),
    "trade_06_img": img06(),
    "trade_07_img": img07(),
    "trade_08_img": img08(),
    "trade_09_img": img09(),
}

for name, svg in jobs.items():
    out = f"images/{name}.png"
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=out, output_width=1200)
    print("wrote", out)
