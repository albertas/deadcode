import re

from pathlib import Path

from test_documented_options import documented_options
from test_documented_rules import documented_rule_codes

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FEATURES_PATH = REPOSITORY_ROOT / 'docs' / 'features.md'
README_PATH = REPOSITORY_ROOT / 'README.md'

TABLE_COLUMNS = ['Feature', 'README', 'Source', 'Tests', 'Minimum test cases']

REQUIRED_FEATURES = {
    'Detection and usage examples',
    '--fix',
    '--dry',
    '--only',
    '--exclude',
    '--ignore-rules',
    '--ignore-names',
    '--ignore-names-in-files',
    '--ignore-names-if-inherits-from',
    '--ignore-names-if-decorated-with',
    '--ignore-bodies-of',
    '--ignore-bodies-if-decorated-with',
    '--ignore-bodies-if-inherits-from',
    '--ignore-definitions',
    '--ignore-definitions-if-inherits-from',
    '--ignore-definitions-if-decorated-with',
    '[tool.deadcode] settings',
    '--no-color',
    '--count',
    '--quiet',
    '-V / --version',
    '-v / --verbose',
    'Decorator matching rules',
    'Exit status',
    'Rules DC01-DC09, DC11-DC13, DC',
    'Per-rule fixing',
    '# noqa comments',
    'Unittest lifecycle methods',
    'Django test lifecycle methods',
    'FastAPI guide',
    'Django guide',
    'Pre-commit hook',
    'Wildcard imports and __all__',
    'Syntax-error files',
    'Quoted annotations',
    'Coverage badge',
}

PATH_PATTERN = re.compile(r'`([^`]+)`')


def parse_coverage_map() -> list[list[str]]:
    lines = FEATURES_PATH.read_text(encoding='utf-8').splitlines()
    section_start = lines.index('## Coverage map')
    rows: list[list[str]] = []
    for line in lines[section_start:]:
        if not line.startswith('|'):
            if rows:
                break
            continue
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if cells == TABLE_COLUMNS:
            continue
        if all(set(cell) <= {'-'} for cell in cells):
            continue
        rows.append(cells)
    return rows


def extract_paths(cell: str) -> list[str]:
    return PATH_PATTERN.findall(cell)


def normalise_feature_name(cell: str) -> str:
    return cell.replace('`', '').replace('&nbsp;', ' ').strip()


def rule_code_is_mapped(code: str, row_text: str) -> bool:
    if code in row_text:
        return True
    if code == 'DC':
        return False
    number = int(code.removeprefix('DC'))
    return any(int(start) <= number <= int(end) for start, end in re.findall(r'DC(\d+)-DC(\d+)', row_text))


def test_coverage_map_has_expected_columns():
    # Having
    lines = FEATURES_PATH.read_text(encoding='utf-8').splitlines()

    # When
    header = next(line for line in lines if line.startswith('| Feature'))

    # Then
    assert [cell.strip() for cell in header.strip().strip('|').split('|')] == TABLE_COLUMNS


def test_every_row_has_no_empty_cell():
    # When
    rows = parse_coverage_map()

    # Then
    for row in rows:
        assert len(row) == len(TABLE_COLUMNS), row
        assert all(cell for cell in row), row


def test_feature_names_are_unique():
    # When
    feature_names = [normalise_feature_name(row[0]) for row in parse_coverage_map()]

    # Then
    assert len(set(feature_names)) == len(feature_names)


def test_readme_options_are_mapped():
    # Having
    row_text = ' '.join(' '.join(row) for row in parse_coverage_map())

    # Then
    for option in documented_options():
        assert option in row_text, option


def test_readme_rule_codes_are_mapped():
    # Having
    row_text = ' '.join(' '.join(row) for row in parse_coverage_map()).replace('`', '')

    # Then
    for code in documented_rule_codes():
        assert rule_code_is_mapped(code, row_text), code


def test_required_readme_behaviours_are_mapped():
    # When
    feature_names = {normalise_feature_name(row[0]) for row in parse_coverage_map()}

    # Then
    assert feature_names >= REQUIRED_FEATURES


def test_source_and_test_paths_exist():
    # When
    rows = parse_coverage_map()

    # Then
    for row in rows:
        for path in extract_paths(row[2]) + extract_paths(row[3]):
            assert (REPOSITORY_ROOT / path).exists(), (row[0], path)


def test_test_files_define_the_minimum_number_of_cases():
    # When
    rows = parse_coverage_map()

    # Then
    for row in rows:
        test_paths = extract_paths(row[3])
        assert test_paths, row
        test_count = 0
        for path in test_paths:
            content = (REPOSITORY_ROOT / path).read_text(encoding='utf-8')
            test_count += len(re.findall(r'^def test_', content, flags=re.MULTILINE))
        assert test_count >= int(row[4]), (row[0], test_count, row[4])


def test_readme_coverage_badge_is_documented():
    # Having
    readme_text = README_PATH.read_text(encoding='utf-8')
    badge_block = readme_text.split('<p align="center">')[1].split('</p>')[0]

    # Then
    assert 'https://codecov.io/gh/albertas/deadcode' in badge_block
    assert 'https://codecov.io/gh/albertas/deadcode/branch/main/graph/badge.svg' in badge_block
    assert 'alt="Coverage"' in badge_block
    assert readme_text.count('branch/main/graph/badge.svg') == 1
