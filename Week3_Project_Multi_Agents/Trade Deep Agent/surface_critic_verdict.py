import nbformat

PATH = "trade_deep_agent.ipynb"
nb = nbformat.read(PATH, as_version=4)

# --- cell 19: trade_critic_subagent now saves its verdict to a file ----------------
src19 = nb.cells[19].source
old_critic_prompt_tail = '''Return a short verdict: READY FOR HUMAN REVIEW, or NEEDS REVISION with the specific fix
needed. If the contract is graded D, say so explicitly in the verdict even if you still
mark it READY FOR HUMAN REVIEW — the human makes the final call on D-graded contracts.""",'''

new_critic_prompt_tail = '''Write your full verdict — all four axes' findings, the READY FOR HUMAN REVIEW or
NEEDS REVISION line, and the D/C-grade flag if applicable — to /review/critic_verdict.md.
This file is what the human reviewer sees at the approval step, so make it complete and
self-contained: don't make the human go dig through the other files to understand why.

End with a short verdict line: READY FOR HUMAN REVIEW, or NEEDS REVISION with the specific
fix needed. If the contract is graded D, say so explicitly in the verdict even if you still
mark it READY FOR HUMAN REVIEW — the human makes the final call on D-graded contracts.""",'''

assert old_critic_prompt_tail in src19, "critic prompt tail not found"
nb.cells[19].source = src19.replace(old_critic_prompt_tail, new_critic_prompt_tail)
nb.cells[19].outputs = []
nb.cells[19].execution_count = None

# --- cell 22: orchestrator step 5 references the critic verdict file ---------------
src22 = nb.cells[22].source
old_step5 = '''5. Once the critic says READY FOR HUMAN REVIEW, save the final ticket and compliance
   verdict to /final/trade_ticket.md.'''
new_step5 = '''5. Once the critic says READY FOR HUMAN REVIEW, save the final ticket, compliance
   verdict, AND the critic's full verdict (from /review/critic_verdict.md) to
   /final/trade_ticket.md, so the human sees one consolidated file.'''
assert old_step5 in src22, "step 5 not found"
nb.cells[22].source = src22.replace(old_step5, new_step5)
nb.cells[22].outputs = []
nb.cells[22].execution_count = None

# --- cell 31: pending_requests cell now also surfaces the critic's verdict ---------
nb.cells[31].source = '''from langgraph.types import Command

# What is the agent waiting to do? In this LangChain version each interrupt's
# .value is a SINGLE HITLRequest dict: {"action_requests": [...], "review_configs": [...]}.
# One action_request == one hanging tool call.
def pending_requests(res):
    reqs = []
    for intr in res.get("__interrupt__", []):
        val = intr.value
        if isinstance(val, dict) and "action_requests" in val:
            reqs.extend(val["action_requests"])      # unwrap the HITLRequest
        elif isinstance(val, list):
            reqs.extend(val)                          # older list-style payload
        else:
            reqs.append(val)
    return reqs

# Surface the trade-critic's own verdict (axes + D/C-grade flags) so the human's
# accept/reject decision is grounded in *why* the agent thinks this is ready, not just
# the raw execute_trade arguments.
critic_verdict_path = Path("review/critic_verdict.md")
if critic_verdict_path.exists():
    print("=" * 70)
    print("TRADE-CRITIC VERDICT (strategy-dashboard validated)")
    print("=" * 70)
    print(critic_verdict_path.read_text())
    print("=" * 70 + "\\n")
else:
    print("(No critic_verdict.md found — the critic may not have run, or the run "
          "stopped before it wrote one.)\\n")

reqs = pending_requests(result)
if reqs:
    for r in reqs:
        print("PENDING APPROVAL — TAKE THIS TRADE?")
        print(r)
else:
    print("No interrupt pending (agent may have rejected the idea on compliance grounds, "
          "or finished without calling execute_trade).")
'''
nb.cells[31].outputs = []
nb.cells[31].execution_count = None

# --- cell 33: re-print the critic verdict on each loop iteration too (in case the
# agent revises and re-runs the critic after a rejection) --------------------------
nb.cells[33].source = '''while "__interrupt__" in result:
    if critic_verdict_path.exists():
        print("=" * 70)
        print("TRADE-CRITIC VERDICT (strategy-dashboard validated)")
        print("=" * 70)
        print(critic_verdict_path.read_text())
        print("=" * 70)

    reqs = pending_requests(result)
    n = len(reqs)
    for r in reqs:
        print("PENDING APPROVAL — TAKE THIS TRADE?")
        print(r)

    raw = input("Approve this trade? [y]es / [n]o: ").strip().lower()
    decision = "approve" if raw in ("y", "yes", "") else "reject"
    print(f"--> Human decision: {decision.upper()}")

    if decision == "approve":
        decisions = [{"type": "approve"} for _ in range(n)]
    else:
        feedback = input("Reason for rejecting (sent back to the agent as feedback): ").strip()
        if not feedback:
            feedback = "Rejected by human reviewer — no reason given."
        print(f"--> Feedback sent to agent: {feedback}")
        decisions = [{"type": "reject", "message": feedback} for _ in range(n)]

    result = agent.invoke(Command(resume={"decisions": decisions}), config=config)

# Sanity check: confirm whether the trade was actually marked taken.
executed = [
    tc["args"]
    for m in result["messages"]
    for tc in (getattr(m, "tool_calls", None) or [])
    if tc["name"] == "execute_trade"
]
print("execute_trade calls made:", executed)

print("\\n===== FINAL RESPONSE =====")
result["messages"][-1].pretty_print()
'''
nb.cells[33].outputs = []
nb.cells[33].execution_count = None

# --- cell 29: markdown header — mention the critic verdict is now shown -----------
nb.cells[29].source = '''## 9. Human-in-the-loop: approve or reject taking the trade

We set `interrupt_on={"execute_trade": True}`, so the run **pauses** before marking the
trade taken and hands control back to us. Before asking for a decision, we print the
**trade-critic's full verdict** (`/review/critic_verdict.md`) — its consistency,
grounding, completeness, and strategy-dashboard checks, including any C/D contract-grade
flag — so the approve/reject call is grounded in the critic's actual reasoning, not just
the raw `execute_trade` arguments. We then **approve**, **reject with feedback**, or
**edit the arguments** before resuming with a `Command`. This is the non-negotiable
boundary from the trading playbook: reads (research, sizing, compliance checks) are
autonomous; the write action that "takes the trade" always needs a human.'''

nbformat.validate(nb)
nbformat.write(nb, PATH)
print("done")
