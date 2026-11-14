# Deadcode

```{include} ../README.md
:end-before: "## Installation"
```

## Rationale

```{include} ../README.md
:start-after: "## Rationale"
:end-before: "## Known limitations"
```

Read the {doc}`installation` page to install deadcode.

Read the {doc}`usage` page for usage examples, command line options, the glossary, decorator matching, and exit status.

Read the {doc}`rules` page for the implemented rules and for ignoring findings with `# noqa` comments.

Read the {doc}`fastapi` page for running deadcode on a FastAPI project, including common use cases, dependency injection, and a complete
example application.

Read the {doc}`django` page for running deadcode on a Django project, including the recommended configuration, settings, models, views, templates,
forms, the admin, middleware, signals, and Django REST Framework.

Read the {doc}`pre_commit` page for setting up and using the pre-commit hook.

Read the {doc}`contributing` page for the contribution workflow and the feature-request checklist.

Read the {doc}`dep` page for the Deadcode Enhancement Proposal (DEP) process and the DEP template. DEP 4 proposes
[source-code tree pruning](dep_4.md) that would trim a Python bundle to the modules its entry points reach.

Read the {doc}`security` page for the vulnerability detection process and how to respond to a finding.

Read the {doc}`known_limitations` page for the analyser's known limitations.

Read the {doc}`release_notes` page for the release history.

Read the {doc}`features` page for the checked map of README features to source files, tests, and minimum test cases.

Read the {doc}`comparison` page for a comparison of deadcode with vulture, starting with the differences that matter most when choosing
between them.

Read the {doc}`performance` page for a review of the implementation's efficiency and for how the analysis cost grows with the size of the input.

Read the {doc}`rust` page for how Rust integrates into deadcode, where the Rust code will be stored, how the package is built, and how releases reach PyPI.

Read the {doc}`open_source_experiment` page for the planned experiment that runs deadcode on popular and large open source Python projects and
defines the metrics, measurement procedure, and reporting template.

```{toctree}
:maxdepth: 2

installation
usage
rules
fastapi
django
pre_commit
contributing
dep
security
known_limitations
release_notes
features
comparison
performance
rust
open_source_experiment
```
