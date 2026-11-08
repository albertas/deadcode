"""
Test unused property fix.
"""

from deadcode.cli import main


def test_unused_property_is_removed(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                class Foo:
                    @property
                    def bar(self):
                        return 1

                instance = Foo()
                print(instance)
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])
    assert unused_names == 'foo.py:3:4: DC08 Property `bar` is never used\n\nRemoved 1 unused code item!'

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                class Foo:
                    pass

                instance = Foo()
                print(instance)
                """
        }
    )
