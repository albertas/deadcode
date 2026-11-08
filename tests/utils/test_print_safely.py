import io

import pytest

from deadcode.utils.print_safely import print_safely

ASCII_ENCODING = 'ascii'


class WritesUnicodeAfterReconfigureStream:
    """A stdout double that raises until reconfigured to UTF-8."""

    def __init__(self):
        self.encoding = 'cp1252'
        self.written_text = ''
        self.reconfigure_calls = []

    def write(self, text):
        text.encode(self.encoding)
        self.written_text += text
        return len(text)

    def flush(self):
        pass

    def reconfigure(self, encoding='utf-8'):
        self.reconfigure_calls.append(encoding)
        self.encoding = encoding


class NonAsciiRefusingStream:
    """A stdout double that refuses non-ASCII text and cannot be reconfigured."""

    def __init__(self):
        self.written_text = ''

    def write(self, text):
        try:
            text.encode('ascii')
        except UnicodeEncodeError as error:
            raise UnicodeEncodeError(ASCII_ENCODING, text, error.start, error.end, error.reason) from None
        self.written_text += text
        return len(text)

    def flush(self):
        pass


def test_working_stream_writes_text_unchanged(monkeypatch: pytest.MonkeyPatch):
    stream = io.StringIO()

    monkeypatch.setattr('sys.stdout', stream)
    print_safely('✨')

    assert stream.getvalue() == '✨\n'


def test_reconfigure_retry_writes_text_unchanged(monkeypatch: pytest.MonkeyPatch):
    stream = WritesUnicodeAfterReconfigureStream()

    monkeypatch.setattr('sys.stdout', stream)
    print_safely('✨')

    assert stream.written_text == '✨\n'
    assert stream.reconfigure_calls == ['utf-8']


def test_ascii_fallback_writes_replacement_character(monkeypatch: pytest.MonkeyPatch):
    stream = NonAsciiRefusingStream()

    monkeypatch.setattr('sys.stdout', stream)
    print_safely('✨')

    assert stream.written_text == '?\n'


def test_custom_file_target_uses_reconfigure():
    stream = WritesUnicodeAfterReconfigureStream()

    print_safely('✨', file=stream)

    assert stream.written_text == '✨\n'
    assert stream.reconfigure_calls == ['utf-8']


def test_custom_file_target_uses_ascii_fallback():
    stream = NonAsciiRefusingStream()

    print_safely('✨', file=stream)

    assert stream.written_text == '?\n'
