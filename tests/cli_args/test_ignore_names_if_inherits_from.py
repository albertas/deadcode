from deadcode.cli import main


def test_ignore_name_if_inherits_from_base_class(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                class Base:
                    pass


                class UnusedClass(Base):
                    pass
                """
    }

    unused_names = main(['foo.py', '--no-color', '--ignore-names-if-inherits-from=Base'])

    assert unused_names is None


def test_ignore_name_if_inherits_from_dotted_base_class(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                import graphene


                class UnusedQuery(graphene.ObjectType):
                    pass
                """
    }

    unused_names = main(['foo.py', '--no-color', '--ignore-names-if-inherits-from=graphene.ObjectType'])

    assert unused_names is None


def test_ignore_name_if_inherits_from_final_base_class_component(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                import graphene


                class UnusedQuery(graphene.ObjectType):
                    pass
                """
    }

    unused_names = main(['foo.py', '--no-color', '--ignore-names-if-inherits-from=ObjectType'])

    assert unused_names is None


def test_ignore_name_if_inherits_from_transitive_base_class(virtual_file_system):
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

    unused_names = main(['foo.py', '--no-color', '--ignore-names-if-inherits-from=Base'])

    assert unused_names is None


def test_ignore_name_if_inherits_from_glob_base_class(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                import graphene


                class UnusedQuery(graphene.ObjectType):
                    pass
                """
    }

    unused_names = main(['foo.py', '--no-color', '--ignore-names-if-inherits-from=*.ObjectType'])

    assert unused_names is None


def test_non_matching_base_class_is_still_reported(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                import graphene


                class UnusedQuery(graphene.ObjectType):
                    pass
                """
    }

    unused_names = main(['foo.py', '--no-color', '--ignore-names-if-inherits-from=*.Other'])

    assert unused_names == 'foo.py:4:0: DC03 Class `UnusedQuery` is never used'


def test_ignored_class_body_is_still_reported_and_fixed(virtual_file_system):
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

    unused_names = main(['foo.py', '--no-color', '--ignore-names-if-inherits-from=Base', '--fix'])

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
        'foo.py:8:4: DC01 Variable `inner` is never used\n'
        'foo.py:11:0: DC03 Class `AnotherUnusedClass` is never used\n'
        'foo.py:14:4: DC01 Variable `another_unused_attribute` is never used\n'
        '\n'
        'Removed 3 unused code items!'
    )
