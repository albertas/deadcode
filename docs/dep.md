# Deadcode Enhancement Proposals (DEPs)

## What a DEP is

A Deadcode Enhancement Proposal (DEP) is a design document that proposes a change to Deadcode. It records the problem being solved, the
alternatives that were considered, and the chosen solution with its motivation. DEPs are the project's design record: they explain why a
feature, rule, or process looks the way it does, not just what it does.

## When to write a DEP

Write a DEP for a new analyser feature, a change in reported output or rule semantics, or a change to a process or documented workflow. A DEP
is not needed for a typo, a dependency bump, or a bug fix that restores documented behaviour.

## DEP files and numbering

DEPs live in `enhancement_proposals/dep_<number>.md` and are numbered from 0 upwards. `dep_0.md` is the index; number 0 is reserved for that
index and is not a proposal itself.

The next number is `max(existing numbers) + 1`. Pick it when you open the pull request. A number is never reused or changed after merge, and the
pull request that adds a DEP also adds its row to `enhancement_proposals/dep_0.md`.

## Required header

Every DEP starts with a level-1 title followed by three required bold metadata lines, and the optional `Implemented in` line follows them when the
proposal has been implemented. Each metadata line is written on its own line, separated from the title and from the other metadata lines by a
blank line:

```markdown
# DEP <number> - <title>

**Status**: <status>

**Type**: <type>

**Created**: <YYYY-MM-DD>

**Implemented in**: <version>
```

`Implemented in` is optional. Add it once the proposal has been implemented and released, using the Deadcode version that contains the
implementation, for example `**Implemented in**: 3.1.0`. Leave the line out while the DEP is unimplemented.

`Status` describes where the proposal is in its lifecycle:

| Status | Meaning |
|---|---|
| `Draft` | The DEP is being written and is not yet ready for review. |
| `Proposed` | The DEP is open for review and has not been accepted, rejected, or withdrawn. |
| `Accepted` | The maintainer has accepted the proposal. |
| `Rejected` | The proposal was declined and will not be implemented. |
| `Withdrawn` | The author abandoned the proposal before a decision. |
| `Superseded` | A later DEP replaced this one. |

`Type` describes what kind of change the DEP proposes:

| Type | Meaning |
|---|---|
| `Feature` | Changes analyser behaviour, reported output, or rules. |
| `Process` | Changes how the project is developed, documented, or released. |

## Required sections

Every DEP contains these level-2 sections, in this order:

- `## Problem statement` — what is wrong, missing, or worth improving, and why it matters.
- `## Considered alternatives` — the realistic options that were evaluated, including the option of doing nothing when it applies.
- `## Chosen solution` — the selected option. It must name the rejected alternatives and state why the chosen one was selected.

These optional sections may follow the chosen solution when they help the reader:

- `## Scope` — what the DEP deliberately does not cover.
- `## Implementation notes` — hints for the implementer, without turning the DEP into a design specification.
- `## Open questions` — decisions that are still unresolved.
- `## References` — links to related discussions, documentation, or prior art.

## Template

Copy this skeleton and fill in each part. Delete the optional sections you do not need.

```markdown
# DEP <number> - <title>

**Status**: Draft

**Type**: Feature

**Created**: <YYYY-MM-DD>

**Implemented in**: <version>

## Problem statement

Describe what is wrong, missing, or worth improving, and why it matters.

## Considered alternatives

List the realistic options that were evaluated and what each one would mean for Deadcode.

## Chosen solution

Describe the selected option, name the alternatives it was chosen over, and explain why it was selected.

## Scope

Optional. State what this DEP does not cover. Delete this section if it is not useful.

## Implementation notes

Optional. Add hints for the implementer. Delete this section if it is not useful.

## Open questions

Optional. List decisions that are still unresolved. Delete this section if there are none.

## References

Optional. Link related discussions, documentation, or prior art. Delete this section if there are none.
```

Delete the `Implemented in` line, and the blank line that separates it from `Created`, in the skeleton until the proposal has been implemented and
released.

## Status lifecycle

A new DEP starts as `Draft`. Once the proposal is complete and ready for review, the author changes it to `Proposed`. The maintainer then changes
the status:

- `Draft` to `Proposed` when the author is ready for review.
- `Proposed` to `Accepted` when the maintainer merges the DEP pull request and records acceptance in the same pull request or a follow-up commit.
- `Proposed` to `Rejected` when the maintainer declines the proposal. The DEP file stays in the repository, with the reason recorded in
  `## Chosen solution` or a status-history note.
- `Proposed` to `Withdrawn` when the author abandons the proposal.
- `Accepted` to `Superseded` when a later DEP replaces it. The superseding DEP is named in the superseded file.

`Rejected` and `Superseded` are terminal. Git history is the audit trail for every status change; no separate changelog is required.

## Submitting a DEP

Write the DEP under `enhancement_proposals/`, add its row to `enhancement_proposals/dep_0.md`, and open a pull request targeting `main`. The pull
request contains the new `enhancement_proposals/dep_<n>.md` file and the index row in `dep_0.md`.

The maintainer reviews the proposal and discussion happens in the pull request. Acceptance or rejection is recorded by the `Status` field. For
branch naming, local checks, and the commands to run before opening the pull request, see {doc}`contributing`.

## Existing DEPs

DEP 1 to DEP 3 predate this process. They are marked as `Draft` and are updated to the required format as part of the work that depends on
them. A DEP merged before this process must gain any missing required sections when it is next modified in substance.

The index below is included from `enhancement_proposals/dep_0.md`, so the published documentation and the repository index stay in sync.

```{include} ../enhancement_proposals/dep_0.md
:start-after: "<!-- dep-index-start -->"
:end-before: "<!-- dep-index-end -->"
```

```{toctree}
:hidden:
dep_1
dep_2
dep_3
dep_4
dep_5
dep_6
dep_7
```
