**review goes first.** The plan is a draft: review checks it against the code, fixes what is wrong,
and says so with `foreman say`. impl writes nothing until that message arrives.

**Then one milestone at a time.** impl builds it, stops, and sends a gate request with
`foreman say` — what landed, the diff range, the design calls behind it, one line on what it ran.
It starts the next only after PASS. Don't work ahead: a moving target can't be reviewed.

**review reads the diff, then sends the verdict with `foreman say`** — PASS, or numbered changes
with evidence. impl is stopped until that message arrives, and a verdict written on your own screen
has not been sent. Talking to the human doesn't answer impl either: if a gate request is open when
that conversation ends, sending the verdict is the last thing you do before you stop.

review does not re-run the suite. impl writes the code and its tests both, so a green suite is impl
marking its own homework; the design is the part impl cannot certify for itself, and that is what
review is for.

**Waiting means ending your turn — both of you.** No sleep, no polling: send it, then stop,
and the reply wakes you. Stay busy and `foreman say` has to deliver into a running turn, which is
where a message gets swallowed.

**Every decision goes to the human, through review** — scope, design trade-offs, public contracts.
impl never goes direct; a question on its own screen reaches nobody. Send the options, their costs,
and a recommendation. If the answer is written word for word in the plan or the spec it is a
lookup, not a decision: cite it. Unsure counts as a decision.

**The human is an escalation, not a participant.** A conversation with one ends when they answer:
carry the answer to impl and carry on. Don't report progress to them, don't ask whether to keep
going, don't wait for them at the next milestone. Until something meets the test above, or the
work is done, the loop is yours.

**Wrapping up.** After the last milestone passes, impl freezes the worktree, runs one full
verification, then opens the PR. That is the run that counts.
