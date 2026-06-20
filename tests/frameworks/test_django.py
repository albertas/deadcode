from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class TestDjangoModels(BaseTestCase):
    def test_models_suppressed_unused_helper_still_reported(self):
        self.files = {
            'models.py': """
                from django.db import models


                class Article(models.Model):
                    title = models.CharField(max_length=200)
                    body = models.TextField()


                def _unused_helper():
                    return 42
                """
        }

        output = main(
            [
                'models.py',
                '--no-color',
                '--ignore-definitions-if-inherits-from=models.Model',
                '--ignore-bodies-if-inherits-from=models.Model',
            ]
        )

        self.assertEqual(output, 'models.py:9:0: DC02 Function `_unused_helper` is never used')


class TestDjangoViews(BaseTestCase):
    def test_function_views_referenced_in_urlconf_used_unused_view_reported(self):
        self.files = {
            'views.py': """
                from django.shortcuts import render


                def index(request):
                    return render(request, "index.html")


                def detail(request, pk):
                    return render(request, "detail.html")


                def _orphan_view(request):
                    return render(request, "orphan.html")
                """,
            'urls.py': """
                from django.urls import path

                from . import views


                urlpatterns = [
                    path("", views.index),
                    path("<int:pk>/", views.detail),
                ]
                """,
        }

        output = main(
            [
                'views.py',
                'urls.py',
                '--no-color',
                '--ignore-names=urlpatterns',
            ]
        )

        self.assertEqual(output, 'views.py:12:0: DC02 Function `_orphan_view` is never used')

    def test_class_based_view_suppressed_via_inherits_from(self):
        self.files = {
            'views.py': """
                from django.views.generic import ListView

                from .models import Article


                class ArticleList(ListView):
                    model = Article
                    template_name = "article_list.html"


                UNUSED_CONSTANT = 1
                """
        }

        output = main(
            [
                'views.py',
                '--no-color',
                '--ignore-definitions-if-inherits-from=ListView',
                '--ignore-bodies-if-inherits-from=ListView',
            ]
        )

        self.assertEqual(output, 'views.py:11:0: DC01 Variable `UNUSED_CONSTANT` is never used')


class TestDjangoAdmin(BaseTestCase):
    def test_admin_register_decorator_suppressed(self):
        self.files = {
            'admin.py': """
                from django.contrib import admin

                from .models import Article


                @admin.register(Article)
                class ArticleAdmin(admin.ModelAdmin):
                    list_display = ("title",)


                def _unused_helper():
                    return None
                """
        }

        output = main(
            [
                'admin.py',
                '--no-color',
                '--ignore-definitions-if-decorated-with=@admin.register*',
            ]
        )

        self.assertEqual(output, 'admin.py:11:0: DC02 Function `_unused_helper` is never used')

    def test_modeladmin_inherits_from_suppressed(self):
        self.files = {
            'admin.py': """
                from django.contrib import admin

                from .models import Article


                class ArticleAdmin(admin.ModelAdmin):
                    model = Article
                    list_display = ("title",)


                UNUSED_CONSTANT = 1
                """
        }

        output = main(
            [
                'admin.py',
                '--no-color',
                '--ignore-definitions-if-inherits-from=admin.ModelAdmin',
                '--ignore-bodies-if-inherits-from=admin.ModelAdmin',
            ]
        )

        self.assertEqual(output, 'admin.py:11:0: DC01 Variable `UNUSED_CONSTANT` is never used')


class TestDjangoSignals(BaseTestCase):
    def test_receiver_decorator_suppressed(self):
        self.files = {
            'signals.py': """
                from django.db.models.signals import post_save
                from django.dispatch import receiver

                from .models import Article


                @receiver(post_save, sender=Article)
                def update_cache(sender, instance, **kwargs):
                    instance.cache_key = "x"


                def _unused_helper():
                    return None
                """
        }

        output = main(
            [
                'signals.py',
                '--no-color',
                '--ignore-definitions-if-decorated-with=@receiver*',
            ]
        )

        self.assertEqual(output, 'signals.py:12:0: DC02 Function `_unused_helper` is never used')


class TestDjangoManagementCommands(BaseTestCase):
    def test_basecommand_suppressed_unused_helper_reported(self):
        self.files = {
            'import_data.py': """
                from django.core.management.base import BaseCommand


                class Command(BaseCommand):
                    help = "Imports data"

                    def add_arguments(self, parser):
                        parser.add_argument("path")

                    def handle(self, *args, **options):
                        self.stdout.write("done")


                def _unused_helper():
                    return None
                """
        }

        output = main(
            [
                'import_data.py',
                '--no-color',
                '--ignore-definitions-if-inherits-from=BaseCommand',
                '--ignore-bodies-if-inherits-from=BaseCommand',
            ]
        )

        self.assertEqual(output, 'import_data.py:14:0: DC02 Function `_unused_helper` is never used')


class TestDjangoAppConfigs(BaseTestCase):
    def test_appconfig_suppressed_unused_constant_reported(self):
        self.files = {
            'apps.py': """
                from django.apps import AppConfig


                class BlogConfig(AppConfig):
                    default_auto_field = "django.db.models.BigAutoField"
                    name = "blog"

                    def ready(self):
                        pass


                UNUSED_CONSTANT = 1
                """
        }

        output = main(
            [
                'apps.py',
                '--no-color',
                '--ignore-definitions-if-inherits-from=AppConfig',
                '--ignore-bodies-if-inherits-from=AppConfig',
            ]
        )

        self.assertEqual(output, 'apps.py:12:0: DC01 Variable `UNUSED_CONSTANT` is never used')


class TestDjangoSettings(BaseTestCase):
    def test_settings_constants_suppressed_via_ignore_names_in_files(self):
        self.files = {
            'settings.py': """
                DEBUG = True
                INSTALLED_APPS = [
                    "django.contrib.admin",
                    "blog",
                ]
                SECRET_KEY = "x"
                ALLOWED_HOSTS = ["*"]
                """,
            'service.py': """
                def _genuinely_unused():
                    return None
                """,
        }

        output = main(
            [
                'settings.py',
                'service.py',
                '--no-color',
                '--ignore-names-in-files=*settings*',
            ]
        )

        self.assertEqual(output, 'service.py:1:0: DC02 Function `_genuinely_unused` is never used')
