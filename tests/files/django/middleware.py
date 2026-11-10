from django.utils.deprecation import MiddlewareMixin


def simple_middleware(get_response):
    def middleware(request):
        return get_response(request)

    return middleware


class CurrentMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)


class SimpleMiddleware(MiddlewareMixin):
    def process_request(self, request):
        return None
