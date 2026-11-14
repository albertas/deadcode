import pytest

from benchmarks.records import aggregate, compare, median, parse_findings, parse_time_output, record_run, sha256

TIME_OUTPUT = """\t\tCommand being timed: "deadcode . --count"
\tUser time (seconds): 0.42
\tSystem time (seconds): 0.06
\tPercent of CPU this job got: 98%
\tElapsed (wall clock) time (h:mm:ss or m:ss): 0:01.50
\tMaximum resident set size (kbytes): 96576
\tMinor (reclaiming a frame) page faults: 12345
"""


class TestParseTimeOutput:
    def test_parses_a_realistic_sample(self) -> None:
        assert parse_time_output(TIME_OUTPUT) == {
            'wall_clock_seconds': 1.5,
            'user_cpu_seconds': 0.42,
            'sys_cpu_seconds': 0.06,
            'peak_rss_kb': 96576,
        }

    def test_parses_hour_form_elapsed(self) -> None:
        assert parse_time_output(TIME_OUTPUT.replace('0:01.50', '1:02:03.5'))['wall_clock_seconds'] == 3723.5

    def test_missing_elapsed_line(self) -> None:
        with pytest.raises(ValueError, match='Elapsed'):
            parse_time_output(TIME_OUTPUT.replace('\tElapsed (wall clock) time (h:mm:ss or m:ss): 0:01.50\n', ''))

    def test_missing_user_time_line(self) -> None:
        with pytest.raises(ValueError, match='User time'):
            parse_time_output(TIME_OUTPUT.replace('\tUser time (seconds): 0.42\n', ''))

    def test_missing_system_time_line(self) -> None:
        with pytest.raises(ValueError, match='System time'):
            parse_time_output(TIME_OUTPUT.replace('\tSystem time (seconds): 0.06\n', ''))

    def test_missing_max_rss_line(self) -> None:
        with pytest.raises(ValueError, match='Maximum resident set size'):
            parse_time_output(TIME_OUTPUT.replace('\tMaximum resident set size (kbytes): 96576\n', ''))


class TestParseFindings:
    def test_empty_stdout_means_zero_findings(self) -> None:
        assert parse_findings(b'') == 0
        assert parse_findings(b'\n') == 0

    def test_single_integer(self) -> None:
        assert parse_findings(b'123\n') == 123
        assert parse_findings(b'0\n') == 0

    def test_multiple_lines_rejected(self) -> None:
        with pytest.raises(ValueError, match='not a single non-negative integer'):
            parse_findings(b'1\n2\n')

    def test_non_integer_rejected(self) -> None:
        with pytest.raises(ValueError, match='not a single non-negative integer'):
            parse_findings(b'abc\n')

    def test_negative_rejected(self) -> None:
        with pytest.raises(ValueError, match='not a single non-negative integer'):
            parse_findings(b'-1\n')


def base_record(**overrides: object) -> dict[str, object]:
    fields: dict[str, object] = {
        'entry': 'flask',
        'label': 'baseline',
        'run': 0,
        'wall_clock_seconds': 2.0,
        'user_cpu_seconds': 1.8,
        'sys_cpu_seconds': 0.2,
        'peak_rss_kb': 100_000,
        'exit_status': 1,
        'findings': 10,
        'stdout_sha256': sha256(b'10'),
        'stderr_sha256': sha256(b''),
    }
    fields.update(overrides)
    return fields


class TestSha256:
    def test_known_digest(self) -> None:
        assert sha256(b'') == 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
        assert len(sha256(b'deadcode')) == 64


class TestRecordRun:
    def test_builds_one_complete_record(self) -> None:
        record = record_run(
            'flask',
            'baseline',
            2,
            {'wall_clock_seconds': 1.5, 'user_cpu_seconds': 0.42, 'sys_cpu_seconds': 0.06, 'peak_rss_kb': 96_576},
            1,
            b'10\n',
            b'',
        )

        assert record == {
            'entry': 'flask',
            'label': 'baseline',
            'run': 2,
            'wall_clock_seconds': 1.5,
            'user_cpu_seconds': 0.42,
            'sys_cpu_seconds': 0.06,
            'peak_rss_kb': 96_576,
            'exit_status': 1,
            'findings': 10,
            'stdout_sha256': sha256(b'10\n'),
            'stderr_sha256': sha256(b''),
        }


class TestMedian:
    def test_odd_count(self) -> None:
        assert median([3.0, 1.0, 2.0]) == 2.0

    def test_even_count_averages_middle_values(self) -> None:
        assert median([1.0, 2.0, 3.0, 4.0]) == 2.5

    def test_empty_rejected(self) -> None:
        with pytest.raises(ValueError, match='empty'):
            median([])


class TestAggregate:
    def test_median_per_metric_per_entry(self) -> None:
        records = [
            base_record(entry='flask', wall_clock_seconds=1.0),
            base_record(entry='flask', wall_clock_seconds=3.0, run=1),
            base_record(entry='flask', wall_clock_seconds=2.0, run=2),
            base_record(entry='django', wall_clock_seconds=10.0, peak_rss_kb=200_000),
        ]

        result = aggregate(records)

        assert result['flask']['wall_clock_seconds'] == 2.0
        assert result['django']['wall_clock_seconds'] == 10.0
        assert result['django']['peak_rss_kb'] == 200_000


class TestCompare:
    def test_identical_records_have_full_parity(self) -> None:
        base = [base_record(), base_record(run=1)]
        candidate = [base_record(label='native'), base_record(label='native', run=1)]

        result = compare(base, candidate)

        assert result['flask']['stdout_hash_match'] is True
        assert result['flask']['stderr_hash_match'] is True
        assert result['flask']['exit_status_match'] is True
        assert result['flask']['findings_match'] is True
        assert result['flask']['wall_clock_speedup'] == 1.0
        assert result['flask']['peak_memory_ratio'] == 1.0

    def test_speedup_and_memory_ratio(self) -> None:
        base = [base_record(wall_clock_seconds=4.0, peak_rss_kb=100_000)]
        candidate = [base_record(label='native', wall_clock_seconds=2.0, peak_rss_kb=150_000)]

        result = compare(base, candidate)

        assert result['flask']['wall_clock_speedup'] == 2.0
        assert result['flask']['peak_memory_ratio'] == 1.5

    def test_divergent_hash_and_count_fail_parity(self) -> None:
        base = [base_record()]
        candidate = [base_record(label='native', stdout_sha256=sha256(b'different'), findings=9)]

        result = compare(base, candidate)

        assert result['flask']['stdout_hash_match'] is False
        assert result['flask']['findings_match'] is False

    def test_divergent_exit_status_fails_parity(self) -> None:
        base = [base_record()]
        candidate = [base_record(label='native', exit_status=0)]

        result = compare(base, candidate)

        assert result['flask']['exit_status_match'] is False

    def test_entries_present_in_only_one_set_are_skipped(self) -> None:
        base = [base_record(), base_record(entry='django')]
        candidate = [base_record(label='native')]

        result = compare(base, candidate)

        assert set(result) == {'flask'}
