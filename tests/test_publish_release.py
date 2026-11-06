"""Tests for the restartable release tool."""

import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from publish_release.publish_release import (  # noqa: E402
    ReleaseError,
    bump_version,
    determine_target_version,
    ensure_release_notes,
    parse_version,
    read_project_version,
    release_notes_versions,
    status_paths,
    tag_name,
    write_project_version,
)


class VersionTest(unittest.TestCase):
    def test_parse_version(self):
        self.assertEqual(parse_version('2.4.1'), (2, 4, 1))

    def test_parse_version_rejects_non_semantic_versions(self):
        with self.assertRaises(ReleaseError):
            parse_version('2.4')

    def test_bump_version(self):
        self.assertEqual(bump_version('2.4.1', 'patch'), '2.4.2')
        self.assertEqual(bump_version('2.4.1', 'minor'), '2.5.0')
        self.assertEqual(bump_version('2.4.1', 'major'), '3.0.0')

    def test_bump_version_rejects_unknown_bump(self):
        with self.assertRaises(ReleaseError):
            bump_version('2.4.1', 'huge')

    def test_tag_name(self):
        self.assertEqual(tag_name('2.4.1', ''), '2.4.1')
        self.assertEqual(tag_name('2.4.1', 'v'), 'v2.4.1')


class ProjectVersionTest(unittest.TestCase):
    def test_read_and_write_project_version(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            pyproject_path = Path(temporary_directory) / 'pyproject.toml'
            pyproject_path.write_text(
                '[project]\nname = "deadcode"\nversion = "2.4.1"\n\n' '[tool.example]\nversion = "9.9.9"\n',
                encoding='utf-8',
            )

            self.assertEqual(read_project_version(pyproject_path), '2.4.1')
            write_project_version(pyproject_path, '2.4.2')

            self.assertEqual(read_project_version(pyproject_path), '2.4.2')
            self.assertIn(
                '[tool.example]\nversion = "9.9.9"',
                pyproject_path.read_text(encoding='utf-8'),
            )

    def test_write_project_version_requires_a_project_table(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            pyproject_path = Path(temporary_directory) / 'pyproject.toml'
            pyproject_path.write_text('[tool.example]\nversion = "9.9.9"\n')
            with self.assertRaises(ReleaseError):
                write_project_version(pyproject_path, '2.4.2')


class ReleaseNotesTest(unittest.TestCase):
    def test_release_notes_versions(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            readme_path = Path(temporary_directory) / 'README.md'
            readme_path.write_text(
                '# deadcode\n\n'
                '## Release notes\n'
                '- v2.4.1:\n'
                '    - First.\n'
                '- 2.4.2:\n'
                '    - Second.\n'
                '\n'
                '## Next section\n'
                '- v9.9.9:\n',
                encoding='utf-8',
            )
            self.assertEqual(release_notes_versions(readme_path), {'2.4.1', '2.4.2'})

    def test_ensure_release_notes_rejects_a_missing_entry(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            readme_path = Path(temporary_directory) / 'README.md'
            readme_path.write_text('# deadcode\n\n## Release notes\n- v2.4.1:\n', encoding='utf-8')
            with self.assertRaises(ReleaseError):
                ensure_release_notes(readme_path, '2.4.2')

    def test_ensure_release_notes_accepts_a_present_entry(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            readme_path = Path(temporary_directory) / 'README.md'
            readme_path.write_text('# deadcode\n\n## Release notes\n- v2.4.2:\n', encoding='utf-8')
            ensure_release_notes(readme_path, '2.4.2')


class TargetVersionTest(unittest.TestCase):
    def test_bumps_when_the_current_version_is_complete(self):
        target = determine_target_version(
            current_version='2.4.1',
            bump='patch',
            explicit_version=None,
            release_is_complete=lambda _version: True,
        )
        self.assertEqual(target.version, '2.4.2')
        self.assertFalse(target.already_bumped)

    def test_resumes_when_the_current_version_is_incomplete(self):
        target = determine_target_version(
            current_version='2.4.1',
            bump='patch',
            explicit_version=None,
            release_is_complete=lambda _version: False,
        )
        self.assertEqual(target.version, '2.4.1')
        self.assertTrue(target.already_bumped)

    def test_explicit_version_wins(self):
        target = determine_target_version(
            current_version='2.4.1',
            bump='patch',
            explicit_version='3.0.0',
            release_is_complete=lambda _version: True,
        )
        self.assertEqual(target.version, '3.0.0')
        self.assertFalse(target.already_bumped)

    def test_explicit_version_cannot_go_backwards(self):
        with self.assertRaises(ReleaseError):
            determine_target_version(
                current_version='2.4.1',
                bump='patch',
                explicit_version='2.3.0',
                release_is_complete=lambda _version: True,
            )


class StatusPathsTest(unittest.TestCase):
    def test_status_paths(self):
        self.assertEqual(status_paths(' M pyproject.toml\n?? README.md\n'), ['pyproject.toml', 'README.md'])


if __name__ == '__main__':
    unittest.main()
