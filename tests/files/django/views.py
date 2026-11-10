from django.http import HttpResponse
from django.views import View
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.views.generic import DetailView, ListView

UNUSED_VIEW_SETTING = 'unused'


def index(request):
    return HttpResponse('ok')


def unused_view(request):
    return HttpResponse('unused')


@require_GET
def article_list(request):
    return HttpResponse('articles')


@require_POST
def article_create(request):
    return HttpResponse('created')


@require_http_methods(['PUT'])
def article_update(request):
    return HttpResponse('updated')


@require_GET
def unreferenced_require_view(request):
    return HttpResponse('helper')


class ArticleListView(ListView):
    def get(self, request):
        return HttpResponse('articles')


class ArticleDetailView(DetailView):
    def get(self, request):
        return HttpResponse('article')


class ArticleView(View):
    def get(self, request):
        return HttpResponse('article')


class UnusedView(View):
    def get(self, request):
        return HttpResponse('unused')
