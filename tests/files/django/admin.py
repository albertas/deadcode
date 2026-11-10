from django.contrib import admin

from .forms import ArticleForm
from .models import Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    form = ArticleForm
    list_display = ('title', 'published')
    search_fields = ('title',)
    list_filter = ('published',)
    actions = ('mark_featured',)

    def mark_featured(self, request, queryset):
        queryset.update(featured=True)


class UnusedAdmin(admin.ModelAdmin):
    list_display = ('title',)
