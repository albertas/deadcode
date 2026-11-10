from django.db import models

from .managers import ArticleManager


class Category(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


class Article(models.Model):  # noqa: DJ008
    title = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='articles')
    published = models.BooleanField(default=False)

    objects = ArticleManager()

    class Meta:
        ordering = ['title']

    @property
    def display_name(self):
        return self.title

    @property
    def published_titles(self):
        return list(Article.objects.published_articles().values_list('title', flat=True))


class UnusedModel(models.Model):  # noqa: DJ008
    value = models.IntegerField()
