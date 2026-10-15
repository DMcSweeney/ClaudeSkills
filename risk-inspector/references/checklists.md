# Review checklists

Work through every pass that applies. These are prompts for judgement, not boxes to tick: a check that doesn't apply to this change is skipped silently, and a problem these lists don't name is still a finding. Sources the lists draw on: OWASP Code Review Guide and ASVS, CWE Top 25, Google's code review guide, GDPR Article 25 (data protection by design), NIST SSDF.

## Pass 1 — Sensitive data handling (highest priority)

Trace every sensitive field (see the policy) touched by the change, from where it enters to everywhere it can leave.

- **Logging & errors:** is a sensitive value, or an object containing one, ever passed to a logger, f-string in an exception, `print`, `repr`, `__str__`, a traceback, or a metrics label? Watch for whole-object logging (`log.info(f"{record}")`, `logger.exception` with request bodies) and dataframe `.head()` in logs.
- **Egress:** any new network call, file write, export, email, queue message, cache, or third-party SDK? Does sensitive data reach it? Is the destination on the policy's allowed list?
- **Minimisation:** does the code read, copy or keep more fields or rows than the feature needs? `SELECT *`, whole-table loads, joins that pull in sensitive columns needlessly.
- **Temp files & caches:** created in a safe location with restrictive permissions (`tempfile`, not `/tmp/fixed-name`), and deleted on every path, including errors? In-memory caches bounded, and keyed without sensitive values?
- **Identifiers:** sensitive values used as filenames, URL paths/query strings, cache keys, or log correlation IDs?
- **De-identification:** where data is pseudonymised or aggregated, is it reversible? Are small counts suppressed if the policy requires it? Is a salt or key handled as a secret?
- **Test fixtures & examples:** synthetic only. Flag realistic-looking names, dates of birth, identifiers or free text in tests and docs.
- **Retention & deletion:** does new storage respect the policy's retention rules? Is there a deletion path?

## Pass 2 — Security

- **Injection:** SQL built with string formatting or concatenation (CWE-89); shell commands with `shell=True` or interpolated arguments (CWE-78); `eval`/`exec`; template injection; path traversal from user-influenced paths (CWE-22); log injection.
- **Deserialisation:** `pickle`, `joblib`, `yaml.load` without `SafeLoader`, `marshal`, `shelve`, or `torch.load` without `weights_only=True` on anything that can come from outside the process (CWE-502).
- **Authentication & access control:** is every new entry point (endpoint, CLI, job, function exposed to callers) checked for who may call it? Missing checks are the commonest serious flaw (CWE-862/863). Are checks enforced server-side, close to the data?
- **Secrets:** hardcoded credentials, keys in config committed to git, secrets passed on command lines (visible in process lists), secrets in exception messages. Never quote a secret's value in a finding.
- **Crypto:** home-made crypto; MD5/SHA1 for security purposes; `random` instead of `secrets`; static IVs/nonces; TLS verification disabled (`verify=False`).
- **Outbound requests:** URLs from user or config input (SSRF); missing timeouts; following redirects to arbitrary hosts.
- **Input validation:** validated at the trust boundary, with an allow-list where possible? Size limits on uploads and payloads?
- **Dependencies:** new packages: well maintained, pinned, from the expected registry, not typo-squatted? Do they pull in network or telemetry behaviour?
- **Failure modes:** fail closed? A caught exception must not skip an authorisation or validation step.

## Pass 3 — Correctness

- Does it do what the spec's acceptance criteria say, including edge cases: empty, one, many, duplicates, nulls/NaN, unicode, time zones and DST, leap days, very large inputs?
- Error handling: bare `except:` / `except Exception: pass`; errors swallowed or turned into wrong-but-plausible results; retries that aren't idempotent.
- Concurrency: shared mutable state, race conditions, check-then-act on files or rows, transactions that should be atomic.
- Resource handling: files, connections and cursors closed (`with`); subprocesses waited on; partial writes on failure.
- Numeric issues: float equality, integer division, rounding of money or doses, unit mix-ups.
- Do the tests actually test the risky logic? Would they fail if the code were wrong? Check for tests that assert on mocks of the thing under test.

## Pass 4 — Design & blast radius

- Changed public signatures, return types, defaults, exceptions raised, file formats, schemas, environment variables, CLI flags. Who else calls or consumes them? Use grep to find callers.
- Migrations: reversible? Safe on a large table (locks, rewrites)? Backfills idempotent?
- Coupling: does the change reach across a module boundary that `ARCHITECTURE.md` describes?
- Is the abstraction right-sized? Flag both premature generality and copy-paste that should be shared.
- Configuration: new settings with unsafe defaults.
- Drift: where the code differs from the plan of action or blueprint stops you were given. Undisclosed drift in behaviour or interfaces is a finding.

## Pass 5 — Efficiency

Only flag what plausibly matters at the data sizes the project handles; ask "how big does this get?".

- Python: loops over dataframe rows (`iterrows`, `apply` with Python functions) where vectorised operations exist; repeated `concat`/`append` in a loop; loading whole files or tables into memory when streaming or chunking would do; O(n²) membership checks on lists; regex compiled in a loop.
- SQL: N+1 queries from application loops; missing indexes for new filters/joins; `SELECT *`; functions on indexed columns in `WHERE`; unbounded result sets; correlated subqueries that should be joins.
- I/O: unbatched network/database calls; no timeouts; reading the same file repeatedly.

## Pass 6 — Readability & style

Follow the repo's existing conventions first; where the repo is silent, follow the language norm (PEP 8 / PEP 257 for Python, the Google Shell Style Guide for shell, the repo's SQL formatting or sqlfluff defaults). Don't flag style the linter already reports unless it hides meaning.

- Names say what things are, in the domain's words; no misleading names.
- Functions do one thing; deep nesting flattened with early returns; long functions split where a reader would get lost.
- Comments explain *why*, not *what*; no stale or lying comments; no commented-out code.
- Magic numbers and strings named.
- Type hints on new public Python functions if the repo uses them.
- Dead code, unused imports and parameters.

## Language specifics

### Python
`subprocess` with lists, never `shell=True` on interpolated input · `pathlib` and `resolve()` + containment checks for user paths · `yaml.safe_load` · `secrets` for tokens · context managers for resources · `logging` with lazy `%s` args, never f-strings of sensitive objects · pandas: watch `SettingWithCopy`, implicit dtype changes, `inplace` misuse · mutable default arguments · timezone-naive datetimes.

### SQL / data pipelines
Parameterised queries only (including in ORMs' `text()`/raw SQL) · identifiers from input must be allow-listed, never parameter-escaped · transactions around multi-step writes · idempotent re-runs of pipeline steps · schema-change safety · `NULL` semantics in joins and `NOT IN` · implicit casts · pipeline outputs written with restrictive permissions · data lineage: can you tell where an output column came from?

### Shell / infra-as-code
`set -euo pipefail` · quote every expansion (`"$var"`) · `--` before user-supplied args · no `eval` · `mktemp` with `trap` cleanup · no secrets in `echo`, `set -x` or CI logs · Dockerfiles: pinned base images, non-root user, no secrets in layers or `ARG`s, `.dockerignore` covers data and env files · CI: least-privilege tokens, pinned third-party actions (by SHA), no untrusted input in `run:` lines · Terraform/IaC: no public buckets, encryption at rest, least-privilege IAM, no secrets in variables committed to git.

### Anything else
If the change includes a language or framework not listed above, review it with these general principles, and report a coverage-gap finding (see the brief): "Reviewed outside the tuned stack: <language>".
