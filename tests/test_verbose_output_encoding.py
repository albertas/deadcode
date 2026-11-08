import io
from pathlib import Path

from deadcode.data_types import Args
from deadcode.visitor.code_item import CodeItem
from deadcode.visitor.dead_code_visitor import DeadCodeVisitor
from deadcode.visitor.utils import LoggingList, LoggingSet


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


def test_logging_list_replaces_unencodable_characters(monkeypatch):
    stream = AsciiOnlyStream()

    monkeypatch.setattr('sys.stdout', stream)
    logging_list = LoggingList('variable', verbose=True)
    logging_list.append(CodeItem(name='✨', type_='variable', filename=Path('example.py')))

    assert stream.getvalue() == 'define variable "?"\n'


def test_logging_set_replaces_unencodable_characters(monkeypatch):
    stream = AsciiOnlyStream()

    monkeypatch.setattr('sys.stdout', stream)
    logging_set = LoggingSet('variable', verbose=True)
    logging_set.add('✨')

    assert stream.getvalue() == 'use variable "?"\n'
    assert "b'" not in stream.getvalue()


def test_logging_list_keeps_ascii_text(monkeypatch):
    stream = io.StringIO()

    monkeypatch.setattr('sys.stdout', stream)
    logging_list = LoggingList('variable', verbose=True)
    logging_list.append(CodeItem(name='used_name', type_='variable', filename=Path('example.py')))

    assert stream.getvalue() == 'define variable "used_name"\n'


def test_logging_set_keeps_ascii_text(monkeypatch):
    stream = io.StringIO()

    monkeypatch.setattr('sys.stdout', stream)
    logging_set = LoggingSet('variable', verbose=True)
    logging_set.add('used_name')

    assert stream.getvalue() == 'use variable "used_name"\n'
