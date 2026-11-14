from deadcode.cli import main, print_main


def test_cascade_reports_both_definitions_in_one_run(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'main.py': b"""
                def helper():
                    return 1


                def main_helper():
                    helper()
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names == (
        'main.py:1:0: DC02 Function `helper` is never used\nmain.py:5:0: DC02 Function `main_helper` is never used'
    )


def test_cross_module_cascade_through_import_chain(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'x.py': b"""
                def foo():
                    return 1
                """,
        'y.py': b"""
                from x import foo


                def relay():
                    return foo()
                """,
        'z.py': b"""
                print('goodbye')
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names == (
        'x.py:1:0: DC02 Function `foo` is never used'
        '\ny.py:1:14: DC07 Import `foo` is never used'
        '\ny.py:4:0: DC02 Function `relay` is never used'
    )


def test_self_referencing_function_is_reported(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'main.py': b"""
                def helper():
                    helper()
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names == 'main.py:1:0: DC02 Function `helper` is never used'


def test_mutually_recursive_dead_definitions_are_reported(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'main.py': b"""
                def a():
                    b()


                def b():
                    a()
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names == (
        'main.py:1:0: DC02 Function `a` is never used\nmain.py:5:0: DC02 Function `b` is never used'
    )


def test_cascade_stops_at_module_level_root_usage(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'main.py': b"""
                def helper():
                    return 1


                def main_helper():
                    helper()


                print(main_helper())
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names is None


def test_method_cascade_inside_dead_class(virtual_file_system):
    # The tool resolves bare names in module scope, so the bare `method_b()` call
    # references the method item and is owned by its caller `method_a`.
    virtual_file_system.files = {
        'main.py': b"""
                class Dead:
                    def method_a(self):
                        return method_b()


                    def method_b(self):
                        return 1
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names == (
        'main.py:1:0: DC03 Class `Dead` is never used'
        '\nmain.py:2:4: DC04 Method `method_a` is never used'
        '\nmain.py:6:4: DC04 Method `method_b` is never used'
    )


def test_getattr_anchor_keeps_target_alive(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'main.py': b"""
                def helper():
                    return 1


                def dead_owner(obj):
                    return getattr(obj, 'helper')
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names == 'main.py:5:0: DC02 Function `dead_owner` is never used'


def test_all_export_element_keeps_target_alive(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'main.py': b"""
                def helper():
                    return 1


                def dead_owner():
                    pass


                __all__ = ['helper']
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names == 'main.py:5:0: DC02 Function `dead_owner` is never used'


def test_middleware_path_keeps_target_alive(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'main.py': b"""
                def helper():
                    return 1


                def dead_owner():
                    pass


                MIDDLEWARE = ['main.helper']
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then: the middleware path keeps `helper` alive; only the dead owner and the
    # unused `MIDDLEWARE` variable itself are reported.
    assert unused_names == (
        'main.py:5:0: DC02 Function `dead_owner` is never used\nmain.py:9:0: DC01 Variable `MIDDLEWARE` is never used'
    )


def test_percent_format_locals_anchor_keeps_target_alive(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'main.py': b"""
                def helper():
                    return 1


                def dead_owner():
                    return '%(helper)s' % locals()
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names == 'main.py:5:0: DC02 Function `dead_owner` is never used'


def test_decorator_name_keeps_target_alive(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'main.py': b"""
                def deco(fn):
                    return fn


                @deco
                def dead_owner():
                    pass
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then: decorator usages are root usages, so they keep `deco` alive.
    assert unused_names == 'main.py:6:0: DC02 Function `dead_owner` is never used'


def test_quoted_return_annotation_keeps_target_alive(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'main.py': b"""
                def helper():
                    return 1


                def dead_owner() -> 'helper':
                    pass
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then: annotation strings are recorded before the usage context is pushed,
    # so they are root usages and keep their targets alive.
    assert unused_names == 'main.py:5:0: DC02 Function `dead_owner` is never used'


def test_unresolved_attribute_load_keeps_target_alive(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'main.py': b"""
                def helper():
                    return 1


                def dead_owner(obj):
                    return obj.helper
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names == 'main.py:5:0: DC02 Function `dead_owner` is never used'


def test_ignore_names_protected_caller_keeps_targets_alive(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'main.py': b"""
                def helper():
                    return 1


                def protected_caller():
                    helper()
                """,
    }

    # When
    unused_names = main(['.', '--no-color', '--ignore-names=protected_caller'])

    # Then: the ignore-protected caller is not reported and its body usages are
    # root usages, so they keep their targets alive.
    assert unused_names is None


def test_noqa_protected_caller_keeps_targets_alive(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'main.py': b"""
                def helper():
                    return 1


                def protected_caller():  # noqa
                    helper()
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then: the noqa-protected caller is not reported and its body usages are
    # root usages, so they keep their targets alive.
    assert unused_names is None


def test_ignore_code_filters_cascade_findings(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'main.py': b"""
                def helper():
                    return 1


                def main_helper():
                    helper()
                """,
    }

    # When
    unused_names = main(['.', '--no-color', '--ignore-rules', 'dc02'])
    exit_status = print_main(['.', '--no-color', '--ignore-rules', 'dc02'])

    # Then: every finding is filtered away, so no item survives and the run is
    # treated as clean.
    assert unused_names is None
    assert exit_status == 0


def test_ambiguous_usage_in_live_caller_keeps_both_targets_alive(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'a.py': b"""
                from b import foo


                def foo():
                    return 1


                def live_caller():
                    foo()


                print(live_caller())
                """,
        'b.py': b"""
                def foo():
                    return 2
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then: the ambiguous usage keeps its conservative `None` fallback, so both
    # same-named definitions stay alive exactly as the name-shadowing tests
    # assert today.
    assert unused_names is None


def test_no_over_cascading_from_root_usage(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'main.py': b"""
                def a():
                    return b()


                def b():
                    return c()


                def c():
                    return 1


                print(a())
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then: the module-level (root) call keeps the whole call chain alive.
    assert unused_names is None
