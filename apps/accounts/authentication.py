from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied


class CSRFSessionAuthentication(SessionAuthentication):
    def authenticate(self, request):
        # Anonymous login/register requests also require a valid CSRF token.
        try:
            self.enforce_csrf(request)
        except PermissionDenied:
            raise PermissionDenied('Refresh the page and try again.', code='csrf_failed')
        return super().authenticate(request)
