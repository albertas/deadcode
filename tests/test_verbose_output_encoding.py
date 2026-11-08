import io
from unittest import TestCase

from deadcode.data_types import Args
from deadcode.visitor.dead_code_visitor import DeadCodeVisitor


class AsciiOnlyStream(io.StringIO):
    """A StringIO that refuses to write text it cannot encode as ASCII."""

    def write(self, text):
        text.encode('ascii')
        return super().write(text)


class TestVerboseOutputEncoding(TestCase):
    def test_log_replaces_unencodable_characters(self):
        visitor = DeadCodeVisitor(filenames=[], args=Args())
        stream = AsciiOnlyStream()

        visitor._log('✨', file=stream, force=True)  # noqa: SLF001

        self.assertEqual(stream.getvalue(), '?\n')
        self.assertNotIn("b'", stream.getvalue())

    def test_log_keeps_ascii_text(self):
        visitor = DeadCodeVisitor(filenames=[], args=Args())
        stream = io.StringIO()

        visitor._log('plain ascii', file=stream, force=True)  # noqa: SLF001

        self.assertEqual(stream.getvalue(), 'plain ascii\n')
