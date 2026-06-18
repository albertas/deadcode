# Design Discussion

## Current State

The `deadcode/` package is a working CLI tool that detects (and optionally
removes) unused Python code via two AST passes. The code is well factored across
`deadcode/actions/` (pipeline steps), `deadcode/visitor/` (AST traversal), and
`deadcode/utils/` (helpers), but **there is no human-facing architecture
documentation**.

- `docs/` exists but contains only assets: `docs/_static/` holds a logo and a
  license SVG — no markdown, no index, no narrative.
- The only prose today is `README.md` (user-facing install/usage) and inline
  comments/TODOs in source (e.g. `code_item.py:39` "should be dataclass").
- Knowledge of how the system fits together is entirely encoded in `research.md`
  and the source itself. A new contributor must reverse-engineer the flow from
  `cli.py:12-31` outward.

So a contributor onboarding today reads `README.md` for usage, then has no map
from the console entry point (`pyproject.toml:38` → `deadcode.cli:main`) to the
five pipeline stages, the visitor layer, or the shared data types.

## Desired End State

A set of markdown files under `docs/` that lets a contributor understand the
system end-to-end without reading every source file first. Structure:

- `docs/index.md` — high-level project goal (what deadcode is, why AST-based),
  plus an index linking to every other doc file.
- `docs/architecture.md` — the five-stage pipeline from `cli.main` to
  output/file mutation, with a flow diagram and `file:line` anchors.
- `docs/cli-and-configuration.md` — argument parsing, `pyproject.toml` merge,
  the `Args` dataclass, and every flag.
- `docs/visitor-layer.md` — AST parsing, defined/used collectors, scopes, noqa.
- `docs/unused-detection-and-ignoring.md` — how "unused" is decided and the
  ignore/exclude mechanisms (including which options are not yet wired up).
- `docs/fix-and-output.md` — merge/remove `Part`s, diff rendering, error messages.
- `docs/data-types.md` — `Args`, `Part`, `CodeItem`, constants/error codes.
- `docs/testing-and-tooling.md` — `tests/` layout, `BaseTestCase`, Make/Just.

**Verification** (success criteria, since there is no compile step for docs):

1. `docs/index.md` exists and links to all sibling files; no link is dangling.
2. Every `file:line` reference in the docs resolves to a real location (spot-
   check the anchors cited in `research.md`).
3. Each of the seven research questions (Q1–Q7) is answered by some doc file.
4. The "partly-unimplemented ignore options" gap (research Open Areas) is
   documented, not silently omitted.
5. `just check` / `make check` still pass (docs are markdown; no code touched, so
   this is a regression guard only).

## Patterns to Follow

- **Ground every claim in `file:line`.** The research already cites anchors
  (e.g. `cli.py:12-31`, `parse_arguments.py:214-229`, `ignore.py:39-42`); carry
  those into the docs verbatim so they stay checkable.
- **Mirror the package's own module boundaries** in the doc split: actions /
  visitor / utils / data_types+constants. This matches `CLAUDE.md` §7 ("split
  along natural boundaries") and the existing source layout.
- **Use full words, no abbreviations** in prose and any identifiers shown,
  consistent with the repo's Code Best Practices.
- **Describe behavior as it is, including bugs and gaps**, the way `research.md`
  does (e.g. `does_include` copy-paste at `merge_overlaping_file_parts.py:11`;
  inert decorator options at `find_unused_code_visitor.py:54`). Flag them as
  observed, not as recommendations.
- **Reuse `README.md`'s vocabulary** (flag names, `DCxx` codes) so docs and the
  user-facing readme stay consistent; link to `README.md` rather than restating
  install/usage.

Patterns NOT to follow / things to avoid:

- Do **not** invent a Sphinx/MkDocs build or `conf.py`. `docs/_static/` hints at
  a past Sphinx intent, but nothing builds it today; adding a doc toolchain is
  out of scope and would violate "minimum code that solves the problem".
- Do **not** copy the numeric gates (coverage 88%, line-length 120) into prose;
  cite `pyproject.toml` instead, since those drift (per Code Best Practices).

## Design Decisions

1. **Format = plain Markdown, no doc generator** — The task says "split into
   multiple files" with `docs/index.md` as the hub. Plain markdown with relative
   links satisfies that with zero new tooling. Assumption: no Sphinx/MkDocs build
   is wanted despite the orphaned `docs/_static/`.
2. **Eight files, split by subsystem** — One index plus seven topic files mapped
   to research Q1–Q7. Keeps each file focused and matches source module
   boundaries. Alternative (one big `spec.md`) rejected: the task explicitly asks
   for multiple files and durable reference docs.
3. **`index.md` carries the project goal + the link index** — Per the task's
   explicit instruction. Goal text is derived from `README.md` and
   `research.md`'s scope paragraph, not re-researched.
4. **Document the unimplemented ignore options as a known gap** — Rather than
   pretend the API is complete or omit those flags. Surfacing it serves the
   onboarding aim and prevents contributors from assuming the options work
   (research Open Areas; `find_unused_code_visitor.py:54`).
5. **Architecture doc leads with the 5-stage flow** — Because that is the single
   most load-bearing mental model (`cli.py:12-31`); everything else hangs off it.
6. **Reference, don't duplicate, the README** — Install/usage stays in
   `README.md`; docs link to it to avoid two sources of truth drifting.
7. **Include a textual flow diagram, not images** — ASCII/mermaid-style text in
   `architecture.md` keeps diagrams diffable and avoids binary assets.
8. **Describe `cli.main`'s implicit exit semantics** — Note there is no
   `sys.exit` (`cli.py:34-35`); the console wrapper prints the returned string.
   This is a common contributor surprise and worth an explicit callout.

## What We're NOT Doing

- Not changing any `deadcode/` source, tests, `README.md`, `Makefile`,
  `Justfile`, or `pyproject.toml`.
- Not adding a documentation build system, CI doc job, or `conf.py`.
- Not fixing the observed bugs/gaps (decorator options, `does_include`); only
  documenting them.
- Not writing per-function API reference / docstring extraction — this is a
  narrative architecture spec, not generated API docs.
- Not adding diagrams as binary images under `docs/_static/`.
- Not documenting the `old/`, `notes`, `enhancement_proposals/`, or `todo`
  scratch areas; scope is the shipping `deadcode/` package per `questions.md`.

## Open Risks

- **`file:line` drift**: anchors are accurate as of the research snapshot but the
  source changes over time. Mitigation: cite module + symbol name alongside line
  numbers so a stale line is still locatable.
- **Gap documentation tone**: describing unimplemented options risks reading as a
  bug report. Mitigation: state them as "currently inert / not consulted",
  matching `research.md`'s neutral framing.
- **Index completeness**: if a doc file is added/renamed later, `index.md` links
  can rot. Mitigation: keep the index list short and co-located with the files it
  references; verification step 1 covers it for this change.
- **Overlap between docs**: visitor, unused-detection, and fix docs share
  concepts (`Part`, `CodeItem`). Risk of duplication or contradiction.
  Mitigation: define shared types once in `data-types.md` and cross-link.
```
