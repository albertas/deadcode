#!/usr/bin/env python3
"""Trigger and follow Read the Docs builds for the deadcode project.

The helper is invoked by the ``Build documentation`` GitHub Actions workflow
and can be run locally to reproduce a build. Calls are throttled and retried
with exponential backoff, and builds are ensured idempotently: an existing
running or successful build for the same commit is reused instead of creating
a duplicate.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

PROJECT_SLUG = 'deadcode'
API_ROOT = 'https://readthedocs.org/api/v3'
PROJECTS_URL = API_ROOT + '/projects/' + PROJECT_SLUG
BUILD_URL_TEMPLATE = 'https://app.readthedocs.org/projects/deadcode/builds/{id}/'
VERSIONS_PAGE_URL = 'https://app.readthedocs.org/projects/deadcode/versions/'
TOKEN_ENVIRONMENT_VARIABLE = 'READTHEDOCS_API_TOKEN'  # noqa: S105
CALL_DELAY_SECONDS = 2.0
RETRY_DELAYS_SECONDS = (2, 4, 8, 16, 30)
EXISTING_BUILD_WAIT_SECONDS = 60
VERSION_SYNC_WAIT_SECONDS = 120
BUILD_POLL_INTERVAL_SECONDS = 10
BUILD_TIMEOUT_SECONDS = 900
SEMANTIC_VERSION_PATTERN = re.compile(r'^[0-9]+\.[0-9]+\.[0-9]+$')


class ReadTheDocsError(Exception):
    """Raised when a Read the Docs build cannot be produced."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def request(method: str, url: str, token: str, payload: dict | None = None, timeout: int = 30) -> dict:
    """Call the Read the Docs API with throttling and exponential backoff."""

    encoded_payload = None if payload is None else json.dumps(payload).encode('utf-8')
    attempts = len(RETRY_DELAYS_SECONDS)
    last_status = None
    last_body = ''
    for attempt in range(1, attempts + 1):
        request_object = urllib.request.Request(  # noqa: S310
            url,
            data=encoded_payload,
            method=method,
            headers={
                'Authorization': f'Token {token}',
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'User-Agent': 'deadcode-documentation',
            },
        )
        try:
            with urllib.request.urlopen(request_object, timeout=timeout) as response:  # noqa: S310
                raw_body = response.read().decode('utf-8')
            time.sleep(CALL_DELAY_SECONDS)
            return json.loads(raw_body) if raw_body.strip() else {}
        except urllib.error.HTTPError as error:
            last_status = error.code
            last_body = error.read().decode('utf-8', errors='replace')
            if 400 <= error.code < 500 and error.code != 429:
                message = f'HTTP {error.code} from {method} {url}: {last_body}'
                if error.code in (401, 403):
                    message += (
                        f'\nThe token in {TOKEN_ENVIRONMENT_VARIABLE} is invalid or lacks permission '
                        f'on the Read the Docs project {PROJECT_SLUG}.'
                    )
                raise ReadTheDocsError(message, status=error.code) from error
            last_error = f'HTTP {error.code}'
        except (urllib.error.URLError, TimeoutError) as error:
            last_error = str(error)
        if attempt < attempts:
            delay = RETRY_DELAYS_SECONDS[attempt - 1]
            print(
                f'attempt {attempt}/{attempts} for {method} {url} failed ({last_error}); retrying in {delay} s',
                file=sys.stderr,
            )
            time.sleep(delay)
    failure_message = (
        f'{method} {url} failed after {attempts} attempts: {last_error}{_body_details(last_status, last_body)}'
    )
    raise ReadTheDocsError(failure_message)


def _body_details(status: int | None, body: str) -> str:
    if status is None:
        return ''
    return f' (last HTTP status {status}: {body})'


def version_url(version_slug: str) -> str:
    """Return the API URL of one version."""

    return f'{PROJECTS_URL}/versions/{version_slug}/'


def get_version(version_slug: str, request_callable) -> dict | None:
    """Return a version, or None when Read the Docs does not know it."""

    try:
        return request_callable('GET', version_url(version_slug))
    except ReadTheDocsError as error:
        if error.status == 404:
            return None
        raise


def list_builds(version_slug: str, request_callable) -> list[dict]:
    """Return the builds of a version, newest first."""

    payload = request_callable('GET', version_url(version_slug) + 'builds/')
    return list(payload.get('results', []))


def trigger_build(version_slug: str, request_callable) -> dict:
    """Queue a new build for a version and return the build object."""

    payload = request_callable('POST', version_url(version_slug) + 'builds/')
    return payload.get('build', payload)


def get_build(build_id, request_callable) -> dict:
    """Return the current state of one build."""

    return request_callable('GET', f'{PROJECTS_URL}/builds/{build_id}/')


def find_build_for_commit(version_slug: str, commit: str, timeout_seconds: int, request_callable) -> dict | None:
    """Poll the build list until a build for the commit appears."""

    deadline = time.monotonic() + timeout_seconds
    while True:
        builds = list_builds(version_slug, request_callable)
        matching = [build for build in builds if str(build.get('commit', '')).startswith(commit)]
        if matching:
            matching.sort(key=lambda build: int(build.get('id') or 0), reverse=True)
            return matching[0]
        if time.monotonic() >= deadline:
            return None
        time.sleep(BUILD_POLL_INTERVAL_SECONDS)


def ensure_build(version_slug: str, commit: str, request_callable) -> dict:
    """Reuse a running or successful build for the commit, else trigger one."""

    if get_version(version_slug, request_callable) is None:
        unknown_version_message = (
            f"Read the Docs does not know version '{version_slug}' of project '{PROJECT_SLUG}'.\n"
            f'Check {VERSIONS_PAGE_URL} - a new tag is only registered after the Read the Docs '
            'GitHub connection (prerequisite P1) syncs it.'
        )
        raise ReadTheDocsError(unknown_version_message)

    existing_build = find_build_for_commit(version_slug, commit, EXISTING_BUILD_WAIT_SECONDS, request_callable)
    if existing_build is not None and existing_build.get('success') is not False:
        build_id = existing_build.get('id')
        print(f"Reusing existing build {build_id} of version '{version_slug}' for commit {commit}.")
        return existing_build

    build = trigger_build(version_slug, request_callable)
    build_id = build.get('id')
    print(f"Triggered a new build {build_id} of version '{version_slug}' for commit {commit}.")
    return build


def wait_for_build(build_id, request_callable) -> dict:
    """Poll a build until it finishes; fail on failure or timeout."""

    build_url = BUILD_URL_TEMPLATE.format(id=build_id)
    print(f'Build URL: {build_url}')
    deadline = time.monotonic() + BUILD_TIMEOUT_SECONDS
    while True:
        build = get_build(build_id, request_callable)
        state_code = (build.get('state') or {}).get('code')
        if state_code == 'finished':
            if not build.get('success'):
                failed_build_message = f'Read the Docs build failed: {build_url}'
                raise ReadTheDocsError(failed_build_message)
            return build
        if time.monotonic() >= deadline:
            timeout_message = f'Read the Docs build did not finish within {BUILD_TIMEOUT_SECONDS} s: {build_url}'
            raise ReadTheDocsError(timeout_message)
        time.sleep(BUILD_POLL_INTERVAL_SECONDS)


def wait_for_version(version_slug: str, timeout_seconds: int, request_callable) -> dict:
    """Poll until Read the Docs knows the version, or fail naming prerequisite P1."""

    deadline = time.monotonic() + timeout_seconds
    while True:
        version = get_version(version_slug, request_callable)
        if version is not None:
            return version
        if time.monotonic() >= deadline:
            missing_version_message = (
                f"Read the Docs does not know version '{version_slug}' of project '{PROJECT_SLUG}' "
                f'after waiting {timeout_seconds} s.\n'
                'The Read the Docs GitHub connection (prerequisite P1) must sync the tag before it can be built; '
                f'see {VERSIONS_PAGE_URL}.'
            )
            raise ReadTheDocsError(missing_version_message)
        time.sleep(BUILD_POLL_INTERVAL_SECONDS)


def activate_version(version_slug: str, request_callable) -> None:
    """Activate an inactive version so Read the Docs can build it."""

    version = get_version(version_slug, request_callable)
    if version is None:
        unknown_version_message = (
            f"Read the Docs does not know version '{version_slug}' of project '{PROJECT_SLUG}'; "
            f'see {VERSIONS_PAGE_URL}.'
        )
        raise ReadTheDocsError(unknown_version_message)
    if not version.get('active'):
        request_callable('PATCH', version_url(version_slug), {'active': True})
        print(f"Activated version '{version_slug}'; Read the Docs queues a build for it.")


def read_stable_ref(request_callable) -> str:
    """Return the release reference the stable version points at."""

    version = get_version('stable', request_callable)
    if version is None:
        missing_stable_message = (
            f"Read the Docs does not know the 'stable' version of project '{PROJECT_SLUG}'; "
            f'see {VERSIONS_PAGE_URL}.'
        )
        raise ReadTheDocsError(missing_stable_message)
    reference = version.get('ref') or version.get('identifier')
    if not reference:
        missing_reference_message = (
            f"Read the Docs version 'stable' of project '{PROJECT_SLUG}' has no ref or identifier; "
            f'see {VERSIONS_PAGE_URL}.'
        )
        raise ReadTheDocsError(missing_reference_message)
    return str(reference)


def verify_stable_ref(expected_tag: str, request_callable) -> None:
    """Fail when stable does not point at the released tag."""

    actual_ref = read_stable_ref(request_callable)
    if actual_ref != expected_tag:
        stable_mismatch_message = (
            f"Read the Docs 'stable' points at '{actual_ref}', not the release tag '{expected_tag}'.\n"
            'Read the Docs did not move stable to the new release. Sync versions or re-point stable '
            f'in the dashboard: {VERSIONS_PAGE_URL}'
        )
        raise ReadTheDocsError(stable_mismatch_message)


def run_release_flow(
    version: str,
    commit: str,
    expect_stable_ref: str | None,
    wait_for_version_seconds: int,
    request_callable,
) -> list[dict]:
    """Build a release tag version, verify stable, then build stable."""

    validate_version_name(version, allow_latest=False)
    if wait_for_version_seconds > 0:
        wait_for_version(version, wait_for_version_seconds, request_callable)
    activate_version(version, request_callable)
    finished_builds = []
    version_build = ensure_build(version, commit, request_callable)
    finished_builds.append(wait_for_build(version_build.get('id'), request_callable))
    if expect_stable_ref is not None:
        verify_stable_ref(expect_stable_ref, request_callable)
    stable_build = ensure_build('stable', commit, request_callable)
    finished_builds.append(wait_for_build(stable_build.get('id'), request_callable))
    return finished_builds


def validate_version_name(version: str, allow_latest: bool = True) -> None:
    """Reject anything that is not 'latest' or a semantic version."""

    if allow_latest and version == 'latest':
        return
    if SEMANTIC_VERSION_PATTERN.match(version):
        return
    invalid_version_message = (
        f"'{version}' is not a valid Read the Docs version of project '{PROJECT_SLUG}'. "
        f"Use 'latest' or a semantic version such as 2.6.0; see {VERSIONS_PAGE_URL}."
    )
    raise ReadTheDocsError(invalid_version_message)


def resolve_commit(argument_commit: str | None, environment) -> str:
    """Resolve the commit from the argument or from GITHUB_SHA."""

    commit = argument_commit or environment.get('GITHUB_SHA')
    if not commit:
        missing_commit_message = 'no commit given: pass --commit <sha> or set the GITHUB_SHA environment variable.'
        raise ReadTheDocsError(missing_commit_message)
    return commit


def require_token(environment) -> str:
    """Return the API token or fail with an actionable message."""

    token = environment.get(TOKEN_ENVIRONMENT_VARIABLE)
    if not token:
        missing_token_message = (
            f'{TOKEN_ENVIRONMENT_VARIABLE} is not set.\n'
            'Add it as a repository secret under Settings -> Secrets and variables -> Actions '
            '(prerequisite P2, described in the Documentation builds section of README.md).'
        )
        raise ReadTheDocsError(missing_token_message)
    return token


def append_step_summary(environment, version: str, build_url: str) -> None:
    """Append one line per version to the GitHub Actions step summary."""

    summary_path = environment.get('GITHUB_STEP_SUMMARY')
    if not summary_path:
        return
    with open(summary_path, 'a', encoding='utf-8') as summary_file:
        summary_file.write(f'- Documentation `{version}`: {build_url}\n')


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""

    parser = argparse.ArgumentParser(description='Trigger and follow Read the Docs builds for deadcode.')
    parser.add_argument('--version', default='latest', help='Read the Docs version to build (default: latest).')
    parser.add_argument('--commit', default=None, help='Commit to build (default: GITHUB_SHA).')
    parser.add_argument(
        '--expect-stable-ref',
        default=None,
        help='Release tag that the stable version must point at before it is built.',
    )
    parser.add_argument(
        '--wait-for-version',
        type=int,
        default=0,
        help=f'Seconds to wait for a new tag version to appear (the release workflow uses {VERSION_SYNC_WAIT_SECONDS}).',
    )
    parser.add_argument('--dry-run', action='store_true', help='Print the planned build without calling the API.')
    return parser


def main(argv=None, environment=None, request_callable=None) -> int:
    """Run the helper: ensure, wait for and report one documentation build."""

    environment = os.environ if environment is None else environment
    request_callable = request if request_callable is None else request_callable
    arguments = build_argument_parser().parse_args(argv)
    try:
        if arguments.expect_stable_ref is not None and arguments.version == 'latest':
            raise ReadTheDocsError(
                "--expect-stable-ref requires an explicit semantic version; 'latest' has no release tag."
            )
        validate_version_name(arguments.version)
        commit = resolve_commit(arguments.commit, environment)
        print(f'Read the Docs version: {arguments.version}')
        print(f'Commit: {commit}')
        if arguments.dry_run:
            print('Dry run: no Read the Docs API call was made.')
            return 0

        token = require_token(environment)

        def token_request(method: str, url: str, payload: dict | None = None, timeout: int = 30) -> dict:
            return request_callable(method, url, token, payload, timeout)

        if arguments.expect_stable_ref is not None:
            finished_builds = run_release_flow(
                arguments.version,
                commit,
                arguments.expect_stable_ref,
                arguments.wait_for_version,
                token_request,
            )
            for version_name, finished_build in zip((arguments.version, 'stable'), finished_builds):
                build_url = BUILD_URL_TEMPLATE.format(id=finished_build.get('id'))
                print(f'Documentation build finished for {version_name}: {build_url}')
                append_step_summary(environment, version_name, build_url)
            return 0

        build = ensure_build(arguments.version, commit, token_request)
        finished_build = wait_for_build(build.get('id'), token_request)
        build_url = BUILD_URL_TEMPLATE.format(id=finished_build.get('id', build.get('id')))
        print(f'Documentation build finished: {build_url}')
        append_step_summary(environment, arguments.version, build_url)
        return 0
    except ReadTheDocsError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
