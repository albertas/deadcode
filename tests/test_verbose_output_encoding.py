import io

from deadcode.data_types import Args
from deadcode.visitor.dead_code_visitor import DeadCodeVisitor


class AsciiOnlyStream(io.StringIO):
    """A StringIO that refuses to write text it cannot encode as ASCII."""

    def write(self, text):
        text.encode('ascii')
        return super().write(text)


def test_log_replaces_unencodable_characters():
    visitor = DeadCodeVisitor(filenames=[], args=Args())
    stream = AsciiOnlyStream()

    visitor._log('✨', file=stream, force=True)  # noqa: SLF001

    assert stream.getvalue() == '?\n'
    assert "b'" not in stream.getvalue()


def test_log_keeps_ascii_text():
    visitor = DeadCodeVisitor(filenames=[], args=Args())
    stream = io.StringIO()

    visitor._log('plain ascii', file=stream, force=True)  # noqa: SLF001

    assert stream.getvalue() == 'plain ascii\n'
