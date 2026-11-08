"""Tests for the Read the Docs build helper."""

import io
import sys
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

SCRIPTS_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPTS_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIRECTORY))

import trigger_readthedocs_builds as trigger  # noqa: E402

TOKEN = 'test-token'  # noqa: S105
LATEST_VERSION_URL = trigger.version_url('latest')
LATEST_BUILDS_URL = LATEST_VERSION_URL + 'builds/'
BUILD_DETAIL_URL = trigger.PROJECTS_URL + '/builds/7/'
COMMIT = 'abc123'
RELEASE_VERSION = '2.4.0'
RELEASE_VERSION_URL = trigger.version_url(RELEASE_VERSION)
RELEASE_BUILDS_URL = RELEASE_VERSION_URL + 'builds/'
RELEASE_BUILD_DETAIL_URL = trigger.PROJECTS_URL + '/builds/11/'
STABLE_VERSION_URL = trigger.version_url('stable')
STABLE_BUILDS_URL = STABLE_VERSION_URL + 'builds/'
STABLE_BUILD_DETAIL_URL = trigger.PROJECTS_URL + '/builds/12/'


class FakeResponse:
    """A minimal stand-in for the object returned by urlopen."""

    def __init__(self, body: bytes) -> None:
        self.body = body

    def read(self) -> bytes:
        return self.body

    def __enter__(self) -> 'FakeResponse':
        return self

    def __exit__(self, *arguments) -> bool:
        return False


class FakeApi:
    """A fake Read the Docs API that records calls and returns queued responses."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.responses: dict[tuple[str, str], list[object]] = {}

    def respond(self, method: str, url: str, *responses: object) -> None:
        self.responses[(method, url)] = list(responses)

    def __call__(self, method: str, url: str, token=None, payload=None, timeout=30) -> dict:
        self.calls.append((method, url))
        queue = self.responses[(method, url)]
        response = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(response, Exception):
            raise response
        return response


def fake_http_error(url: str, code: int, body: bytes = b'error body') -> urllib.error.HTTPError:
    """Build an HTTPError carrying a readable body."""

    return urllib.error.HTTPError(url, code, 'error', {}, io.BytesIO(body))


def finished_build(build_id: int = 7, success: bool = True, commit: str = COMMIT) -> dict:
    """Build a finished build record."""

    return {'id': build_id, 'commit': commit, 'success': success, 'state': {'code': 'finished'}}


class RequestTest(unittest.TestCase):
    def test_retries_on_rate_limit_then_succeeds(self) -> None:
        # Given
        url = trigger.PROJECTS_URL + '/'
        responses = [fake_http_error(url, 429), FakeResponse(b'{"ok": true}')]

        # When
        with (
            mock.patch.object(trigger.urllib.request, 'urlopen', side_effect=responses) as urlopen_mock,
            mock.patch.object(trigger.time, 'sleep') as sleep_mock,
        ):
            payload = trigger.request('GET', url, TOKEN)

        # Then
        self.assertEqual(payload, {'ok': True})
        self.assertEqual(urlopen_mock.call_count, 2)
        sleep_mock.assert_any_call(trigger.RETRY_DELAYS_SECONDS[0])
        sleep_mock.assert_any_call(trigger.CALL_DELAY_SECONDS)

    def test_retries_on_server_errors_twice_then_succeeds(self) -> None:
        # Given
        url = trigger.PROJECTS_URL + '/'
        responses = [
            fake_http_error(url, 502),
            fake_http_error(url, 503),
            FakeResponse(b'{"ok": true}'),
        ]

        # When
        with (
            mock.patch.object(trigger.urllib.request, 'urlopen', side_effect=responses) as urlopen_mock,
            mock.patch.object(trigger.time, 'sleep') as sleep_mock,
        ):
            payload = trigger.request('GET', url, TOKEN)

        # Then
        self.assertEqual(payload, {'ok': True})
        self.assertEqual(urlopen_mock.call_count, 3)
        sleep_mock.assert_any_call(trigger.RETRY_DELAYS_SECONDS[1])

    def test_retries_on_connection_error_then_succeeds(self) -> None:
        # Given
        url = trigger.PROJECTS_URL + '/'
        responses = [urllib.error.URLError('connection refused'), FakeResponse(b'{"ok": true}')]

        # When
        with (
            mock.patch.object(trigger.urllib.request, 'urlopen', side_effect=responses),
            mock.patch.object(trigger.time, 'sleep'),
        ):
            payload = trigger.request('GET', url, TOKEN)

        # Then
        self.assertEqual(payload, {'ok': True})

    def test_retries_on_timeout_then_succeeds(self) -> None:
        # Given
        url = trigger.PROJECTS_URL + '/'
        responses = [TimeoutError('timed out'), FakeResponse(b'{"ok": true}')]

        # When
        with (
            mock.patch.object(trigger.urllib.request, 'urlopen', side_effect=responses),
            mock.patch.object(trigger.time, 'sleep'),
        ):
            payload = trigger.request('GET', url, TOKEN)

        # Then
        self.assertEqual(payload, {'ok': True})

    def test_permanent_client_error_fails_without_retry(self) -> None:
        # Given
        url = trigger.PROJECTS_URL + '/'

        # When
        with (
            mock.patch.object(
                trigger.urllib.request, 'urlopen', side_effect=[fake_http_error(url, 400)]
            ) as urlopen_mock,
            mock.patch.object(trigger.time, 'sleep'),
            self.assertRaises(trigger.ReadTheDocsError) as raised,  # noqa: PT027
        ):
            trigger.request('GET', url, TOKEN)

        # Then
        self.assertEqual(urlopen_mock.call_count, 1)
        self.assertEqual(raised.exception.status, 400)
        self.assertIn('HTTP 400', str(raised.exception))

    def test_not_found_fails_without_retry_and_exposes_the_status(self) -> None:
        # When
        with (
            mock.patch.object(
                trigger.urllib.request, 'urlopen', side_effect=[fake_http_error(LATEST_VERSION_URL, 404)]
            ),
            mock.patch.object(trigger.time, 'sleep'),
            self.assertRaises(trigger.ReadTheDocsError) as raised,  # noqa: PT027
        ):
            trigger.request('GET', LATEST_VERSION_URL, TOKEN)

        # Then
        self.assertEqual(raised.exception.status, 404)

    def test_unauthorized_error_names_the_token(self) -> None:
        # When
        with (
            mock.patch.object(
                trigger.urllib.request, 'urlopen', side_effect=[fake_http_error(LATEST_VERSION_URL, 401)]
            ),
            mock.patch.object(trigger.time, 'sleep'),
            self.assertRaises(trigger.ReadTheDocsError) as raised,  # noqa: PT027
        ):
            trigger.request('GET', LATEST_VERSION_URL, TOKEN)

        # Then
        self.assertIn(trigger.TOKEN_ENVIRONMENT_VARIABLE, str(raised.exception))

    def test_gives_up_after_five_attempts(self) -> None:
        # When
        with (
            mock.patch.object(
                trigger.urllib.request, 'urlopen', side_effect=urllib.error.URLError('down')
            ) as urlopen_mock,
            mock.patch.object(trigger.time, 'sleep') as sleep_mock,
            self.assertRaises(trigger.ReadTheDocsError) as raised,  # noqa: PT027
        ):
            trigger.request('GET', LATEST_VERSION_URL, TOKEN)

        # Then
        self.assertEqual(urlopen_mock.call_count, len(trigger.RETRY_DELAYS_SECONDS))
        self.assertEqual(sleep_mock.call_count, len(trigger.RETRY_DELAYS_SECONDS) - 1)
        self.assertIn('after 5 attempts', str(raised.exception))

    def test_returns_empty_dictionary_for_an_empty_body(self) -> None:
        # When
        with (
            mock.patch.object(trigger.urllib.request, 'urlopen', side_effect=[FakeResponse(b'')]),
            mock.patch.object(trigger.time, 'sleep'),
        ):
            payload = trigger.request('GET', LATEST_VERSION_URL, TOKEN)

        # Then
        self.assertEqual(payload, {})

    def test_sends_the_authorization_header_and_payload(self) -> None:
        # When
        with (
            mock.patch.object(trigger.urllib.request, 'urlopen', side_effect=[FakeResponse(b'{}')]) as urlopen_mock,
            mock.patch.object(trigger.time, 'sleep'),
        ):
            trigger.request('POST', LATEST_BUILDS_URL, TOKEN, {'version': 'latest'})

        # Then
        sent_request = urlopen_mock.call_args.args[0]
        self.assertEqual(sent_request.get_method(), 'POST')
        self.assertEqual(sent_request.data, b'{"version": "latest"}')
        self.assertEqual(sent_request.get_header('Authorization'), f'Token {TOKEN}')


class VersionTest(unittest.TestCase):
    def test_accepts_latest_and_semantic_versions(self) -> None:
        # When / Then
        trigger.validate_version_name('latest')
        trigger.validate_version_name('2.6.0')
        trigger.validate_version_name('2.6.0', allow_latest=False)

    def test_rejects_non_semantic_versions(self) -> None:
        # When / Then
        for version in ('9.9.9x', 'v2.6.0', '2.5', 'latest'):
            with self.subTest(version=version), self.assertRaises(trigger.ReadTheDocsError) as raised:  # noqa: PT027
                trigger.validate_version_name(version, allow_latest=False)
            self.assertIn(version, str(raised.exception))

    def test_rejection_names_the_versions_page(self) -> None:
        # When
        with self.assertRaises(trigger.ReadTheDocsError) as raised:  # noqa: PT027
            trigger.validate_version_name('9.9.9x')

        # Then
        self.assertIn(trigger.VERSIONS_PAGE_URL, str(raised.exception))


class EnsureBuildTest(unittest.TestCase):
    def test_reuses_a_successful_build_without_triggering(self) -> None:
        # Given
        api = FakeApi()
        api.respond('GET', LATEST_VERSION_URL, {'slug': 'latest'})
        api.respond('GET', LATEST_BUILDS_URL, {'results': [finished_build()]})

        # When
        build = trigger.ensure_build('latest', COMMIT, api)

        # Then
        self.assertEqual(build['id'], 7)
        self.assertNotIn(('POST', LATEST_BUILDS_URL), api.calls)

    def test_reuses_a_running_build_without_triggering(self) -> None:
        # Given
        running_build = {'id': 5, 'commit': COMMIT, 'success': None, 'state': {'code': 'running'}}
        api = FakeApi()
        api.respond('GET', LATEST_VERSION_URL, {'slug': 'latest'})
        api.respond('GET', LATEST_BUILDS_URL, {'results': [running_build]})

        # When
        build = trigger.ensure_build('latest', COMMIT, api)

        # Then
        self.assertEqual(build['id'], 5)
        self.assertNotIn(('POST', LATEST_BUILDS_URL), api.calls)

    def test_triggers_a_new_build_when_the_existing_one_failed(self) -> None:
        # Given
        failed_build = finished_build(build_id=5, success=False)
        api = FakeApi()
        api.respond('GET', LATEST_VERSION_URL, {'slug': 'latest'})
        api.respond('GET', LATEST_BUILDS_URL, {'results': [failed_build]})
        api.respond('POST', LATEST_BUILDS_URL, {'build': {'id': 8}})

        # When
        build = trigger.ensure_build('latest', COMMIT, api)

        # Then
        self.assertEqual(build['id'], 8)
        self.assertIn(('POST', LATEST_BUILDS_URL), api.calls)

    def test_triggers_a_build_when_none_exists(self) -> None:
        # Given
        api = FakeApi()
        api.respond('GET', LATEST_VERSION_URL, {'slug': 'latest'})
        api.respond('GET', LATEST_BUILDS_URL, {'results': []})
        api.respond('POST', LATEST_BUILDS_URL, {'build': {'id': 8}})

        # When
        with mock.patch.object(trigger, 'EXISTING_BUILD_WAIT_SECONDS', 0):
            build = trigger.ensure_build('latest', COMMIT, api)

        # Then
        self.assertEqual(build['id'], 8)
        self.assertIn(('POST', LATEST_BUILDS_URL), api.calls)

    def test_reuses_the_newest_matching_build(self) -> None:
        # Given
        api = FakeApi()
        api.respond('GET', LATEST_VERSION_URL, {'slug': 'latest'})
        api.respond(
            'GET',
            LATEST_BUILDS_URL,
            {'results': [finished_build(build_id=3), finished_build(build_id=9)]},
        )

        # When
        build = trigger.ensure_build('latest', COMMIT, api)

        # Then
        self.assertEqual(build['id'], 9)

    def test_rejects_a_version_read_the_docs_does_not_know(self) -> None:
        # Given
        api = FakeApi()
        api.respond(
            'GET',
            trigger.version_url('9.9.9'),
            trigger.ReadTheDocsError('not found', status=404),
        )

        # When
        with self.assertRaises(trigger.ReadTheDocsError) as raised:  # noqa: PT027
            trigger.ensure_build('9.9.9', COMMIT, api)

        # Then
        self.assertIn('9.9.9', str(raised.exception))
        self.assertIn(trigger.VERSIONS_PAGE_URL, str(raised.exception))

    def test_finds_a_build_that_appears_after_a_poll(self) -> None:
        # Given
        api = FakeApi()
        api.respond('GET', LATEST_BUILDS_URL, {'results': []}, {'results': [finished_build()]})

        # When
        with mock.patch.object(trigger.time, 'sleep') as sleep_mock:
            build = trigger.find_build_for_commit('latest', COMMIT, 60, api)

        # Then
        self.assertEqual(build['id'], 7)
        sleep_mock.assert_called_once_with(trigger.BUILD_POLL_INTERVAL_SECONDS)

    def test_returns_none_when_no_build_appears_before_the_timeout(self) -> None:
        # Given
        api = FakeApi()
        api.respond('GET', LATEST_BUILDS_URL, {'results': []})

        # When
        build = trigger.find_build_for_commit('latest', COMMIT, 0, api)

        # Then
        self.assertIsNone(build)


class WaitForBuildTest(unittest.TestCase):
    def test_returns_a_finished_successful_build_and_prints_its_url(self) -> None:
        # Given
        api = FakeApi()
        api.respond('GET', BUILD_DETAIL_URL, finished_build())

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            build = trigger.wait_for_build(7, api)

        # Then
        self.assertTrue(build['success'])
        self.assertIn(trigger.BUILD_URL_TEMPLATE.format(id=7), output.getvalue())

    def test_polls_until_the_build_finishes(self) -> None:
        # Given
        api = FakeApi()
        api.respond('GET', BUILD_DETAIL_URL, {'id': 7, 'state': {'code': 'running'}}, finished_build())

        # When
        with mock.patch.object(trigger.time, 'sleep') as sleep_mock:
            build = trigger.wait_for_build(7, api)

        # Then
        self.assertEqual(build['id'], 7)
        sleep_mock.assert_called_once_with(trigger.BUILD_POLL_INTERVAL_SECONDS)

    def test_raises_when_the_build_failed(self) -> None:
        # Given
        api = FakeApi()
        api.respond('GET', BUILD_DETAIL_URL, finished_build(success=False))

        # When
        with self.assertRaises(trigger.ReadTheDocsError) as raised:  # noqa: PT027
            trigger.wait_for_build(7, api)

        # Then
        self.assertIn(trigger.BUILD_URL_TEMPLATE.format(id=7), str(raised.exception))

    def test_raises_when_the_build_does_not_finish_before_the_timeout(self) -> None:
        # Given
        api = FakeApi()
        api.respond('GET', BUILD_DETAIL_URL, {'id': 7, 'state': {'code': 'running'}})

        # When
        with (
            mock.patch.object(trigger, 'BUILD_TIMEOUT_SECONDS', 0),
            self.assertRaises(trigger.ReadTheDocsError) as raised,  # noqa: PT027
        ):
            trigger.wait_for_build(7, api)

        # Then
        self.assertIn(trigger.BUILD_URL_TEMPLATE.format(id=7), str(raised.exception))


class VersionSyncTest(unittest.TestCase):
    def test_returns_a_version_that_appears_after_a_poll(self) -> None:
        # Given
        api = FakeApi()
        api.respond('GET', RELEASE_VERSION_URL, None, {'active': True})

        # When
        with mock.patch.object(trigger.time, 'sleep') as sleep_mock:
            version = trigger.wait_for_version(RELEASE_VERSION, 5, api)

        # Then
        self.assertTrue(version['active'])
        sleep_mock.assert_called_once_with(trigger.BUILD_POLL_INTERVAL_SECONDS)

    def test_raises_the_p1_message_when_the_version_never_appears(self) -> None:
        # Given
        api = FakeApi()
        api.respond('GET', RELEASE_VERSION_URL, None)

        # When
        with self.assertRaises(trigger.ReadTheDocsError) as raised:  # noqa: PT027
            trigger.wait_for_version(RELEASE_VERSION, 0, api)

        # Then
        message = str(raised.exception)
        self.assertIn(RELEASE_VERSION, message)
        self.assertIn('P1', message)
        self.assertIn(trigger.VERSIONS_PAGE_URL, message)

    def test_activates_an_inactive_version(self) -> None:
        # Given
        api = FakeApi()
        api.respond('GET', STABLE_VERSION_URL, {'active': False})
        api.respond('PATCH', STABLE_VERSION_URL, {})

        # When
        trigger.activate_version('stable', api)

        # Then
        self.assertEqual(api.calls, [('GET', STABLE_VERSION_URL), ('PATCH', STABLE_VERSION_URL)])

    def test_does_not_patch_an_active_version(self) -> None:
        # Given
        api = FakeApi()
        api.respond('GET', STABLE_VERSION_URL, {'active': True})

        # When
        trigger.activate_version('stable', api)

        # Then
        self.assertEqual(api.calls, [('GET', STABLE_VERSION_URL)])

    def test_activation_fails_when_the_version_is_unknown(self) -> None:
        # Given
        api = FakeApi()
        api.respond('GET', RELEASE_VERSION_URL, None)

        # When
        with self.assertRaises(trigger.ReadTheDocsError) as raised:  # noqa: PT027
            trigger.activate_version(RELEASE_VERSION, api)

        # Then
        self.assertIn(RELEASE_VERSION, str(raised.exception))

    def test_reads_the_stable_ref_and_falls_back_to_the_identifier(self) -> None:
        # Given
        api = FakeApi()
        api.respond('GET', STABLE_VERSION_URL, {'identifier': RELEASE_VERSION})

        # When / Then
        self.assertEqual(trigger.read_stable_ref(api), RELEASE_VERSION)

    def test_read_stable_ref_fails_when_stable_is_missing(self) -> None:
        # Given
        api = FakeApi()
        api.respond('GET', STABLE_VERSION_URL, None)

        # When
        with self.assertRaises(trigger.ReadTheDocsError) as raised:  # noqa: PT027
            trigger.read_stable_ref(api)

        # Then
        self.assertIn('stable', str(raised.exception))

    def test_read_stable_ref_fails_without_a_reference(self) -> None:
        # Given
        api = FakeApi()
        api.respond('GET', STABLE_VERSION_URL, {'active': True})

        # When
        with self.assertRaises(trigger.ReadTheDocsError) as raised:  # noqa: PT027
            trigger.read_stable_ref(api)

        # Then
        self.assertIn('no ref or identifier', str(raised.exception))

    def test_verify_stable_ref_accepts_the_release_tag(self) -> None:
        # Given
        api = FakeApi()
        api.respond('GET', STABLE_VERSION_URL, {'ref': RELEASE_VERSION})

        # When / Then
        trigger.verify_stable_ref(RELEASE_VERSION, api)

    def test_verify_stable_ref_rejects_an_older_release(self) -> None:
        # Given
        api = FakeApi()
        api.respond('GET', STABLE_VERSION_URL, {'ref': '2.3.0'})

        # When
        with self.assertRaises(trigger.ReadTheDocsError) as raised:  # noqa: PT027
            trigger.verify_stable_ref(RELEASE_VERSION, api)

        # Then
        message = str(raised.exception)
        self.assertIn('2.3.0', message)
        self.assertIn(RELEASE_VERSION, message)
        self.assertIn(trigger.VERSIONS_PAGE_URL, message)


class ReleaseFlowTest(unittest.TestCase):
    def configure_release_api(self) -> FakeApi:
        api = FakeApi()
        api.respond('GET', RELEASE_VERSION_URL, {'active': True})
        api.respond('GET', RELEASE_BUILDS_URL, {'results': []})
        api.respond('POST', RELEASE_BUILDS_URL, {'build': {'id': 11}})
        api.respond('GET', RELEASE_BUILD_DETAIL_URL, finished_build(build_id=11))
        api.respond('GET', STABLE_VERSION_URL, {'active': True, 'ref': RELEASE_VERSION})
        api.respond('GET', STABLE_BUILDS_URL, {'results': []})
        api.respond('POST', STABLE_BUILDS_URL, {'build': {'id': 12}})
        api.respond('GET', STABLE_BUILD_DETAIL_URL, finished_build(build_id=12))
        return api

    def run_flow(self, api: FakeApi, expect_stable_ref: str | None = RELEASE_VERSION) -> list[dict]:
        with (
            mock.patch.object(trigger, 'EXISTING_BUILD_WAIT_SECONDS', 0),
            redirect_stdout(io.StringIO()),
        ):
            return trigger.run_release_flow(
                RELEASE_VERSION, COMMIT, expect_stable_ref, 0, api
            )

    def test_builds_the_version_and_stable(self) -> None:
        # Given
        api = self.configure_release_api()

        # When
        builds = self.run_flow(api)

        # Then
        self.assertEqual([build['id'] for build in builds], [11, 12])
        self.assertIn(('POST', RELEASE_BUILDS_URL), api.calls)
        self.assertIn(('POST', STABLE_BUILDS_URL), api.calls)

    def test_activates_an_inactive_version_before_its_build(self) -> None:
        # Given
        api = self.configure_release_api()
        api.respond('GET', RELEASE_VERSION_URL, {'active': False})
        api.respond('PATCH', RELEASE_VERSION_URL, {})

        # When
        self.run_flow(api)

        # Then
        patch_index = api.calls.index(('PATCH', RELEASE_VERSION_URL))
        build_index = api.calls.index(('POST', RELEASE_BUILDS_URL))
        self.assertLess(patch_index, build_index)

    def test_waits_for_the_version_when_a_wait_is_configured(self) -> None:
        # Given
        api = self.configure_release_api()
        api.respond('GET', RELEASE_VERSION_URL, None, {'active': True})

        # When
        with (
            mock.patch.object(trigger, 'EXISTING_BUILD_WAIT_SECONDS', 0),
            mock.patch.object(trigger.time, 'sleep'),
            redirect_stdout(io.StringIO()),
        ):
            builds = trigger.run_release_flow(
                RELEASE_VERSION, COMMIT, RELEASE_VERSION, 5, api
            )

        # Then
        self.assertEqual([build['id'] for build in builds], [11, 12])

    def test_rejects_an_invalid_tag_before_any_call(self) -> None:
        # Given
        api = FakeApi()

        # When
        with self.assertRaises(trigger.ReadTheDocsError) as raised:  # noqa: PT027
            trigger.run_release_flow('v2.6.0', COMMIT, 'v2.6.0', 0, api)

        # Then
        self.assertIn('v2.6.0', str(raised.exception))
        self.assertEqual(api.calls, [])


class InputValidationTest(unittest.TestCase):
    def test_resolves_the_commit_from_the_environment(self) -> None:
        # When / Then
        self.assertEqual(trigger.resolve_commit(None, {'GITHUB_SHA': COMMIT}), COMMIT)
        self.assertEqual(trigger.resolve_commit('explicit', {'GITHUB_SHA': COMMIT}), 'explicit')

    def test_rejects_a_missing_commit(self) -> None:
        # When
        with self.assertRaises(trigger.ReadTheDocsError) as raised:  # noqa: PT027
            trigger.resolve_commit(None, {})

        # Then
        self.assertIn('--commit', str(raised.exception))

    def test_requires_a_token(self) -> None:
        # When
        with self.assertRaises(trigger.ReadTheDocsError) as raised:  # noqa: PT027
            trigger.require_token({})

        # Then
        message = str(raised.exception)
        self.assertIn(trigger.TOKEN_ENVIRONMENT_VARIABLE, message)
        self.assertIn('README.md', message)
        self.assertIn('Documentation builds', message)

    def test_returns_the_token_when_present(self) -> None:
        # When / Then
        self.assertEqual(trigger.require_token({trigger.TOKEN_ENVIRONMENT_VARIABLE: TOKEN}), TOKEN)


class MainTest(unittest.TestCase):
    def test_dry_run_makes_no_api_call(self) -> None:
        # Given
        api = FakeApi()

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = trigger.main(
                ['--version', 'latest', '--commit', COMMIT, '--dry-run'],
                environment={},
                request_callable=api,
            )

        # Then
        self.assertEqual(exit_code, 0)
        self.assertEqual(api.calls, [])
        self.assertIn(COMMIT, output.getvalue())

    def test_missing_token_fails_before_any_call(self) -> None:
        # Given
        api = FakeApi()

        # When
        error_output = io.StringIO()
        with redirect_stderr(error_output):
            exit_code = trigger.main(
                ['--version', 'latest', '--commit', COMMIT],
                environment={},
                request_callable=api,
            )

        # Then
        self.assertEqual(exit_code, 1)
        self.assertEqual(api.calls, [])
        self.assertIn(trigger.TOKEN_ENVIRONMENT_VARIABLE, error_output.getvalue())

    def test_returns_one_when_read_the_docs_rejects_the_version(self) -> None:
        # Given
        api = FakeApi()
        api.respond('GET', trigger.version_url('9.9.9'), trigger.ReadTheDocsError('not found', status=404))

        # When
        error_output = io.StringIO()
        with redirect_stderr(error_output):
            exit_code = trigger.main(
                ['--version', '9.9.9', '--commit', COMMIT],
                environment={trigger.TOKEN_ENVIRONMENT_VARIABLE: TOKEN},
                request_callable=api,
            )

        # Then
        self.assertEqual(exit_code, 1)
        self.assertIn('9.9.9', error_output.getvalue())

    def test_successful_run_prints_the_build_and_writes_the_step_summary(self) -> None:
        # Given
        api = FakeApi()
        api.respond('GET', LATEST_VERSION_URL, {'slug': 'latest'})
        api.respond('GET', LATEST_BUILDS_URL, {'results': []})
        api.respond('POST', LATEST_BUILDS_URL, {'build': {'id': 7}})
        api.respond('GET', BUILD_DETAIL_URL, finished_build())
        with tempfile.TemporaryDirectory() as temporary_directory:
            summary_path = Path(temporary_directory) / 'summary.md'

            # When
            output = io.StringIO()
            with (
                mock.patch.object(trigger, 'EXISTING_BUILD_WAIT_SECONDS', 0),
                redirect_stdout(output),
            ):
                exit_code = trigger.main(
                    ['--version', 'latest', '--commit', COMMIT],
                    environment={
                        trigger.TOKEN_ENVIRONMENT_VARIABLE: TOKEN,
                        'GITHUB_STEP_SUMMARY': str(summary_path),
                    },
                    request_callable=api,
                )

            # Then
            self.assertEqual(exit_code, 0)
            self.assertIn(trigger.BUILD_URL_TEMPLATE.format(id=7), output.getvalue())
            self.assertIn('Documentation `latest`', summary_path.read_text(encoding='utf-8'))

    def test_uses_the_github_sha_when_no_commit_is_given(self) -> None:
        # Given
        api = FakeApi()
        api.respond('GET', LATEST_VERSION_URL, {'slug': 'latest'})
        api.respond('GET', LATEST_BUILDS_URL, {'results': [finished_build()]})
        api.respond('GET', BUILD_DETAIL_URL, finished_build())

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = trigger.main(
                ['--version', 'latest'],
                environment={trigger.TOKEN_ENVIRONMENT_VARIABLE: TOKEN, 'GITHUB_SHA': COMMIT},
                request_callable=api,
            )

        # Then
        self.assertEqual(exit_code, 0)
        self.assertIn(COMMIT, output.getvalue())

    def test_release_run_prints_and_summarizes_both_versions(self) -> None:
        # Given
        api = FakeApi()
        api.respond('GET', RELEASE_VERSION_URL, {'active': True})
        api.respond('GET', RELEASE_BUILDS_URL, {'results': []})
        api.respond('POST', RELEASE_BUILDS_URL, {'build': {'id': 11}})
        api.respond('GET', RELEASE_BUILD_DETAIL_URL, finished_build(build_id=11))
        api.respond('GET', STABLE_VERSION_URL, {'active': True, 'ref': RELEASE_VERSION})
        api.respond('GET', STABLE_BUILDS_URL, {'results': []})
        api.respond('POST', STABLE_BUILDS_URL, {'build': {'id': 12}})
        api.respond('GET', STABLE_BUILD_DETAIL_URL, finished_build(build_id=12))
        with tempfile.TemporaryDirectory() as temporary_directory:
            summary_path = Path(temporary_directory) / 'summary.md'

            # When
            output = io.StringIO()
            with (
                mock.patch.object(trigger, 'EXISTING_BUILD_WAIT_SECONDS', 0),
                redirect_stdout(output),
            ):
                exit_code = trigger.main(
                    [
                        '--version', RELEASE_VERSION,
                        '--commit', COMMIT,
                        '--expect-stable-ref', RELEASE_VERSION,
                    ],
                    environment={
                        trigger.TOKEN_ENVIRONMENT_VARIABLE: TOKEN,
                        'GITHUB_STEP_SUMMARY': str(summary_path),
                    },
                    request_callable=api,
                )

            # Then
            self.assertEqual(exit_code, 0)
            self.assertIn(trigger.BUILD_URL_TEMPLATE.format(id=11), output.getvalue())
            self.assertIn(trigger.BUILD_URL_TEMPLATE.format(id=12), output.getvalue())
            summary = summary_path.read_text(encoding='utf-8')
            self.assertIn(f'Documentation `{RELEASE_VERSION}`', summary)
            self.assertIn('Documentation `stable`', summary)

    def test_rejects_expect_stable_ref_with_latest(self) -> None:
        # Given
        api = FakeApi()

        # When
        error_output = io.StringIO()
        with redirect_stderr(error_output):
            exit_code = trigger.main(
                ['--version', 'latest', '--commit', COMMIT, '--expect-stable-ref', RELEASE_VERSION],
                environment={trigger.TOKEN_ENVIRONMENT_VARIABLE: TOKEN},
                request_callable=api,
            )

        # Then
        self.assertEqual(exit_code, 1)
        self.assertEqual(api.calls, [])
        self.assertIn('--expect-stable-ref', error_output.getvalue())

    def test_step_summary_is_optional(self) -> None:
        # When
        with mock.patch('builtins.open') as open_mock:
            trigger.append_step_summary({}, 'latest', trigger.BUILD_URL_TEMPLATE.format(id=7))

        # Then
        open_mock.assert_not_called()


if __name__ == '__main__':
    unittest.main()
