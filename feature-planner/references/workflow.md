# Feature Planning Workflow

## 0. Triage

Before starting, decide which path to use.

Use the **lightweight path** (below) when the request is a single-file/localized change AND introduces no new user-facing behavioural decisions — for example, a small addition to existing behaviour that follows an obvious existing pattern, an internal-only change, or a narrowly scoped fix-adjacent tweak.

Use the **full path** (Steps 1–15) for anything else, including any request where scope, behaviour, or architecture is ambiguous, where more than one file/component is meaningfully involved, or where a genuine product or architectural decision is needed.

When uncertain, use the full path — it's cheaper to over-invest on a simple request than to under-investigate a genuinely consequential one.

### Lightweight path

1. Confirm the specific desired behaviour if it isn't already fully explicit — one focused question at most, only if truly needed.
2. Locate the relevant code directly; skip repository orientation via `architecture-map`. If `ARCHITECTURE.md` already exists, a quick read of it is fine and cheap — just don't generate or refresh it for a lightweight-path request.
3. Check for one obviously analogous existing pattern to follow, if any.
4. Produce a single feature specification using `templates/feature.md` (see `references/feature-specification.md`), still with real acceptance criteria — the process is shorter, not the quality bar.
5. Skip decomposition and dependency analysis: there is exactly one feature, with no dependencies.
6. Still write `plan.md` (it will list the single feature) and save both files per the output location convention in `SKILL.md`.

If, partway through the lightweight path, the change turns out to be more consequential than it first appeared (touches multiple components, surfaces a real product decision, etc.), switch to the full path rather than forcing it through.

## 1. Intake

Capture:

- the user's broad request;
- stated goals;
- constraints;
- external information;
- known scope;
- explicit non-goals.

Do not immediately convert the request into implementation tasks.

Separate explicit requirements from anything inferred.

## 2. High-level clarification

Before substantial repository investigation, ask questions about product and behavioural intent.

Prioritise:

- desired behaviour;
- motivation and outcome;
- scope;
- permissions;
- user experience;
- external requirements;
- important exceptional cases;
- what must remain unchanged;
- what is explicitly out of scope.

Do not ask implementation questions that repository investigation can answer.

Ask a manageable batch of high-value questions rather than presenting a large questionnaire.

Continue questioning until there is enough understanding of the desired behaviour to investigate the repository intelligently.

## 3. Repository orientation

Use the `architecture-map` skill to get orientation instead of re-deriving it from scratch:

1. Run `architecture-map`'s staleness script against the repository root.
2. If `ARCHITECTURE.md` exists at the repo root and its stored `staleness_key` matches the freshly computed one, read it directly — orientation is done.
3. If it's missing or stale, invoke the `architecture-map` skill to (re)generate it, then read the result.

The map covers top-level structure, apps/packages, frontend/backend boundaries, major domains, test organisation, build/package configuration, and developer/architecture docs — everything this step previously had to derive by hand.

Treat the map as a fast starting point, not ground truth: the staleness key only catches file changes, not semantic drift in code that wasn't touched. Verify anything load-bearing against the actual code during later steps.

Do not attempt to read the entire repository beyond what the map plus targeted investigation in later steps requires.

## 4. Concept discovery

Search for concepts from the user's request rather than relying only on filenames.

For each important concept, establish where it is:

- represented;
- validated;
- persisted;
- transformed;
- exposed;
- tested.

Follow concepts across architectural boundaries where appropriate.

## 5. Find analogous behaviour

Actively search for existing functionality that resembles the requested behaviour.

Look for:

- similar UI controls;
- similar workflows;
- similar validation;
- similar warnings;
- similar permissions;
- similar data models;
- similar API behaviour;
- similar integrations;
- similar tests.

Prefer reuse and consistency unless there is a clear reason not to.

## 6. Trace relevant behaviour end-to-end

Trace the relevant behaviour through the actual architecture.

A typical flow may be:

UI → API → validation → domain model → persistence → business logic → external integration → result/error → UI

Do not assume every layer exists.

Establish:

- where behaviour originates;
- where it is transformed;
- where it is persisted;
- where it is exposed;
- where failures occur;
- where it is tested.

Inspect relevant tests alongside implementation code.

## 7. Investigate Git history selectively

Use Git history when the current code does not adequately explain an important decision.

Useful questions include:

- Why does this abstraction exist?
- Is unusual behaviour deliberate?
- Is an invariant relied upon elsewhere?
- Was similar functionality previously attempted?

Do not perform broad historical investigation without a specific reason.

## 8. Technical clarification

After investigating the codebase, ask detailed technical questions that cannot reasonably be answered by inspection.

For consequential decisions:

1. Explain what the codebase currently does.
2. Explain why the decision matters.
3. Present meaningful alternatives.
4. Give a recommendation where appropriate.
5. Let the user make the consequential decision.

Do not make consequential product or architectural decisions silently.

## 9. Build a shared model

Before feature decomposition, establish:

- current behaviour;
- desired behaviour;
- repository facts;
- external requirements;
- assumptions;
- decisions.

Do not represent assumptions as facts.

## 10. Decompose into behavioural features

Split the work into meaningful behavioural capabilities.

Prefer:

"Persist the export configuration associated with an approved project."

over:

"Add an `export_destination` database column."

The database change is an implementation detail of the behavioural feature.

A feature should be coherent enough to:

- have a clear purpose;
- have meaningful acceptance criteria;
- be independently implemented where its dependencies allow;
- be independently verified.

## 11. Establish dependencies

For each feature, identify prerequisite features.

Consider:

- which features can be implemented independently;
- which must be stacked;
- which can naturally form stacked pull requests;
- which features produce contracts or data consumed by later features.

Do not create artificial dependencies merely to force an order.

## 12. Draft the plan and feature specifications

Before asking the user to review, produce full drafts — they may still change in Step 14:

1. A short human-facing summary plan (`templates/plan.md`).
2. One detailed specification per feature (`templates/feature.md`, see `references/feature-specification.md`).
3. A decision log when consequential decisions were made.

Keep the human summary concise and put detailed technical context in the feature specifications. Do not duplicate feature detail into the summary plan — link to the feature files instead.

For each feature, also work out what the blueprint floor walk (Step 14) needs — there's no need to write this out separately in chat, it feeds the walk directly:

- **Approach**: how it will be implemented.
- **Components and files** it's expected to touch, and any new components or connections.
- **Design calls**: the real forks in the road from Step 8, with what was chosen and why.
- **Planned tests**: the tests implied by the acceptance criteria.
- **Security risks**: input validation, auth boundaries, data exposure, injection, dependencies. These become red `security` flags on the walk.
- **Blast radius**: anything outside this feature that could behave differently. These become red `blast-radius` flags on the walk.

## 13. Planning quality gate

Verify:

- objective is clear;
- scope and constraints are captured;
- external requirements are captured;
- relevant repository areas were investigated;
- analogous behaviour was considered;
- relevant tests and conventions were inspected;
- important ambiguities are resolved or explicitly recorded;
- consequential alternatives have been discussed;
- features represent behavioural capabilities;
- every feature has a clear purpose and dependencies;
- every feature has observable acceptance criteria;
- important edge cases are addressed;
- failure behaviour is defined where relevant;
- features are sufficiently self-contained for independent implementation;
- dependencies form a coherent graph;
- the features collectively achieve the original goal.

If an important item is unresolved, investigate further or ask the user.

## 14. Blueprint floor walk

**Full path only.** The lightweight path's single feature has no new decisions to walk through, so it skips straight to Step 15.

Invoke the `floor-walk` skill in **`blueprint`** mode over the whole plan: the drafted feature specs and their plan-of-action detail (Step 12), plus `ARCHITECTURE.md`. Use the `<feature-name>` slug as the walk's id/name. It publishes the walk, writes a record, gives the user the link, and waits — this is the one point in planning where the user reviews and gives feedback before anything is finalised.

If the decomposition is large enough that the walk would run to many more than ~8 stops, say so when handing off the link — the user may prefer to split the plan — but don't withhold the review over it.

When the review comes back:

- **Approved** → continue to Step 15.
- **Changes requested** → apply each "Change this" note — to a feature spec, the decision log, or the decomposition/dependencies itself if the note calls for it — redraft the affected artefacts (Step 12), re-publish the walk on the same URL, and wait again.
- **The user rejects the decomposition outright** (in a note or in chat) → go back to Step 10 with their reasoning. Don't finalise a shape they've rejected.

Answer any questions the user asks from the walk page in their comment threads (`floor-walk` covers how).

## 15. Save outputs

Write the plan and feature files to `.plans/<feature-name>/` as described in `SKILL.md`, including the blueprint walk's record and link. Record the walk's URL in `plan.md` (see its template) so `implementation-cycle` can carry it through to the as-built walk and the PR. Tell the user where the plan was saved and that it is ready to hand off to the `implementation-cycle` skill, already reviewed.
