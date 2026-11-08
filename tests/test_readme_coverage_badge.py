import re

from pathlib import Path

README_PATH = Path(__file__).resolve().parents[1] / 'README.md'

CODECOV_LINK = 'https://codecov.io/gh/albertas/deadcode'
CODECOV_IMAGE = 'https://codecov.io/gh/albertas/deadcode/branch/main/graph/badge.svg'


def read_badge_block() -> str:
    readme_text = README_PATH.read_text(encoding='utf-8')
    match = re.search(r'<p align="center">.*?</p>', readme_text, flags=re.DOTALL)
    assert match is not None
    return match.group(0)


def test_badge_block_contains_codecov_coverage_badge():
    # Having
    badge_block = read_badge_block()

    # When
    coverage_images = [image for image in re.findall(r'<img[^>]+>', badge_block) if 'coverage' in image.lower()]

    # Then
    assert f'<a href="{CODECOV_LINK}">' in badge_block
    assert CODECOV_IMAGE in badge_block
    assert 'alt="Coverage"' in badge_block
    assert len(coverage_images) == 1


def test_readme_contains_only_one_coverage_badge():
    # Having
    readme_text = README_PATH.read_text(encoding='utf-8')

    # When
    image_urls = re.findall(r'<img[^>]+src="([^"]+)"', readme_text)
    coverage_urls = [url for url in image_urls if 'codecov' in url or 'coverage' in url.lower()]

    # Then
    assert coverage_urls == [CODECOV_IMAGE]
