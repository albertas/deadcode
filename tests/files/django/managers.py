from django.db import models


class ArticleQuerySet(models.QuerySet):
    def published(self):
        return self.filter(published=True)


class ArticleManager(models.Manager.from_queryset(ArticleQuerySet)):
    def published_articles(self):
        return self.published()

    def unused_manager_method(self):
        return self.none()
