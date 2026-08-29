**review goes first.** The plan is a draft: review checks it against the code, fixes what is wrong,
and says so with `foreman say`. impl writes nothing until that message arrives.

**Then one milestone at a time.** impl builds it, stops, and sends a gate request — what landed,
the diff range, the design calls behind it, one line on what it ran. It starts the next only after
PASS. Don't work ahead: a moving target can't be reviewed.

**review reads the diff and replies PASS, or numbered changes with evidence.** It does not re-run
the suite. impl writes the code and its tests both, so a green suite is impl marking its own
homework; the design is the part impl cannot certify for itself, and that is what review is for.

**Waiting means ending your turn — both of you.** No sleep, no polling: say your piece and stop,
and the reply wakes you. Stay busy and `foreman say` has to deliver into a running turn, which is
where a message gets swallowed.

**Every decision goes to the human, through review** — scope, design trade-offs, public contracts.
impl never goes direct; a question on its own screen reaches nobody. Send the options, their costs,
and a recommendation. If the answer is written word for word in the plan or the spec it is a
lookup, not a decision: cite it. Unsure counts as a decision.

**Wrapping up.** After the last milestone passes, impl freezes the worktree, runs one full
verification, then opens the PR. That is the run that counts.
