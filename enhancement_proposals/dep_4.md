# DEP 4 - Tree pruning for smaller Python source bundles

**Status**: Proposed

**Type**: Feature

**Created**: 2026-11-11

## Problem statement

Tree pruning, also called tree shaking, makes a source bundle smaller without changing what the program does. It keeps only the code
that is reachable from the entry points of a program. An entry point is where execution starts, such as a script, a command, or a
function that a host calls. Anything that no entry point can reach is left out of the bundle.

Python running in the browser has a bundle-size problem that tree pruning could solve. A browser has to download, parse and compile every
file that a page loads. Large bundles make a page load more slowly, use more memory, and take longer before it becomes interactive, and the
cost is worse on slow networks and on mobile devices. A Python runtime, the standard library, and the packages a program uses all have to
reach the browser before the first line of Python runs. A bundler that copies every Python file from a package ships modules that the
program never imports.

Consider a small package with two entry points and a helper module that nothing imports:

```text
example/
├── app.py            # entry point, starts the web application
├── cli.py            # entry point, runs the command line tool
├── reports.py        # imported by app.py
├── parsing.py        # imported by reports.py
└── legacy_export.py  # unused module, could be dropped
```

`app.py` and `cli.py` are entry points. `reports.py` and `parsing.py` are reachable from `app.py`, so they stay. `legacy_export.py` is
reachable from nothing, so tree pruning could drop the whole file. A definition-level tool would only report the names inside
`legacy_export.py` that are unused, and it would still ship the parts of the module that it considers used.

Two related techniques are easy to confuse with tree pruning:

- Minification removes whitespace and shortens names. It makes each file smaller but keeps every module and every definition.
- Removing individual unused names deletes single definitions such as an unused variable or function. It works file by file and does not
  need to know which modules are reachable.

Tree pruning works at a higher level than both. It reasons about modules and exports, and it can drop a whole module whose code is never
reached.

### How deadcode works today

`deadcode` reads Python source files and parses them with `ast`, the abstract syntax tree module of the standard library. It does not
build a module or package graph, and it does not read packaging metadata.

The decision for a definition is `item.name not in used_names`. `used_names` is one global set collected from the whole analysed file set,
so a name used anywhere keeps every definition with that name. Import rules and module-level rules add a few refinements, but the core
check stays name based.

The output is a per-file finding with a `DC` code, such as `DC02` for an unused function. With `--fix`, `deadcode` removes the byte ranges
of the findings, and `--dry` prints the same change as a unified diff instead of writing it. A file whose content becomes empty is deleted.

Tree pruning needs capabilities that `deadcode` does not have:

- a module or package graph that connects imported modules to their importers;
- explicit entry-point roots instead of one global name set;
- export-level reachability that follows imports across modules;
- a side-effect model for imports and module bodies that must run;
- repeated pruning until the output stops changing.

These gaps overlap with the documented [known limitations](known_limitations.md) and with the
[feature-request list](contributing.md). The same-name limitation means that a definition is kept whenever any definition with the same
name is used, and wildcard imports are resolved by module basename. The feature requests for distinguishing same-named definitions and for
applying `deadcode` repeatedly are still unchecked.

### Why Python is harder than ES modules

JavaScript modules are static syntax: `import` and `export` name their bindings, and a bundler can resolve them before any code runs.
Python resolves imports and attribute access at runtime, so a source-only analyser cannot always know which modules and names a program
will reach. The features below are the main reasons a Python tree pruner needs a conservative policy instead of a purely syntactic one.

- **Dynamic imports.** An `import` statement can run conditionally, and `importlib.import_module(name)` or `__import__(name)` accepts a
  computed string ([importlib documentation](https://docs.python.org/3/library/importlib.html#importlib.import_module)). The target module
  is unknown until the call runs.
- **Reflection.** `getattr` and `setattr` reach names without a syntactic load
  ([built-in functions](https://docs.python.org/3/library/functions.html#getattr)), so a string computed at runtime can keep a definition
  alive.
- **`eval` and `exec`.** Both execute arbitrary strings ([built-in functions](https://docs.python.org/3/library/functions.html#eval)),
  which can create imports, definitions, and calls that no static visitor sees.
- **Wildcard imports and `__all__`.** `from module import *` is resolved at runtime and exports the names in `__all__`, or the public names
  when `__all__` is absent ([Python tutorial](https://docs.python.org/3/tutorial/modules.html#importing-from-a-package)). A module-level
  `__getattr__` can also synthesize attributes dynamically ([PEP 562](https://peps.python.org/pep-0562/)), and a computed `__all__` cannot
  be read statically.
- **Entry points and plugin discovery.** Console scripts and plugin entry points are declared in packaging metadata
  ([entry point specification](https://packaging.python.org/en/latest/specifications/entry-points/)) and are commonly loaded through
  `importlib.metadata.entry_points()` ([importlib.metadata documentation](https://docs.python.org/3/library/importlib.metadata.html#entry-points)),
  which is a runtime lookup with no static call edge.
- **Decorator and metaclass registration.** A decorator, a metaclass, `__init_subclass__`, `__set_name__`, or a registry populated at import
  time can create a use that never appears as a name load. Without executing the module, the analyser cannot see that registration.

### What Python-to-browser toolchains do today

Python in the browser is usually packaged as a runtime plus Python files or wheels. The reviewed documentation describes packaging,
compilation, and minification, and it does not document a Python-level tree-shaking step. That is a statement about the sources reviewed,
not proof that no pruning happens anywhere in these projects.

[Pyodide](https://pyodide.org/en/stable/usage/quickstart.html) compiles CPython to WebAssembly and installs Python packages as wheels loaded
through `micropip` or `pyodide.loadPackage` ([loading packages](https://pyodide.org/en/stable/usage/loading-packages.html)). Its
[bundler guide](https://pyodide.org/en/stable/usage/working-with-bundlers.html) explains how to copy the runtime and packages into a web
build. The JavaScript bundler sees the loader code and the wheel files, not the Python modules inside a wheel.

[Transcrypt](https://github.com/QQuick/Transcrypt) compiles Python to JavaScript and then minifies the result with Closure Compiler at the
`WHITESPACE_ONLY` level, which does not run Closure's dead-code elimination. Its documentation calls the result a
["minified but not treeshaked"](https://github.com/QQuick/Transcrypt/blob/master/transcrypt/docs/sphinx/integration_javascript.rst)
runtime.

[Brython](https://github.com/brython-dev/brython) runs Python in the browser and ships `brython.js` plus `brython_stdlib.js`, which its
README describes as a bundle of all the files in the standard distribution. The README does not describe a per-module pruning option.

## Considered alternatives

### Do nothing and keep definition-level removal

The status quo already removes unused definitions. It is safe, cheap, and incremental, and it works without a module graph. It cannot drop a
module whose exports are never imported, and it cannot follow an export across module boundaries, so the bundle still contains code that no
entry point can reach. Repeated runs find definitions that only become unused after an earlier removal, but `deadcode` does not repeat them
automatically, so the user has to run the tool until the output stops changing.

### Delegate pruning to JavaScript bundlers

A Python-to-browser build already runs a JavaScript bundler over the loader and the copied packages. That bundler understands ES modules,
not Python modules, so it can drop unused JavaScript but not an unreachable Python module inside a wheel. Teaching each bundler to read
Python would duplicate the pruner in every toolchain and would not help server-side Python bundles.

### Prune modules without a side-effect model

Dropping a module that has no import path from an entry point is correct only when importing a module has no effect that the program
observes. Registration through decorators, metaclasses, and import-time side effects makes that assumption unsafe. A module-level pruner
without a side-effect policy can silently remove code that runs for its effects.

### Prior art in the JavaScript ecosystem

Most JavaScript tools that remove unused code follow the same pipeline. They differ in which layers of the pipeline they own.

```text
entry modules -> module graph -> reachable exports -> side-effect check -> smaller bundle
```

The module graph connects every import to the module it names. Reachability starts at the entry modules and follows only the exports that
importers actually use. A side-effect check then keeps statements whose evaluation matters, even when their result is unused.

#### Rollup

[Rollup](https://rollupjs.org/introduction/) is an ES-module bundler. It statically analyses the modules it is given, builds a graph of their
imports, and excludes statements that nothing reachable uses. Tree shaking is on by default through the `treeshake` option
(see the [configuration reference](https://rollupjs.org/configuration-options/#treeshake)).

The prerequisite is ES-module syntax. CommonJS input needs a plugin before Rollup can analyse it.

Rollup stays conservative about side effects: when an imported module appears to have effects, Rollup
[plays it safe and includes them](https://rollupjs.org/troubleshooting/). That can keep code that is never used. The same troubleshooting
page notes that `eval` defeats static analysis and that holding the whole module graph in memory can exhaust Node's heap on large projects.

#### webpack

[webpack](https://webpack.js.org/guides/tree-shaking/) builds a module graph and implements tree shaking from the static structure of ES2015
`import` and `export` declarations. Its guide separates two mechanisms. `sideEffects` in `package.json` lets webpack skip a whole module and
its dependency subtree. `usedExports` marks unused exports, and webpack relies on [Terser](https://terser.org/docs/options/) to remove the
statements that become dead.

The prerequisites are ES2015 module syntax and no compiler transformation to CommonJS. `ModuleConcatenationPlugin` is required, and
`mode: 'production'` adds it.

The documented failure modes are an over-optimistic `sideEffects: false`, which can drop CSS imports, polyfills, or globals; re-exports with
side effects that get skipped; and testing only in development mode. webpack also says `usedExports` cannot skip a dependency subtree on its
own.

#### esbuild

[esbuild](https://esbuild.github.io/api/#tree-shaking) performs declaration-level dead code removal, which it calls tree shaking. It is
enabled by default when bundling or when the output format is `iife`.

The prerequisite is ES-module syntax. esbuild does not tree-shake CommonJS input, and it prefers the `module` field over `main` to find ESM.

The documented limitation is its conservative side-effect analysis. Literals are treated as pure, but string concatenation (which may call
`toString`), member access (which may invoke a getter), and global identifier references are treated as side effects, so esbuild keeps code
it cannot prove removable. `/* @__PURE__ */` annotations and the `sideEffects` field let an author narrow that analysis.

#### Vite

[Vite](https://vitejs.dev/guide/why.html) is a development server and build tool rather than a tree-shaking algorithm of its own. Its
production build delegates bundling and tree shaking to Rollup historically and to Rolldown in the current documentation.

The documented limitation follows from that delegation: the removal a reader observes is the bundler's, not a Vite-specific pass. Vite's
[features page](https://vitejs.dev/guide/features.html) also notes that the default lazy form of `import.meta.glob` creates dynamic
imports, so those modules are not tree-shaken unless the eager form with named imports is used.

#### Terser

[Terser](https://terser.org/docs/options/) is a JavaScript parser, compressor, and mangler, not a module bundler. It performs scope analysis
inside one file and removes statements that are unreachable or free of side effects.

The prerequisite is a bundle or a set of files to compress. Terser has no module graph, so it cannot remove an unused module or an unused
export on its own; that decision belongs to the bundler that runs before it.

The documented limitation is its default for top-level removal. The `toplevel` option defaults to `false`, so unreferenced top-level
functions and variables are kept unless the option is enabled.

#### Google Closure Compiler

[Google Closure Compiler](https://github.com/google/closure-compiler/wiki/An-Overview-of-Closure-Compiler) is a whole-program optimiser. It
parses JavaScript, analyses it, removes dead code, and rewrites and minimises what remains, and it also checks syntax, references, and
types.

The prerequisite is a complete program together with externs that describe the external API and exports that mark the public surface. The
[FAQ](https://github.com/google/closure-compiler/wiki/FAQ) states that "the big wins in advanced optimizations come from externs and
exports". Its `ADVANCED` compilation level removes code that is neither exported nor declared in externs, while `SIMPLE` performs only local
optimisations.

The documented failure mode is that `ADVANCED` can break code when type information is wrong. The FAQ suggests disabling type-based
optimisation with `--use_types_for_optimization false` while debugging.

#### Comparing the JavaScript approaches

The table places each tool at the layer where it makes removal decisions. The failure mode column records the limitation each project
documents.

| Tool | Layer | Unit of removal | Input requirement | Main failure mode |
| --- | --- | --- | --- | --- |
| Rollup | Bundler | Unreachable statements in an ES-module graph | ES-module syntax | Conservative side effects and `eval` keep code that is unused |
| webpack | Bundler | Whole modules through `sideEffects`, statements through Terser | ES2015 modules without CommonJS transformation | Wrong `sideEffects` metadata drops CSS or globals |
| esbuild | Bundler | Unused declarations | ES-module syntax, no CommonJS | Conservative side-effect rules keep code it cannot prove removable |
| Vite | Build tool | Whatever the production bundler removes | Bundler configuration | Lazy glob imports are not tree-shaken |
| Terser | Compressor | Unreachable or side-effect-free statements in one file | A bundle or file set | Top-level removal is off by default and there is no module graph |
| Google Closure Compiler | Whole-program optimiser | Unexported code under `ADVANCED` | Externs and exports | Wrong type information can break code under `ADVANCED` |

## Chosen solution

Expand `deadcode` with an opt-in tree-pruning mode that implements the whole pipeline inside the analyser, so it works for Python
modules that a JavaScript bundler cannot see. The mode builds on the existing definition-level analysis instead of replacing it: the
current findings remain the per-file layer, and the new layer decides which modules and exports are reachable.

A tree-pruning mode for `deadcode` requires all of the following capabilities:

1. A module or package graph that records which module imports which, including package `__init__` files.
2. Explicit entry-point roots, such as scripts, console scripts, and framework hooks, instead of one global set of used names.
3. Export-level reachability that starts at the roots and follows only the imports and attributes that importers use.
4. A side-effect policy for imports and module bodies that must run even when their names are unused.
5. Repeated pruning to a fixed point, so definitions that become unused after an earlier removal are removed too.
6. Post-edit validation, because removing a module or an import can break syntax or leave a package that no longer imports.

The diagram contrasts the current per-file pipeline with the proposed whole-program pipeline:

```text
today: per-file findings                 tree pruning: whole-program pipeline
+---------------------------+            +---------------------------+
| Python source files       |            | entry points              |
|      |                    |            |      |                    |
|      v                    |            |      v                    |
| ast parse per file        |            | module graph              |
|      |                    |            |      |                    |
|      v                    |            |      v                    |
| global used-name set      |            | reachable exports         |
|      |                    |            |      |                    |
|      v                    |            |      v                    |
| DC findings -> --fix      |            | side-effect policy        |
+---------------------------+            |      |                    |
                                         |      v                    |
                                         | smaller bundle            |
                                         +---------------------------+
                                         (not implemented in deadcode)
```

The left side is what `deadcode` does today. The right side is the proposed tree-pruning pipeline.

This option was chosen over the alternatives because it removes code the current analyser cannot see, keeps the analysis inside the
Python toolchain that the project already owns, and can reuse the existing `DC` findings and `--fix`/`--dry` output. It also follows
the model that the JavaScript ecosystem has converged on: a module graph, explicit entry points, export-level reachability, a
side-effect check, and repeated removal. The alternatives either keep whole unreachable modules in the bundle (do nothing), depend on
tools that cannot read Python modules (delegate to bundlers), or risk removing code that runs for its effects (prune without a
side-effect model).

## Scope

This DEP covers an opt-in tree-pruning mode for Python source bundles. It does not cover minification, name mangling, or transpilation, and it
does not cover the Python runtime, the standard library, or wheel extraction, which the packaging toolchain already handles. Runtime-only
reachability through `eval`, `exec`, reflection, and dynamically computed imports stays conservative: the analyser must keep anything it
cannot prove unreachable.

Until this mode is implemented, definition-level removal is the available path for reducing a code base, and each step stays definition
based:

- run `deadcode` to list unused definitions, one finding per definition and file;
- apply `--fix` to remove them, or `--dry` to review the diff first;
- run `deadcode` again after fixing, and repeat until the output stops changing;
- use the ignore options and `# noqa` comments to keep definitions that are used dynamically;
- read the [known limitations](known_limitations.md) page before relying on the result for a whole package.

Rerunning until the output stops changing can find definitions that only became unused after an earlier removal. `deadcode` has no mode
that repeats this automatically, so the repetition is manual.

## Implementation notes

The six capabilities map to a sequence of passes over the same parsed source tree. The module graph is built first from `Import` and
`ImportFrom` nodes, with package `__init__` files represented as graph nodes. Entry-point roots are then resolved from configuration and,
where available, from packaging metadata. Reachability walks the graph from the roots and marks the imports and attributes that importers
actually use. The side-effect policy decides which module bodies and import statements survive even when their names are unused. Pruning
repeats until a pass changes nothing, and a post-edit syntax and import check rejects a result that no longer parses or imports.

The existing `DC` findings and the `--fix`/`--dry` mechanics can carry the per-definition part of the output. The new mode needs a way to
report whole-module removals and to describe why a module or export was kept, so a dry run remains reviewable.

## Open questions

- Should entry points come only from explicit configuration, or also from packaging metadata such as console scripts and plugin entry
  points?
- How conservative should the side-effect policy be: AST-only rules, or executing module bodies in a sandbox to observe registrations?
- Should pruning produce rewritten source files, a manifest of removable modules, or both?
- What memory and time budget is acceptable for the module graph on a large package, given that Rollup's documentation warns about heap
  exhaustion on large projects?
- How should diagnostics explain why a module was kept, so a user can fix a false positive without disabling the mode?

## References

All pages linked from this DEP were retrieved on 2026-11-11.

- Rollup: [introduction](https://rollupjs.org/introduction/), [configuration options](https://rollupjs.org/configuration-options/#treeshake),
  [troubleshooting](https://rollupjs.org/troubleshooting/)
- webpack: [tree shaking guide](https://webpack.js.org/guides/tree-shaking/)
- esbuild: [tree shaking](https://esbuild.github.io/api/#tree-shaking)
- Vite: [why Vite](https://vitejs.dev/guide/why.html), [features](https://vitejs.dev/guide/features.html)
- Terser: [options reference](https://terser.org/docs/options/)
- Google Closure Compiler: [overview](https://github.com/google/closure-compiler/wiki/An-Overview-of-Closure-Compiler),
  [FAQ](https://github.com/google/closure-compiler/wiki/FAQ)
- Python: [importlib](https://docs.python.org/3/library/importlib.html#importlib.import_module),
  [built-in functions](https://docs.python.org/3/library/functions.html#getattr), [eval](https://docs.python.org/3/library/functions.html#eval),
  [importing from a package](https://docs.python.org/3/tutorial/modules.html#importing-from-a-package),
  [PEP 562](https://peps.python.org/pep-0562/)
- Packaging: [entry point specification](https://packaging.python.org/en/latest/specifications/entry-points/),
  [importlib.metadata entry points](https://docs.python.org/3/library/importlib.metadata.html#entry-points)
- Pyodide: [quickstart](https://pyodide.org/en/stable/usage/quickstart.html),
  [loading packages](https://pyodide.org/en/stable/usage/loading-packages.html),
  [working with bundlers](https://pyodide.org/en/stable/usage/working-with-bundlers.html)
- Transcrypt: [README](https://github.com/QQuick/Transcrypt),
  [integration documentation](https://github.com/QQuick/Transcrypt/blob/master/transcrypt/docs/sphinx/integration_javascript.rst)
- Brython: [README](https://github.com/brython-dev/brython)
- Related documentation: [known limitations](known_limitations.md), [contribution guidance](contributing.md)
