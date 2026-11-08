"""
Test method def.
"""

from deadcode.cli import main


def test_method(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                class MyTest:
                    def some_method(self):
                        pass

                instance = MyTest()
                print(instance)
                """
    }

    main(['foo.py', '--no-color', '--fix'])

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
            class MyTest:
                pass

            instance = MyTest()
            print(instance)
        """
        }
    )


def test_method_at_the_end_of_file(virtual_file_system):
    virtual_file_system.files = {
        'bar.py': b"""
                class MyTest:
                    def some_method(self):
                        pass
                """,
        'foo.py': b"""
                from foo import MyTest

                instance = MyTest()
                print(instance)
                """,
    }

    main(['foo.py', '--no-color', '--fix'])

    virtual_file_system.assert_files(
        {
            'bar.py': b"""
            class MyTest:
                pass
            """,
            'foo.py': b"""
                from foo import MyTest

                instance = MyTest()
                print(instance)
            """,
        }
    )
