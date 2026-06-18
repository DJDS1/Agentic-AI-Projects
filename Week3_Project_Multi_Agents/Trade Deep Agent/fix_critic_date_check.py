import nbformat

PATH = "trade_deep_agent.ipynb"
nb = nbformat.read(PATH, as_version=4)

src19 = nb.cells[19].source

old_axis2 = '''2. GROUNDING — is every claim in the ticket's rationale supported by the market brief
   or the trading playbook, with nothing invented?'''

new_axis2 = '''2. GROUNDING — is every claim in the ticket's rationale supported by the market brief
   or the trading playbook, with nothing invented? Also check the brief's own date
   label for self-consistency: if it claims a live search but the header still reads
   "May 31, 2026" (the playbook snapshot's date, not today's), that is a mislabeling
   bug — flag it explicitly as NEEDS REVISION (re-run market-analyst) rather than
   silently trusting a header that contradicts the body.'''

assert old_axis2 in src19, "axis 2 text not found"
nb.cells[19].source = src19.replace(old_axis2, new_axis2)
nb.cells[19].outputs = []
nb.cells[19].execution_count = None

nbformat.validate(nb)
nbformat.write(nb, PATH)
print("done")
