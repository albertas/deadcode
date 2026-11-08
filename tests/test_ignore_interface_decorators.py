from deadcode.cli import main


def test_abstractmethod_and_override_are_ignored_by_default(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                from abc import ABC, abstractmethod
                from typing import override


                class Base(ABC):
                    @abstractmethod
                    def compute(self):
                        ...


                class Impl(Base):
                    @override
                    def compute(self):
                        return 1


                Impl()
                """
    }

    unused_names = main(['foo.py', '--no-color'])

    assert unused_names is None


def test_qualified_spellings_are_ignored(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                import abc
                import typing
                import typing_extensions


                class Base(abc.ABC):
                    @abc.abstractmethod
                    def compute(self):
                        ...


                class Impl(Base):
                    @typing.override
                    def compute(self):
                        return 1


                @typing_extensions.override
                def callback():
                    return 1


                Impl()
                """
    }

    unused_names = main(['foo.py', '--no-color'])

    assert unused_names is None


def test_unqualified_spellings_are_ignored(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                from abc import abstractmethod
                from typing import override


                @abstractmethod
                def compute():
                    ...


                @override
                def render():
                    ...
                """
    }

    unused_names = main(['foo.py', '--no-color'])

    assert unused_names is None


def test_stacked_decorators_are_ignored(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                class Service:
                    @property
                    @override
                    def value(self):
                        return 1


                Service()
                """
    }

    unused_names = main(['foo.py', '--no-color'])

    assert unused_names is None


def test_aliased_import_is_still_reported(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                from abc import abstractmethod as abstract


                class Service:
                    @abstract
                    def compute(self):
                        return 1


                Service()
                """
    }

    unused_names = main(['foo.py', '--no-color'])

    assert unused_names == 'foo.py:6:4: DC04 Method `compute` is never used'


def test_unused_method_next_to_ignored_method_is_reported(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                class Service:
                    @override
                    def compute(self):
                        return 1

                    def render(self):
                        return 2


                Service()
                """
    }

    unused_names = main(['foo.py', '--no-color'])

    assert unused_names == 'foo.py:6:4: DC04 Method `render` is never used'


def test_fix_keeps_decorated_methods_and_removes_other_unused_code(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                class Service:
                    @override
                    def compute(self):
                        return 1

                    @abstractmethod
                    def render(self):
                        return 2


                def unused():
                    pass


                Service()
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])

    assert unused_names == ('foo.py:11:0: DC02 Function `unused` is never used\n\nRemoved 1 unused code item!')

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                class Service:
                    @override
                    def compute(self):
                        return 1

                    @abstractmethod
                    def render(self):
                        return 2


                Service()
                """
        }
    )
