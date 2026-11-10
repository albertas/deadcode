from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Article


@receiver(post_save, sender=Article)
def article_saved(sender, instance, **kwargs: object):
    pass


def article_saved_direct(sender, instance, **kwargs: object):
    pass


post_save.connect(article_saved_direct, sender=Article)


def unused_signal_handler(sender, **kwargs: object):
    pass
