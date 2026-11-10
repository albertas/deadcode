from rest_framework import serializers, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Article


class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ['id', 'title', 'published']


class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        return Response({'status': 'published'})

    def list(self, request):
        return Response([])

    def create(self, request):
        return Response({})

    def retrieve(self, request):
        return Response({})

    def update(self, request):
        return Response({})

    def destroy(self, request):
        return Response({})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def article_stats(request):
    return Response({'articles': Article.objects.count()})


def unused_api_helper(request):
    return Response({})
