from deadcode.cli import main


def test_absolute_import_forms_resolve_inherited_models(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                from django.db import models
                from django.db.models import Model
                import django.db.models as m
                import django.db.models
                from django.db.models import Model as M
                from django.db.models import *


                class A(models.Model):
                    pass


                class B(Model):
                    pass


                class C(m.Model):
                    pass


                class D(M):
                    pass


                class E(django.db.models.Model):
                    pass


                class W(Model):
                    pass


                def unused_sentinel():
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-definitions-if-inherits-from=django.db.models.Model'])

    # Then
    assert unused_names == 'foo.py:33:0: DC02 Function `unused_sentinel` is never used'


def test_absolute_import_forms_resolve_decorators(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                from django.contrib import admin
                from django.contrib.admin import register
                from django.dispatch import receiver


                @admin.register
                class AdminA:
                    pass


                @register
                class AdminB:
                    pass


                @receiver
                def receiver_handler(sender, **kwargs):
                    pass


                def unused_sentinel():
                    pass
                """
    }

    # When
    unused_names = main(
        [
            'foo.py',
            '--no-color',
            '--ignore-definitions-if-decorated-with=@django.contrib.admin.register,@django.dispatch.receiver',
        ]
    )

    # Then
    assert unused_names == 'foo.py:21:0: DC02 Function `unused_sentinel` is never used'


def test_relative_import_keeps_bare_source_candidate(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                from .models import Model
                from . import Model as RelativeModel


                class LocalModel(Model):
                    pass


                class AnotherLocalModel(RelativeModel):
                    pass


                def unused_sentinel():
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-definitions-if-inherits-from=Model'])

    # Then
    assert unused_names == (
        'foo.py:9:0: DC03 Class `AnotherLocalModel` is never used\n'
        'foo.py:13:0: DC02 Function `unused_sentinel` is never used'
    )


def test_relative_import_is_not_resolved_to_a_qualified_name(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                from .models import Model


                class LocalModel(Model):
                    pass


                def unused_sentinel():
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-definitions-if-inherits-from=django.db.models.Model'])

    # Then
    assert unused_names == (
        'foo.py:4:0: DC03 Class `LocalModel` is never used\n'
        'foo.py:8:0: DC02 Function `unused_sentinel` is never used'
    )
