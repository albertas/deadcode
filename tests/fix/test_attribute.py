"""
Test unused attribute fix.
"""

import ast

from deadcode.cli import main


def test_unused_attribute_is_removed(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                class Foo:
                    def __init__(self):
                        self.bar = 1

                instance = Foo()
                print(instance)
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])
    assert unused_names == 'foo.py:3:8: DC05 Attribute `bar` is never used\n\nRemoved 1 unused code item!'

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                class Foo:
                    def __init__(self):
                        pass

                instance = Foo()
                print(instance)
                """
        }
    )

    fixed_content = virtual_file_system.updated_files['foo.py']
    ast.parse(fixed_content)
