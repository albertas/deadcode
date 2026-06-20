from unittest import expectedFailure

from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase

_DECORATED = """
    def mark(func):
        return func


    @mark
    def decorated_handler():
        return 1
    """

_INHERITS = """
    class Base:
        pass


    class Derived(Base):
        pass
    """

_MEMBER = """
    class Base:
        pass


    class Derived(Base):
        def helper(self):
            return 1


    Derived()
    """

_DECORATED_CLASS = """
    def mark(cls):
        return cls


    @mark
    class Service:
        def helper(self):
            return 1


    Service()
    """


class DeadCliFlagTests(BaseTestCase):
    @expectedFailure
    def test_ignore_if_decorated_with_should_suppress_definition(self):
        self.files = {'foo.py': _DECORATED}
        assert main(['foo.py', '--no-color', '--ignore-if-decorated-with=@mark']) is None

    @expectedFailure
    def test_ignore_if_inherits_from_should_suppress_definition(self):
        self.files = {'foo.py': _INHERITS}
        assert main(['foo.py', '--no-color', '--ignore-if-inherits-from=Base']) is None

    @expectedFailure
    def test_ignore_names_if_inherits_from_should_suppress_definition(self):
        self.files = {'foo.py': _MEMBER}
        assert main(['foo.py', '--no-color', '--ignore-names-if-inherits-from=Base']) is None

    @expectedFailure
    def test_ignore_names_if_decorated_with_should_suppress_definition(self):
        self.files = {'foo.py': _DECORATED}
        assert main(['foo.py', '--no-color', '--ignore-names-if-decorated-with=@mark']) is None

    @expectedFailure
    def test_ignore_bodies_of_should_suppress_definition(self):
        self.files = {'foo.py': _MEMBER}
        assert main(['foo.py', '--no-color', '--ignore-bodies-of=Derived']) is None

    @expectedFailure
    def test_ignore_bodies_if_decorated_with_should_suppress_definition(self):
        self.files = {'foo.py': _DECORATED_CLASS}
        assert main(['foo.py', '--no-color', '--ignore-bodies-if-decorated-with=@mark']) is None
