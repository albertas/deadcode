# DEP 3 - Removal of unused code might create new unused code

**Status**: Accepted

**Type**: Feature

**Created**: 2024-04-16

## Problem statement

Removing an unused definition can make other definitions unused. A definition that is used only by other unused definitions is itself dead, but
the current analyser cannot see that in one run, because every usage inside the unused definition still suppresses the finding of its target.

Consider a module with two functions:

```python
# a.py
def helper():
    return 1


def main_helper():
    return helper()
```

`helper()` is used only by `main_helper()`, and `main_helper()` is used by nothing. One run of `deadcode` reports only `main_helper()`: the call
to `helper()` inside `main_helper()` puts `helper` into the global used-name set, so `helper()` is not reported. Only after the user removes
`main_helper()` and runs `deadcode` again does the tool report `helper()`. A code base where unused definitions call each other needs one rerun
for every level of the cascade, and the user has to repeat the process until the output stops changing.

The feature-request list records this as an unchecked request: "Repeated application of `deadcode` till the output stops changing" (`README.md:349`).
Tools without automatic fixing push the same loop onto their users: vulture documents manual deletion followed by a rerun
(`docs/comparison.md:9`, `docs/comparison.md:46`), while `deadcode` already removes code with `--fix` and can therefore close the loop inside a
single run.

### How deadcode works today

`deadcode` parses each file with `ast` and traverses it once with a visitor. All usages are collected into one global `used_names` set
(`deadcode/visitor/dead_code_visitor.py:71`), and a definition is reported unused when its name is absent from that set
(`deadcode/visitor/ignore.py:68-75`). A name used anywhere keeps every definition with that name alive, no matter where the usage lives or which
definition it actually refers to.

Usages that cannot be resolved statically stay conservative anchors that keep their targets alive: `getattr`/`hasattr` calls with string
constants, old-style `%(name)s` format strings evaluated over `locals()`, decorator names, `__all__` assignments, `MIDDLEWARE` assignments,
match-statement keywords, and unresolvable attribute loads, which are recorded as plain names (`deadcode/visitor/dead_code_visitor.py:566-569`).
This preserves today's false-negative behaviour: dynamic usage can hide dead code, but static analysis never removes live code.

The visitor already retains per-module structures — `module_exports`, `bare_used_names`, `wildcard_imports`, `explicit_imports`,
`qualified_imports`, `import_edges`, and `module_definitions` (`deadcode/visitor/dead_code_visitor.py:74-80`) — but the unused filter consumes
none of them; it compares names only.

The CLI calls `find_unused_names` exactly once per run (`deadcode/cli.py:39`), so a cascade can only be surfaced by running the tool again,
which is the manual loop described above.

## Considered alternatives

### Do nothing and keep manual reruns

- Idea: keep the current single-pass, name-based analysis and let users run `deadcode` repeatedly until the output stops changing.
- Trade-off: no implementation cost and no change to the analysis, but every cascade level costs the user one extra run, and nothing tells the
  user how many runs remain.
- Why not chosen: the unchecked feature request (`README.md:349`) exists precisely because of this loop, so it does not satisfy the single-run
  goal.

### Repeated runs inside the tool

- Idea: have `deadcode` call `find_unused_names` in a loop internally, removing or suppressing findings between iterations until the report is
  stable.
- Trade-off: reachable without new metadata, but it multiplies parse and traversal cost, it needs a stability criterion, and it still models the
  problem as iteration rather than reachability.
- Why not chosen: it moves the iteration from the user into the tool but keeps the same non-single-run model; the reachability formulation in the
  chosen solution reaches the fixed point with one traversal plus one pass.

### Usage-count metadata without usage places

- Idea: record for every definition a count of the usages that reference it and report the definition when its count drops to zero.
- Trade-off: slightly more metadata than a name set, but a bare integer cannot express which usage disappears when its user is removed: when the
  only user of X is removed, X's count must drop by that usage, and a count has no record of which user contributed it.
- Why not chosen: the task's own example — "if a usage place is removed, the corresponding usage could be removed as well" — requires places,
  not counts, so counts alone cannot cascade.

### Usage-place tracking and a usage graph

- Idea: record, for every usage the analyser resolves, the definition it resolves to, and compute reachability over the resulting graph.
- Trade-off: needs per-usage edge records and a reachability pass, but it reuses the per-module structures the visitor already retains and yields
  cascading findings without any rerun.
- Why not chosen: this is the chosen direction; it is described in the next section.

### Full tree building and tree shaking (DEP 4)

- Idea: build the whole-module import graph, declare entry points, and prune everything unreachable, as DEP 4 proposes for Python source bundles.
- Trade-off: resolves per binding, so cascades fall out of one pass, and the JavaScript tools surveyed in DEP 4 (Rollup, webpack, esbuild, Vite,
  Terser, and Closure Compiler) show that the model works.
- Why not chosen: DEP 4 targets whole-module bundle pruning from declared entry points, a different goal with a much larger surface (a side-effect
  model and entry-point configuration). Citing it as prior art and deferring module-level pruning to DEP 4 keeps DEP 3 scoped to the
  definition-level linting and fixing behaviour `deadcode` already has.

## Chosen solution

Build a definition-anchored usage graph and compute transitive reachability from live roots within the single run the tool already performs. The
visitor records, for every usage it resolves, an edge from the usage to the definition it resolves to, reusing the existing per-module structures
(`bare_used_names`, `explicit_imports`, `qualified_imports`, `import_edges`, `module_exports`) and the resolution mechanism proposed in DEP 5.
After the traversal completes, one reachability pass computes the definitions reachable from live roots. Definitions reachable only from other
reported-unused definitions — and not from any live root — are cascading dead code; they are reported together with the existing findings in the
one report, and removed in the same run under `--fix`/`--dry`.

In the problem-statement example, `main_helper()` has no incoming edge from a live root, so it is reported; `helper()` has one incoming edge, but
that edge comes from `main_helper()`, which is itself unreachable, so `helper()` is reported in the same run.

The safety rules of the current tool are preserved:

- Unresolvable and dynamic usages stay conservative anchors that suppress their targets (`getattr`/`hasattr` string constants, `%(name)s` format
  strings and `.format(**locals())` over `locals()`, annotation strings, decorator names, `__all__`, `MIDDLEWARE`, match keywords), so today's
  false-negative behaviour is preserved.
- Definitions kept alive by ignore options — `--ignore` rule codes, `--ignore-names`, `# noqa`, and ignored test or lifecycle names — are live
  anchors, so a cascade never removes code that an ignore option protects.
- A cascade removal also drops the usages the removed definition contributed, which is what makes the transitive closure complete.

The solution requires the following capabilities:

1. Per-usage edge recording during the existing single traversal: every usage the visitor resolves records the definition identity it resolves
   to, together with the using module and the usage kind.
2. One transitive-reachability pass after the traversal: live roots are definitions reachable from entry code, ignore-option anchors, and dynamic
   anchors; everything unreachable is dead.
3. Cascading findings merged into the single existing report: no second report section, so `--count` and `--quiet` keep working unchanged.
4. A single `--fix` pass: all removal parts are computed against the original file content in one pass, because removals never introduce new code
   and their regions are disjoint or merged by the existing `merge_overlaping_file_parts` (`deadcode/actions/merge_overlaping_file_parts.py:66-85`).
5. No new CLI option: the behaviour is strictly more complete detection under the same safety rules, so the report improves without a flag.

The rejected alternatives are doing nothing (manual reruns), repeated runs inside the tool, usage-count metadata without usage places, and full
tree shaking per DEP 4. The chosen solution wins on completeness (one run reports the whole cascade), on cost (one traversal plus one
reachability pass instead of repeated runs), on memory (lightweight edge records instead of retained AST nodes or whole-module graphs), and on
scope (it narrows DEP 4's reachability idea to the definition level `deadcode` already operates on).

## Scope

In scope: definition-level cascading-dead-code detection, reporting, and fixing in a single run, including the interaction of cascades with
dynamic anchors and ignore options.

Out of scope: module-level bundle pruning (DEP 4), new CLI options, and implementing the solution in `deadcode/` — the implementation is a
separate future task.

## Implementation notes

The edge-record shape is per usage site: the resolved definition identity, the using module, and the usage kind. The number of edges is bounded
by the number of usage sites, and the records live in the per-module structures DEP 5 already introduced (binding tables, import edges,
`deadcode/visitor/dead_code_visitor.py:74-80`). Per-usage AST-node retention — linking every usage call site to its AST node, which would keep
the whole AST forest alive for the run — is deliberately rejected for its memory cost; lightweight edge records are enough.

`--fix` computes all removal parts over the original bytes in one pass, and the `assert_valid_python` test contract (`tests/conftest.py`) keeps
every fixed file parseable, as it already does for today's multi-definition removals.

The memory and time budget of the usage graph on large packages is an open question. `docs/performance.md` records that no benchmark baseline
exists yet, so this DEP records the constraint instead of inventing a number.

## Open questions

- What memory and time budget is acceptable for the usage graph on large packages? No benchmark baseline exists yet (`docs/performance.md`).
- How should cascade semantics interact with `--ignore`/`noqa` anchors in edge cases — for example, a definition protected by an ignore option
  whose own usages are all dead?
- Can currently unresolvable attribute loads (recorded as plain `used_names`, `deadcode/visitor/dead_code_visitor.py:566-569`) ever be resolved
  to definitions, or do they stay anchors permanently?

## References

All pages linked from this DEP were retrieved on 2026-11-14.

- DEP 1, "More accurate usage detection": [dep_1.md](dep_1.md) — generic-name fallback for unresolvable usages.
- DEP 4, "Tree pruning for smaller Python source bundles": [dep_4.md](dep_4.md) — tree-shaking prior art: Rollup, webpack, esbuild, Vite, Terser,
  and Closure Compiler resolve per binding, so cascades fall out of one pass.
- DEP 5, "Resolving name shadowing": [dep_5.md](dep_5.md) — definition-anchored usage resolution (DAUR), the in-repo mechanism the usage graph
  builds on.
- Process: [DEP process and template](../docs/dep.md).
- Performance: [performance notes](../docs/performance.md) — no benchmark baseline exists yet.
- Feature request: "Repeated application of `deadcode` till the output stops changing" (`README.md:349`).
- Vulture's documented manual-delete-and-rerun workflow (`docs/comparison.md:9`, `docs/comparison.md:46`).
