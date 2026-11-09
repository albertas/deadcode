from django.urls import path

from . import views

app_name = 'django_example'

urlpatterns = [
    path('', views.index, name='index'),
    path('articles/', views.ArticleListView.as_view(), name='articles'),
]

UNUSED_URL_NAME = 'unused'
