# Trade Deep Agent notebooks

Financial Portfolio Review **Deep Agents** framework (LangChain's batteries-included
agent layer on LangGraph), sharing the same `uv` environment.

## Trade Review Deep Agent — `trade_deep_agent.ipynb`

**Use case:** Week 3 Project 3B ("Multi-Agent Deal Review Pipeline"), adapted to a $100K
futures portfolio. An orchestrator delegates to a market-analyst, a risk-sizer, a
compliance-checker, and a trade-critic to research, size, and validate one trade idea
against the portfolio's hard risk rules — then drafts a trade ticket. The final
"take the trade" action (`execute_trade`) is **simulated** and gated behind mandatory
human approval; nothing is ever sent to a real broker. Decision-support only, not
financial advice.

## Setup (uv)

```bash
uv sync                       # install dependencies into .venv
cp .env.example .env          # then add your OPENAI_API_KEY (Tavily optional)
```

Open either notebook and select the project's `.venv` as the kernel, then run the cells
top to bottom. (If keys aren't in `.env`, the notebook prompts for them.)

## Layout

| Path | What it is |
|---|---|
| `trade_deep_agent.ipynb` | Trade review tutorial — run/explain cell by cell |
| `grounding/gen_academy.md` | Brand facts the GTM agent is grounded in |
| `grounding/trading_playbook.md` | Hard risk caps + macro snapshot the trade agent is grounded in |
| `grounding/trading_strategy_dashboard.md` | Entry/exit/sizing rules + live contract grades, pulled from the Financial Portfolio Intelligence System Dashboard — the trade-critic validates against this |
| `skills/linkedin-style/SKILL.md` | LinkedIn voice guide (loaded on demand) |
| `skills/email-style/SKILL.md` | Email voice guide (loaded on demand) |
| `skills/trade-ticket-style/SKILL.md` | Trade ticket format guide (loaded on demand) |
| `skills/compliance-review-style/SKILL.md` | Compliance review format guide (loaded on demand) |
| `images/0X_img.png` | Section-by-section infographics for the GTM notebook |
| `images/trade_0X_img.png` | Section-by-section infographics for the trade-review notebook |
| `research/`, `drafts/`, `review/`, `final/` | Created at runtime by the agents (gitignored) |

## Concepts demonstrated

Planning (`write_todos`) · subagent delegation (`task`) with isolated context · shared
filesystem state · skills (progressive disclosure) · cross-session memory via a `Store` ·
human-in-the-loop approval · `recursion_limit` as the runaway-loop backstop.
