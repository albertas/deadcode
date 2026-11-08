from pathlib import Path

import pytest

from deadcode.cli import main


def test_ignore_name_if_inherits_from_base_class(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Base:
                    pass


                class UnusedClass(Base):
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-names-if-inherits-from=Base'])

    # Then
    assert unused_names is None


def test_ignore_name_if_inherits_from_dotted_base_class(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                import graphene


                class UnusedQuery(graphene.ObjectType):
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-names-if-inherits-from=graphene.ObjectType'])

    # Then
    assert unused_names is None


def test_ignore_name_if_inherits_from_final_base_class_component(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                import graphene


                class UnusedQuery(graphene.ObjectType):
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-names-if-inherits-from=ObjectType'])

    # Then
    assert unused_names is None


def test_ignore_name_if_inherits_from_transitive_base_class(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Base:
                    pass


                class Middle(Base):
                    pass


                class Leaf(Middle):
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-names-if-inherits-from=Base'])

    # Then
    assert unused_names is None


def test_ignore_name_if_inherits_from_glob_base_class(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                import graphene


                class UnusedQuery(graphene.ObjectType):
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-names-if-inherits-from=*.ObjectType'])

    # Then
    assert unused_names is None


def test_non_matching_base_class_is_still_reported(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                import graphene


                class UnusedQuery(graphene.ObjectType):
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-names-if-inherits-from=*.Other'])

    # Then
    assert unused_names == 'foo.py:4:0: DC03 Class `UnusedQuery` is never used'


def test_ignored_class_body_is_still_reported_and_fixed(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Base:
                    pass


                class UnusedClass(Base):
                    \"\"\"Unused class.\"\"\"

                    inner = 1


                class AnotherUnusedClass:
                    \"\"\"Another unused class.\"\"\"

                    another_unused_attribute = None
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-names-if-inherits-from=Base', '--fix'])

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                class Base:
                    pass


                class UnusedClass(Base):
                    \"\"\"Unused class.\"\"\"
                """
        }
    )

    assert unused_names == (
        'foo.py:8:4: DC06 Name `inner` is never used\n'
        'foo.py:11:0: DC03 Class `AnotherUnusedClass` is never used\n'
        'foo.py:14:4: DC06 Name `another_unused_attribute` is never used\n'
        '\n'
        'Removed 3 unused code items!'
    )


@pytest.fixture()
def project_directory(tmp_path, monkeypatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_configuration_in_pyproject_toml_ignores_base_class_names(project_directory: Path, virtual_file_system) -> None:
    # Having
    Path(project_directory, 'pyproject.toml').write_text(
        '[tool.deadcode]\nignore-names-if-inherits-from = ["ViewEventListener"]\n'
    )
    virtual_file_system.files = {
        'foo.py': b"""
                import sublime_plugin


                class MyListener(sublime_plugin.ViewEventListener):
                    def on_load(self):
                        pass


                class Plain(sublime_plugin.ViewEventListener):
                    pass


                class Unrelated:
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color'])

    # Then
    assert unused_names == (
        'foo.py:5:4: DC04 Method `on_load` is never used' '\nfoo.py:13:0: DC03 Class `Unrelated` is never used'
    )


def test_pyproject_configuration_and_command_line_values_are_united(
    project_directory: Path, virtual_file_system
) -> None:
    # Having
    Path(project_directory, 'pyproject.toml').write_text(
        '[tool.deadcode]\nignore-names-if-inherits-from = ["BaseFromConfiguration"]\n'
    )
    virtual_file_system.files = {
        'foo.py': b"""
                class BaseFromConfiguration:
                    pass


                class BaseFromCommandLine:
                    pass


                class ConfiguredSubclass(BaseFromConfiguration):
                    pass


                class CommandLineSubclass(BaseFromCommandLine):
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-names-if-inherits-from=BaseFromCommandLine'])

    # Then
    assert unused_names is None


def test_scalar_configuration_value_is_treated_as_one_pattern(project_directory: Path, virtual_file_system) -> None:
    # Having
    Path(project_directory, 'pyproject.toml').write_text(
        '[tool.deadcode]\nignore-names-if-inherits-from = "ViewEventListener"\n'
    )
    virtual_file_system.files = {
        'foo.py': b"""
                import sublime_plugin


                class MyListener(sublime_plugin.ViewEventListener):
                    pass


                class Plain(sublime_plugin.ViewEventListener):
                    pass


                class Unrelated:
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color'])

    # Then
    assert unused_names == 'foo.py:12:0: DC03 Class `Unrelated` is never used'
