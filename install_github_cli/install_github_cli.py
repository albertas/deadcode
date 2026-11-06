#!/usr/bin/env python3
"""Install and verify the GitHub CLI (gh) used to work with pull requests.

The installer is restartable: a second run detects the pinned version and
changes nothing. The release archive is verified against the published SHA256
checksums before an existing binary is replaced, so a failed or tampered
download never breaks a working installation.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

DEFAULT_GH_VERSION = '2.46.0'
GH_RELEASE_BASE_URL = 'https://github.com/cli/cli/releases/download/v{version}'
GH_ARCHIVE_NAME = 'gh_{version}_linux_amd64.tar.gz'
GH_CHECKSUMS_NAME = 'gh_{version}_checksums.txt'
GH_ARCHIVE_MEMBER = 'bin/gh'
LOCAL_BINARY_DIRECTORY = Path.home() / '.local' / 'bin'
GH_CONFIG_DIRECTORY = Path.home() / '.config' / 'gh'
TARGET_REPOSITORY = 'albertas/deadcode'
SMOKE_REPOSITORY = 'albertas/gh-cli-smoke-test'
SMOKE_REPOSITORY_URL = f'https://github.com/{SMOKE_REPOSITORY}.git'
SMOKE_REPOSITORY_DESCRIPTION = 'Scratch repository for deadcode GitHub CLI smoke tests'
SMOKE_REVIEW_BODY = 'Automated GitHub CLI smoke review.'
DELAY_AFTER_CALL_SECONDS = 1.0
RETRY_COUNT = 3
RETRY_INITIAL_DELAY_SECONDS = 2.0
RETRY_MAX_DELAY_SECONDS = 30.0
DOWNLOAD_RETRY_INITIAL_DELAY_SECONDS = 1.0
COMMAND_TIMEOUT_SECONDS = 120
RETRYABLE_HTTP_STATUS_CODES = (429, 500, 502, 503, 504)
ACCOUNT_PATTERN = re.compile(r'Logged in to \S+ account (?P<account>\S+)')
SCOPES_PATTERN = re.compile(r'Token scopes:\s*(?P<scopes>.+)')
PULL_REQUEST_URL_PATTERN = re.compile(r'/pull/(?P<number>\d+)')
EXPECTED_ACCOUNT = 'albertas'
REQUIRED_SCOPE = 'repo'
AUTH_LOGIN_COMMAND = '  gh auth login --hostname github.com --git-protocol ssh --scopes repo'
MISSING_GH_MESSAGE = (
    'the GitHub CLI (gh) is not installed; run: python3 install_github_cli/install_github_cli.py install'
)


class InstallError(Exception):
    """Raised when the GitHub CLI cannot be installed or used."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass(frozen=True)
class CommandResult:
    """Outcome of one external command."""

    return_code: int
    standard_output: str
    standard_error: str


@dataclass(frozen=True)
class CapabilityResult:
    """Outcome of one verified GitHub CLI capability."""

    name: str
    ok: bool
    detail: str = ''


def sha256_digest(data: bytes) -> str:
    """Return the lowercase hexadecimal SHA256 digest of the data."""
    return hashlib.sha256(data).hexdigest()


def parse_checksums(checksums_text: str, filename: str, source_url: str) -> str:
    """Return the SHA256 digest published for the filename."""
    for line in checksums_text.splitlines():
        fields = line.split()
        if len(fields) != 2:
            continue
        digest, listed_name = fields
        if listed_name.removeprefix('*') == filename:
            return digest.lower()
    raise InstallError(f'checksum for {filename} is missing in {source_url}')


def download_bytes(url: str) -> bytes:
    """Download a URL, retrying transient failures with a doubling delay."""
    last_error: str = ''
    for attempt in range(1, RETRY_COUNT + 1):
        try:
            with urllib.request.urlopen(url, timeout=COMMAND_TIMEOUT_SECONDS) as response:  # noqa: S310
                data = response.read()
        except urllib.error.HTTPError as error:
            if error.code not in RETRYABLE_HTTP_STATUS_CODES:
                raise InstallError(f'download failed: {url} ({error})') from error
            last_error = str(error)
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_error = str(error)
        else:
            time.sleep(DELAY_AFTER_CALL_SECONDS)
            return data
        if attempt < RETRY_COUNT:
            delay = min(DOWNLOAD_RETRY_INITIAL_DELAY_SECONDS * 2 ** (attempt - 1), RETRY_MAX_DELAY_SECONDS)
            time.sleep(delay)
    raise InstallError(f'download failed after {RETRY_COUNT} attempts: {url} ({last_error})')


def installed_version(binary_path: Path) -> str | None:
    """Return the version reported by an existing gh binary, or None."""
    if not binary_path.is_file() or not os.access(binary_path, os.X_OK):
        return None
    try:
        result = subprocess.run(
            [str(binary_path), '--version'],
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    first_line = result.stdout.splitlines()[0] if result.stdout else ''
    fields = first_line.split()
    if len(fields) < 3 or fields[0] != 'gh' or fields[1] != 'version':
        return None
    return fields[2]


def extract_binary(tarball_bytes: bytes, member_suffix: str, destination: Path) -> None:
    """Write the gh executable from the release archive to the destination."""
    with tarfile.open(fileobj=io.BytesIO(tarball_bytes), mode='r:gz') as archive:
        members = [member for member in archive.getmembers() if member.name.endswith(member_suffix)]
        if not members:
            raise InstallError(f'the release archive has no member ending with {member_suffix}')
        source = archive.extractfile(members[0])
        if source is None:
            raise InstallError(f'the release archive member {members[0].name} is not a regular file')
        binary_bytes = source.read()
    destination.write_bytes(binary_bytes)
    destination.chmod(0o755)


def install_binary(version: str, binary_directory: Path) -> int:
    """Install a checksum-verified gh binary of the pinned version."""
    binary_path = binary_directory / 'gh'
    if installed_version(binary_path) == version:
        print(f'gh {version} already installed at {binary_path}')
        return 0
    release_url = GH_RELEASE_BASE_URL.format(version=version)
    archive_name = GH_ARCHIVE_NAME.format(version=version)
    checksums_url = f'{release_url}/{GH_CHECKSUMS_NAME.format(version=version)}'
    archive_url = f'{release_url}/{archive_name}'
    checksums_text = download_bytes(checksums_url).decode('utf-8', errors='replace')
    expected_digest = parse_checksums(checksums_text, archive_name, checksums_url)
    archive_bytes = download_bytes(archive_url)
    actual_digest = sha256_digest(archive_bytes)
    if actual_digest != expected_digest:
        raise InstallError(
            f'checksum mismatch for {archive_url}: expected {expected_digest}, got {actual_digest}',
        )
    binary_directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=binary_directory) as temporary_directory:
        temporary_path = Path(temporary_directory) / 'gh'
        extract_binary(archive_bytes, GH_ARCHIVE_MEMBER, temporary_path)
        temporary_path.replace(binary_path)
    print(f'installed gh {version} at {binary_path}')
    return 0


def require_github_cli() -> str:
    """Return the gh executable path or raise when it cannot be found."""
    gh_path = shutil.which('gh')
    if gh_path is not None:
        return gh_path
    local_path = LOCAL_BINARY_DIRECTORY / 'gh'
    if local_path.is_file() and os.access(local_path, os.X_OK):
        print('export PATH="$HOME/.local/bin:$PATH"')
        raise InstallError(f'{local_path} exists but is not on PATH', exit_code=3)
    raise InstallError(MISSING_GH_MESSAGE, exit_code=3)


def run_github_cli(
    arguments: list[str],
    standard_input: str | None = None,
    working_directory: Path | None = None,
) -> CommandResult:
    """Run one gh command, retrying failures with a doubling delay."""
    last_result: CommandResult | None = None
    for attempt in range(1, RETRY_COUNT + 1):
        try:
            completed = subprocess.run(  # noqa: S603
                arguments,
                input=standard_input,
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT_SECONDS,
                check=False,
                cwd=working_directory,
            )
        except FileNotFoundError as error:
            raise InstallError(MISSING_GH_MESSAGE, exit_code=3) from error
        except (OSError, subprocess.SubprocessError) as error:
            last_result = CommandResult(return_code=1, standard_output='', standard_error=str(error))
        else:
            last_result = CommandResult(completed.returncode, completed.stdout, completed.stderr)
        if last_result.return_code == 0:
            time.sleep(DELAY_AFTER_CALL_SECONDS)
            return last_result
        if attempt < RETRY_COUNT:
            delay = min(RETRY_INITIAL_DELAY_SECONDS * 2 ** (attempt - 1), RETRY_MAX_DELAY_SECONDS)
            time.sleep(delay)
    assert last_result is not None  # noqa: S101
    return last_result


def parse_authentication_status(output: str) -> tuple[str | None, list[str]]:
    """Return the logged-in account and its token scopes."""
    account_match = ACCOUNT_PATTERN.search(output)
    scopes_match = SCOPES_PATTERN.search(output)
    account = account_match.group('account') if account_match else None
    scopes: list[str] = []
    if scopes_match:
        for candidate in scopes_match.group('scopes').split(','):
            scope = candidate.strip().strip('\'"')
            if scope:
                scopes.append(scope)
    return account, scopes


def authentication_status(gh_path: str) -> CommandResult:
    """Return the gh authentication status for github.com."""
    return run_github_cli([gh_path, 'auth', 'status', '--hostname', 'github.com'])


def read_token(environment: Mapping[str, str], standard_input: str) -> str:
    """Return the token from the environment or from standard input."""
    token = environment.get('GH_TOKEN', '').strip()
    if token:
        return token
    return standard_input.strip()


def authenticate(gh_path: str, environment: Mapping[str, str], standard_input: str) -> int:
    """Log gh in as albertas with the repo scope, without an interactive flow."""
    status = authentication_status(gh_path)
    if status.return_code == 0:
        account, scopes = parse_authentication_status(status.standard_output)
        if account == EXPECTED_ACCOUNT and REQUIRED_SCOPE in scopes:
            print(f'already authenticated as {EXPECTED_ACCOUNT}')
            return 0
        if account is not None and REQUIRED_SCOPE not in scopes:
            print(
                'authenticated without the repo scope; run: '
                f'gh auth refresh --hostname github.com --scopes {REQUIRED_SCOPE}',
            )
            return 4
        if account is not None:
            print(f'authenticated as {account}; expected {EXPECTED_ACCOUNT}')
            return 4
    token = read_token(environment, standard_input)
    if not token:
        print('not authenticated; run:')
        print(AUTH_LOGIN_COMMAND)
        print('or set GH_TOKEN=<token> and rerun: python3 install_github_cli/install_github_cli.py authenticate')
        return 3
    run_github_cli(
        [gh_path, 'auth', 'login', '--with-token', '--hostname', 'github.com'],
        standard_input=token + '\n',
    )
    status = authentication_status(gh_path)
    account, _scopes = parse_authentication_status(status.standard_output)
    if status.return_code == 0 and account == EXPECTED_ACCOUNT:
        print(f'authenticated as {EXPECTED_ACCOUNT}')
        return 0
    print(f'authenticate failed: {status.standard_error.strip() or status.standard_output.strip()}')
    return 4


def command_error(result: CommandResult) -> str:
    """Return the most useful error text from a failed command."""
    return result.standard_error.strip() or result.standard_output.strip() or f'exit code {result.return_code}'


def run_json_github_cli(arguments: list[str]) -> tuple[CommandResult, object | None]:
    """Run one gh command and parse its JSON output when it succeeds."""
    result = run_github_cli(arguments)
    if result.return_code != 0:
        return result, None
    try:
        return result, json.loads(result.standard_output)
    except json.JSONDecodeError:
        return result, None


def verify_pull_requests(gh_path: str) -> CapabilityResult:
    """List open pull requests and read one of them back."""
    name = 'fetch pull requests'
    list_result, pull_requests = run_json_github_cli(
        [
            gh_path,
            'pr',
            'list',
            '--repo',
            TARGET_REPOSITORY,
            '--state',
            'open',
            '--limit',
            '5',
            '--json',
            'number,title,state',
        ],
    )
    if list_result.return_code != 0 or not isinstance(pull_requests, list):
        detail = (
            f'gh pr list failed: {command_error(list_result)}'
            if list_result.return_code != 0
            else 'gh pr list returned invalid JSON'
        )
        return CapabilityResult(name, False, detail)
    if not pull_requests:
        return CapabilityResult(name, True, 'no open pull requests')
    first_pull_request = pull_requests[0]
    number = first_pull_request.get('number') if isinstance(first_pull_request, dict) else None
    if number is None:
        return CapabilityResult(name, False, 'gh pr list returned no pull request number')
    view_result, pull_request = run_json_github_cli(
        [
            gh_path,
            'pr',
            'view',
            str(number),
            '--repo',
            TARGET_REPOSITORY,
            '--json',
            'number,title,state,url',
        ],
    )
    if view_result.return_code != 0:
        return CapabilityResult(name, False, f'gh pr view failed: {command_error(view_result)}')
    if not isinstance(pull_request, dict) or not pull_request.get('state'):
        return CapabilityResult(name, False, 'gh pr view returned invalid JSON')
    title = pull_request.get('title', '')
    return CapabilityResult(name, True, f'#{number} {title} ({pull_request["state"]})')


def verify_issues(gh_path: str) -> CapabilityResult:
    """List open issues."""
    name = 'fetch issues'
    list_result, issues = run_json_github_cli(
        [
            gh_path,
            'issue',
            'list',
            '--repo',
            TARGET_REPOSITORY,
            '--state',
            'open',
            '--limit',
            '5',
            '--json',
            'number,title,state',
        ],
    )
    if list_result.return_code != 0:
        return CapabilityResult(name, False, f'gh issue list failed: {command_error(list_result)}')
    if not isinstance(issues, list):
        return CapabilityResult(name, False, 'gh issue list returned invalid JSON')
    return CapabilityResult(name, True, f'{len(issues)} open issues')


def print_capability(result: CapabilityResult) -> None:
    """Print one capability result."""
    if not result.ok:
        print(f'{result.name} failed: {result.detail}')
    elif result.detail:
        print(f'{result.name} ok ({result.detail})')
    else:
        print(f'{result.name} ok')


def verify_create_capability(gh_path: str) -> CapabilityResult:
    """Check that gh pr create accepts the flags the worker needs."""
    name = 'create pull request'
    required_flags = ['--base', '--head', '--title', '--body-file']
    result = run_github_cli([gh_path, 'pr', 'create', '--help'])
    if result.return_code != 0:
        return CapabilityResult(name, False, f'gh pr create --help failed: {command_error(result)}')
    help_text = f'{result.standard_output}\n{result.standard_error}'
    missing_flags = [flag for flag in required_flags if flag not in help_text]
    if missing_flags:
        return CapabilityResult(name, False, f'gh pr create --help does not mention {" ".join(missing_flags)}')
    return CapabilityResult(name, True, f'pr create supports {" ".join(required_flags)}')


def verify_review_capability(gh_path: str) -> CapabilityResult:
    """Check that gh pr review accepts approve, comment, and request changes."""
    name = 'review pull request'
    required_flags = ['--approve', '--comment', '--request-changes']
    result = run_github_cli([gh_path, 'pr', 'review', '--help'])
    if result.return_code != 0:
        return CapabilityResult(name, False, f'gh pr review --help failed: {command_error(result)}')
    help_text = f'{result.standard_output}\n{result.standard_error}'
    missing_flags = [flag for flag in required_flags if flag not in help_text]
    if missing_flags:
        return CapabilityResult(name, False, f'gh pr review --help does not mention {" ".join(missing_flags)}')
    return CapabilityResult(name, True, f'pr review supports {" ".join(required_flags)}')


def verify_approve_capability(gh_path: str) -> CapabilityResult:
    """Check the scope needed to approve, and record the self-approval limit."""
    name = 'approve pull request'
    status = authentication_status(gh_path)
    if status.return_code != 0:
        return CapabilityResult(name, False, f'gh auth status failed: {command_error(status)}')
    _account, scopes = parse_authentication_status(status.standard_output)
    if REQUIRED_SCOPE not in scopes:
        return CapabilityResult(name, False, f'the token lacks the {REQUIRED_SCOPE} scope')
    return CapabilityResult(
        name,
        True,
        'own pull requests cannot be approved; requires a pull request by another account',
    )


def parse_pull_request_number(output: str) -> int | None:
    """Return the pull request number from a gh pull request URL."""
    match = PULL_REQUEST_URL_PATTERN.search(output)
    if match is None:
        return None
    return int(match.group('number'))


def run_checked_command(arguments: list[str], working_directory: Path | None = None) -> CommandResult:
    """Run one command in the working directory, raising when it fails."""
    result = run_github_cli(arguments, working_directory=working_directory)
    if result.return_code != 0:
        raise InstallError(f'{" ".join(arguments)} failed: {command_error(result)}')
    return result


def prepare_smoke_repository(working_directory: Path, title: str) -> None:
    """Create a one-commit git repository for the smoke pull request."""
    readme_path = working_directory / 'README.md'
    timestamp = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
    readme_path.write_text(f'# GitHub CLI smoke test\n\nCreated at {timestamp}\n', encoding='utf-8')
    for command in (
        ['init'],
        ['remote', 'add', 'origin', SMOKE_REPOSITORY_URL],
        ['add', 'README.md'],
        ['commit', '-m', title],
    ):
        run_checked_command(['git', *command], working_directory)


def push_smoke_branch(working_directory: Path, branch: str) -> None:
    """Push the smoke commit with a per-command gh credential helper."""
    run_checked_command(
        [
            'git',
            '-c',
            'credential.helper=',
            '-c',
            'credential.helper=!gh auth git-credential',
            'push',
            'origin',
            f'HEAD:refs/heads/{branch}',
        ],
        working_directory,
    )


def repository_has_default_branch(gh_path: str) -> bool:
    """Return whether the smoke repository has a default branch."""
    _result, repository = run_json_github_cli(
        [gh_path, 'repo', 'view', SMOKE_REPOSITORY, '--json', 'defaultBranchRef'],
    )
    if not isinstance(repository, dict):
        return False
    return bool(repository.get('defaultBranchRef'))


def find_open_smoke_pull_request(gh_path: str) -> int | None:
    """Return the number of an open smoke pull request, when one exists."""
    result, pull_requests = run_json_github_cli(
        [gh_path, 'pr', 'list', '--repo', SMOKE_REPOSITORY, '--state', 'open', '--json', 'number,headRefName'],
    )
    if result.return_code != 0 or not isinstance(pull_requests, list):
        return None
    for pull_request in pull_requests:
        if not isinstance(pull_request, dict):
            continue
        number = pull_request.get('number')
        if str(pull_request.get('headRefName', '')).startswith('smoke-') and isinstance(number, int):
            return number
    return None


def create_smoke_pull_request(gh_path: str, branch: str, title: str, needs_main_branch: bool) -> int:
    """Push a scratch branch and open a pull request for it."""
    with tempfile.TemporaryDirectory() as temporary_directory:
        working_directory = Path(temporary_directory)
        prepare_smoke_repository(working_directory, title)
        if needs_main_branch:
            push_smoke_branch(working_directory, 'main')
        push_smoke_branch(working_directory, branch)
        body_path = working_directory / 'pull-request-body.md'
        body_path.write_text(f'Automated GitHub CLI smoke test for {branch}.\n', encoding='utf-8')
        create_result = run_checked_command(
            [
                gh_path,
                'pr',
                'create',
                '--repo',
                SMOKE_REPOSITORY,
                '--base',
                'main',
                '--head',
                branch,
                '--title',
                title,
                '--body-file',
                str(body_path),
            ],
            working_directory,
        )
    number = parse_pull_request_number(create_result.standard_output)
    if number is None:
        raise InstallError(f'gh pr create printed no pull request number: {create_result.standard_output.strip()}')
    return number


def smoke_pull_request(gh_path: str) -> CapabilityResult:
    """Create, review, and close a scratch pull request as a write check."""
    name = 'smoke pull request'
    today = datetime.datetime.now(tz=datetime.timezone.utc).date()
    branch = f'smoke-{today.isoformat()}'
    title = f'GitHub CLI smoke test {branch}'
    try:
        repository_view = run_github_cli([gh_path, 'repo', 'view', SMOKE_REPOSITORY, '--json', 'name'])
        repository_exists = repository_view.return_code == 0
        if not repository_exists:
            run_checked_command(
                [
                    gh_path,
                    'repo',
                    'create',
                    SMOKE_REPOSITORY,
                    '--public',
                    '--add-readme',
                    '--description',
                    SMOKE_REPOSITORY_DESCRIPTION,
                ],
            )
        number = find_open_smoke_pull_request(gh_path)
        if number is None:
            needs_main_branch = repository_exists and not repository_has_default_branch(gh_path)
            number = create_smoke_pull_request(gh_path, branch, title, needs_main_branch)
        run_checked_command(
            [
                gh_path,
                'pr',
                'review',
                str(number),
                '--repo',
                SMOKE_REPOSITORY,
                '--comment',
                '--body',
                SMOKE_REVIEW_BODY,
            ],
        )
        run_checked_command(
            [gh_path, 'pr', 'close', str(number), '--repo', SMOKE_REPOSITORY, '--delete-branch'],
        )
    except InstallError as error:
        return CapabilityResult(name, False, str(error))
    return CapabilityResult(name, True, f'#{number} created, reviewed, closed')


def handle_install(arguments: argparse.Namespace) -> int:
    """Install the pinned gh binary."""
    return install_binary(arguments.version, LOCAL_BINARY_DIRECTORY)


def handle_authenticate(_arguments: argparse.Namespace) -> int:
    """Log the installed gh binary in as albertas."""
    standard_input = '' if sys.stdin.isatty() else sys.stdin.read()
    return authenticate(require_github_cli(), os.environ, standard_input)


def handle_verify(arguments: argparse.Namespace) -> int:
    """Verify authentication and the read and write capabilities of the installed gh."""
    gh_path = require_github_cli()
    status = authentication_status(gh_path)
    account, scopes = parse_authentication_status(status.standard_output)
    if status.return_code != 0 or account != EXPECTED_ACCOUNT or REQUIRED_SCOPE not in scopes:
        print('not authenticated; run:')
        print(AUTH_LOGIN_COMMAND)
        return 3
    live_capabilities = [verify_pull_requests(gh_path), verify_issues(gh_path)]
    for capability in live_capabilities:
        if capability.ok:
            print_capability(capability)
    live_failures = [capability for capability in live_capabilities if not capability.ok]
    if live_failures:
        for capability in live_failures:
            print_capability(capability)
        return 5
    capability_checks = [
        verify_create_capability(gh_path),
        verify_review_capability(gh_path),
        verify_approve_capability(gh_path),
    ]
    for capability in capability_checks:
        if capability.ok:
            print_capability(capability)
    smoke_capability = smoke_pull_request(gh_path) if arguments.smoke_pull_request else None
    if smoke_capability is not None and smoke_capability.ok:
        print_capability(smoke_capability)
    failures = [capability for capability in capability_checks if not capability.ok]
    if smoke_capability is not None and not smoke_capability.ok:
        failures.append(smoke_capability)
    for capability in failures:
        print_capability(capability)
    if any(not capability.ok for capability in capability_checks):
        return 4
    if smoke_capability is not None and not smoke_capability.ok:
        return 5
    return 0


def build_argument_parser() -> argparse.ArgumentParser:
    """Return the command line parser."""
    parser = argparse.ArgumentParser(
        prog='install_github_cli',
        description='Install and verify the GitHub CLI (gh) for the deadcode package.',
    )
    subparsers = parser.add_subparsers(dest='command')
    install_parser = subparsers.add_parser('install', help='install a pinned gh binary into ~/.local/bin')
    install_parser.add_argument(
        '--version',
        default=DEFAULT_GH_VERSION,
        help=f'gh release to install (default {DEFAULT_GH_VERSION})',
    )
    install_parser.set_defaults(handler=handle_install, version=DEFAULT_GH_VERSION)
    authenticate_parser = subparsers.add_parser(
        'authenticate',
        help='log gh in as albertas with the repo scope, using GH_TOKEN or standard input',
    )
    authenticate_parser.set_defaults(handler=handle_authenticate)
    verify_parser = subparsers.add_parser(
        'verify',
        help='verify authentication and the read and write capabilities of the installed gh',
    )
    verify_parser.add_argument(
        '--smoke-pull-request',
        action='store_true',
        help=f'create, review, and close a scratch pull request in {SMOKE_REPOSITORY}',
    )
    verify_parser.set_defaults(handler=handle_verify)
    parser.set_defaults(handler=handle_install, version=DEFAULT_GH_VERSION)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the requested command and return the process exit code."""
    parser = build_argument_parser()
    arguments = parser.parse_args(argv)
    try:
        return arguments.handler(arguments)
    except InstallError as error:
        print(error, file=sys.stderr)
        return error.exit_code


if __name__ == '__main__':
    sys.exit(main())
