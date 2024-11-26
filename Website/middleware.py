from django.utils.deprecation import MiddlewareMixin

class SkipLoginForAPI(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith('/api/'):
            request.user = None

class DisableCSRFForAPI(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith('/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)