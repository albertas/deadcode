from deadcode.cli import main


def test_same_named_definition_in_another_module_is_reported_unused(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'a.py': b"""
                def foo():
                    return 1


                print(foo())
                """,
        'b.py': b"""
                def foo():
                    return 2
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names == 'b.py:1:0: DC02 Function `foo` is never used'


def test_usage_through_direct_import_edge_suppresses_source_definition(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'a.py': b"""
                from b import foo


                print(foo())
                """,
        'b.py': b"""
                def foo():
                    return 2
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names is None


def test_usage_through_aliased_import_edge_suppresses_source_definition(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'a.py': b"""
                from b import foo as f


                print(f())
                """,
        'b.py': b"""
                def foo():
                    return 2
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names is None


def test_usage_through_two_hop_import_chain_suppresses_origin_definition(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'x.py': b"""
                def foo():
                    return 1
                """,
        'y.py': b"""
                from x import foo
                """,
        'z.py': b"""
                from y import foo


                print(foo())
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names == 'y.py:1:14: DC07 Import `foo` is never used'


def test_unresolvable_bare_usage_keeps_current_suppression(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'a.py': b"""
                print(foo())
                """,
        'b.py': b"""
                def foo():
                    return 2
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names is None


def test_ambiguous_usage_defined_and_imported_keeps_current_suppression(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'a.py': b"""
                from b import foo


                def foo():
                    return 1


                print(foo())
                """,
        'b.py': b"""
                def foo():
                    return 2
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names is None


def test_ambiguous_usage_imported_from_two_sources_keeps_current_suppression(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'a.py': b"""
                from b import foo
                from c import foo


                print(foo())
                """,
        'b.py': b"""
                def foo():
                    return 1
                """,
        'c.py': b"""
                def foo():
                    return 2
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names is None


def test_own_module_usage_satisfies_only_own_function_definition(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'a.py': b"""
                def foo():
                    return 1


                print(foo())
                """,
        'b.py': b"""
                def foo():
                    return 2
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names == 'b.py:1:0: DC02 Function `foo` is never used'


def test_own_module_usage_satisfies_only_own_variable_definition(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'a.py': b"""
                foo = 1

                print(foo)
                """,
        'b.py': b"""
                foo = 2
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names == 'b.py:1:0: DC01 Variable `foo` is never used'


def test_wildcard_import_resolves_usage_to_exporting_source(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'a.py': b"""
                from b import *


                print(foo())
                """,
        'b.py': b"""
                def foo():
                    return 1
                """,
        'c.py': b"""
                def foo():
                    return 2
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names == 'c.py:1:0: DC02 Function `foo` is never used'


def test_wildcard_import_from_unanalysed_module_keeps_current_suppression(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'a.py': b"""
                from b import *


                print(foo())
                """,
        'b.py': b"""
                __all__ += ['foo']
                """,
        'c.py': b"""
                def foo():
                    return 2
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names is None


def test_helper_in_package_init_reached_via_from_import_is_not_reported(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'pkg/__init__.py': b"""
                def helper():
                    return 1
                """,
        'a.py': b"""
                from pkg import helper


                print(helper())
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names is None


def test_helper_in_both_pkg_py_and_pkg_init_reached_via_from_import_reports_neither(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'pkg.py': b"""
                def helper():
                    return 1
                """,
        'pkg/__init__.py': b"""
                def helper():
                    return 2
                """,
        'a.py': b"""
                from pkg import helper


                print(helper())
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names is None


def test_reexport_chain_through_package_init_suppresses_origin_definition(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'w.py': b"""
                def n():
                    return 1
                """,
        'pkg/__init__.py': b"""
                from w import n
                """,
        'a.py': b"""
                from pkg import n


                print(n())
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names is None


def test_own_module_usage_satisfies_only_own_class_definition(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'a.py': b"""
                class Foo:
                    pass


                print(Foo())
                """,
        'b.py': b"""
                class Foo:
                    pass
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names == 'b.py:1:0: DC03 Class `Foo` is never used'
