**The gate loop.** impl finishes a Milestone → **stops** → asks for the gate → starts the next
one only after PASS. Don't work ahead while waiting: a moving target can't be reviewed, and
whatever you added gets reworked when the gate comes back red.

    impl    foreman say "M1 gate request: <what landed>. diff <range>. verified <command, result>. AC <numbers>"
    review  foreman say "M1 gate: PASS"
            foreman say "M1 gate: changes needed — 1) <evidence> 2) <evidence>"

**Waiting means ending your turn — both of you.** There is no sleep and no poll. Say your
piece and stop talking; the other side's reply arrives as a new prompt in your pane and wakes
you. Polling `herdr agent read` in a loop is worse than useless: it keeps you busy, so
`foreman say` can't catch you free and has to deliver into a running turn, which is exactly
where a message gets swallowed. Read your partner's screen (`herdr agent read {peer_pane}`)
only when they appear stuck — never as a way to wait.

review reads the plan and the golden reference first and forms its own judgment — a standard
set after seeing the implementation is worth nothing. **Then it stops until that gate request
arrives**: no polling git, no watching the other screen, no reviewing uncommitted work, no
running verification (one tree, shared cores). Only on the request does it read the diff and
run what it needs, checking that **one** milestone for four things: is the AC actually met; is
the golden behaviour really exercised or merely asserted; did scope leak; and **did it bloat**
(a test file per AC, explanatory comments, new abstractions serving no current contract,
superseded tests left behind).

Verdict first, findings numbered, each carrying evidence (`file:line` or command output). On
findings impl either fixes them or pushes back with evidence — never disagrees silently. After
PASS impl carries on by itself; what makes it stop is "this needs human judgment", not a
milestone boundary.

**Routing a decision to the human.** The human talks only to review; impl never goes direct —
a question sitting on impl's own screen reaches nobody. impl packages it into one message:

    foreman say "human call needed: <question>. Option A <cost> / B <cost>. Recommend <which, why>. Blocks <which step of which milestone>"

**Question + options + costs + recommendation**, not an open-ended question. One test decides
whether review may answer it itself:

> **Can the answer be pointed at, word for word, in the plan / golden / spec?** Yes — look it
> up, answer, cite (`file:line`). No — it is a decision, and **every decision goes to the
> human.**

**Inferring a new rule from a few pieces of evidence is not looking it up.** A pattern showing
up in the golden reference doesn't make it the contract; anything that would become a new
sentence in the spec belongs here. **Unsure counts as no.** Whatever goes to the human, review
writes out where the human will see it: the question, the options and their costs, what each
option rests on in the plan or golden, its own recommendation and why, and what it blocks.
**Never answer for the human and seek confirmation afterwards** — impl will act on it
immediately. Once the human decides, review carries it back and says the human decided it.

While waiting, impl **must not treat its own recommendation as settled**: it stops touching
that interface (the shape of one hook reaches every model implementing it) and picks up only
genuinely unrelated work, stopping when it can't tell.

**Wrapping up.** After the last milestone passes, impl freezes the worktree and runs **one**
authoritative full verification — not concurrently with review — and only then opens the PR.
