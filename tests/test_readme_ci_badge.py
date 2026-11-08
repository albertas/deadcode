import re

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
README_PATH = REPOSITORY_ROOT / 'README.md'
WORKFLOW_PATH = REPOSITORY_ROOT / '.github' / 'workflows' / 'test.yml'

WORKFLOW_RUNS_URL = 'https://github.com/albertas/deadcode/actions/workflows/test.yml'
BADGE_IMAGE_URL = 'https://github.com/albertas/deadcode/actions/workflows/test.yml/badge.svg?branch=main'
BADGE_ACCESSIBLE_NAME = 'CI'

CENTERED_PARAGRAPH_PATTERN = re.compile(r'<p align="center">(.*?)</p>', re.DOTALL)


def _centered_badge_paragraph() -> str:
    readme_text = README_PATH.read_text(encoding='utf-8')
    match = CENTERED_PARAGRAPH_PATTERN.search(readme_text)
    assert match is not None, f'{README_PATH} has no <p align="center"> badge paragraph actually present'
    return match.group(1)


def test_centered_badge_paragraph_contains_exactly_one_workflow_image():
    # Having
    paragraph = _centered_badge_paragraph()

    # When
    workflow_images = [image for image in re.findall(r'<img[^>]+>', paragraph) if WORKFLOW_RUNS_URL in image]

    # Then
    assert len(workflow_images) == 1
    assert len(re.findall(r'actions/workflows/', paragraph)) == 2
    assert paragraph.count('actions/workflows/test.yml/badge.svg?branch=main') == 1


def test_ci_badge_anchor_links_to_workflow_runs_page():
    # Having
    paragraph = _centered_badge_paragraph()

    # Then
    assert f'<a href="{WORKFLOW_RUNS_URL}">' in paragraph


def test_ci_badge_image_has_expected_source_and_accessible_name():
    # Having
    paragraph = _centered_badge_paragraph()

    # When
    expected_image = f'<img alt="{BADGE_ACCESSIBLE_NAME}" src="{BADGE_IMAGE_URL}">'

    # Then
    assert expected_image in paragraph, f'README CI badge image is not actually present as {expected_image}'


def test_ci_badge_reports_existing_test_workflow():
    # Having
    assert WORKFLOW_PATH.is_file(), f'{WORKFLOW_PATH} does not exist'

    # When
    workflow_lines = WORKFLOW_PATH.read_text(encoding='utf-8').splitlines()

    # Then
    assert 'name: Test' in [line.strip() for line in workflow_lines]
