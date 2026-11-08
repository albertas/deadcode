from deadcode.cli import main


def test_ignore_names_matched_by_word_and_group_regexp_patterns(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'ignore_names_by_pattern.py': b"""
                class MyModel:
                    pass

                class MyUserModel:
                    pass

                class Unused:
                    pass

                class ThisClassShouldBeIgnored:
                    pass
                """
    }
    # unused_names = main(["ignore_names_by_pattern.py", "--no-color", "--ignore-names=\\w*Model,.*[Ii]{1}gnore.*"])

    # When
    unused_names = main(['ignore_names_by_pattern.py', '--no-color', '--ignore-names=*Model,*[Ii]gnore*'])

    # Then
    assert unused_names == ('ignore_names_by_pattern.py:7:0: DC03 Class `Unused` is never used')


def test_ignore_names_uses_glob_not_regexp(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'ignore_names_by_pattern.py': b"""
                class MyModel:
                    pass

                class MyUserModel:
                    pass

                class Unused:
                    pass

                class ThisClassShouldBeIgnored:
                    pass
                """
    }

    # When
    unused_names = main(['ignore_names_by_pattern.py', '--no-color', '--ignore-names=*Model,*Ignore*'])

    # Then
    assert unused_names == ('ignore_names_by_pattern.py:7:0: DC03 Class `Unused` is never used')

    # `.*Model` is a regexp, not a glob, so it must not match any class.

    # When
    all_unused_names = main(['ignore_names_by_pattern.py', '--no-color', '--ignore-names=.*Model'])

    # Then
    assert all_unused_names is not None
    assert all_unused_names.count('DC03') == 4
    for class_name in ('MyModel', 'MyUserModel', 'Unused', 'ThisClassShouldBeIgnored'):
        assert class_name in all_unused_names


def test_ignore_names_matched_exactly(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'ignore_names_by_pattern.py': b"""
                class MyModel:
                    pass

                class MyUserModel:
                    pass

                class Unused:
                    pass

                class ThisClassShouldBeIgnored:
                    pass
                """
    }

    # When
    unused_names = main(
        ['ignore_names_by_pattern.py', '--no-color', '--ignore-names=MyModel,MyUserModel,ThisClassShouldBeIgnored']
    )

    # Then
    assert unused_names == ('ignore_names_by_pattern.py:7:0: DC03 Class `Unused` is never used')
