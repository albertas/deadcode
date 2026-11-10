from django.test import TestCase

from .models import Article


class ArticleTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.article = Article.objects.create(title='Example')

    def _pre_setup(self):
        pass

    def _post_teardown(self):
        pass

    def _fixture_setup(self):
        pass

    def _fixture_teardown(self):
        pass

    def test_article(self):
        assert self.article.title == 'Example'

    def unused_test_helper(self):
        return None
