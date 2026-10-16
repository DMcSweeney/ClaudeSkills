---
name: risk-inspector
description: "Rigorous, risk-averse code review for software that handles sensitive data. Runs in the background with no user interaction: an independent reviewer subagent runs automated gates (secrets, static analysis, dependency audit, shell and SQL linters) and six review passes (sensitive-data handling, security, correctness, design and blast radius, efficiency, readability), then a second subagent tries to disprove each finding. Unresolved findings become flags on a floor walk, and fixed ones appear there as 'caught in review'. Used by implementation-cycle after each feature's tests pass. Also use it when the user asks to review, audit or security-check a branch, PR or set of changes."
---

# Risk Inspector

An independent, risk-averse reviewer for code that will handle sensitive data. The user never interacts with it directly. Everything it finds reaches them through a floor walk (the `floor-walk` skill): unresolved issues as flags they sign off, and resolved ones as a quiet "caught in review" list.

The reviewer itself never sees sensitive data. It reviews how the *code* treats sensitive data, and it is fenced off from data files, env files and real services (see the guardrails in `references/reviewer-brief.md`).

**How it's built:**
- automated gates (`scripts/run_gates.py`)
- a fresh reviewer subagent working through the checklists (`references/reviewer-brief.md`, `references/checklists.md`)
- a fresh verifier subagent that tries to disprove each finding (`references/verifier-brief.md`)
- this skill, which orchestrates the rounds and maps the results onto the floor walk

Author and reviewer are always separate contexts. Never review code in the same context that wrote it.

## Modes

| Mode | Trigger | Loop | Output |
|---|---|---|---|
| `cycle` | implementation-cycle, after a feature's tests pass | Review → the cycle fixes → re-review, up to 3 rounds | Findings files, which the cycle passes to the as-built walk |
| `standalone` | The user asks to review a branch, PR or diff | One round; nothing is fixed unless the user asks | An as-built floor walk of the branch, with findings as flags |

## Running one round

1. **Set up.**
   - Inputs: the repo root and the base ref. In cycle mode, the base is `HEAD`: the feature is still uncommitted on the batch branch, so the working tree against `HEAD` is exactly the feature. In standalone mode, it's the merge base with the target branch.
   - Policy: `REVIEW-POLICY.md` at the repo root, else `none`.
   - Findings directory: `.walks/<batch-id>/reviews/` in cycle mode, the scratchpad in standalone mode.
   - Gather the spec and the plan of action (cycle), or the stated intent (PR description, commit messages; standalone).
2. **Reviewer.** Spawn a fresh `general-purpose` subagent (Agent tool, `model: "sonnet"`), and wait for its completion notification. Its prompt:
   > Read `<skill_dir>/references/reviewer-brief.md` and follow it exactly; it references `checklists.md` and `scripts/run_gates.py` in the same skill. Inputs: repo=`…`, base=`…`, out=`<dir>/<feature-or-branch>-r<n>.reviewer.json`, skill_dir=`…`, policy=`…`, round=`n`, previous=`<path or none>`. Spec / stated intent: `…`. Plan of action: `…`.
3. **Verifier.** Spawn a second fresh `general-purpose` subagent (Agent tool, `model: "opus"`) — the verifier's job is adversarial (disprove or confirm each finding), which benefits more from a stronger model than the reviewer's checklist sweep:
   > Read `<skill_dir>/references/verifier-brief.md` and follow it exactly. Inputs: repo, base, findings=`<the reviewer's out>`, out=`<dir>/<feature-or-branch>-r<n>.json`, skill_dir.
4. **Merge.**
   - Drop `refuted` findings, but keep them in the file for the record.
   - Anything in `missed`: in cycle mode, pass it to the next round's reviewer as a lead. In the final round, or in standalone mode, add it as a `plausible` finding using the verifier's wording.
   - Never paste finding text that contains secret or sensitive values into chat. If the reviewer or verifier slipped, redact before going further.

## Cycle mode

implementation-cycle calls one round per review iteration:

- **Round result → fixes.** The cycle fixes every open `critical`, `high` and `medium` finding. It fixes `low` findings when cheap. A `low` it deliberately leaves gets `status: "accepted"` with a one-line reason.
- **Re-review.** Run the next round with `previous` set to the last merged file. The new reviewer marks each previous finding `resolved` or `unresolved`.
- **Cap.** Stop after round 3, or as soon as a round leaves no open `critical/high/medium` findings. Don't interrupt the user mid-batch; the walk is where they see what's left.

## Mapping to the floor walk

When the cycle builds the as-built walk, or in standalone mode, turn the final state of every finding into walk data. Assign each one to the stop that owns its `location`. A finding spanning stops goes to the first stop it touches, with the others named in the detail.

| Final state | On the walk |
|---|---|
| Resolved during the loop | Stop's `caught` list: `{title, severity, pass}` |
| Open, `critical`/`high`, pass `data` or `security` | Red flag, category `security` |
| Open, `critical`/`high`, `external_impact: true` | Red flag, category `blast-radius` |
| Open, `critical`/`high`, any other pass (including `coverage`) | Red flag, category `unresolved` |
| Open or accepted, `medium`/`low` | Yellow flag, category `debt` |
| Refuted | Not shown |

Flag `detail` is the failure scenario plus the fix, in two or three sentences, with the location. Flag ids derive from the finding id (`R2-03` → `r2-03`), so they stay stable across walk re-publishes.

## Standalone mode

1. Run one round against the branch.
2. Invoke `floor-walk` in `as-built` mode with no blueprint, passing the findings mapped as above. Deviation flags compare against the stated intent, if there is one.
3. Tell the user in chat in two or three lines: the walk link, counts of red and yellow flags, and the single most serious finding in one sentence.
4. Fix nothing unless the user asks. If they do, follow cycle mode from round 2.

## Notes

- **Tools** run through `uv tool run`: detect-secrets, bandit, ruff, pip-audit, shellcheck (via `shellcheck-py`), sqlfluff and semgrep. Nothing is installed into the project. Semgrep's rules download from `semgrep.dev`; if that's blocked, semgrep is reported as an unavailable optional gate.
- **Untuned languages:** the tuned stack is Python, SQL/data pipelines, and shell/infra-as-code. Anything else is still reviewed with general principles, and raises a coverage finding so the user knows the review had less depth there. By default it's a yellow flag; it becomes red when the untuned code handles data, input or credentials.
- **Policy file:** to start using one in a repo, copy `templates/REVIEW-POLICY.md` to the repo root. Offer this the first time a repo has no policy, but don't block on it.
