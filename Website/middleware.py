from django.utils.deprecation import MiddlewareMixin

import logging
logger = logging.getLogger(__name__)

class DisableCSRFForAPI:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Désactiver la vérification CSRF pour les URLs commençant par "/api/"
        if request.path.startswith('/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)
        return self.get_response(request)


class SkipLoginForAPI:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Ignorer l'utilisateur pour les URLs commençant par "/api/"
        if request.path.startswith('/api/'):
            request.user = None
        return self.get_response(request)

