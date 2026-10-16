# Grilling: the design-tree questioning method

Use this method for workflow Steps 2 (high-level clarification) and 8 (technical clarification). It replaces ad-hoc question batches with one running model: a design tree that gets interviewed in rounds until nothing is left unsettled.

## The design tree

Model the feature as a tree of decisions. The root is the user's request. Each decision branches into the decisions that hang off it — a product choice forces a UX choice, which forces a data-shape choice, which forces an edge-case choice, and so on.

Build this tree progressively across the workflow: Step 2 populates the product/behavioural layer before repository investigation; Steps 3–7 investigation adds repository facts and surfaces new technical-layer decisions; Step 8 interviews that technical layer. Steps 2 and 8 are two rounds-phases of the same tree, not two unrelated question sessions.

## The frontier

At any point, the **frontier** is every decision whose prerequisites are already settled — the questions answerable right now without guessing at something not yet decided. A question whose answer depends on another still-open question belongs to a later round, not this one.

## Rounds

Ask the current frontier using the `AskUserQuestion` tool, not freeform question text in a message. For each frontier node, phrase it as a question with your recommended answer as the first option, marked "(Recommended)", plus genuinely distinct alternatives — the user can still answer outside the options via "Other", so you don't need to pre-enumerate every possibility.

Keep each round small. `AskUserQuestion` caps a single call at 4 questions, each with up to 4 options — treat that as a ceiling, not a target. A round dumping the maximum every time is the same "wall of questions" problem as a long freeform list; prefer 2–3 of the highest-value frontier nodes per call over cramming in everything that happens to be unblocked. If the frontier has more nodes than fit comfortably in one call, split it across sequential calls rather than one dense batch — each call still blocks for an answer before the next, so this doesn't cost you a turn.

Each batch of answers resolves part of the tree and may unblock questions that were waiting on it — recompute the frontier before the next call rather than asking from a fixed pre-written list.

## Facts are never the user's job

If a frontier question needs a fact from the repository rather than a decision, don't ask the user — investigate it yourself, dispatching a sub-agent for anything non-trivial. Don't block the round on it: questions that depend on an outstanding investigation move to a later round, but ask the rest of the current frontier now. Only put a question to the user when the repository genuinely cannot answer it, or the answer is a product/behavioural choice rather than a fact.

## Scaling intensity to complexity

The design tree is the thing that scales. Build it honestly and the number of rounds follows its actual size — there's no separate "how many questions should I ask" judgment call to make on top of that.

- **Clearly scoped, plan-sourced requests** — the user points you at an existing written plan or spec (typically a file path: a `.plans/<x>/plan.md`, a design doc in the repo, or a feature spec they've already drafted themselves), rather than describing the feature to you fresh. Most of the tree is already decided by that document. The frontier is mostly fact-checking nodes ("does the plan's claim about the codebase still hold?"), not open product decisions.

  Investigate the plan's claims against the codebase first, in full, before saying anything — don't interrupt mid-investigation to flag the first contradiction you find. Once investigation is done, present every divergence together as one batched list ("the plan assumes X, but the codebase currently does Y" for each), then put only the genuine forks that surfaces to the user as frontier questions. This is the lightweight path's version of grilling: a near-empty tree that gets checked rather than interviewed, and checked wholesale rather than interactively.
- **Familiar, narrow asks that follow an existing pattern**: the tree is small — a handful of nodes, usually one round each for Steps 2 and 8.
- **Brand-new or broad features**: the tree is large and its shape is genuinely unknown up front. Keep running rounds — product layer, then technical layer — until the frontier is empty. Don't compress this into fewer questions than the tree actually has; the point of grilling is to surface branches neither of you had considered yet, not to minimize question count.

## Stopping rule

Default to exhaustive: grilling for a given layer is done when that layer's frontier is empty — every branch of the tree at that layer visited, nothing left silently assumed. A single round answered is not the same as an empty frontier; if the answers opened new branches, recompute and keep going. Do not advance to the next workflow step — repository investigation after Step 2, decomposition after Step 8 — just because one round happened. This has been a real failure mode: treat "I asked a batch of questions" and "the frontier is empty" as different things, and only the second licenses moving on.

The one override: if the user explicitly says to stop (e.g. "that's enough", "move on", "draft it"), stop immediately regardless of what's left in the frontier. Record any still-open nodes as explicit assumptions or open questions in the output (per `references/planning-principles.md`'s open-issues distinctions) rather than silently dropping them — don't just treat the cut-short as if the frontier had actually emptied.
