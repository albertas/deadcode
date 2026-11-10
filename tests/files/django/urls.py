from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views
from .api import ArticleViewSet

app_name = 'django_example'

router = DefaultRouter()
router.register(r'articles', ArticleViewSet, basename='article')

urlpatterns = [
    path('', views.index, name='index'),
    path('articles/', views.article_list, name='article-list'),
    path('articles/create/', views.article_create, name='article-create'),
    path('articles/<int:pk>/update/', views.article_update, name='article-update'),
    path('articles/view/', views.ArticleView.as_view(), name='article-view'),
    path('api/', include(router.urls)),
]

UNUSED_URL_NAME = 'unused'
