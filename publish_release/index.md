# publish_release

Restartable release tool for the `deadcode` package. `make publish` in the
package repository (or in `deadcode_py/`, which delegates) invokes it.

## What one run does

1. Verifies the current branch is `main` (override with `--allow-branch`).
2. Reads the current version from `pyproject.toml`.
3. Chooses the target version:
   - explicit `--version X.Y.Z`, or
   - the next `--bump` (`patch`, `minor`, `major`) when the current version is
     already fully released (tag on the remote and version on PyPI), or
   - the current version when a previous release run stopped early.
4. **Requires release notes for the target version in `README.md`** under
   `## Release notes`, as a line like `- vX.Y.Z:`. If the entry is missing,
   the release stops before changing anything. Update the pre-commit `rev:` in
   the README to the same version in the same edit.
5. Allows only `pyproject.toml` and `README.md` to be dirty, writes the version
   bump, and commits both as `Bump version to X.Y.Z` (or
   `Add release notes for X.Y.Z` when only the notes changed).
6. Runs `make check` unless `--skip-checks`.
7. Builds the distributions with `hatch build`.
8. Uploads to PyPI with `hatch publish` unless the version is already there or
   `--skip-publish` is set.
9. Pushes the branch, then creates the tag `X.Y.Z` (or
   `<tag-prefix>X.Y.Z`) if missing, verifies it points at HEAD, and pushes it.
   Pushing the branch first makes a failed tag push safely resumable.

The command is safe to rerun: a bump commit, an existing PyPI upload, and an
already-pushed tag are recognized and skipped.

## Usage

```bash
make publish                    # patch bump
make publish BUMP=minor
make publish BUMP=major
make publish VERSION=3.0.0
```

Feature work lands on `task/<task_id>` branches and is merged to `main` via
pull requests. Release only from `main` after the feature PR is merged; the
script refuses any other branch unless `--allow-branch` is passed.

Before running, add the release notes to `README.md`:

```markdown
## Release notes
- v2.4.2:
    - Describe the change.
```

## Credentials

`hatch publish` reads `HATCH_INDEX_USER` and `HATCH_INDEX_AUTH`, or the
keyring / `~/.pypirc` configuration:

```bash
export HATCH_INDEX_USER=__token__
export HATCH_INDEX_AUTH=pypi-...
```

## Options

| Option | Meaning |
|--------|---------|
| `--bump patch\|minor\|major` | next version when the current one is released (default patch) |
| `--version X.Y.Z` | release this exact version |
| `--branch main` | required branch (default `main`) |
| `--allow-branch` | release from the current branch |
| `--tag-prefix` | tag prefix (default empty, matching existing `2.4.1` tags) |
| `--remote origin` | git remote |
| `--skip-checks` | skip `make check` |
| `--skip-publish` | skip the PyPI upload |
| `--dry-run` | print the plan; read-only checks still run |

## Tests

```bash
python3 -m unittest tests.test_publish_release -v
```
