from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class TestIgnoreDefinitionIfInheritsFrom(BaseTestCase):
    def test_ignore_class_definition_if_inherits_from_base_class(self):
        self.files = {
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

        output = main(['ignore_names_by_pattern.py', '--no-color', '--ignore-bodies-if-inherits-from=Base', '--fix'])

        self.assertFiles(
            {
                'foo.py': b"""
                class Base:
                    pass
                """
            }
        )

        self.assertEqual(
            output,
            'foo.py:5:0: DC03 Class `UnusedClass` is never used\n'
            'foo.py:15:0: DC03 Class `AnotherUnusedClass` is never used\n'
            'foo.py:16:4: DC01 Variable `another_unused_attribute` is never used\n'
            '\n'
            'Removed 3 unused code items!',
        )

    def test_ignore_class_body_if_inherits_from_dotted_base_class(self):
        self.files = {
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

        output = main(
            [
                'ignore_names_by_pattern.py',
                '--no-color',
                '--ignore-bodies-if-inherits-from=graphene.ObjectType',
                '--fix',
            ]
        )

        self.assertFiles({'foo.py': b'\nimport graphene\n'})

        self.assertEqual(
            output,
            'foo.py:4:0: DC03 Class `UnusedQuery` is never used\n'
            'foo.py:11:0: DC03 Class `AnotherUnusedClass` is never used\n'
            'foo.py:12:4: DC01 Variable `another_unused_attribute` is never used\n'
            '\n'
            'Removed 3 unused code items!',
        )

    def test_ignore_class_body_if_inherits_from_final_base_class_component(self):
        self.files = {
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

        output = main(
            ['ignore_names_by_pattern.py', '--no-color', '--ignore-bodies-if-inherits-from=ObjectType', '--fix']
        )

        self.assertFiles({'foo.py': b'\nimport graphene\n'})

        self.assertEqual(
            output,
            'foo.py:4:0: DC03 Class `UnusedQuery` is never used\n'
            'foo.py:11:0: DC03 Class `AnotherUnusedClass` is never used\n'
            'foo.py:12:4: DC01 Variable `another_unused_attribute` is never used\n'
            '\n'
            'Removed 3 unused code items!',
        )

    def test_ignore_class_body_if_inherits_from_glob_base_class(self):
        self.files = {
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

        output = main(
            ['ignore_names_by_pattern.py', '--no-color', '--ignore-bodies-if-inherits-from=*.ObjectType', '--fix']
        )

        self.assertFiles({'foo.py': b'\nimport graphene\n'})

        self.assertEqual(
            output,
            'foo.py:4:0: DC03 Class `UnusedQuery` is never used\n'
            'foo.py:11:0: DC03 Class `AnotherUnusedClass` is never used\n'
            'foo.py:12:4: DC01 Variable `another_unused_attribute` is never used\n'
            '\n'
            'Removed 3 unused code items!',
        )
