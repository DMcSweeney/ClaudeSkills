---
name: floor-walk
description: "Builds an interactive 'floor walk' review page for a set of code changes. The reviewer is walked through the system like a shop manager on a floor walk: a fixed map of the system with the changed domains lit up, a detail map of where inside them things moved, one list of every issue and risk, then one stop per changed component covering what changed, why, knock-on effects, evidence it works, and red/yellow flags to sign off. Two modes: a blueprint walk (before code is written, from per-feature plans) and an as-built walk (after, from a branch diff). Use it when implementation-cycle reaches a review checkpoint, or whenever the user asks to be walked through, shown, or to review changes on a branch, a PR, or a planned set of features at a high level rather than line by line."
model: opus
---

# Floor Walk

A floor walk is how the user reviews code. They are the shop manager walking the floor, not an inspector with a magnifying glass. Tests and the `risk-inspector` skill own line-level correctness. The walk answers four questions:

1. **Where** in the system did things move? (the system map and the detail map)
2. **What** changed at each place, and **why**? (the stops)
3. **What does it affect** beyond itself? (knock-on effects)
4. **What needs my judgement?** (red flags, which they must mark, and yellow flags, which are for awareness)

The user's own words for what overwhelmed them with PRs: too frequent, arrives too late, can't see the impact. Every choice below serves those three.

Read the walk as the user does: a manager of a large system. They want the overall picture first and they always want to know about issues, inefficiencies and risks. Individual code changes matter less to them. That means:

- **Plain language.** Lead with what something does for the system, in words a manager would use. IDs, paths and branch names are for cross-reference only; the page shows them small and grey.
- **The same map every time.** The system map is copied from `ARCHITECTURE.md` unchanged, so every walk starts from a picture the user already knows.
- **Issues are never buried.** Every flag appears in one issues list near the top as well as on its stop.

## Modes

| Mode | When | Built from | Stops show |
|---|---|---|---|
| `blueprint` | Before any code is written | Per-feature plans of action, the plan/spec files, `ARCHITECTURE.md` | Planned changes, design calls, planned tests, anticipated flags |
| `as-built` | After the code is written, before push | `git diff <base>...HEAD`, the blueprint walk (if any), test results, risk-inspector findings | Actual changes, evidence, deviations, full diff per stop |

Used outside implementation-cycle (e.g. "walk me through branch X"), run `as-built` with no blueprint. Then `deviation` flags compare against the stated intent instead (PR description, commit messages, linked issue). If there is no stated intent, there are no deviation flags.

## Step 1 — Gather

- **Map source:** read `ARCHITECTURE.md` at the repo root (see the `architecture-map` skill): its Domain map, Structure overview and Domains table (ids and colours). If it has no Domain map or no domain colours, run `architecture-map` to upgrade it before going on. Otherwise don't regenerate it here: if it is stale, use what's there and verify the touched parts against the code.
- **Blueprint:** the per-feature plans of action and the feature spec files.
- **As-built:** `git diff --stat <base>...HEAD`, then the diff itself. Also gather the test run output, the final `risk-inspector` findings (mapped to flags and `caught` lists by risk-inspector's mapping table), and the blueprint walk's data if one exists (the JSON from `.walks/<batch>/blueprint.md`, or the published page).

## Step 2 — Plan the route

Stops are **components**, not files. A component is something a person would point at on the map: a service, a module, a table, a queue, a page.

- Group the changed files by the component they belong to. One stop per component that changed meaningfully. Each stop belongs to one domain from `ARCHITECTURE.md`.
- **Order the stops along the flow**, the way a request or data travels through the system, so each stop sets up the next. Don't order alphabetically or by size.
- Put all the mechanical changes (renames, config, fixtures, docs, the `ARCHITECTURE.md` refresh) in one last stop called **Housekeeping**. It usually has no flags.
- Aim for 3-8 stops for a batch. Beyond 8, the batch was too big; say so in the hand-off.

## Step 3 — Write each stop

Write for a manager who knows the system but hasn't seen this work. Use short, concrete sentences. Say what a thing does before naming the function, endpoint or table that does it.

- **headline** and **purpose** (walk level): the headline says what the batch does for the system in one line; the purpose says, in 1-2 sentences, what problem it solves and who or what benefits. If either needs a file name or an ID to make sense, rewrite it.

- **what** and **why**: 1-2 sentences each. "Why" ties back to the spec, or names the problem being fixed.
- **ripple**: other components, callers, data or users this touches. Write "None" only when that's true. This is the field that answers "can't see the impact", so think hardest here: callers of changed signatures, consumers of changed data, changed defaults, migrations, new outbound calls, new permissions.
- **decisions** (blueprint mainly; as-built when a new call was made during the build): the choice, what it was chosen over, and why in one line. Only real forks in the road, never restated facts.
- **proof**:
  - as-built: real test names rewritten as plain sentences, with their real pass/fail status. Add behaviour receipts (a before/after of something you actually ran) where you have them. Never list a test that doesn't exist, or a run you didn't do.
  - blueprint: the tests you plan to write, with status `planned`.
- **flags** follow the severity rules below.
- **caught** (as-built only): risk-inspector findings that were found and fixed during the review loop, as `{title, severity, pass}`. They render as a collapsed "Caught in review" list, so the user can see the reviewer working without being asked to act.
- **diff** (as-built only): `git diff <base>...HEAD -- <this stop's paths>`.

### Flags

| Level | Category | Raise it when |
|---|---|---|
| Red | `deviation` | The build differs from the blueprint/spec in substance: a different approach, a missing acceptance criterion, a scope cut, extra scope. As-built only. |
| Red | `security` | Anything touching trust boundaries: input handling, auth, secrets, data exposure, outbound calls to user-controlled targets, new dependencies. |
| Red | `blast-radius` | Something outside this batch can now behave differently or break: changed public signatures, migrations, defaults, shared config, removed behaviour. |
| Red | `unresolved` | A `critical`/`high` risk-inspector finding still open after the round cap (that isn't `security` or `blast-radius`), or a high-severity review coverage gap: a required gate that couldn't run, or untuned-language code that handles data, input or credentials. |
| Yellow | `debt` | Shortcuts, TODOs, known limitations, deliberately deferred work, missing tests for non-core paths, **inefficiencies** (wasted work, duplication, extra queries or calls, cost or performance that won't hold at scale), and open or accepted `medium`/`low` risk-inspector findings. |

- The user must mark every red flag **OK** or **Change this**. Yellow flags never block.
- Don't invent flags to look thorough. Don't drop or soften flags to make the walk look clean. A walk with zero red flags is fine when true.
- Always raise inefficiencies you know about, even small ones, as yellow `debt` flags whose title names the inefficiency. The user wants to know about them, not just about risks.
- A red flag states the fact and its limits: "Guarded against private IPs; DNS rebinding not handled." Don't write a vague "might be a security concern".
- In a blueprint walk, raise the red flags you can already foresee (e.g. "this needs a migration on the orders table"), so the user signs off before you build.

## Step 4 — Draw the maps

Follow the map rules in `references/walk-data.md`. In short:

- **System map:** the Domain map from `ARCHITECTURE.md`, copied verbatim. Append a domain this batch adds, never rearrange. Fill `domains` with every domain on it, its colour from `ARCHITECTURE.md`, and its change for this batch. The page colours it, so the same domain is the same colour on every walk.
- **Detail map:** from the Structure overview, the touched domains as subgraphs (tinted by domain) with the touched components and their neighbours, reusing the canonical ids. Number the stops in the labels, mark change type with the `modified` / `added` / `removed` classes (teal / purple / red; untouched is grey), and label the new connections. Set each stop's `domain` and `node`.

The page shows each map fitted whole, with drag and zoom and a full-window view, so don't restyle a map or trim it to make it fit.

Write the `floorplan_caption` as the one thing the reader should see ("Only Payments changes inside; a new Merchant integrations domain hangs off it").

## Step 5 — Build and publish the page

1. Copy `templates/walk.html` to the scratchpad as `walk-<batch-id>-<mode>.html`.
2. Replace the `walk-data` JSON (schema: `references/walk-data.md`) and the two mermaid blocks under `SYSTEM MAP` and `DETAIL MAP`. Set the `<title>` to a name, e.g. `Checkout Reliability Blueprint`. Don't restyle or restructure the template; consistency between walks is what makes them quick to read.
3. Validate the JSON (`python3 -c 'import json,re,sys; ...'` or similar). Check that every red/yellow level matches its category, every stop's `domain` is in `domains`, and every stop's `node` appears in the detail map.
4. Publish with the Artifact tool:
   - `capabilities: {"db": {}, "user": {}, "comments": {}}`
   - `icon: "map"`
   - a one-sentence `description`
   - First publish of this walk: no `url`. Re-publish: the same file path in this session, or the walk's `url` from an earlier session. Before re-publishing a walk for another round, `ArtifactData delete review/state` (see `references/walk-data.md`).
5. The page starts private. It contains code, so don't suggest sharing it unless the user asks.

## Step 6 — Keep a record

Write `.walks/<batch-id>/<mode>.md` in the repo. The heading is the walk's headline and link, then the purpose, followed by a short markdown rendering of the stops: each stop's what/why/ripple and its flags. Then a fenced `json` block with the full walk data, minus diffs. After the review, append the outcome (each red flag's verdict and note, plus the overall verdict). implementation-cycle commits these files. When running standalone, leave them uncommitted and mention them.

## Step 7 — Hand off and wait

Give the user the link in one or two lines: what's on the walk (N stops, N red flags) and that the page's **Approve** / **Send back** button tells you when they're done. Then end your turn; the review happens on the page.

While waiting:

- **A comment sent to Claude from a stop** (the "Ask Claude about this stop" box), **or from a red flag's note** (its "Send to Claude" button, once the user has marked it "Change this" and written what should change) arrives as a comment notification either way. Answer it in that comment thread with the `ArtifactComments` tool, using the real repo to answer or discuss. Keep answers short, and if the honest answer reveals a new problem, say so and add a red flag on the next re-publish. If an automatic reply already landed in the thread, read it. When it is generic or misread the question, post a real answer as a follow-up (`acknowledge_duplicate: true`), opening with a one-line correction. Resolve the thread once it's answered. A flag's note is still the authoritative record of what to change when the review finishes — a discussion in its thread doesn't replace it; if the discussion changes what the user wants, make sure the note reflects that before you treat the review as finished.
- **"Review finished: …"** (sent by the page), or the user saying they're done in the terminal: read `review/state` and `acks` with `ArtifactData`. If `review/state` is missing, ask the user to press the button or tell you their calls.

Return to the caller (or report to the user):
- `approved` → proceed.
- `changes_requested` → the list of flags marked **Change this**, each with its note. If a flagged item has an empty note and the change isn't obvious from the flag itself, ask in the "Review finished" thread what they want changed. Don't guess. The caller makes the changes, then re-runs this skill in the same mode on the same URL. Keep stop and flag ids stable as set out in the schema rules.

## Things a walk is not

- It is not a substitute for tests or for the internal review loop. If a stop needs line-by-line scrutiny to trust, that's a missing test, so add a red `unresolved` flag rather than asking the user to read code.
- It is not a changelog. Leave out anything that doesn't help the user judge, understand or own the change.
