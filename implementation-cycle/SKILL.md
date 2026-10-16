---
name: implementation-cycle
description: "Defines the full workflow for implementing a batch of features from an existing overarching plan file: propose a batch and get it quickly confirmed, implement each feature against its spec with targeted tests and an independent review loop (building independent features in parallel, dependent ones in sequence), then get the result signed off on an as-built floor walk before pushing one PR. Use this whenever the user says \"start implementation cycle,\" \"implement this feature,\" \"implement the next batch,\" \"start the implementation loop,\" or points to a plan file and asks for features from it to be built. Requires a plan file path to begin. Make sure to trigger this any time the user is asking Claude Code to build out features from a broader plan/roadmap document, even if they don't use the exact phrase \"implementation cycle.\""
---

# Implementation Cycle

A disciplined workflow for building a **batch** of features, picking up from a plan that was already reviewed on a blueprint floor walk when it was finalised (see the `feature-planner` skill):

propose a batch → quick confirmation in chat → branch → build each feature (independent features in parallel, dependent ones in sequence; tests, internal review, local commit) → refresh the architecture map → **as-built walk** → push and open one thin PR → report back.

Why this shape: one PR per feature was too frequent to review properly, it arrived after every decision was already baked in, and a diff never showed which part of the system moved. A batch means fewer reviews. The user already reviewed the planned shape once, on the blueprint walk, when the plan was finalised — re-reviewing it here, batch by batch, would just be the same review again in smaller, more disruptive pieces. So this skill only asks for a quick go-ahead on which features make up the batch, and saves the one full review for the as-built walk, which starts from the floor plan.

## Hard requirement to start

**A path to an overarching plan file** (e.g. `PLAN.md`, or `.plans/<name>/plan.md`), written by another agent/process, containing a list of features. It may be an index linking out to per-feature spec files rather than containing full detail inline.

If it's missing, ask for it and stop. The user may also name the features to build. If they don't, you propose the batch (Step 2).

## Step 1 — Read the plan and orient

Read the plan file. Where a feature entry links to a feature spec file (e.g. `features/F001-<name>.md`, as produced by the `feature-planner` skill), read that too. It holds the acceptance criteria, edge cases and other detail.

If the plan file has a "Review" section with a blueprint walk link (written by `feature-planner`), note the URL — it means this plan was already reviewed, and the link is carried through to the as-built walk (Step 7) and the PR body (Step 8). If there's no such link — the plan wasn't produced by `feature-planner`, or predates this review step — mention that to the user when you confirm the batch in Step 2, and offer to run `floor-walk` in `blueprint` mode yourself first if they want the planned shape reviewed before you build.

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

**Confirm before building.** If the user named the features to build, skip this — they've already decided. Otherwise, once the batch is chosen, tell them what you're about to build in one or two lines, naming the dependency shape so they know what runs in parallel versus in sequence, e.g.:

> I'll build F012, F013 and F014 this pass. F013 depends on F012, so it builds after; F014 is independent and builds in parallel with F012. OK?

Wait for a go-ahead before branching. This is a quick confirmation, not a floor walk — the planned shape was already reviewed at the blueprint stage.

## Step 3 — Plan each feature

For each feature, work out a brief plan of action. It's handed to that feature's coding subagent in Step 4 and seeds the as-built walk's flags later, so there's no need to write it out in chat beyond the one-line confirmation in Step 2:
- **Approach**: how you'll implement it.
- **Components and files** you expect to touch, and any new components or connections.
- **Design calls**: real forks in the road, with what you chose and why.
- **Tests** for the core logic you'll write (see Step 4).
- **Security risks**: input validation, auth boundaries, data exposure, injection, dependencies. These become red `security` flags.
- **Blast radius**: anything outside the batch that could behave differently. These become red `blast-radius` flags.
- **Open questions** you're resolving by judgment. Each becomes a design call recorded for the as-built walk.

## Step 4 — Branch and build

Check out **one batch branch** off the current base branch, e.g. `batch/b02-checkout-reliability`. Do this once.

Group the batch into **dependency levels**: level 1 is every feature in the batch with no dependency still to build; level 2 is every feature whose dependencies are all in level 1; and so on. Build one level at a time, in order — a later level may depend on an earlier one's code, so don't start it until the previous level is fully merged into the batch branch.

Within a level:
- **One feature** → build it directly on the batch branch (4a-4d below).
- **More than one feature** → they don't depend on each other, so build them concurrently. Spawn one coding subagent per feature with the Agent tool's `isolation: "worktree"`, each branched from the batch branch's current tip — this gives each feature its own working copy, so concurrent edits never collide. Run 4a-4c independently in each worktree. As each feature's review loop converges, merge its worktree branch into the batch branch (`git merge --no-ff`) and remove the worktree (`git worktree remove`) — one at a time, in whatever order they finish, so the batch branch's history stays a clean sequence of single-feature commits even though the work happened in parallel. If a merge conflicts, hand the conflict to that feature's coding subagent to resolve before committing the merge.

### 4a — Implement against spec, with targeted tests

Spawn a **fresh coding subagent** for the feature (Agent tool, `general-purpose`; add `isolation: "worktree"` when it's building alongside another feature in the same level). It writes the code; this session orchestrates and keeps its own context clean for the rest of the batch. Its prompt:

> Read `<skills_dir>/coding-agent/SKILL.md` and follow it for all code you write. Implement feature `<id>` in `<repo>` on the checked-out branch. Don't commit, push, or switch branches.
> Spec: `<the plan file entry and its linked feature file>`. Blueprint walk stops for this feature, if recorded in the plan: `<stops>`. Plan of action: `<plan>`.
> This is spec-driven, not strict TDD: write tests for the core logic (the parts with real risk of being wrong, and anything flagged as a security risk) alongside the code. Skip tests for trivial glue, straightforward wiring and thin wrappers. Match the repo's test framework (default `pytest`), and run the suite before you finish.
> Finish with a report: files changed; tests added and the suite result; every deviation from the blueprint, with why; any `shortcut:` comments; new dependencies; anything that changes the blast radius; what you skipped or didn't check.

Wait for its completion notification. **Keep a running build log** for the as-built walk, filled from each report: deviations, debt and shortcuts, blast-radius changes. Check that the suite really passes before moving on.

### 4b — Independent review

Once tests pass, invoke the `risk-inspector` skill in **`cycle`** mode for this feature. Base is `HEAD` (that feature's own worktree `HEAD`, when built in parallel), because the feature is still uncommitted. Give it the feature spec (the plan file entry and its linked feature file, if any), this feature's plan of action, and the blueprint stops it touches. risk-inspector runs a fresh reviewer subagent and a fresh verifier subagent in the background, and returns the verified findings. Its findings files go in `.walks/<batch-id>/reviews/`.

### 4c — Converge

- Send the open findings back to **the same coding subagent** (SendMessage, so it keeps its context of the feature). It fixes every open `critical`, `high` and `medium` finding, adding or adjusting targeted tests so each fix is pinned down. It fixes `low` findings when cheap, and marks the rest `accepted` with a one-line reason. It reports back in the same format as 4a. If that subagent can no longer be reached, spawn a fresh one with the 4a prompt plus the findings.
- Re-run risk-inspector for the next round. It re-checks the previous findings and reviews the fixes.
- Stop after **3 rounds**, or sooner when no open `critical/high/medium` findings remain. **Don't interrupt the user mid-batch.** Whatever is still open goes onto the as-built walk, mapped as risk-inspector's "Mapping to the floor walk" table describes. Resolved findings go into the walk's "caught in review" lists.

### 4d — Commit locally

Commit the feature: one commit per feature, with a message naming the feature id. **Don't push.** When built directly on the batch branch, commit there. When built in a worktree (parallel level), commit there first, then merge the worktree branch into the batch branch and remove the worktree, as described above.

If a feature turns out much bigger than the plan implied, use judgment to keep going, but record what grew and why in the build log. It becomes a `deviation` flag.

## Step 5 — When a later feature no longer makes sense

If building a feature reveals that a later feature (or level) in the batch is now wrong-headed (its spec no longer makes sense), stop before starting it. Tell the user what changed and ask whether to continue, re-plan it, or drop it. This is the only mid-batch interruption.

## Step 6 — Refresh the architecture map

After the last feature, invoke the `architecture-map` skill on the repo.
- If it reports the map was already fresh, there's nothing to commit.
- Otherwise, commit the `ARCHITECTURE.md` / `.architecture/domains/*.md` changes as **their own commit**, separate from the feature commits, so the history distinguishes "the features" from "the doc update the features caused".

The refreshed map is also the floor plan for the as-built walk.

## Step 7 — As-built walk

This is the one full review in this skill — the user already signed off on the planned shape at the blueprint stage (Step 1), so this walk is where they review what was actually built.

Invoke `floor-walk` in **`as-built`** mode against `<base>...HEAD`. Pass it the blueprint walk's data and URL if the plan file recorded one (Step 1), the build log (deviations, debt), every feature's final risk-inspector findings from `.walks/<batch-id>/reviews/` (mapped to flags and "caught in review" lists as risk-inspector describes), and the test results. If there's no blueprint walk to pass, proceed without one — `floor-walk` compares deviations against the spec instead. It publishes the walk, writes `.walks/<batch-id>/as-built.md`, and waits.

When the review comes back:
- **Changes requested** → for each "Change this" flag, make the change on the batch branch (re-running 4a-4c for the affected feature, and committing as a follow-up commit). Then re-publish the as-built walk on the same URL and wait again.
- **Approved** → continue.

## Step 8 — Push and open a thin PR

Commit the `.walks/<batch-id>/` records (with the review outcomes appended) as their own commit. Push the branch and open **one** pull request. The body is deliberately thin, because the walk is the review and the PR is the record:

```
<3-line summary: what this batch does, and the features it covers (ids + names)>

Reviewed on a floor walk: <as-built walk link><, blueprint: <blueprint walk link>, if the plan recorded one>
Records: .walks/<batch-id>/
```

## Step 9 — Wrap up

Report back in chat, briefly:
- the PR link
- test results
- whether the architecture map was refreshed or already fresh
- features left out of the batch (Step 2) and what each needs
- anything from the build log the user should still know that isn't already on the walk
