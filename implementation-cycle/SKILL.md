---
name: implementation-cycle
description: "Defines the full workflow for implementing a batch of features from an existing overarching plan file: propose a batch, get the planned shape signed off on a blueprint floor walk, implement each feature against its spec with targeted tests and an independent review loop, then get the result signed off on an as-built floor walk before pushing one PR. Use this whenever the user says \"start implementation cycle,\" \"implement this feature,\" \"implement the next batch,\" \"start the implementation loop,\" or points to a plan file and asks for features from it to be built. Requires a plan file path to begin. Make sure to trigger this any time the user is asking Claude Code to build out features from a broader plan/roadmap document, even if they don't use the exact phrase \"implementation cycle.\""
---

# Implementation Cycle

A disciplined workflow for building a **batch** of features with the user reviewing at exactly two checkpoints, both done as floor walks (see the `floor-walk` skill):

propose a batch → plan each feature → **blueprint walk** (checkpoint 1) → branch → build each feature (tests, internal review, local commit) → refresh the architecture map → **as-built walk** (checkpoint 2) → push and open one thin PR → report back.

Why this shape: one PR per feature was too frequent to review properly, it arrived after every decision was already baked in, and a diff never showed which part of the system moved. A batch means fewer reviews. The blueprint walk catches wrong turns before they're built, and both walks start from the floor plan.

## Hard requirement to start

**A path to an overarching plan file** (e.g. `PLAN.md`, or `.plans/<name>/plan.md`), written by another agent/process, containing a list of features. It may be an index linking out to per-feature spec files rather than containing full detail inline.

If it's missing, ask for it and stop. The user may also name the features to build. If they don't, you propose the batch (Step 2).

## Step 1 — Read the plan and orient

Read the plan file. Where a feature entry links to a feature spec file (e.g. `features/F001-<name>.md`, as produced by the `feature-planner` skill), read that too. It holds the acceptance criteria, edge cases and other detail.

**Orient in the codebase via `ARCHITECTURE.md` first, before any of your own exploration.** If a repo-root `ARCHITECTURE.md` exists, read it and check its freshness the same way the `architecture-map` skill does: run that skill's `scripts/staleness_key.sh` against the repo root and compare the result to the `staleness_key` recorded in the file's frontmatter.
- **Fresh, and it answers what you need** (which module owns the area a feature touches, conventions to follow, related domains, where similar prior features live) → use it and skip redundant exploration of that ground.
- **Fresh, but it doesn't cover something you need** (a specific function signature, a test convention) → explore just that gap.
- **Stale, or `ARCHITECTURE.md` doesn't exist** → explore as normal. Don't block on regenerating the map here; that's Step 7's job.

Treat the map as a structural orientation aid. Verify anything load-bearing (exact APIs you'll call, exact paths you'll edit) against the actual code.

## Step 2 — Propose the batch

Unless the user named the features, pick a **coherent batch of about 3-5 features**:
- Features not yet implemented (check the plan's status markers and the codebase).
- Respect dependencies: a feature goes in only if everything it depends on is already built or in this batch. Order the batch so dependencies come first.
- Prefer features that touch related parts of the system, so one walk tells one story.
- Keep it small enough that the as-built walk stays under about 8 stops.

For each feature in the batch, check it's implementable as scoped: clear boundaries, and enough detail to know what "done" looks like (acceptance criteria, expected behaviour, what's out of scope).
- **Clear enough** (even if small implementation details are left to judgment) → it stays in.
- **Too vague or missing scope-defining details** (no clear acceptance criteria, ambiguous boundaries, conflicting requirements) → leave it out of the batch. List it in the hand-off with exactly what needs adding to the plan. Don't guess on anything that defines a feature's scope.

Minor implementation-detail ambiguity ("dataclass or dict?") is fine to resolve with judgment later.

## Step 3 — Plan each feature

For each feature, work out a brief plan of action. It feeds the blueprint walk, so there's no need to write it out in chat:
- **Approach**: how you'll implement it.
- **Components and files** you expect to touch, and any new components or connections.
- **Design calls**: real forks in the road, with what you chose and why.
- **Tests** for the core logic you'll write (see Step 5).
- **Security risks**: input validation, auth boundaries, data exposure, injection, dependencies. These become red `security` flags.
- **Blast radius**: anything outside the batch that could behave differently. These become red `blast-radius` flags.
- **Open questions** you're resolving by judgment. Each becomes a design call on the walk.

## Step 4 — Blueprint walk (checkpoint 1)

Invoke the `floor-walk` skill in **`blueprint`** mode for the whole batch. It publishes the walk, writes `.walks/<batch-id>/blueprint.md`, gives the user the link, and waits. Use a batch id like `B<NN>` with a short slug from the batch's theme.

When the review comes back:
- **Approved** → continue to Step 5.
- **Changes requested** → apply each "Change this" note to the plans (and to the batch membership if a note says so), re-publish the blueprint walk on the same URL via `floor-walk`, and wait again.
- **The user rejects the batch outright** (in a note or in chat) → go back to Step 2 with their reasoning. Don't build anything on a shape they've rejected.

Answer any questions the user asks from the walk page in their comment threads (floor-walk covers how).

## Step 5 — Branch and build

Check out **one batch branch** off the current base branch, e.g. `batch/b02-checkout-reliability`. Do this once.

Then, for each feature **in dependency order**:

### 5a — Implement against spec, with targeted tests

Implement the feature to meet its spec (the "why" and "what") and the approved blueprint (the "how"). This is spec-driven, not strict TDD. Don't write a test for every code path up front, and don't aim for exhaustive coverage; that bloats the context window for little benefit.
- Write tests for the **core logic**: the parts that carry real risk of being wrong (business logic, non-trivial branching, anything flagged as a security risk). Write them alongside or just ahead of the corresponding implementation.
- Skip tests for trivial glue, straightforward wiring, or thin wrappers around well-tested libraries.
- Match the repo's testing framework and conventions; default to `pytest` if there are none.
- Run the test suite and confirm everything passes.

**Keep a running build log** for the as-built walk. For each feature, note every deviation from the blueprint and why, any debt or shortcuts, and anything you learned that changes the blast radius. Write these down as they happen; they're easy to lose by the end of the batch.

### 5b — Independent review

Once tests pass, spawn an independent subagent (via the Agent tool) with **fresh context** to review the feature. Give it:
- the diff for this feature
- this feature's plan of action and the relevant blueprint stops
- the feature spec (from the plan file and its linked feature file, if any)

Ask it to review for, explicitly:
- **Clarity**: is the code readable and reasonably self-explanatory?
- **Style**: does it match the repo's existing conventions?
- **Security vulnerabilities**: think adversarially about edge cases and misuse.
- **Functionality**: does it do what the feature requires, including edge cases?
- **Performance**: any obvious inefficiencies or scaling concerns?
- **Drift**: where does the implementation differ from the blueprint, and is each difference justified?

### 5c — Converge

- If the reviewer raises issues, fix them (back to 5a, adjusting targeted tests as needed), then re-review with a fresh subagent.
- Allow **up to ~3 rounds**. If the review hasn't converged by then, **don't interrupt the user mid-batch**. Record each remaining issue in the build log as an `unresolved` item; each one becomes a red flag on the as-built walk.

### 5d — Commit locally

Commit the feature on the batch branch: one commit per feature, with a message naming the feature id. **Don't push.**

If a feature turns out much bigger than the plan implied, use judgment to keep going, but record what grew and why in the build log. It becomes a `deviation` flag.

## Step 6 — When a later feature no longer makes sense

If building a feature reveals that a later feature in the batch is now wrong-headed (its blueprint no longer makes sense), stop before building that one. Tell the user what changed and ask whether to continue, re-plan it, or drop it. This is the only mid-batch interruption.

## Step 7 — Refresh the architecture map

After the last feature, invoke the `architecture-map` skill on the repo.
- If it reports the map was already fresh, there's nothing to commit.
- Otherwise, commit the `ARCHITECTURE.md` / `.architecture/domains/*.md` changes as **their own commit**, separate from the feature commits, so the history distinguishes "the features" from "the doc update the features caused".

The refreshed map is also the floor plan for the as-built walk.

## Step 8 — As-built walk (checkpoint 2)

Invoke `floor-walk` in **`as-built`** mode against `<base>...HEAD`. Pass it the blueprint walk's data and URL, the build log (deviations, debt, unresolved review issues), and the test results. It publishes the walk, writes `.walks/<batch-id>/as-built.md`, and waits.

When the review comes back:
- **Changes requested** → for each "Change this" flag, make the change on the batch branch (re-running 5a-5c for the affected feature, and committing as a follow-up commit). Then re-publish the as-built walk on the same URL and wait again.
- **Approved** → continue.

## Step 9 — Push and open a thin PR

Commit the `.walks/<batch-id>/` records (with the review outcomes appended) as their own commit. Push the branch and open **one** pull request. The body is deliberately thin, because the walk is the review and the PR is the record:

```
<3-line summary: what this batch does, and the features it covers (ids + names)>

Reviewed on a floor walk: <as-built walk link> (blueprint: <blueprint walk link>)
Records: .walks/<batch-id>/
```

## Step 10 — Wrap up

Report back in chat, briefly:
- the PR link
- test results
- whether the architecture map was refreshed or already fresh
- features left out of the batch (Step 2) and what each needs
- anything from the build log the user should still know that isn't already on the walk
