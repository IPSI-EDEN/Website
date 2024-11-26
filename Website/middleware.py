from django.utils.deprecation import MiddlewareMixin

import logging
logger = logging.getLogger(__name__)

class DisableCSRFForAPI(MiddlewareMixin):
    def __init__(self, get_response=None):
        self.get_response = get_response
        logger.info("DisableCSRFForAPI chargé")
        print("DisableCSRFForAPI chargé")

    def process_request(self, request):
        if request.path.startswith('/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)


class SkipLoginForAPI(MiddlewareMixin):
    def __init__(self, get_response=None):
        self.get_response = get_response
        print("SkipLoginForAPI chargé")

    def process_request(self, request):
        if request.path.startswith('/api/'):
            request.user = None
