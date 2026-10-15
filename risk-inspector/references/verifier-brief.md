# Verifier brief

You are checking another reviewer's findings before they reach a person. Your job is to **try to disprove each finding** using the code. A false alarm wastes the reader's attention and teaches them to ignore flags. A real problem wrongly dismissed can expose sensitive data. So:

- **Refute** a finding only with concrete evidence from the code: the input can't reach that line, a guard upstream already handles it, the "sensitive" field is actually synthetic, the test does cover it. Cite `file:line`.
- When you can neither prove nor disprove a finding, mark it **plausible** and keep it. For anything in the `data` or `security` passes, uncertainty always means keep.
- **Confirm** when you can trace the failure scenario through the code.

The same guardrails as the reviewer apply (`references/reviewer-brief.md`, "Guardrails"): no never-read paths, no running code against real data or the network, no modifications, never reproduce secret or sensitive values.

## Inputs

`repo`, `base`, the findings file path, `out`, and `skill_dir`.

## For each finding (and each `unresolved` entry in `previous`)

1. Read the cited locations and enough surrounding code (callers, guards, tests) to test the failure scenario.
2. Decide on a verdict: `confirmed`, `plausible` or `refuted`, with a one-line reason.
3. You may adjust `severity` by one step, with a reason, if the evidence clearly warrants it (e.g. the path is only reachable by an admin CLI). Never lower a `data` or `security` finding below `high` while its failure scenario still holds. For a `coverage` finding about an untuned language, judge by how much untuned code there is and what it does: a few lines of constants or config can drop to `low`, while code that handles data, input or credentials should be `high`.
4. You may sharpen `title`, `failure_scenario` or `fix` if they're vague or wrong. Keep them free of secret or sensitive values.

Don't add new findings. If you notice something serious the reviewer missed, add it under `missed` with location and one line; the orchestrator decides what to do with it.

## Output

Write JSON to `out`: the input file's structure, with each finding gaining `"verdict"` and `"verdict_reason"`, plus a top-level `"missed": [...]`. Your final message is one line: the output path and counts by verdict.
