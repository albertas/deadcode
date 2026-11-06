# install_github_cli

Installs and verifies the [GitHub CLI](https://cli.github.com/) (`gh`) used to
fetch pull requests and issues, create pull requests, and review or approve
them for the `deadcode` package.

`make github-cli` in the package repository installs a pinned `gh` release into
`~/.local/bin` and authenticates it.

## Why this shape

- **Pinned release tarball, checksum-verified.** `gh_<version>_linux_amd64.tar.gz`
  is downloaded from the official GitHub releases, and its SHA256 is compared
  with `gh_<version>_checksums.txt` before anything is written. A tampered or
  truncated download never replaces a working binary.
- **User-local, no sudo.** The binary goes to `~/.local/bin`, which is already
  on `PATH` on this machine and already holds the other maintainer tools.
  Installing into `/usr/local/bin` or `/opt` would need root, so the setup
  could not run unattended. Rollback is one `rm`.
- **Idempotent.** A second run finds the pinned version and does nothing, so the
  command can be rerun after any interruption.

The script uses the system `python3` and only the standard library, so it works
before (and without) the package virtual environment.

## Usage

```bash
make github-cli                       # install then authenticate
python3 install_github_cli/install_github_cli.py install
python3 install_github_cli/install_github_cli.py install --version 2.50.0
```

With no subcommand the script installs, so `python3
install_github_cli/install_github_cli.py` behaves like `… install`.

## What one run does

1. Runs `~/.local/bin/gh --version`. If it already reports the requested
   version, prints `gh <version> already installed at <path>` and stops without
   a network call.
2. Downloads the published checksums file and reads the digest for the release
   archive.
3. Downloads the release archive, verifies its SHA256, and only then extracts
   `bin/gh` into a temporary directory inside `~/.local/bin`.
4. Moves the verified binary into place with an atomic replace, so an existing
   `gh` is replaced only by a verified one.

Every download retries transient failures (HTTP 429/5xx, timeouts) up to three
attempts with a doubling delay (1 s, 2 s, capped at 30 s) and sleeps 1 s after a
successful call.

## Credentials

`gh` needs an OAuth token; the SSH key that pushes to GitHub is not enough for
API calls. Create a classic personal access token with the `repo` scope
(GitHub → Settings → Developer settings → Personal access tokens), then pass it
once:

```bash
printf '%s\n' "$GH_TOKEN" | python3 install_github_cli/install_github_cli.py authenticate
GH_TOKEN=… python3 install_github_cli/install_github_cli.py authenticate
```

`gh` stores the token in `~/.config/gh/hosts.yml`, outside both repositories.
The script never writes a token into a repository file, never passes it as a
command line argument, and never prints it.

`authenticate` first runs `gh auth status --hostname github.com`:

- already logged in as `albertas` with the `repo` scope → prints
  `already authenticated as albertas`, exits `0`, changes nothing;
- logged in without the `repo` scope → prints the `gh auth refresh` command and
  exits `4`;
- no token available → prints the exact command to run and exits `3` instead of
  opening a browser.

The interactive fallback, run by hand in a terminal, is:

```bash
gh auth login --hostname github.com --git-protocol ssh --scopes repo
```

## Verification

`make github-cli-verify` (or `python3 install_github_cli/install_github_cli.py
verify`) checks that the authenticated `gh` can read from the repository and
carries the flags needed to write. It first requires an authenticated
`albertas` account with the `repo` scope and then runs these read-only commands
against `albertas/deadcode`:

```bash
gh pr list --repo albertas/deadcode --state open --limit 5 --json number,title,state
gh pr view <number> --repo albertas/deadcode --json number,title,state,url
gh issue list --repo albertas/deadcode --state open --limit 5 --json number,title,state
```

Expected output (the pull request number and issue count vary):

```text
fetch pull requests ok (#38 <title> (OPEN))
fetch issues ok (<n> open issues)
create pull request ok (pr create supports --base --head --title --body-file)
review pull request ok (pr review supports --approve --comment --request-changes)
approve pull request ok (own pull requests cannot be approved; requires a pull request by another account)
```

`verify` never writes to GitHub. Every command is bounded by `--limit 5`,
sleeps 1 s after success, and retries a failed call up to three times with a
doubling delay (2 s, 4 s, capped at 30 s). A live read failure prints
`<capability> failed: <reason>` as the last line and exits `5`; a missing flag
or scope exits `4`; missing authentication exits `3` with the `gh auth login`
command.

## What `verify` proves

1. **Live read access** — `gh pr list`, `gh pr view`, and `gh issue list` really
   answer for `albertas/deadcode`, so the token and the network work.
2. **Write flags** — `gh pr create --help` must mention `--base`, `--head`,
   `--title`, and `--body-file`; `gh pr review --help` must mention `--approve`,
   `--comment`, and `--request-changes`. This is the surface the maintainer and
   the worker rely on.
3. **Scope** — `gh auth status` must report the `repo` scope, which is what
   GitHub requires to open, review, and approve pull requests.
4. **Opt-in write cycle** — `verify --smoke-pull-request` (or
   `make github-cli-verify SMOKE=1`) creates the scratch repository
   `albertas/gh-cli-smoke-test` when it is missing, pushes a dated `smoke-…`
   branch, opens a pull request against `main`, posts a review comment, closes
   the pull request, and deletes the branch. Rerunning reuses and closes an
   already open smoke pull request instead of opening another one, so the check
   can be repeated safely. A plain `make github-cli-verify` never touches the
   scratch repository.

The `approve pull request` line only reports the scope and the following
GitHub policy: own pull requests cannot be approved; requires a pull request by
another account. The smoke cycle therefore covers create and review only.

Cleanup, when the scratch repository is no longer needed:

```bash
gh repo delete albertas/gh-cli-smoke-test
```

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | success, including "already installed" and "already authenticated" |
| `1` | download, checksum, or extraction failure |
| `2` | usage error |
| `3` | `gh` is not installed or not authenticated |
| `4` | a capability is missing: no `repo` scope, or a required `gh` flag |
| `5` | a live verification call or the opt-in smoke cycle failed |

## Rollback

```bash
rm -f ~/.local/bin/gh
```

Nothing outside `~/.local/bin` is written by the installer. The opt-in smoke
cycle writes only to `albertas/gh-cli-smoke-test`, which is removed with
`gh repo delete albertas/gh-cli-smoke-test`.

## Tests

The unit tests use a temporary directory and a patched downloader; they never
touch `~/.local/bin` or the network.

```bash
python3 -m unittest tests.test_install_github_cli -v
```
