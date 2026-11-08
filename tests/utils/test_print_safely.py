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


class ReconfiguresButStillRefusesUnicodeStream:
    """A stdout double whose reconfigure call succeeds but whose write still refuses non-ASCII text."""

    def __init__(self):
        self.written_text = ''
        self.reconfigure_calls = []

    def write(self, text):
        try:
            text.encode('ascii')
        except UnicodeEncodeError as error:
            raise UnicodeEncodeError(ASCII_ENCODING, text, error.start, error.end, error.reason) from None
        self.written_text += text
        return len(text)

    def flush(self):
        pass

    def reconfigure(self, encoding='utf-8'):
        self.reconfigure_calls.append(encoding)


def test_working_stream_writes_text_unchanged(monkeypatch: pytest.MonkeyPatch):
    # Having
    stream = io.StringIO()

    monkeypatch.setattr('sys.stdout', stream)

    # When
    print_safely('✨')

    # Then
    assert stream.getvalue() == '✨\n'


def test_reconfigure_retry_writes_text_unchanged(monkeypatch: pytest.MonkeyPatch):
    # Having
    stream = WritesUnicodeAfterReconfigureStream()

    monkeypatch.setattr('sys.stdout', stream)

    # When
    print_safely('✨')

    # Then
    assert stream.written_text == '✨\n'
    assert stream.reconfigure_calls == ['utf-8']


def test_ascii_fallback_writes_replacement_character(monkeypatch: pytest.MonkeyPatch):
    # Having
    stream = NonAsciiRefusingStream()

    monkeypatch.setattr('sys.stdout', stream)

    # When
    print_safely('✨')

    # Then
    assert stream.written_text == '?\n'


def test_custom_file_target_uses_reconfigure():
    # Having
    stream = WritesUnicodeAfterReconfigureStream()

    # When
    print_safely('✨', file=stream)

    # Then
    assert stream.written_text == '✨\n'
    assert stream.reconfigure_calls == ['utf-8']


def test_custom_file_target_uses_ascii_fallback():
    # Having
    stream = NonAsciiRefusingStream()

    # When
    print_safely('✨', file=stream)

    # Then
    assert stream.written_text == '?\n'


def test_reconfigure_retry_failure_falls_back_to_ascii(monkeypatch: pytest.MonkeyPatch):
    # Having
    stream = ReconfiguresButStillRefusesUnicodeStream()

    monkeypatch.setattr('sys.stdout', stream)

    # When
    print_safely('✨')

    # Then
    assert stream.written_text == '?\n'
    assert stream.reconfigure_calls == ['utf-8']
