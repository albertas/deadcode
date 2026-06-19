# Design Discussion

## Current State

`ruff check deadcode/ tests/` is **not** clean today. A live run reports **249
errors** (229 in `deadcode/`, 20 in `tests/`) plus several non-error warnings.
The research left this unverified ("Open Areas"); it is now confirmed. The
config (`pyproject.toml:61-163`) uses `select = ["ALL"]` with a ~90-line `ignore`
list and a `tests/*` per-file-ignore block. Ruff infers the target from
`requires-python = ">= 3.11"` (no explicit `target-version`).

Violation breakdown (`ruff check --statistics`):

| Code | Count | Fixable | What |
|------|-------|---------|------|
| UP006 | 79 | yes | `typing.List`→`list` etc. (PEP 585) |
| UP035 | 42 | yes | deprecated `from typing import …` |
| F401 | 35 | yes | unused imports (mostly `fix_unused_code_visitor.py` copied header, Q4) |
| UP045 | 23 | yes | `Optional[X]`→`X | None` |
| RUF059 | 16 | no | unused unpacked variable (merge/remove file-parts, Q4) |
| E501 | 14 | no | line too long (>120) |
| UP007 | 11 | yes | `Union[…]`→`X | Y` |
| SIM905 | 9 | yes | `'a.b'.split('.')`→list literal |
| F841 | 4 | no | unused local |
| PTH109 | 2 | no | `os.getcwd()`→`Path.cwd()` (tests) |
| SIM103 | 2 | no | needless bool (`merge_overlaping_file_parts.py`, Q6) |
| ANN201,D301,D403,EM101,F811,PLR1704,PLR5501,PT011,RUF023,SLF001,TRY003,UP036 | 1 each | mixed | misc |

Non-error warnings also surface: `ANN101` in the ignore list is a **removed
rule** (no effect), and ruff prints "Invalid `# noqa` directive" on
`noqa.py:9-12` because the regex's example comments contain literal `` `# noqa` ``
text (`noqa.py:5-15`) that ruff tries to parse as directives.

## Desired End State

- `just check-lint` (= `ruff check deadcode/ tests/`) exits 0 with **no errors
  and no warnings**.
- The `ignore` list is **trimmed**: every entry that was masking a now-fixed
  violation is removed, so "most" rules are actively enforced. Only deliberate
  project-policy ignores remain.
- The rest of `just check` stays green: `check-format`, `check-complexity`
  (`--select C901`), `check-typecheck` (mypy `strict`), and `test` (pytest,
  `--cov-fail-under=95.0`). Behavior is unchanged.

Verify: `just check` passes end-to-end; `ruff check deadcode/ tests/` produces
zero output; `git diff` touches only lint-driven lines.

## Patterns to Follow

- **Builtin generics / PEP 604 unions** already appear natively in 5 spots
  (`find_unused_code_visitor.py:82`, `fix_unused_code_visitor.py:96,98`,
  `data_types.py:47,50`, research Q1). The UP006/UP007/UP045/UP035 fixes converge
  the whole package onto that existing style. Runtime-safe on 3.11: builtin
  generics and `X | None` evaluate fine in dataclass/`NamedTuple` bodies
  (`data_types.py:13,37`) and `Literal` aliases (`constants.py:4-33`).
- **`_`-prefix for deliberately-unused bindings** is an established convention
  (`merge_overlaping_file_parts.py:6-7` `_insert_condition_*`, CLAUDE.md §6 caveat
  for throwaways). Apply it to RUF059/F841 sites rather than adding `# noqa`.
- **Intentional keeps must survive**: `show` imports carry `# noqa: F401`
  (`find_unused_code_visitor.py:23`, `fix_unused_code_visitor.py:62`) and
  `except:  # noqa: E722` (`parse_abstract_syntax_tree.py:10`). Ruff honors these;
  do not strip them. `[tool.deadcode] ignore_names` (`pyproject.toml:180-197`)
  protects getattr-dispatched `visit_*` etc. — orthogonal to ruff, leave intact.
- **Single internal raise** convention (`fix_unused_code_visitor.py:182`,
  research Q3) is the only EM101/TRY003 site — fixing it once keeps both rules on.
- **Test harness untouched**: `BaseTestCase` patching seams (Q7) and the inline
  source-string fixtures (incl. the intentionally-malformed `# noqa: DC02`
  fixture, `tests/noqa/test_noqa_comments.py:71`) are behavioral — never "fix"
  fixture strings.

Pattern to NOT follow: do not chase line-count reduction on the two near-twin
visitor files (Cross-Cutting Obs). Remove only the imports ruff flags; do not
refactor the duplicated header (CLAUDE.md §3, §7).

## Design Decisions

1. **Autofix-first, then manual** — run `ruff check --fix` (safe fixes only, no
   `--unsafe-fixes`) for the 168 autofixable errors (UP006/UP007/UP035/UP045/
   SIM905/F401/D403/PLR5501/RUF023), then hand-fix the ~80 remaining. Review the
   autofix diff before committing; gate every batch on `just test` + mypy.
2. **No `from __future__ import annotations`** — unnecessary on 3.11 for the
   annotation forms present, and the package currently has zero such imports
   (Q1). Adding it would be speculative scope (CLAUDE.md §2).
3. **Trim, don't expand, the ignore list** — remove `ANN101` (dead/removed rule)
   and every entry now clean after fixes. Keep deliberate-policy ignores:
   docstring opt-outs (`D1xx/D2xx/D4xx`), `T201` (print is the CLI's output
   channel), `S101`, `FBT00x`, `PLR09xx`/`C901` (owned by `check-complexity`),
   `G004`, `COM812`/`ISC001` (formatter conflicts), `RUF100`/`RUF012`.
4. **Fix one-off real issues rather than suppress** — EM101+TRY003 (extract the
   message to a local), UP036 (remove the dead `sys.version_info` branch), F811,
   PLR1704, SIM103 (`merge_overlaping_file_parts.py`), D301/D403, E501 (manual
   wrap). Each is ≤1 site; fixing keeps the rule enforced.
5. **Test-only ignores go in `per-file-ignores["tests/*"]`** — add `SLF001`
   (tests legitimately touch `visitor._log`, `test_find_unused_code_visitor.py:61`)
   and `PT011` *only if* adding `match=` is awkward; prefer adding `match=` to the
   single `pytest.raises(ValueError)` (`test_fix_unused_code_visitor.py:15`).
   Fix the 2 `PTH109` to `Path.cwd()` (small, keeps PTH109 active) rather than
   broaden the already-ignored PTH family.
6. **Silence the `noqa.py` parser warnings** — reword the example comments at
   `noqa.py:8-12` so ruff no longer parses `` `# noqa` `` as a directive (e.g.
   drop the leading `#` from the inline examples or describe them in prose). This
   is required for a *warning-free* run, not just error-free.
7. **Verify F401 removals behaviorally** — the big unused-import block in
   `fix_unused_code_visitor.py` (Q4) includes names possibly reachable via
   attribute access; rely on `just test` + mypy `strict` to catch any wrongly
   removed symbol, not on static reading alone.

## What We're NOT Doing

- Not deduplicating the twin visitor files or their import headers.
- Not changing `[tool.deadcode] ignore_names`, coverage config, or mypy config.
- Not touching fixture source strings or test assertions for cosmetics.
- Not enabling `--unsafe-fixes`.
- Not removing policy ignores (docstrings, print, asserts, complexity).
- Not adding new rules to `select` (already `ALL`); only trimming `ignore`.

## Open Risks

- **Autofix collateral**: `ruff --fix` may remove an import used only via
  getattr/string dispatch. Mitigation: full `just test` + mypy after each batch;
  bisect by rule code if a test breaks.
- **mypy vs. PEP 604 at runtime**: `Optional[X]`→`X | None` in `Literal` aliases
  (`constants.py`) and `NamedTuple`/`dataclass` bodies is evaluated at import; on
  3.11 this is safe, but confirm import-time success via the test run.
- **Hidden ignore couplings**: removing an `ignore` entry may surface a violation
  in a file not in today's 249 (e.g. a rule with zero current hits but latent
  cases). Mitigation: re-run `ruff check` after each ignore-list edit.
- **`noqa.py` warning fix**: rewording comments must not change `NOQA_REGEXP`
  semantics — only comment text above `noqa.py:13` is editable; the regex string
  and `tests/noqa/` fixtures stay byte-identical.
