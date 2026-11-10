from deadcode.cli import main


def test_middleware_list_marks_registered_class_and_function_as_used(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'project/settings.py': b"""
                MIDDLEWARE = [
                    'project.middleware.ListedMiddleware',
                    'project.middleware.listed_middleware',
                ]
                """,
        'project/middleware.py': b"""
                class ListedMiddleware:
                    pass


                def listed_middleware(get_response):
                    return get_response


                class UnregisteredMiddleware:
                    pass
                """,
    }

    # When
    unused_names = main(['project', '--no-color', '--ignore-names-in-files=*/settings.py'])

    # Then
    assert unused_names == 'project/middleware.py:9:0: DC03 Class `UnregisteredMiddleware` is never used'


def test_middleware_tuple_marks_registered_class_as_used(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'project/settings.py': b"MIDDLEWARE = ('project.middleware.ListedMiddleware',)",
        'project/middleware.py': b"""
                class ListedMiddleware:
                    pass


                class UnregisteredMiddleware:
                    pass
                """,
    }

    # When
    unused_names = main(['project', '--no-color', '--ignore-names-in-files=*/settings.py'])

    # Then
    assert unused_names == 'project/middleware.py:5:0: DC03 Class `UnregisteredMiddleware` is never used'


def test_non_registration_shapes_keep_definitions_reported(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'project/settings.py': b"""
                MIDDLEWARE = 'project.middleware.NotRegistered'
                OTHER = ['project.middleware.NotRegisteredEither']
                MIDDLEWARE = [
                    'project.middleware.ListedWithEmptyPath',
                    1,
                    None,
                    '',
                    'project.middleware.multi.part.ListedWithManyDots',
                ]


                def configure():
                    MIDDLEWARE = ['project.middleware.NestedMiddleware']
                """,
        'project/middleware.py': b"""
                class NotRegistered:
                    pass


                class NotRegisteredEither:
                    pass


                class ListedWithEmptyPath:
                    pass


                class ListedWithManyDots:
                    pass


                class NestedMiddleware:
                    pass
                """,
    }

    # When
    unused_names = main(['project', '--no-color', '--ignore-names-in-files=*/settings.py'])

    # Then
    assert unused_names == (
        'project/middleware.py:1:0: DC03 Class `NotRegistered` is never used\n'
        'project/middleware.py:5:0: DC03 Class `NotRegisteredEither` is never used\n'
        'project/middleware.py:17:0: DC03 Class `NestedMiddleware` is never used'
    )


def test_multiple_assignment_targets_do_not_mark_middleware_as_used(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'project/settings.py': b"""
                MIDDLEWARE = OTHER = ['project.middleware.MultiTargetMiddleware']
                """,
        'project/middleware.py': b"""
                class MultiTargetMiddleware:
                    pass
                """,
    }

    # When
    unused_names = main(['project', '--no-color', '--ignore-names-in-files=*/settings.py'])

    # Then
    assert unused_names == 'project/middleware.py:1:0: DC03 Class `MultiTargetMiddleware` is never used'
