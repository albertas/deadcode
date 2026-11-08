import pytest

from deadcode.cli import main


def test_ignore_class_definition_if_inherits_from_base_class(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                class Base:
                    pass


                class UnusedClass(Base):
                    unused_attribute = None

                    def unused_method(self, unused_parameter: str = "") -> None:
                        unused_local_var = 123

                    class UnusedInnerClass:
                        unused_class_attribute = ""


                class AnotherUnusedClass:
                    another_unused_attribute = None
                """
    }

    output = main(['ignore_names_by_pattern.py', '--no-color', '--ignore-definitions-if-inherits-from=Base', '--fix'])

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                class Base:
                    pass


                class UnusedClass(Base):
                    unused_attribute = None

                    def unused_method(self, unused_parameter: str = "") -> None:
                        unused_local_var = 123

                    class UnusedInnerClass:
                        unused_class_attribute = ""
                """
        }
    )

    assert output == (
        'foo.py:15:0: DC03 Class `AnotherUnusedClass` is never used\n'
        'foo.py:16:4: DC01 Variable `another_unused_attribute` is never used\n'
        '\n'
        'Removed 2 unused code items!'
    )


@pytest.mark.skip(reason='Skipped without a recorded reason before the pytest migration; behaviour preserved')
def test_ignore_class_definition_if_inherits_from_multiple_classes(virtual_file_system):
    # TODO:
    # Implement class inheritance tracking, so that not only the first level of
    # inherited classes would be considered, but whole inheritance tree would be considered.

    virtual_file_system.files = {
        'foo.py': b"""
                class Base:
                    pass


                class Interface(Base):
                    pass


                class UnusedClass(Interface):
                    unused_attribute = None

                    def unused_method(self, unused_parameter: str = "") -> None:
                        unused_local_var = 123

                    class UnusedInnerClass:
                        unused_class_attribute = ""


                class AnotherUnusedClass:
                    another_unused_attribute = None
                """
    }

    output = main(['ignore_names_by_pattern.py', '--no-color', '--ignore-definitions-if-inherits-from=Base', '--fix'])

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                class Base:
                    pass


                class Interface(Base):
                    pass


                class UnusedClass(Interface):
                    unused_attribute = None

                    def unused_method(self, unused_parameter: str = "") -> None:
                        unused_local_var = 123

                    class UnusedInnerClass:
                        unused_class_attribute = ""
                """
        }
    )

    assert output == (
        'foo.py:15:0: DC03 Class `AnotherUnusedClass` is never used\n'
        'foo.py:16:4: DC01 Variable `another_unused_attribute` is never used\n'
        '\n'
        'Removed 2 unused code items!'
    )


def test_ignore_class_definition_if_inherits_from_dotted_base_class(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                import graphene


                class UnusedQuery(graphene.ObjectType):
                    this_field_is_used = graphene.String()

                    def resolve_this_field_is_used(self, info):
                        return ""


                class AnotherUnusedClass:
                    another_unused_attribute = None
                """
    }

    output = main(
        [
            'ignore_names_by_pattern.py',
            '--no-color',
            '--ignore-definitions-if-inherits-from=graphene.ObjectType',
            '--fix',
        ]
    )

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                import graphene


                class UnusedQuery(graphene.ObjectType):
                    this_field_is_used = graphene.String()

                    def resolve_this_field_is_used(self, info):
                        return ""
                """
        }
    )

    assert output == (
        'foo.py:11:0: DC03 Class `AnotherUnusedClass` is never used\n'
        'foo.py:12:4: DC01 Variable `another_unused_attribute` is never used\n'
        '\n'
        'Removed 2 unused code items!'
    )


def test_ignore_class_definition_if_inherits_from_final_base_class_component(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                import graphene


                class UnusedQuery(graphene.ObjectType):
                    this_field_is_used = graphene.String()

                    def resolve_this_field_is_used(self, info):
                        return ""


                class AnotherUnusedClass:
                    another_unused_attribute = None
                """
    }

    output = main(
        [
            'ignore_names_by_pattern.py',
            '--no-color',
            '--ignore-definitions-if-inherits-from=ObjectType',
            '--fix',
        ]
    )

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                import graphene


                class UnusedQuery(graphene.ObjectType):
                    this_field_is_used = graphene.String()

                    def resolve_this_field_is_used(self, info):
                        return ""
                """
        }
    )

    assert output == (
        'foo.py:11:0: DC03 Class `AnotherUnusedClass` is never used\n'
        'foo.py:12:4: DC01 Variable `another_unused_attribute` is never used\n'
        '\n'
        'Removed 2 unused code items!'
    )


def test_ignore_class_definition_if_inherits_from_transitive_dotted_base_class(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                import graphene


                class Intermediate(graphene.ObjectType):
                    this_field_is_used = graphene.String()

                    def resolve_this_field_is_used(self, info):
                        return ""


                class UnusedQuery(Intermediate):
                    unused_attribute = None


                class AnotherUnusedClass:
                    another_unused_attribute = None
                """
    }

    output = main(
        [
            'ignore_names_by_pattern.py',
            '--no-color',
            '--ignore-definitions-if-inherits-from=ObjectType',
            '--fix',
        ]
    )

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                import graphene


                class Intermediate(graphene.ObjectType):
                    this_field_is_used = graphene.String()

                    def resolve_this_field_is_used(self, info):
                        return ""


                class UnusedQuery(Intermediate):
                    unused_attribute = None
                """
        }
    )

    assert output == (
        'foo.py:15:0: DC03 Class `AnotherUnusedClass` is never used\n'
        'foo.py:16:4: DC01 Variable `another_unused_attribute` is never used\n'
        '\n'
        'Removed 2 unused code items!'
    )
