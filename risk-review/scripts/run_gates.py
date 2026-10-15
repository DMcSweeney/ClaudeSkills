#!/usr/bin/env python3
"""Run the automated review gates over the files changed since a base ref.

Usage:
    run_gates.py --repo <path> --base <ref> --out <dir> [--exclude-file <file>] [--sql-dialect ansi]

Scope is the change only: files that differ from <base> in the working tree,
plus untracked files. Paths matching the never-read list (built-in defaults plus
--exclude-file, one glob per line) are never opened or passed to any tool.

Every tool runs through `uv tool run`, so nothing is installed into the project.
Writes <out>/gates.json (summary) and one raw output file per gate, and prints
a short summary. Exit code is always 0 unless the arguments are wrong: a gate
that cannot run is reported as `unavailable`, never silently skipped.
"""
import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import tempfile

DEFAULT_NEVER_READ = [
    ".env", ".env.*", "*.env", "*.pem", "*.key", "*.p12", "*.pfx", "*.jks", "id_rsa*", "id_ed25519*",
    "secrets/", ".secrets/", "credentials*", "*.kdbx",
    "data/", "datasets/", "raw/", "exports/", "dumps/",
    "*.csv", "*.tsv", "*.parquet", "*.feather", "*.arrow", "*.avro", "*.orc",
    "*.xlsx", "*.xls", "*.json.gz", "*.jsonl",
    "*.sqlite", "*.sqlite3", "*.db", "*.dump", "*.bak", "*.sql.gz",
    "*.pkl", "*.pickle", "*.joblib", "*.h5", "*.hdf5", "*.npy", "*.npz",
    "*.dcm", "*.nii", "*.nii.gz", "*.edf",
]

UNTUNED_CODE_EXT = {
    ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".kt", ".kts", ".rb", ".php",
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".cs", ".swift", ".scala", ".r", ".jl", ".m", ".mm",
    ".lua", ".pl", ".pm", ".ps1", ".dart", ".ex", ".exs", ".erl", ".hs", ".clj", ".groovy", ".vb",
}


def run(cmd, cwd, timeout=600):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError as e:
        return 127, "", str(e)
    except subprocess.TimeoutExpired:
        return 124, "", f"timed out after {timeout}s"


def never_read(path, patterns):
    base = os.path.basename(path)
    for pat in patterns:
        pat = pat.strip()
        if not pat or pat.startswith("#"):
            continue
        if pat.endswith("/"):
            d = pat.rstrip("/")
            if path == d or path.startswith(d + "/") or f"/{d}/" in f"/{path}":
                return True
        elif fnmatch.fnmatch(path, pat) or fnmatch.fnmatch(base, pat):
            return True
    return False


def shebang(path):
    try:
        with open(path, "rb") as f:
            first = f.readline(200)
    except OSError:
        return ""
    return first.decode("utf-8", "replace") if first.startswith(b"#!") else ""


def changed_files(repo, base):
    rc, out, err = run(["git", "diff", "--name-only", "--diff-filter=ACMRT", base], repo)
    if rc != 0:
        sys.exit(f"git diff against {base!r} failed: {err.strip()}")
    files = set(out.split())
    rc, out, _ = run(["git", "ls-files", "--others", "--exclude-standard"], repo)
    files |= set(out.split())
    return sorted(f for f in files if os.path.isfile(os.path.join(repo, f)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--exclude-file")
    ap.add_argument("--sql-dialect", default="ansi")
    a = ap.parse_args()

    repo = os.path.abspath(a.repo)
    os.makedirs(a.out, exist_ok=True)
    patterns = list(DEFAULT_NEVER_READ)
    if a.exclude_file:
        with open(a.exclude_file) as f:
            patterns += [ln.strip() for ln in f]

    all_changed = changed_files(repo, a.base)
    excluded = [f for f in all_changed if never_read(f, patterns)]
    files = [f for f in all_changed if f not in excluded]

    py, sh, sql, iac, untuned = [], [], [], [], []
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        name = os.path.basename(f)
        sb = shebang(os.path.join(repo, f)) if not ext else ""
        if ext == ".py" or "python" in sb:
            py.append(f)
        elif ext in (".sh", ".bash") or any(s in sb for s in ("/sh", "bash", "env sh")):
            sh.append(f)
        elif ext == ".sql":
            sql.append(f)
        elif name.startswith("Dockerfile") or ext in (".tf", ".tfvars", ".hcl") or f.startswith(".github/workflows/"):
            iac.append(f)
        elif ext in UNTUNED_CODE_EXT:
            untuned.append(f)

    gates = []

    def record(gate, kind, required, status, files_, count=None, raw=None, note=""):
        gates.append({"gate": gate, "kind": kind, "required": required, "status": status,
                      "files": len(files_), "findings": count, "raw": raw, "note": note})

    def save(name, text):
        p = os.path.join(a.out, name)
        with open(p, "w") as f:
            f.write(text)
        return p

    # 1. Secrets (always, over every changed file we may read). detect-secrets reports hashes, never values.
    if files:
        rc, out, err = run(["uv", "tool", "run", "--from", "detect-secrets", "detect-secrets", "scan", *files], repo)
        try:
            n = sum(len(v) for v in json.loads(out)["results"].values())
            record("secrets", "security", True, "ran", files, n, save("secrets.json", out))
        except (ValueError, KeyError):
            record("secrets", "security", True, "unavailable", files, note=(err or out).strip()[-400:])
    else:
        record("secrets", "security", True, "skipped", files, note="no readable changed files")

    # 2. Python static security analysis.
    if py:
        rc, out, err = run(["uv", "tool", "run", "bandit", "-f", "json", "-q", *py], repo)
        try:
            d = json.loads(out)
            for r in d["results"]:
                r.pop("code", None)  # snippets can carry secret values; file + line is enough
                r["issue_text"] = re.sub(r"'[^']*'", "'***'", r.get("issue_text", ""))
            n = len(d["results"])
            record("python-sast", "security", True, "ran", py, n, save("bandit.json", json.dumps(d, indent=1)))
        except (ValueError, KeyError):
            record("python-sast", "security", True, "unavailable", py, note=(err or out).strip()[-400:])
        rc, out, err = run(["uv", "tool", "run", "ruff", "check", "--no-fix", "--output-format", "json", *py], repo)
        try:
            n = len(json.loads(out))
            record("python-lint", "quality", False, "ran", py, n, save("ruff.json", out))
        except ValueError:
            record("python-lint", "quality", False, "unavailable", py, note=(err or out).strip()[-400:])
    else:
        record("python-sast", "security", False, "skipped", py, note="no Python changes")

    # 3. Dependency vulnerabilities (pinned manifests only; never installs the project).
    manifests = []
    with tempfile.TemporaryDirectory() as td:
        if os.path.isfile(os.path.join(repo, "uv.lock")):
            rc, out, err = run(["uv", "export", "--frozen", "--format", "requirements-txt", "--no-emit-project",
                                "-o", os.path.join(td, "uv-lock.txt")], repo)
            if rc == 0:
                manifests.append(("uv.lock", os.path.join(td, "uv-lock.txt")))
            else:
                record("dependencies", "security", True, "unavailable", ["uv.lock"], note=err.strip()[-400:])
        for f in sorted(os.listdir(repo)):
            if f.startswith("requirements") and f.endswith(".txt"):
                manifests.append((f, os.path.join(repo, f)))
        for label, path in manifests:
            rc, out, err = run(["uv", "tool", "run", "pip-audit", "-f", "json", "--no-deps", "--disable-pip",
                                "-r", path], repo)
            try:
                d = json.loads(out)
                n = sum(len(dep.get("vulns", [])) for dep in d.get("dependencies", []))
                record(f"dependencies:{label}", "security", True, "ran", [label], n,
                       save(f"pip-audit-{label.replace('/', '_')}.json", out))
            except ValueError:
                record(f"dependencies:{label}", "security", True, "unavailable", [label],
                       note=(err or out).strip()[-400:])
    if not manifests and not any(g["gate"] == "dependencies" for g in gates):
        record("dependencies", "security", False, "skipped", [], note="no uv.lock or requirements*.txt")

    # 4. Shell.
    if sh:
        rc, out, err = run(["uv", "tool", "run", "--from", "shellcheck-py", "shellcheck", "-f", "json", *sh], repo)
        try:
            n = len(json.loads(out))
            record("shell", "security", True, "ran", sh, n, save("shellcheck.json", out))
        except ValueError:
            record("shell", "security", True, "unavailable", sh, note=(err or out).strip()[-400:])

    # 5. SQL lint (style and parse errors; injection is a reading pass, not a linter's job).
    if sql:
        rc, out, err = run(["uv", "tool", "run", "sqlfluff", "lint", "--format", "json",
                            "--dialect", a.sql_dialect, *sql], repo)
        try:
            n = sum(len(x.get("violations", [])) for x in json.loads(out))
            record("sql-lint", "quality", False, "ran", sql, n, save("sqlfluff.json", out))
        except ValueError:
            record("sql-lint", "quality", False, "unavailable", sql, note=(err or out).strip()[-400:])

    # 6. Semgrep (optional: its rules download from semgrep.dev, which may be blocked).
    configs = (["p/python"] if py else []) + (["p/bash"] if sh else []) + (["p/sql-injection"] if py or sql else [])
    if configs:
        targets = py + sh + sql
        cmd = ["uv", "tool", "run", "semgrep", "scan", "--metrics", "off", "--json", "-q"]
        for c in configs:
            cmd += ["--config", c]
        rc, out, err = run(cmd + targets, repo)
        try:
            d = json.loads(out)
            if d.get("errors") and not d.get("results"):
                raise ValueError(str(d["errors"][0].get("message"))[:400])
            for r in d["results"]:
                r.get("extra", {}).pop("lines", None)  # same reason as bandit's snippets
            record("semgrep", "security", False, "ran", targets, len(d["results"]),
                   save("semgrep.json", json.dumps(d, indent=1)))
        except ValueError as e:
            record("semgrep", "security", False, "unavailable", targets, note=str(e) or (err or out).strip()[-400:])

    summary = {
        "repo": repo, "base": a.base,
        "changed": len(all_changed), "reviewed": files, "excluded_never_read": excluded,
        "by_kind": {"python": py, "shell": sh, "sql": sql, "infra": iac},
        "untuned": untuned,
        "gates": gates,
    }
    with open(os.path.join(a.out, "gates.json"), "w") as f:
        json.dump(summary, f, indent=2)

    print(f"{len(files)} changed file(s) in scope, {len(excluded)} excluded as never-read, "
          f"{len(untuned)} in untuned languages")
    for g in gates:
        flag = "" if g["status"] != "unavailable" or not g["required"] else "  <-- REQUIRED GATE DID NOT RUN"
        cnt = "" if g["findings"] is None else f", {g['findings']} finding(s)"
        print(f"  {g['gate']:<28} {g['status']:<12}{cnt}{flag}")
    print(f"summary: {os.path.join(a.out, 'gates.json')}")


if __name__ == "__main__":
    main()
