# Task

Make the `Justfile` the single source of truth for project command aliases. Port
every Makefile recipe that has no Justfile equivalent (`publish`, `fix`,
`fixlint`, `deadcode`, `audit`, `compile`) into the `Justfile` using its existing
`uv run` / `sync`-dependency style, then delete the `Makefile`. Update the CI
workflow and docs that still invoke `make` so nothing breaks when the Makefile is
gone.
