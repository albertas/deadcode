#!/usr/bin/env python3
"""Release a new deadcode version: bump, check, build, publish, tag, push.

The script is restartable. If a run stops after the version bump but before
the tag or the PyPI upload, rerunning the same command resumes the release
instead of bumping again.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

PROJECT_NAME = 'deadcode'
README_RELEASE_NOTES_HEADING = '## Release notes'
PYPI_JSON_URL = 'https://pypi.org/pypi/{name}/{version}/json'
SEMANTIC_VERSION_PATTERN = re.compile(r'^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$')
BUMP_CHOICES = ('patch', 'minor', 'major')
PYPI_RETRY_COUNT = 3
PYPI_RETRY_INITIAL_DELAY_SECONDS = 2.0
PYPI_RETRY_MAX_DELAY_SECONDS = 30.0
PYPI_DELAY_SECONDS = 1.0


class ReleaseError(Exception):
    """Raised when the release cannot continue."""


@dataclass(frozen=True)
class ReleaseOptions:
    """One release invocation."""

    code_root: Path
    bump: str
    explicit_version: str | None
    branch: str
    allow_branch: bool
    tag_prefix: str
    remote: str
    skip_checks: bool
    skip_publish: bool
    dry_run: bool


@dataclass(frozen=True)
class TargetVersion:
    """The version to release and whether it is already the project version."""

    version: str
    current_version: str
    already_bumped: bool


def parse_version(version: str) -> tuple[int, int, int]:
    match = SEMANTIC_VERSION_PATTERN.match(version)
    if match is None:
        raise ReleaseError(f'version {version!r} is not a semantic version (expected X.Y.Z)')
    return (
        int(match.group('major')),
        int(match.group('minor')),
        int(match.group('patch')),
    )


def format_version(parts: tuple[int, int, int]) -> str:
    return '.'.join(str(part) for part in parts)


def bump_version(version: str, bump: str) -> str:
    major, minor, patch = parse_version(version)
    if bump == 'major':
        return format_version((major + 1, 0, 0))
    if bump == 'minor':
        return format_version((major, minor + 1, 0))
    if bump == 'patch':
        return format_version((major, minor, patch + 1))
    raise ReleaseError(f'unknown bump {bump!r}; expected one of {BUMP_CHOICES}')


def tag_name(version: str, tag_prefix: str) -> str:
    return f'{tag_prefix}{version}'


def read_project_version(pyproject_path: Path) -> str:
    try:
        import tomllib
    except ModuleNotFoundError:  # Python 3.10
        import tomli as tomllib  # type: ignore[no-redef]

    try:
        with pyproject_path.open('rb') as pyproject_file:
            document = tomllib.load(pyproject_file)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ReleaseError(f'could not read {pyproject_path}: {error}') from error

    project = document.get('project')
    if not isinstance(project, dict):
        raise ReleaseError(f'{pyproject_path}: missing [project] table')
    version = project.get('version')
    if not isinstance(version, str):
        raise ReleaseError(f'{pyproject_path}: [project].version must be a string')
    return version


def write_project_version(pyproject_path: Path, version: str) -> None:
    text = pyproject_path.read_text(encoding='utf-8')
    project_start = re.search(r'^\[project\][ \t]*$', text, flags=re.MULTILINE)
    if project_start is None:
        raise ReleaseError(f'{pyproject_path}: missing [project] table')

    next_table = re.search(r'^\[', text[project_start.end() :], flags=re.MULTILINE)
    section_end = project_start.end() + next_table.start() if next_table is not None else len(text)
    section = text[project_start.end() : section_end]
    version_pattern = re.compile(r'^version[ \t]*=[ \t]*"[^"]*"[ \t]*$', flags=re.MULTILINE)
    if version_pattern.search(section) is None:
        raise ReleaseError(f'{pyproject_path}: [project].version line not found')
    updated_section = version_pattern.sub(f'version = "{version}"', section, count=1)
    pyproject_path.write_text(
        text[: project_start.end()] + updated_section + text[section_end:],
        encoding='utf-8',
    )


def release_notes_versions(readme_path: Path) -> set[str]:
    """Return the versions that have an entry under "## Release notes"."""

    text = readme_path.read_text(encoding='utf-8')
    heading = re.search(
        rf'^{re.escape(README_RELEASE_NOTES_HEADING)}\s*$',
        text,
        flags=re.MULTILINE,
    )
    if heading is None:
        raise ReleaseError(f'{readme_path}: missing {README_RELEASE_NOTES_HEADING!r} heading')
    section = text[heading.end() :]
    next_heading = re.search(r'^##\s', section, flags=re.MULTILINE)
    if next_heading is not None:
        section = section[: next_heading.start()]
    return {
        match.group('version')
        for match in re.finditer(
            r'^\s*-\s+v?(?P<version>\d+\.\d+\.\d+)\s*:',
            section,
            flags=re.MULTILINE,
        )
    }


def ensure_release_notes(readme_path: Path, version: str) -> None:
    if version in release_notes_versions(readme_path):
        return
    raise ReleaseError(
        f'{readme_path} has no release notes entry for {version}; add a line '
        f"like '- v{version}:' under {README_RELEASE_NOTES_HEADING!r} before "
        'releasing'
    )


def status_paths(status: str) -> list[str]:
    return [line[3:].strip() for line in status.splitlines() if len(line) > 3]


def determine_target_version(
    current_version: str,
    bump: str,
    explicit_version: str | None,
    release_is_complete,
) -> TargetVersion:
    """Choose the version to release, resuming a partially finished release.

    ``release_is_complete(version)`` is true only when the version is on PyPI,
    its tag is on the remote, and the remote branch equals local HEAD. When it
    is false, the current version is resumed instead of bumping again.
    """

    if explicit_version is not None:
        parse_version(explicit_version)
        if parse_version(explicit_version) < parse_version(current_version):
            raise ReleaseError(
                f'explicit version {explicit_version} is lower than the ' f'current version {current_version}'
            )
        return TargetVersion(
            version=explicit_version,
            current_version=current_version,
            already_bumped=explicit_version == current_version,
        )

    if release_is_complete(current_version):
        return TargetVersion(
            version=bump_version(current_version, bump),
            current_version=current_version,
            already_bumped=False,
        )
    return TargetVersion(
        version=current_version,
        current_version=current_version,
        already_bumped=True,
    )


def run_command(
    command: list[str],
    working_directory: Path,
    dry_run: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess:
    if dry_run:
        print(f"would run: {' '.join(command)}")
        return subprocess.CompletedProcess(command, 0, '', '')
    completed = subprocess.run(
        command,
        cwd=str(working_directory),
        capture_output=True,
        text=True,
        check=False,
    )
    if check and completed.returncode != 0:
        raise ReleaseError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"{completed.stdout.strip()}\n{completed.stderr.strip()}"
        )
    return completed


def git_output(code_root: Path, arguments: list[str]) -> str:
    """Run a read-only git command; dry runs still inspect the repository."""

    return run_command(['git', *arguments], code_root).stdout.strip()


def tag_exists(code_root: Path, tag: str) -> bool:
    completed = run_command(
        ['git', 'rev-parse', '--verify', f'refs/tags/{tag}'],
        code_root,
        check=False,
    )
    return completed.returncode == 0


def remote_tag_hash(code_root: Path, remote: str, tag: str) -> str:
    """Return the commit hash a remote tag points to, or an empty string."""

    completed = run_command(
        [
            'git',
            'ls-remote',
            '--tags',
            remote,
            f'refs/tags/{tag}',
            f'refs/tags/{tag}^{{}}',
        ],
        code_root,
        check=False,
    )
    if completed.returncode != 0:
        return ''
    tag_hash = ''
    peeled_hash = ''
    for line in completed.stdout.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        if parts[1] == f'refs/tags/{tag}':
            tag_hash = parts[0]
        elif parts[1] == f'refs/tags/{tag}^{{}}':
            peeled_hash = parts[0]
    return peeled_hash or tag_hash


def version_on_pypi(project_name: str, version: str) -> bool:
    """Return whether a version is on PyPI, retrying transient failures."""

    url = PYPI_JSON_URL.format(name=project_name, version=version)
    last_error = ''
    for attempt in range(1, PYPI_RETRY_COUNT + 1):
        request = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'deadcode-release'})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode('utf-8'))
            time.sleep(PYPI_DELAY_SECONDS)
            return isinstance(payload, dict) and payload.get('info', {}).get('version') == version
        except urllib.error.HTTPError as error:
            if error.code == 404:
                time.sleep(PYPI_DELAY_SECONDS)
                return False
            last_error = f'HTTP {error.code}'
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            last_error = str(error)
        if attempt < PYPI_RETRY_COUNT:
            delay = min(
                PYPI_RETRY_INITIAL_DELAY_SECONDS * (2 ** (attempt - 1)),
                PYPI_RETRY_MAX_DELAY_SECONDS,
            )
            time.sleep(delay)
    raise ReleaseError(f'could not query PyPI for {project_name} {version}: {last_error}')


def ensure_clean_tree(options: ReleaseOptions, target_version: str, pyproject_path: Path) -> None:
    """Allow only the release files to be dirty: pyproject.toml and README.md."""

    status = git_output(options.code_root, ['status', '--porcelain'])
    if not status:
        return

    dirty_paths = status_paths(status)
    allowed_paths = {'pyproject.toml', 'README.md'}
    unexpected_paths = [path for path in dirty_paths if path not in allowed_paths]
    if unexpected_paths:
        raise ReleaseError(
            "the code repository has uncommitted changes outside the release "
            f"files: {', '.join(unexpected_paths)}\n{status}"
        )
    if 'pyproject.toml' in dirty_paths:
        pending_version = read_project_version(pyproject_path)
        if pending_version != target_version:
            raise ReleaseError(
                f'pyproject.toml has uncommitted version {pending_version}, '
                f'but the target is {target_version}; commit or discard it first'
            )


def check_branch(options: ReleaseOptions) -> None:
    current_branch = git_output(options.code_root, ['rev-parse', '--abbrev-ref', 'HEAD'])
    if current_branch != options.branch and not options.allow_branch:
        raise ReleaseError(
            f'releases must run on branch {options.branch!r}; the current branch '
            f'is {current_branch!r} (pass --allow-branch to override)'
        )


def commit_release_files(
    options: ReleaseOptions,
    target: TargetVersion,
    pyproject_path: Path,
    readme_path: Path,
) -> None:
    """Write the version bump and commit it together with README release notes."""

    changed_paths = []
    if read_project_version(pyproject_path) != target.version:
        print(f'bumping {target.current_version} -> {target.version}')
        if not options.dry_run:
            write_project_version(pyproject_path, target.version)
        changed_paths.append('pyproject.toml')

    if 'README.md' in status_paths(git_output(options.code_root, ['status', '--porcelain'])):
        changed_paths.append(readme_path.name)

    if not changed_paths:
        return

    message = (
        f'Bump version to {target.version}'
        if 'pyproject.toml' in changed_paths
        else f'Add release notes for {target.version}'
    )
    run_command(
        ['git', 'add', '--', *changed_paths],
        options.code_root,
        dry_run=options.dry_run,
    )
    run_command(
        [
            'git',
            'commit',
            '--only',
            '-m',
            message,
            '--',
            *changed_paths,
        ],
        options.code_root,
        dry_run=options.dry_run,
    )


def run_checks(options: ReleaseOptions) -> None:
    if options.skip_checks:
        print('skipping checks (--skip-checks)')
        return
    print('running checks')
    run_command(['make', 'check'], options.code_root, dry_run=options.dry_run)


def hatch_executable(code_root: Path) -> str:
    local_hatch = code_root / '.venv' / 'bin' / 'hatch'
    if local_hatch.exists():
        return str(local_hatch)
    executable = shutil.which('hatch')
    if executable is None:
        raise ReleaseError('hatch is not installed; run `make .venv` first')
    return executable


def build_distributions(options: ReleaseOptions) -> None:
    distribution_directory = options.code_root / 'dist'
    if distribution_directory.exists() and not options.dry_run:
        for child in distribution_directory.iterdir():
            if child.is_file():
                child.unlink()
    print('building distributions')
    run_command(
        [hatch_executable(options.code_root), 'build'],
        options.code_root,
        dry_run=options.dry_run,
    )


def publish_distributions(options: ReleaseOptions, target_version: str) -> None:
    if options.skip_publish:
        print('skipping PyPI upload (--skip-publish)')
        return
    if version_on_pypi(PROJECT_NAME, target_version):
        print(f'{PROJECT_NAME} {target_version} is already on PyPI; skipping upload')
        return

    print(f'publishing {PROJECT_NAME} {target_version} to PyPI')
    completed = run_command(
        [hatch_executable(options.code_root), 'publish'],
        options.code_root,
        dry_run=options.dry_run,
        check=False,
    )
    if completed.returncode == 0:
        return
    combined_output = f'{completed.stdout}\n{completed.stderr}'.lower()
    if 'already exists' in combined_output or 'file already exists' in combined_output:
        print('PyPI reports the files already exist; treating the upload as complete')
        return
    raise ReleaseError('PyPI upload failed:\n' f'{completed.stdout.strip()}\n{completed.stderr.strip()}')


def create_and_push_tag(options: ReleaseOptions, tag: str) -> None:
    if options.dry_run:
        if tag_exists(options.code_root, tag):
            print(f'tag {tag} already exists locally')
        else:
            print(f'would create tag {tag}')
        print(f'would push tag {tag} to {options.remote}')
        return

    local_tag_hash = ''
    if tag_exists(options.code_root, tag):
        local_tag_hash = git_output(options.code_root, ['rev-parse', f'refs/tags/{tag}^{{commit}}'])
        head_hash = git_output(options.code_root, ['rev-parse', 'HEAD'])
        if local_tag_hash != head_hash:
            raise ReleaseError(
                f'tag {tag} already exists at {local_tag_hash}, not at HEAD '
                f'{head_hash}; refusing to move a release tag'
            )
        print(f'tag {tag} already exists at HEAD')
    else:
        print(f'creating tag {tag}')
        run_command(
            [
                'git',
                'tag',
                '-a',
                tag,
                '-m',
                f'{PROJECT_NAME} {tag}',
            ],
            options.code_root,
            dry_run=options.dry_run,
        )
        local_tag_hash = git_output(options.code_root, ['rev-parse', f'refs/tags/{tag}^{{commit}}'])

    remote_hash = remote_tag_hash(options.code_root, options.remote, tag)
    if remote_hash:
        if remote_hash != local_tag_hash:
            raise ReleaseError(
                f'remote tag {tag} points to {remote_hash}, local tag points to '
                f'{local_tag_hash}; refusing to overwrite a pushed release tag'
            )
        print(f'tag {tag} is already on {options.remote}')
        return
    print(f'pushing tag {tag} to {options.remote}')
    run_command(
        ['git', 'push', options.remote, tag],
        options.code_root,
        dry_run=options.dry_run,
    )


def push_branch(options: ReleaseOptions) -> None:
    print(f'pushing branch {options.branch} to {options.remote}')
    run_command(
        ['git', 'push', '-u', options.remote, options.branch],
        options.code_root,
        dry_run=options.dry_run,
    )


def release(options: ReleaseOptions) -> int:
    pyproject_path = options.code_root / 'pyproject.toml'
    if not pyproject_path.exists():
        raise ReleaseError(f'pyproject.toml not found in {options.code_root}')

    check_branch(options)
    current_version = read_project_version(pyproject_path)

    def release_is_complete(version: str) -> bool:
        tag = tag_name(version, options.tag_prefix)
        if not remote_tag_hash(options.code_root, options.remote, tag):
            return False
        return version_on_pypi(PROJECT_NAME, version)

    target = determine_target_version(
        current_version=current_version,
        bump=options.bump,
        explicit_version=options.explicit_version,
        release_is_complete=release_is_complete,
    )
    print(f'current version: {current_version}')
    print(f'target version:  {target.version}')

    readme_path = options.code_root / 'README.md'
    ensure_release_notes(readme_path, target.version)
    ensure_clean_tree(options, target.version, pyproject_path)
    commit_release_files(options, target, pyproject_path, readme_path)
    run_checks(options)
    build_distributions(options)
    publish_distributions(options, target.version)
    # Push the branch before the tag: a pushed tag then implies the branch is
    # already published, so a failed tag push is safely resumable.
    push_branch(options)
    create_and_push_tag(options, tag_name(target.version, options.tag_prefix))

    if options.dry_run:
        print('dry run complete; no changes were made')
    else:
        print(f'released {PROJECT_NAME} {target.version} ' f'(tag {tag_name(target.version, options.tag_prefix)})')
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='publish_release.py',
        description='Bump, check, build, publish, tag, and push a deadcode release.',
    )
    parser.add_argument('--bump', choices=BUMP_CHOICES, default='patch')
    parser.add_argument('--version', dest='explicit_version', default=None)
    parser.add_argument('--branch', default='main')
    parser.add_argument('--allow-branch', action='store_true')
    parser.add_argument('--tag-prefix', default='')
    parser.add_argument('--remote', default='origin')
    parser.add_argument('--skip-checks', action='store_true')
    parser.add_argument('--skip-publish', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    return parser


def main(argument_values: list[str] | None = None) -> int:
    parsed_arguments = build_parser().parse_args(argument_values)
    options = ReleaseOptions(
        code_root=Path(__file__).resolve().parents[1],
        bump=parsed_arguments.bump,
        explicit_version=parsed_arguments.explicit_version,
        branch=parsed_arguments.branch,
        allow_branch=parsed_arguments.allow_branch,
        tag_prefix=parsed_arguments.tag_prefix,
        remote=parsed_arguments.remote,
        skip_checks=parsed_arguments.skip_checks,
        skip_publish=parsed_arguments.skip_publish,
        dry_run=parsed_arguments.dry_run,
    )
    try:
        return release(options)
    except ReleaseError as error:
        print(f'error: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
