import importlib
import io
import sys
from unittest import TestCase
from unittest.mock import patch

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
            raise UnicodeEncodeError(
                ASCII_ENCODING, text, error.start, error.end, error.reason
            ) from None
        return super().write(text)


class CliOutputEncodingTests(TestCase):
    def test_main_finishes_when_stdout_cannot_encode(self):
        stream = Cp1252Stream()

        with patch('sys.stdout', stream), patch(
            'deadcode.cli.find_python_filenames', return_value=[]
        ), patch('deadcode.cli.find_unused_names', return_value=[]):
            result = main(['tests/files/variables.py', '--no-color'])

        self.assertIsNone(result)
        self.assertIn('Well done!', stream.written_text)

    def test_stringio_stdout_without_buffer_or_reconfigure(self):
        stream = AsciiOnlyStringStream()

        with patch('sys.stdout', stream), patch(
            'deadcode.cli.find_python_filenames', return_value=[]
        ), patch('deadcode.cli.find_unused_names', return_value=[]):
            result = main(['tests/files/variables.py', '--no-color'])

        self.assertIsNone(result)
        self.assertIn('Well done!', stream.getvalue())
        self.assertNotIn('✨', stream.getvalue())
        self.assertIn('?', stream.getvalue())

    def test_import_does_not_rebind_stdout(self):
        original_stdout = sys.stdout

        importlib.reload(deadcode.cli)

        self.assertIs(sys.stdout, original_stdout)
