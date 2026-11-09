from django.http import HttpResponse
from django.views import View

UNUSED_VIEW_SETTING = 'unused'


def index(request):
    return HttpResponse('ok')


def unused_view(request):
    return HttpResponse('unused')


class ArticleListView(View):
    def get(self, request):
        return HttpResponse('articles')


class UnusedView(View):
    def get(self, request):
        return HttpResponse('unused')
