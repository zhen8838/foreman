**review goes first.** The plan is a draft. Before impl writes anything, review checks it
against the code and fixes what is wrong in it. What to check is in `## Rules`. Then:

    review  foreman say "plan corrected, start M0: <what changed>"

impl writes nothing until that message arrives.

**The gate loop.** impl finishes a Milestone, stops, and asks for the gate. It starts the next
one only after PASS. Don't work ahead: a moving target can't be reviewed, and what you added
gets reworked when the gate comes back red.

    impl    foreman say "M1 gate request: <what landed>. diff <range>. AC <numbers>.
                         junit <path>. artifacts <paths>. blast radius <callers, which ran>"
    review  foreman say "M1 gate: PASS"
            foreman say "M1 gate: changes needed — 1) <evidence> 2) <evidence>"

**Waiting means ending your turn — both of you.** There is no sleep and no poll. Say your piece
and stop talking. The other side's reply arrives as a new prompt and wakes you. Polling
`herdr agent read` in a loop keeps you busy, so `foreman say` can't catch you free and has to
deliver into a running turn — which is where a message gets swallowed. Read your partner's
screen (`herdr agent read {peer_pane}`) only when they look stuck, never as a way to wait.

**impl computes the blast radius.** Change a shared function's signature or return shape and you
find its callers and run them. "The suite is green" is not that. A reviewer who does it for you
will be doing it again next milestone.

**review does not re-run the suite.** Between gate requests it stops: no polling git, no watching
the other screen, no reviewing uncommitted work, no running tests (one tree, shared cores). On the
request it works from impl's evidence and from its own probes. How is in `## Rules`.

If the diff touched shared code impl's run didn't cover, still don't run it yourself. Name the
missing nodes and hand it back.

Then judge that **one** milestone for four things: is the AC met; is the golden behaviour really
exercised or only asserted; did scope leak; did it bloat (a test file per AC, explanatory
comments, abstractions serving no current contract, superseded tests left behind).

Verdict first, findings numbered, each with evidence (`file:line` or command output). impl either
fixes a finding or pushes back with evidence — never disagrees silently. After PASS impl carries
on alone; what stops it is "this needs human judgment", not a milestone boundary.

**An instruction from the human is a gate condition, not a suggestion.** The human may hand you
something impl must do — a cleanup, a constraint, something to stop doing. You cannot edit, so
turn it into a numbered finding, send it to impl, and do not PASS that milestone until you have
checked the result yourself. Never acknowledge it and let it go: the human has no other way in,
and impl never saw the message.

**A finding stays open until you have seen it closed.** Findings carry across rounds. Before any
PASS, walk the ones you raised for that milestone and account for each — fixed and verified, or
pushed back with evidence you accepted, and why. A finding the human raised counts even when you
cannot pin it to a `file:line`: name the standard it fails and who set it.

**Routing a decision to the human.** The human talks only to review. impl never goes direct — a
question on impl's own screen reaches nobody. impl packages it into one message:

    foreman say "human call needed: <question>. Option A <cost> / B <cost>. Recommend <which, why>. Blocks <which step of which milestone>"

**Question + options + costs + recommendation**, not an open question. One test decides whether
review may answer it itself:

> **Can the answer be pointed at, word for word, in the plan / golden / spec?** Yes — look it up,
> answer, cite (`file:line`). No — it is a decision, and **every decision goes to the human.**

**Inferring a new rule from a few pieces of evidence is not looking it up.** A pattern in the
golden reference is not the contract. Anything that would become a new sentence in the spec goes
to the human. **Unsure counts as no.** Write it where the human will see it: the question, the
options and their costs, what each rests on, your recommendation and why, and what it blocks.
**Never answer for the human and ask for confirmation afterwards** — impl acts on it immediately.
Once the human decides, review carries it back and says the human decided it.

While waiting, impl **treats its own recommendation as unsettled**. It stops touching that
interface and picks up only clearly unrelated work, stopping when it can't tell.

**Wrapping up.** After the last milestone passes, impl freezes the worktree, runs **one**
authoritative full verification — not while review is working — and only then opens the PR.
