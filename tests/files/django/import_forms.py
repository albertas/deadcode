from django import forms
from django.contrib import admin
from django.contrib.admin import register
from django.db import models
from django.db.models import Model
from django.db.models.signals import post_save
from django.dispatch import receiver


class ImportedModel(Model):  # noqa: DJ008
    title = models.CharField(max_length=100)


class QualifiedModel(models.Model):  # noqa: DJ008
    title = models.CharField(max_length=100)


class ImportedForm(forms.Form):
    title = forms.CharField(max_length=100)


@admin.register(ImportedModel)
class QualifiedAdmin(admin.ModelAdmin):
    pass


@register(ImportedModel)
class BareAdmin(admin.ModelAdmin):
    pass


@receiver(post_save)
def imported_receiver(sender, **kwargs: object):
    pass
