import nbformat

PATH = "trade_deep_agent.ipynb"
nb = nbformat.read(PATH, as_version=4)

# --- cell 6: markdown header for grounding section -------------------------------
nb.cells[6].source = '''## 2. Portfolio grounding

We ground the agent in two files instead of one:

- **`trading_playbook.md`** — the hard risk caps (never-rules) and the May 31, 2026
  macro snapshot.
- **`trading_strategy_dashboard.md`** — the detailed strategy rulebook pulled from the
  *Financial Portfolio Intelligence System Dashboard* (entry rules, stop/exit rules,
  position sizing, strategy-review triggers, and the live per-contract grade scorecard).
  The trade-critic subagent validates every reviewed trade against this file specifically.

Grounding is how we keep an LLM from inventing risk rules, strategy rules, or market
facts — the agent is told to honor these files and not go beyond them.'''

# --- cell 7: load both grounding files --------------------------------------------
nb.cells[7].source = '''GROUNDING = Path("grounding/trading_playbook.md").read_text()
STRATEGY_RULES = Path("grounding/trading_strategy_dashboard.md").read_text()
print(GROUNDING)
print("\\n" + "=" * 70 + "\\n")
print(STRATEGY_RULES)'''
nb.cells[7].outputs = []
nb.cells[7].execution_count = None

# --- cell 17: markdown header for subagents section -------------------------------
nb.cells[17].source = '''## 6. Specialist subagents

Each subagent is a dict: a name, a description (the orchestrator reads this to decide
*when* to delegate), a focused system prompt, its own tools, and its own skills.
Subagents are **stateless** — each `task` call is a fresh run — so instructions must be
complete, and (since subagent context is isolated from the orchestrator's) any grounding
text a subagent needs has to be embedded directly into its own prompt, not just
referenced.

Note the **division of labour**, mirroring the Week 3 "Multi-Agent Deal Review Pipeline"
framework (extract → check compliance → flag risk/summarize → orchestrate): the
market-analyst gets web search **and** both grounding files so it can read the *current*
market trend against the playbook's last snapshot, the risk-sizer only gets the
calculator, the compliance-checker only gets the compliance tool, and the critic gets
both review tools plus the strategy dashboard so it can validate the trade against the
actual entry/exit/sizing rules and the live per-contract grade — not just the high-level
risk caps.'''

# --- cell 19: subagent definitions --------------------------------------------------
nb.cells[19].source = '''SKILLS = ["/skills/"]  # loaded from disk via the FilesystemBackend

market_analyst_subagent = {
    "name": "market-analyst",
    "description": (
        "Researches the CURRENT technical/macro trend for one futures contract and "
        "writes a short brief. Use first, before any sizing or compliance work."
    ),
    "system_prompt": f"""You research one futures contract for a proposed trade idea.
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
conviction call.""",
    "tools": research_tools,
}

risk_sizer_subagent = {
    "name": "risk-sizer",
    "description": (
        "Sizes a proposed trade (entry/stop/target) using risk_calculator and drafts a "
        "trade ticket. Use after market-analyst has set a conviction call."
    ),
    "system_prompt": (
        "Load the 'trade-ticket-style' skill and follow it strictly. Read "
        "/research/market_brief.md for the conviction call and rationale. Call "
        "portfolio_state to get current portfolio value and open positions, then call "
        "risk_calculator with the proposed entry/stop/target/conviction. Draft one trade "
        "ticket with the exact dollar risk, R:R, and contract count, then save it to "
        "/drafts/trade_ticket.md. Return the full ticket text."
    ),
    "tools": [portfolio_state, risk_calculator],
    "skills": SKILLS,
}

compliance_checker_subagent = {
    "name": "compliance-checker",
    "description": (
        "Checks a drafted trade ticket against the hard risk rules using compliance_check. "
        "Use after risk-sizer has produced /drafts/trade_ticket.md."
    ),
    "system_prompt": (
        "Load the 'compliance-review-style' skill and follow it strictly. Read "
        "/drafts/trade_ticket.md. Call portfolio_state, then call compliance_check with "
        "the ticket's risk_pct, reward:risk, sector, the open_positions_json from "
        "portfolio_state, and whether a stop is present. Save your PASS/FAIL review to "
        "/review/compliance_report.md. Return the verdict line plus the full review."
    ),
    "tools": [portfolio_state, compliance_check],
    "skills": SKILLS,
}

trade_critic_subagent = {
    "name": "trade-critic",
    "description": (
        "Cross-checks the trade ticket and compliance report for consistency, "
        "completeness, AND validates the trade against the trading strategy dashboard "
        "(entry/exit/sizing rules, live contract grade). Use last, before the "
        "orchestrator finalizes anything."
    ),
    "system_prompt": f"""Read /research/market_brief.md, /drafts/trade_ticket.md, and
/review/compliance_report.md. Review on four axes:

1. CONSISTENCY — do the ticket's numbers match what compliance_check actually
   evaluated? Re-run compliance_check yourself if anything looks off.
2. GROUNDING — is every claim in the ticket's rationale supported by the market brief
   or the trading playbook, with nothing invented?
3. COMPLETENESS — does the ticket have an entry, stop, target, size, dollar risk, and
   R:R? Flag anything missing.
4. STRATEGY VALIDATION — check the trade against the trading strategy dashboard below.
   Specifically: is the contract's grade C or D (flag and recommend reduce-size/pause
   per the scorecard)? Does the position size match the dashboard's HIGH/MEDIUM sizing
   bands? Is the R:R at least 2:1? Note if the market brief's conviction call was based
   on a live search or a stale snapshot (less confidence if stale).

Trading strategy dashboard (validate the trade against this; never invent strategy
rules beyond it + the playbook):
{STRATEGY_RULES}

Return a short verdict: READY FOR HUMAN REVIEW, or NEEDS REVISION with the specific fix
needed. If the contract is graded D, say so explicitly in the verdict even if you still
mark it READY FOR HUMAN REVIEW — the human makes the final call on D-graded contracts.""",
    "tools": [risk_calculator, compliance_check],
    "skills": SKILLS,
}

print("4 subagents defined.")'''
nb.cells[19].outputs = []
nb.cells[19].execution_count = None

# --- cell 22: orchestrator prompt + assembly ---------------------------------------
nb.cells[22].source = '''from deepagents import create_deep_agent

ORCHESTRATOR_PROMPT = f"""You are the trade review lead for a $100,000 futures
portfolio. For one proposed trade idea, you decide whether it is ready to take — but you
NEVER make the final call yourself; a human always approves or rejects before the trade
is marked taken.

Trading playbook grounding (always honor this; never invent rules or market facts beyond
it + research):
{GROUNDING}

Workflow — first call write_todos to plan, then:
1. Delegate to 'market-analyst' to research the CURRENT market trend for the contract
   and set a conviction call (writes /research/market_brief.md).
2. Delegate to 'risk-sizer' to size the trade and draft a ticket
   (writes /drafts/trade_ticket.md).
3. Delegate to 'compliance-checker' to PASS/FAIL it against the hard risk rules
   (writes /review/compliance_report.md).
4. Delegate to 'trade-critic' for a final cross-check AND strategy-dashboard validation
   (entry/exit/sizing rules + live contract grade). If it says NEEDS REVISION,
   re-delegate to the relevant subagent to fix it, then re-run the critic.
5. Once the critic says READY FOR HUMAN REVIEW, save the final ticket and compliance
   verdict to /final/trade_ticket.md.
6. Save a one-paragraph note on this trade's risk profile and any flags to
   /memories/risk_profile.md for future sessions.
7. Finally, call execute_trade with the ticket's exact contract/direction/entry/stop/
   target/size. This call will pause for human approval — do not write any summary or
   final message until the human's decision comes back.

If compliance_check ever returns FAIL and the critic can't get it to PASS after one
revision, do NOT call execute_trade — instead report the FAIL and stop, recommending the
human reject the idea outright.

Keep everything concise and numbers-first."""

agent = create_deep_agent(
    model=MODEL,
    system_prompt=ORCHESTRATOR_PROMPT,
    tools=[execute_trade],
    subagents=[market_analyst_subagent, risk_sizer_subagent, compliance_checker_subagent,
               trade_critic_subagent],
    backend=backend,
    store=store,
    skills=SKILLS,
    interrupt_on={"execute_trade": True},   # HITL gate — needs the checkpointer
    checkpointer=checkpointer,
)
print("Deep agent assembled.")'''
nb.cells[22].outputs = []
nb.cells[22].execution_count = None

nbformat.validate(nb)
nbformat.write(nb, PATH)
print("done")
