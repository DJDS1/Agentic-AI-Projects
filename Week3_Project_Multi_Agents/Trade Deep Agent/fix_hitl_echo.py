import nbformat

PATH = "trade_deep_agent.ipynb"

nb = nbformat.read(PATH, as_version=4)

decision_code = '''while "__interrupt__" in result:
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

nb.cells[33].source = decision_code
nb.cells[33].outputs = []
nb.cells[33].execution_count = None

nbformat.validate(nb)
nbformat.write(nb, PATH)
print("done")
