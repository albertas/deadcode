# Releasing deadcode

The release is one restartable command:

```bash
make publish
```

`make publish` runs `publish_release/publish_release.py` from the package
repository. It bumps the version, runs the checks, builds the distributions,
publishes to PyPI, creates a version tag, and pushes the branch and the tag.

## 1. Write the release notes

Add an entry for the version you are about to release under
`## Release notes` in `README.md`:

```markdown
## Release notes
- v2.4.2:
    - Describe the user-visible change.
    - Add a second line when needed.
```

The release script refuses to continue when the target version has no entry.
This keeps the README's release notes and the PyPI release in sync.

Also update the `rev:` value in the README's pre-commit example to the new
version, so consumers pin the tag this release creates.

## 2. Choose the version

`make publish` defaults to a patch bump. Use:

```bash
make publish BUMP=minor
make publish BUMP=major
make publish VERSION=3.0.0
```

The target is chosen like this:

- With `VERSION=X.Y.Z`, that exact version is released.
- Otherwise, when the current version is already fully released (its tag is on
  the remote and the version is on PyPI), the next `BUMP` version is released.
- Otherwise, the current version is resumed. This is how a failed or
  interrupted release continues without bumping twice.

## 3. What the command does

1. Verifies the current branch is `main` (use `--allow-branch` to override).
2. Reads the current version from `pyproject.toml`.
3. Checks that `README.md` has release notes for the target version.
4. Allows only `pyproject.toml` and `README.md` to be dirty, writes the version
   bump, and commits both as `Bump version to X.Y.Z`.
5. Runs `make check` (tests, lint, mypy, deadcode; `--skip-checks` skips
   it). `make audit` is a separate target: on Python 3.10 it reports a
dev-only `filelock` advisory whose fix requires Python 3.11 or newer.
6. Builds the distributions with `hatch build`.
7. Uploads to PyPI with `hatch publish`, unless the version is already there or
   `--skip-publish` is set.
8. Pushes the branch, then creates the tag `X.Y.Z` (or
   `<tag-prefix>X.Y.Z`) if missing and pushes it. The tag points at the version
   bump commit.
9. Verifies the remote tag and branch hashes.

The tag format is plain `X.Y.Z`, matching the existing `2.4.1` tag. Consumers
pin the pre-commit hook to the same value:

```yaml
repos:
  - repo: https://github.com/albertas/deadcode
    rev: 2.4.2
    hooks:
      - id: deadcode
```

## Credentials

`hatch publish` reads `HATCH_INDEX_USER` and `HATCH_INDEX_AUTH`, or the
keyring / `~/.pypirc` configuration:

```bash
export HATCH_INDEX_USER=__token__
export HATCH_INDEX_AUTH=pypi-...
```

## Resuming a failed release

Rerun `make publish` with the same arguments. The script recognizes:

- an existing bump commit (the tree is clean and the version is already the
  target),
- an existing PyPI upload (the version is skipped),
- an existing local or remote tag (the tag is verified and not moved).

If the bump commit exists but the release stopped before the push, the current
version is resumed instead of bumping again. Fix the cause (credentials,
network, branch divergence) and rerun.

## Manual fallback

If the script cannot run, perform the same steps by hand:

```bash
# 1. release notes in README.md, then:
python3 - <<'PY'
from pathlib import Path
path = Path("pyproject.toml")
text = path.read_text()
path.write_text(text.replace('version = "2.4.1"', 'version = "2.4.2"', 1))
PY
make check
rm -rf dist
.venv/bin/hatch build
.venv/bin/hatch publish
git add pyproject.toml README.md
git commit -m "Bump version to 2.4.2"
git push -u origin main
git tag -a 2.4.2 -m "deadcode 2.4.2"
git push origin 2.4.2
```

Do not move or force-push an existing release tag. If a published release is
wrong, yank it on PyPI and release a new patch version; do not rewrite history.

## Verifying a release

```bash
git tag --list 2.4.2
git ls-remote --tags origin refs/tags/2.4.2
pip index versions deadcode
python3 -m pip download --no-deps --dest /tmp/deadcode-check deadcode==2.4.2
```

The PyPI project page and the README's `## Release notes` section must show the
same version.
