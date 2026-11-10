from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Import article data from a file.'

    def add_arguments(self, parser):
        parser.add_argument('path')

    def handle(self, *args, **options: object):
        pass


class UnusedCommand(BaseCommand):
    def handle(self, *args, **options: object):
        pass
