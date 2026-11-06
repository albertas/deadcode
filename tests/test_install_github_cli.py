"""Tests for the GitHub CLI setup tool."""

from __future__ import annotations

import hashlib
import io
import os
import shutil
import sys
import tarfile
import tempfile
import unittest
import urllib.error
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

if TYPE_CHECKING:
    from collections.abc import Iterator

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from install_github_cli import install_github_cli as github_cli  # noqa: E402

VERSION = '2.46.0'
ARCHIVE_NAME = f'gh_{VERSION}_linux_amd64.tar.gz'
FAKE_GH_SCRIPT = b"#!/bin/sh\necho 'gh version 2.46.0 (2024-03-15)'\n"

FAKE_GIT_SCRIPT = """#!/usr/bin/env python3
import os
import sys

with open(os.environ['GIT_CALL_LOG'], 'a', encoding='utf-8') as log:
    log.write(' '.join(sys.argv[1:]) + '\\n')
sys.exit(0)
"""

FAKE_GH_AUTH_SCRIPT = """#!/usr/bin/env python3
import json
import os
import sys

SMOKE_REPOSITORY = 'albertas/gh-cli-smoke-test'
PR_CREATE_HELP = '''Create a pull request on GitHub.

USAGE
  gh pr create [flags]

FLAGS
  -B, --base branch        The branch into which you want your code merged
      --body-file file     Read body text from file
  -H, --head branch        The branch that contains commits for your pull request
  -t, --title string       Title for the pull request
'''
PR_REVIEW_HELP = '''Add a review to a pull request.

USAGE
  gh pr review [<number> | <url> | <branch>] [flags]

FLAGS
  -a, --approve            Approve pull request
  -c, --comment            Comment on a pull request
  -r, --request-changes    Request changes on a pull request
'''


def help_output(text):
    without = os.environ.get('GH_HELP_WITHOUT', '')
    if not without:
        return text
    return '\\n'.join(line for line in text.splitlines() if without not in line)


arguments = sys.argv[1:]
with open(os.environ['GH_CALL_LOG'], 'a', encoding='utf-8') as log:
    log.write(' '.join(arguments) + '\\n')

mode = os.environ.get('GH_FAKE_MODE', 'authenticated')
token_file = os.environ['GH_TOKEN_FILE']
failure_file = os.environ.get('GH_FAKE_FAILURE_FILE', '')

if arguments[:1] != ['auth'] and failure_file and os.path.exists(failure_file):
    with open(failure_file, encoding='utf-8') as handle:
        remaining = int(handle.read().strip() or '0')
    if remaining > 0:
        with open(failure_file, 'w', encoding='utf-8') as handle:
            handle.write(str(remaining - 1))
        print('HTTP 429: rate limit exceeded', file=sys.stderr)
        sys.exit(1)

if arguments[:2] == ['auth', 'status']:
    if mode == 'unauthenticated':
        print('You are not logged into any GitHub hosts.', file=sys.stderr)
        sys.exit(1)
    if mode == 'unauthenticated-until-login' and not os.path.exists(token_file):
        print('You are not logged into any GitHub hosts.', file=sys.stderr)
        sys.exit(1)
    print('github.com')
    print('  \u2713 Logged in to github.com account albertas (keyring)')
    print('  - Active account: true')
    print('  - Git operations protocol: ssh')
    print('  - Token: gho_************************************')
    if mode == 'missing-scope':
        print("  - Token scopes: 'gist', 'read:org'")
    else:
        print("  - Token scopes: 'gist', 'read:org', 'repo', 'workflow'")
    sys.exit(0)

if arguments[:3] == ['auth', 'login', '--with-token']:
    with open(token_file, 'w', encoding='utf-8') as handle:
        handle.write(sys.stdin.read().strip())
    sys.exit(0)

if arguments[:3] == ['pr', 'create', '--help']:
    print(help_output(PR_CREATE_HELP))
    sys.exit(0)

if arguments[:3] == ['pr', 'review', '--help']:
    print(help_output(PR_REVIEW_HELP))
    sys.exit(0)

if arguments[:2] == ['repo', 'view']:
    if os.environ.get('GH_FAKE_SMOKE_REPOSITORY_EXISTS', '1') != '1':
        print('HTTP 404: Not Found', file=sys.stderr)
        sys.exit(1)
    if 'defaultBranchRef' in arguments:
        print(json.dumps({'defaultBranchRef': {'name': 'main'}}))
    else:
        print(json.dumps({'name': 'gh-cli-smoke-test'}))
    sys.exit(0)

if arguments[:2] == ['repo', 'create']:
    print('https://github.com/albertas/gh-cli-smoke-test')
    sys.exit(0)

if arguments[:2] == ['pr', 'list'] and SMOKE_REPOSITORY in arguments:
    if os.environ.get('GH_FAKE_SMOKE_OPEN_PULL_REQUEST', '0') == '1':
        print(json.dumps([{'number': 5, 'headRefName': 'smoke-test-branch'}]))
    else:
        print(json.dumps([]))
    sys.exit(0)

if arguments[:2] == ['pr', 'create']:
    print('https://github.com/albertas/gh-cli-smoke-test/pull/7')
    sys.exit(0)

if arguments[:2] == ['pr', 'review']:
    sys.exit(0)

if arguments[:2] == ['pr', 'close']:
    sys.exit(0)

if arguments[:2] == ['pr', 'list']:
    count = int(os.environ.get('GH_FAKE_PULL_REQUEST_COUNT', '1'))
    pull_requests = [
        {'number': 38 + index, 'title': f'Pull request {38 + index}', 'state': 'OPEN'}
        for index in range(count)
    ]
    print(json.dumps(pull_requests))
    sys.exit(0)

if arguments[:2] == ['issue', 'list']:
    issues = [
        {'number': 12, 'title': 'Issue 12', 'state': 'OPEN'},
        {'number': 11, 'title': 'Issue 11', 'state': 'OPEN'},
    ]
    print(json.dumps(issues))
    sys.exit(0)

if arguments[:2] == ['pr', 'view']:
    number = int(arguments[2])
    pull_request = {
        'number': number,
        'title': f'Pull request {number}',
        'state': 'OPEN',
        'url': f'https://github.com/albertas/deadcode/pull/{number}',
    }
    print(json.dumps(pull_request))
    sys.exit(0)

print('unexpected gh arguments: ' + ' '.join(arguments), file=sys.stderr)
sys.exit(1)
"""


class FakeGitHubCli:
    """Handle to a fake gh binary installed on PATH for one test."""

    def __init__(self, binary_path: Path, call_log: Path, token_file: Path) -> None:
        self.binary_path = binary_path
        self.call_log = call_log
        self.token_file = token_file

    @property
    def calls(self) -> list[str]:
        """Return the logged argument vectors, one per gh invocation."""
        if not self.call_log.exists():
            return []
        return self.call_log.read_text(encoding='utf-8').splitlines()


@contextmanager
def fake_git() -> Iterator[Path]:
    """Put a fake git on PATH that logs its arguments and succeeds."""
    with tempfile.TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)
        binary_directory = directory / 'bin'
        binary_directory.mkdir()
        write_executable(binary_directory / 'git', FAKE_GIT_SCRIPT.encode())
        environment = {
            'PATH': f'{binary_directory}{os.pathsep}{os.environ.get("PATH", "")}',
            'GIT_CALL_LOG': str(directory / 'git-calls.log'),
        }
        with mock.patch.dict(os.environ, environment):
            yield directory


@contextmanager
def fake_github_cli(
    mode: str = 'authenticated',
    pull_request_count: int = 1,
    failure_count: int = 0,
    smoke_repository_exists: bool = True,
    smoke_open_pull_request: bool = False,
    help_without: str = '',
) -> Iterator[FakeGitHubCli]:
    """Put a fake gh on PATH that logs its arguments and fakes gh output."""
    with tempfile.TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)
        binary_directory = directory / 'bin'
        binary_directory.mkdir()
        binary_path = binary_directory / 'gh'
        write_executable(binary_path, FAKE_GH_AUTH_SCRIPT.encode())
        failure_file = directory / 'failures.txt'
        failure_file.write_text(str(failure_count), encoding='utf-8')
        environment = {
            'PATH': f'{binary_directory}{os.pathsep}{os.environ.get("PATH", "")}',
            'GH_CALL_LOG': str(directory / 'calls.log'),
            'GH_TOKEN_FILE': str(directory / 'token.txt'),
            'GH_FAKE_MODE': mode,
            'GH_FAKE_FAILURE_FILE': str(failure_file),
            'GH_FAKE_PULL_REQUEST_COUNT': str(pull_request_count),
            'GH_FAKE_SMOKE_REPOSITORY_EXISTS': '1' if smoke_repository_exists else '0',
            'GH_FAKE_SMOKE_OPEN_PULL_REQUEST': '1' if smoke_open_pull_request else '0',
            'GH_HELP_WITHOUT': help_without,
            'GH_TOKEN': '',
        }
        with mock.patch.dict(os.environ, environment):
            yield FakeGitHubCli(binary_path, directory / 'calls.log', directory / 'token.txt')


def build_archive(binary_bytes: bytes = FAKE_GH_SCRIPT) -> bytes:
    """Return a release archive with the gh binary inside."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
        info = tarfile.TarInfo(f'gh_{VERSION}_linux_amd64/bin/gh')
        info.size = len(binary_bytes)
        info.mode = 0o755
        archive.addfile(info, io.BytesIO(binary_bytes))
    return buffer.getvalue()


def checksums_text(archive_bytes: bytes) -> str:
    """Return a checksums file listing the digest of the archive."""
    digest = hashlib.sha256(archive_bytes).hexdigest()
    return f'{digest}  {ARCHIVE_NAME}\n' + '0' * 64 + '  gh_2.46.0_checksums.txt\n'


def write_executable(path: Path, content: bytes) -> None:
    """Write an executable file."""
    path.write_bytes(content)
    path.chmod(0o755)


class FakeResponse:
    """Minimal stand-in for the object returned by urlopen."""

    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> FakeResponse:  # noqa: PYI034
        return self

    def __exit__(self, *_arguments: object) -> bool:
        return False


def server_error(code: int = 503) -> urllib.error.HTTPError:
    """Return an HTTP error for the given status code."""
    return urllib.error.HTTPError('https://example.invalid/gh', code, 'server error', None, None)


class ChecksumsTest(unittest.TestCase):
    def test_parse_checksums_returns_digest(self):
        text = 'abc123  gh_2.46.0_linux_amd64.tar.gz\n' 'def456  gh_2.46.0_linux_amd64.zip\n'
        self.assertEqual(
            github_cli.parse_checksums(text, 'gh_2.46.0_linux_amd64.tar.gz', 'https://example.invalid/checksums'),
            'abc123',
        )

    def test_parse_checksums_accepts_star_prefixed_names(self):
        text = 'ABC123  *gh_2.46.0_linux_amd64.tar.gz\n'
        self.assertEqual(
            github_cli.parse_checksums(text, 'gh_2.46.0_linux_amd64.tar.gz', 'https://example.invalid/checksums'),
            'abc123',
        )

    def test_parse_checksums_missing_entry_raises(self):
        with self.assertRaises(github_cli.InstallError) as raised:
            github_cli.parse_checksums('abc123  other.tar.gz\n', 'missing.tar.gz', 'https://example.invalid/checksums')
        self.assertIn('missing.tar.gz', str(raised.exception))
        self.assertIn('https://example.invalid/checksums', str(raised.exception))


class InstalledVersionTest(unittest.TestCase):
    def test_installed_version_parses_output(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            binary_path = Path(temporary_directory) / 'gh'
            write_executable(binary_path, FAKE_GH_SCRIPT)
            self.assertEqual(github_cli.installed_version(binary_path), VERSION)

    def test_installed_version_returns_none_when_missing(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            self.assertIsNone(github_cli.installed_version(Path(temporary_directory) / 'gh'))

    def test_installed_version_returns_none_for_non_executable(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            binary_path = Path(temporary_directory) / 'gh'
            binary_path.write_bytes(FAKE_GH_SCRIPT)
            binary_path.chmod(0o644)
            self.assertIsNone(github_cli.installed_version(binary_path))


class InstallBinaryTest(unittest.TestCase):
    def test_install_writes_verified_binary(self):
        archive_bytes = build_archive()
        with tempfile.TemporaryDirectory() as temporary_directory:
            binary_directory = Path(temporary_directory) / 'bin'
            with (
                mock.patch.object(
                    github_cli,
                    'download_bytes',
                    side_effect=[checksums_text(archive_bytes).encode(), archive_bytes],
                ),
                redirect_stdout(io.StringIO()) as output,
            ):
                self.assertEqual(github_cli.install_binary(VERSION, binary_directory), 0)
            binary_path = binary_directory / 'gh'
            self.assertEqual(binary_path.read_bytes(), FAKE_GH_SCRIPT)
            self.assertEqual(binary_path.stat().st_mode & 0o777, 0o755)
            self.assertIn(f'installed gh {VERSION} at {binary_path}', output.getvalue())

    def test_install_is_idempotent(self):
        archive_bytes = build_archive()
        with tempfile.TemporaryDirectory() as temporary_directory:
            binary_directory = Path(temporary_directory) / 'bin'
            with (
                mock.patch.object(
                    github_cli,
                    'download_bytes',
                    side_effect=[checksums_text(archive_bytes).encode(), archive_bytes],
                ),
                redirect_stdout(io.StringIO()),
            ):
                github_cli.install_binary(VERSION, binary_directory)
            with (
                mock.patch.object(
                    github_cli,
                    'download_bytes',
                    side_effect=AssertionError('the second run must not download anything'),
                ),
                redirect_stdout(io.StringIO()) as output,
            ):
                self.assertEqual(github_cli.install_binary(VERSION, binary_directory), 0)
            self.assertIn('already installed', output.getvalue())

    def test_checksum_mismatch_leaves_existing_binary_untouched(self):
        archive_bytes = build_archive()
        mismatched_checksums = f'{"0" * 64}  {ARCHIVE_NAME}\n'
        with tempfile.TemporaryDirectory() as temporary_directory:
            binary_directory = Path(temporary_directory) / 'bin'
            binary_directory.mkdir()
            binary_path = binary_directory / 'gh'
            write_executable(binary_path, b'previous binary')
            with (
                mock.patch.object(
                    github_cli,
                    'download_bytes',
                    side_effect=[mismatched_checksums.encode(), archive_bytes],
                ),
                self.assertRaises(github_cli.InstallError) as raised,
            ):
                github_cli.install_binary(VERSION, binary_directory)
            message = str(raised.exception)
            self.assertIn('0' * 64, message)
            self.assertIn(hashlib.sha256(archive_bytes).hexdigest(), message)
            self.assertEqual(binary_path.read_bytes(), b'previous binary')


class DownloadTest(unittest.TestCase):
    def test_download_retries_on_server_error(self):
        sleeps = []
        with (
            mock.patch.object(
                github_cli.urllib.request,
                'urlopen',
                side_effect=[server_error(503), server_error(429), FakeResponse(b'payload')],
            ) as urlopen,
            mock.patch.object(github_cli.time, 'sleep', side_effect=sleeps.append),
        ):
            self.assertEqual(github_cli.download_bytes('https://example.invalid/gh'), b'payload')
        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual(sleeps[:2], [1.0, 2.0])
        self.assertEqual(sleeps[-1], github_cli.DELAY_AFTER_CALL_SECONDS)

    def test_download_gives_up_after_three_attempts(self):
        with (
            mock.patch.object(github_cli.urllib.request, 'urlopen', side_effect=server_error(500)) as urlopen,
            mock.patch.object(github_cli.time, 'sleep'),
            self.assertRaises(github_cli.InstallError) as raised,
        ):
            github_cli.download_bytes('https://example.invalid/gh')
        self.assertEqual(urlopen.call_count, 3)
        self.assertIn('https://example.invalid/gh', str(raised.exception))
        self.assertIn('3 attempts', str(raised.exception))

    def test_download_does_not_retry_client_errors(self):
        with (
            mock.patch.object(github_cli.urllib.request, 'urlopen', side_effect=server_error(404)) as urlopen,
            mock.patch.object(github_cli.time, 'sleep'),
            self.assertRaises(github_cli.InstallError),
        ):
            github_cli.download_bytes('https://example.invalid/gh')
        self.assertEqual(urlopen.call_count, 1)


class AuthenticationStatusTest(unittest.TestCase):
    def test_authentication_status_parses_account_and_scopes(self):
        output = (
            'github.com\n'
            '  \u2713 Logged in to github.com account albertas (keyring)\n'
            '  - Active account: true\n'
            "  - Token scopes: 'gist', 'read:org', 'repo', 'workflow'\n"
        )
        self.assertEqual(
            github_cli.parse_authentication_status(output),
            ('albertas', ['gist', 'read:org', 'repo', 'workflow']),
        )

    def test_authentication_status_parses_logged_out_output(self):
        self.assertEqual(
            github_cli.parse_authentication_status('You are not logged into any GitHub hosts.\n'),
            (None, []),
        )


class AuthenticateTest(unittest.TestCase):
    def test_authenticate_is_noop_when_already_authenticated(self):
        with fake_github_cli() as fake_gh, mock.patch.object(github_cli.time, 'sleep'):
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(github_cli.authenticate(str(fake_gh.binary_path), {}, ''), 0)
            self.assertIn('already authenticated as albertas', output.getvalue())
            self.assertNotIn('auth login', '\n'.join(fake_gh.calls))

    def test_authenticate_requires_token_and_prints_command(self):
        with fake_github_cli('unauthenticated') as fake_gh, mock.patch.object(github_cli.time, 'sleep'):
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(github_cli.authenticate(str(fake_gh.binary_path), {}, ''), 3)
            lines = output.getvalue().splitlines()
            self.assertIn('not authenticated; run:', lines)
            self.assertIn('  gh auth login --hostname github.com --git-protocol ssh --scopes repo', lines)

    def test_authenticate_logs_in_with_token_from_standard_input(self):
        with fake_github_cli('unauthenticated-until-login') as fake_gh, mock.patch.object(github_cli.time, 'sleep'):
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(
                    github_cli.authenticate(str(fake_gh.binary_path), {}, 'secret-token\n'),
                    0,
                )
            self.assertIn('auth login --with-token --hostname github.com', fake_gh.calls)
            self.assertEqual(fake_gh.token_file.read_text(encoding='utf-8'), 'secret-token')
            self.assertIn('authenticated as albertas', output.getvalue())
            self.assertNotIn('secret-token', output.getvalue())

    def test_authenticate_reads_token_from_environment(self):
        with fake_github_cli('unauthenticated-until-login') as fake_gh, mock.patch.object(github_cli.time, 'sleep'):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(
                    github_cli.authenticate(str(fake_gh.binary_path), {'GH_TOKEN': 'env-token'}, ''),
                    0,
                )
            self.assertEqual(fake_gh.token_file.read_text(encoding='utf-8'), 'env-token')

    def test_authenticate_reports_missing_repo_scope(self):
        with fake_github_cli('missing-scope') as fake_gh, mock.patch.object(github_cli.time, 'sleep'):
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(github_cli.authenticate(str(fake_gh.binary_path), {}, ''), 4)
            self.assertIn('gh auth refresh --hostname github.com --scopes repo', output.getvalue())

    def test_authenticate_never_writes_credentials_into_the_repository(self):
        working_directory = tempfile.mkdtemp()
        previous_directory = Path.cwd()
        try:
            os.chdir(working_directory)
            with (
                fake_github_cli('unauthenticated-until-login') as fake_gh,
                mock.patch.object(github_cli.time, 'sleep'),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(
                    github_cli.authenticate(str(fake_gh.binary_path), {}, 'secret-token\n'),
                    0,
                )
        finally:
            os.chdir(previous_directory)
            written = sorted(os.listdir(working_directory))
            shutil.rmtree(working_directory)
        self.assertEqual(written, [])


class VerifyReadCapabilitiesTest(unittest.TestCase):
    def test_verify_pull_requests_uses_exact_arguments(self):
        with fake_github_cli() as fake_gh, mock.patch.object(github_cli.time, 'sleep'):
            result = github_cli.verify_pull_requests(str(fake_gh.binary_path))
            calls = fake_gh.calls
        self.assertTrue(result.ok)
        self.assertEqual(result.detail, '#38 Pull request 38 (OPEN)')
        self.assertEqual(
            calls,
            [
                'pr list --repo albertas/deadcode --state open --limit 5 --json number,title,state',
                'pr view 38 --repo albertas/deadcode --json number,title,state,url',
            ],
        )

    def test_verify_pull_requests_with_no_open_pull_requests(self):
        with fake_github_cli(pull_request_count=0) as fake_gh, mock.patch.object(github_cli.time, 'sleep'):
            result = github_cli.verify_pull_requests(str(fake_gh.binary_path))
            calls = fake_gh.calls
        self.assertTrue(result.ok)
        self.assertEqual(result.detail, 'no open pull requests')
        self.assertEqual(
            calls,
            ['pr list --repo albertas/deadcode --state open --limit 5 --json number,title,state'],
        )

    def test_verify_issues_uses_exact_arguments(self):
        with fake_github_cli() as fake_gh, mock.patch.object(github_cli.time, 'sleep'):
            result = github_cli.verify_issues(str(fake_gh.binary_path))
            calls = fake_gh.calls
        self.assertTrue(result.ok)
        self.assertEqual(result.detail, '2 open issues')
        self.assertEqual(
            calls,
            ['issue list --repo albertas/deadcode --state open --limit 5 --json number,title,state'],
        )

    def test_verify_sleeps_one_second_after_success(self):
        sleeps = []
        with (
            fake_github_cli() as fake_gh,
            mock.patch.object(github_cli.time, 'sleep', side_effect=sleeps.append),
        ):
            github_cli.verify_issues(str(fake_gh.binary_path))
        self.assertEqual(sleeps, [github_cli.DELAY_AFTER_CALL_SECONDS])

    def test_verify_retries_rate_limited_call_with_doubling_delay(self):
        sleeps = []
        with (
            fake_github_cli(failure_count=2) as fake_gh,
            mock.patch.object(github_cli.time, 'sleep', side_effect=sleeps.append),
        ):
            result = github_cli.verify_pull_requests(str(fake_gh.binary_path))
            calls = fake_gh.calls
        self.assertTrue(result.ok)
        self.assertEqual(sleeps[:2], [2.0, 4.0])
        self.assertEqual(len([call for call in calls if call.startswith('pr list')]), 3)

    def test_verify_returns_five_after_three_failed_attempts(self):
        with fake_github_cli(failure_count=3) as fake_gh, mock.patch.object(github_cli.time, 'sleep'):
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(github_cli.main(['verify']), 5)
            calls = fake_gh.calls
        lines = output.getvalue().splitlines()
        self.assertTrue(lines[-1].startswith('fetch pull requests failed: '))
        self.assertEqual(len([call for call in calls if call.startswith('pr list')]), 3)

    def test_verify_reports_missing_gh_with_path_hint(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            binary_directory = Path(temporary_directory)
            write_executable(binary_directory / 'gh', FAKE_GH_SCRIPT)
            with (
                mock.patch.object(github_cli.shutil, 'which', return_value=None),
                mock.patch.object(github_cli, 'LOCAL_BINARY_DIRECTORY', binary_directory),
                redirect_stdout(io.StringIO()) as output,
            ):
                self.assertEqual(github_cli.main(['verify']), 3)
            self.assertIn('export PATH="$HOME/.local/bin:$PATH"', output.getvalue())


class VerifyWriteCapabilitiesTest(unittest.TestCase):
    def test_verify_create_capability_ok(self):
        with fake_github_cli() as fake_gh, mock.patch.object(github_cli.time, 'sleep'):
            result = github_cli.verify_create_capability(str(fake_gh.binary_path))
        self.assertTrue(result.ok)
        self.assertEqual(result.name, 'create pull request')
        self.assertEqual(result.detail, 'pr create supports --base --head --title --body-file')

    def test_verify_review_capability_ok(self):
        with fake_github_cli() as fake_gh, mock.patch.object(github_cli.time, 'sleep'):
            result = github_cli.verify_review_capability(str(fake_gh.binary_path))
        self.assertTrue(result.ok)
        self.assertEqual(result.name, 'review pull request')
        self.assertEqual(result.detail, 'pr review supports --approve --comment --request-changes')

    def test_verify_review_capability_missing_approve_returns_four(self):
        with fake_github_cli(help_without='--approve') as fake_gh, mock.patch.object(github_cli.time, 'sleep'):
            result = github_cli.verify_review_capability(str(fake_gh.binary_path))
        self.assertFalse(result.ok)
        self.assertIn('--approve', result.detail)

    def test_verify_create_capability_missing_flag_returns_four(self):
        with fake_github_cli(help_without='--base') as fake_gh, mock.patch.object(github_cli.time, 'sleep'):
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(github_cli.main(['verify']), 4)
            self.assertNotIn('auth login', '\n'.join(fake_gh.calls))
        lines = output.getvalue().splitlines()
        self.assertTrue(lines[-1].startswith('create pull request failed: '))
        self.assertIn('--base', lines[-1])

    def test_verify_approve_capability_prints_self_approval_note(self):
        with fake_github_cli() as fake_gh, mock.patch.object(github_cli.time, 'sleep'):
            result = github_cli.verify_approve_capability(str(fake_gh.binary_path))
        self.assertTrue(result.ok)
        self.assertEqual(result.name, 'approve pull request')
        self.assertEqual(
            result.detail,
            'own pull requests cannot be approved; requires a pull request by another account',
        )

    def test_verify_prints_all_five_capabilities_in_order(self):
        with fake_github_cli() as fake_gh, mock.patch.object(github_cli.time, 'sleep'):
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(github_cli.main(['verify']), 0)
            calls = fake_gh.calls
        self.assertEqual(
            output.getvalue().splitlines(),
            [
                'fetch pull requests ok (#38 Pull request 38 (OPEN))',
                'fetch issues ok (2 open issues)',
                'create pull request ok (pr create supports --base --head --title --body-file)',
                'review pull request ok (pr review supports --approve --comment --request-changes)',
                'approve pull request ok (own pull requests cannot be approved; '
                'requires a pull request by another account)',
            ],
        )
        self.assertFalse([call for call in calls if call.startswith('repo view')])

    def test_verify_exits_four_when_capability_missing(self):
        with fake_github_cli(help_without='--approve') as fake_gh, mock.patch.object(github_cli.time, 'sleep'):
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(github_cli.main(['verify']), 4)
            calls = fake_gh.calls
        lines = output.getvalue().splitlines()
        self.assertTrue(lines[-1].startswith('review pull request failed: '))
        self.assertEqual(len([call for call in calls if call.startswith('pr review --help')]), 1)


class SmokePullRequestTest(unittest.TestCase):
    def test_smoke_pull_request_creates_reviews_and_closes(self):
        with (
            fake_github_cli(smoke_repository_exists=False) as fake_gh,
            fake_git(),
            mock.patch.object(github_cli.time, 'sleep'),
        ):
            result = github_cli.smoke_pull_request(str(fake_gh.binary_path))
            calls = fake_gh.calls
        self.assertTrue(result.ok)
        self.assertEqual(result.name, 'smoke pull request')
        self.assertEqual(result.detail, '#7 created, reviewed, closed')
        commands = list(dict.fromkeys(' '.join(call.split()[:2]) for call in calls))
        self.assertEqual(
            commands,
            ['repo view', 'repo create', 'pr list', 'pr create', 'pr review', 'pr close'],
        )
        create_call = next(call for call in calls if call.startswith('pr create'))
        self.assertIn('--base main', create_call)
        close_call = next(call for call in calls if call.startswith('pr close'))
        self.assertIn('--delete-branch', close_call)

    def test_smoke_pull_request_reuses_open_pull_request(self):
        with (
            fake_github_cli(smoke_open_pull_request=True) as fake_gh,
            fake_git(),
            mock.patch.object(github_cli.time, 'sleep'),
        ):
            result = github_cli.smoke_pull_request(str(fake_gh.binary_path))
            calls = fake_gh.calls
        self.assertTrue(result.ok)
        self.assertEqual(result.detail, '#5 created, reviewed, closed')
        self.assertEqual([call for call in calls if call.startswith('pr create')], [])
        self.assertTrue(any(call.startswith('pr review 5 ') for call in calls))
        self.assertTrue(any(call.startswith('pr close 5 ') for call in calls))

    def test_verify_with_smoke_flag_prints_sixth_line(self):
        with (
            fake_github_cli(smoke_repository_exists=False),
            fake_git(),
            mock.patch.object(github_cli.time, 'sleep'),
            redirect_stdout(io.StringIO()) as output,
        ):
            self.assertEqual(github_cli.main(['verify', '--smoke-pull-request']), 0)
        lines = output.getvalue().splitlines()
        self.assertEqual(len(lines), 6)
        self.assertEqual(lines[-1], 'smoke pull request ok (#7 created, reviewed, closed)')


class MainTest(unittest.TestCase):
    def test_main_install_returns_zero(self):
        archive_bytes = build_archive()
        with tempfile.TemporaryDirectory() as temporary_directory:
            binary_directory = Path(temporary_directory) / 'bin'
            with (
                mock.patch.object(github_cli, 'LOCAL_BINARY_DIRECTORY', binary_directory),
                mock.patch.object(
                    github_cli,
                    'download_bytes',
                    side_effect=[checksums_text(archive_bytes).encode(), archive_bytes],
                ),
                redirect_stdout(io.StringIO()) as output,
            ):
                self.assertEqual(github_cli.main(['install']), 0)
            self.assertTrue((binary_directory / 'gh').is_file())
            self.assertIn(f'installed gh {VERSION}', output.getvalue())

    def test_main_returns_one_when_download_fails(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with (
                mock.patch.object(github_cli, 'LOCAL_BINARY_DIRECTORY', Path(temporary_directory) / 'bin'),
                mock.patch.object(
                    github_cli,
                    'download_bytes',
                    side_effect=github_cli.InstallError('download failed after 3 attempts'),
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()) as error_output,
            ):
                self.assertEqual(github_cli.main(['install']), 1)
            self.assertIn('download failed after 3 attempts', error_output.getvalue())

    def test_require_github_cli_reports_missing_binary(self):
        with (
            tempfile.TemporaryDirectory() as temporary_directory,
            mock.patch.object(github_cli.shutil, 'which', return_value=None),
            mock.patch.object(github_cli, 'LOCAL_BINARY_DIRECTORY', Path(temporary_directory)),
            self.assertRaises(github_cli.InstallError) as raised,
        ):
            github_cli.require_github_cli()
        self.assertEqual(raised.exception.exit_code, 3)
        self.assertIn('install_github_cli.py install', str(raised.exception))

    def test_main_authenticate_returns_three_without_a_token(self):
        with fake_github_cli('unauthenticated') as fake_gh, mock.patch.object(github_cli.time, 'sleep'):
            with (
                mock.patch.object(github_cli.shutil, 'which', return_value=str(fake_gh.binary_path)),
                mock.patch.object(github_cli.sys, 'stdin', mock.Mock(isatty=lambda: True)),
                redirect_stdout(io.StringIO()) as output,
            ):
                self.assertEqual(github_cli.main(['authenticate']), 3)
            self.assertIn('gh auth login --hostname github.com', output.getvalue())

    def test_require_github_cli_prints_path_hint_for_local_binary(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            binary_directory = Path(temporary_directory)
            write_executable(binary_directory / 'gh', FAKE_GH_SCRIPT)
            with (
                mock.patch.object(github_cli.shutil, 'which', return_value=None),
                mock.patch.object(github_cli, 'LOCAL_BINARY_DIRECTORY', binary_directory),
                redirect_stdout(io.StringIO()) as output,
                self.assertRaises(github_cli.InstallError) as raised,
            ):
                github_cli.require_github_cli()
        self.assertEqual(raised.exception.exit_code, 3)
        self.assertIn('export PATH="$HOME/.local/bin:$PATH"', output.getvalue())


if __name__ == '__main__':
    unittest.main()
