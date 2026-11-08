import importlib
import io
import sys
from unittest.mock import MagicMock

import deadcode.cli
from deadcode.cli import main

ASCII_ENCODING = 'ascii'


class Cp1252Stream:
    """A stdout double that cannot encode non-ASCII text until reconfigured."""

    def __init__(self):
        self.encoding = 'cp1252'
        self.written_text = ''

    def write(self, text):
        text.encode(self.encoding)
        self.written_text += text
        return len(text)

    def flush(self):
        pass

    def reconfigure(self, encoding='utf-8'):
        self.encoding = encoding


class AsciiOnlyStringStream(io.StringIO):
    """A StringIO without buffer or reconfigure that refuses non-ASCII text."""

    def write(self, text):
        try:
            text.encode('ascii')
        except UnicodeEncodeError as error:
            raise UnicodeEncodeError(ASCII_ENCODING, text, error.start, error.end, error.reason) from None
        return super().write(text)


def test_main_finishes_when_stdout_cannot_encode(monkeypatch):
    stream = Cp1252Stream()

    monkeypatch.setattr('sys.stdout', stream)
    monkeypatch.setattr('deadcode.cli.find_python_filenames', MagicMock(return_value=[]))
    monkeypatch.setattr('deadcode.cli.find_unused_names', MagicMock(return_value=[]))

    result = main(['tests/files/variables.py', '--no-color'])

    assert result is None
    assert 'Well done!' in stream.written_text


def test_stringio_stdout_without_buffer_or_reconfigure(monkeypatch):
    stream = AsciiOnlyStringStream()

    monkeypatch.setattr('sys.stdout', stream)
    monkeypatch.setattr('deadcode.cli.find_python_filenames', MagicMock(return_value=[]))
    monkeypatch.setattr('deadcode.cli.find_unused_names', MagicMock(return_value=[]))

    result = main(['tests/files/variables.py', '--no-color'])

    assert result is None
    assert 'Well done!' in stream.getvalue()
    assert '✨' not in stream.getvalue()
    assert '?' in stream.getvalue()


def test_import_does_not_rebind_stdout():
    original_stdout = sys.stdout

    importlib.reload(deadcode.cli)

    assert sys.stdout is original_stdout


def test_parse_warning_with_non_ascii_filename_on_cp1252_stream(virtual_file_system, monkeypatch):
    stream = Cp1252Stream()

    virtual_file_system.files = {'café.py': b'def broken(:\n'}
    monkeypatch.setattr('sys.stdout', stream)

    result = main(['café.py', '--no-color'])

    assert result is None
    assert 'Failed to parse café.py' in stream.written_text
    assert 'Well done!' in stream.written_text


def test_parse_warning_with_non_ascii_filename_on_ascii_only_stream(virtual_file_system, monkeypatch):
    stream = AsciiOnlyStringStream()

    virtual_file_system.files = {'café.py': b'def broken(:\n'}
    monkeypatch.setattr('sys.stdout', stream)

    result = main(['café.py', '--no-color'])

    assert result is None
    assert 'Failed to parse caf?.py' in stream.getvalue()
    assert "b'" not in stream.getvalue()
    assert 'Well done!' in stream.getvalue()
