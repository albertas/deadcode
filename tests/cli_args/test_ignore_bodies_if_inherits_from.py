from deadcode.cli import main


def test_ignore_class_definition_if_inherits_from_base_class(virtual_file_system):
    # Having
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

    # When
    output = main(['ignore_names_by_pattern.py', '--no-color', '--ignore-bodies-if-inherits-from=Base', '--fix'])

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                class Base:
                    pass
                """
        }
    )

    assert output == (
        'foo.py:5:0: DC03 Class `UnusedClass` is never used\n'
        'foo.py:15:0: DC03 Class `AnotherUnusedClass` is never used\n'
        'foo.py:16:4: DC06 Name `another_unused_attribute` is never used\n'
        '\n'
        'Removed 3 unused code items!'
    )


def test_ignore_class_body_if_inherits_from_dotted_base_class(virtual_file_system):
    # Having
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

    # When
    output = main(
        [
            'ignore_names_by_pattern.py',
            '--no-color',
            '--ignore-bodies-if-inherits-from=graphene.ObjectType',
            '--fix',
        ]
    )

    # Then
    virtual_file_system.assert_files({'foo.py': b'\nimport graphene\n'})

    assert output == (
        'foo.py:4:0: DC03 Class `UnusedQuery` is never used\n'
        'foo.py:11:0: DC03 Class `AnotherUnusedClass` is never used\n'
        'foo.py:12:4: DC06 Name `another_unused_attribute` is never used\n'
        '\n'
        'Removed 3 unused code items!'
    )


def test_ignore_class_body_if_inherits_from_final_base_class_component(virtual_file_system):
    # Having
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

    # When
    output = main(['ignore_names_by_pattern.py', '--no-color', '--ignore-bodies-if-inherits-from=ObjectType', '--fix'])

    # Then
    virtual_file_system.assert_files({'foo.py': b'\nimport graphene\n'})

    assert output == (
        'foo.py:4:0: DC03 Class `UnusedQuery` is never used\n'
        'foo.py:11:0: DC03 Class `AnotherUnusedClass` is never used\n'
        'foo.py:12:4: DC06 Name `another_unused_attribute` is never used\n'
        '\n'
        'Removed 3 unused code items!'
    )


def test_ignore_class_body_if_inherits_from_glob_base_class(virtual_file_system):
    # Having
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

    # When
    output = main(
        ['ignore_names_by_pattern.py', '--no-color', '--ignore-bodies-if-inherits-from=*.ObjectType', '--fix']
    )

    # Then
    virtual_file_system.assert_files({'foo.py': b'\nimport graphene\n'})

    assert output == (
        'foo.py:4:0: DC03 Class `UnusedQuery` is never used\n'
        'foo.py:11:0: DC03 Class `AnotherUnusedClass` is never used\n'
        'foo.py:12:4: DC06 Name `another_unused_attribute` is never used\n'
        '\n'
        'Removed 3 unused code items!'
    )
