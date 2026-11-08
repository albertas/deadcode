from deadcode.cli import main


def test_ignore_names_matched_by_word_and_group_regexp_patterns(virtual_file_system):
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
    unused_names = main(['ignore_names_by_pattern.py', '--no-color', '--ignore-names=*Model,*[Ii]gnore*'])

    assert unused_names == ('ignore_names_by_pattern.py:7:0: DC03 Class `Unused` is never used')


def test_ignore_names_matched_by_dot_regexp_pattern(virtual_file_system):
    # TODO: README has to be updated to not use .*, use * instead.
    # TODO: Ignoring does not work as expected: wild cards have to be used.

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
    unused_names = main(['ignore_names_by_pattern.py', '--no-color', '--ignore-names=*Model,*Ignore*'])

    assert unused_names == ('ignore_names_by_pattern.py:7:0: DC03 Class `Unused` is never used')


def test_ignore_names_matched_exactly(virtual_file_system):
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
    unused_names = main(
        ['ignore_names_by_pattern.py', '--no-color', '--ignore-names=MyModel,MyUserModel,ThisClassShouldBeIgnored']
    )

    assert unused_names == ('ignore_names_by_pattern.py:7:0: DC03 Class `Unused` is never used')
