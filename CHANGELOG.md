# Changelog

## Unreleased

- `--changed-only [REF]` checks only the versions that differ from a git ref (PR base in GitHub Actions, `HEAD` locally). Lockfiles that are new in the diff count as fully changed. The Action takes `changed-only: true`.

## 0.1.0 (2026-11-17)

- First release: npm, pnpm, yarn (v1 and berry), bun, uv, poetry, requirements.txt, Cargo.lock and go.sum against npm, PyPI, crates.io and the Go proxy. `--days`, `--ignore`, `--json`, `--strict`, GitHub Action.
