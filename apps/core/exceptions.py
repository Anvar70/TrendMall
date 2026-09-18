from django.http import JsonResponse
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class Conflict(APIException):
    status_code = 409
    default_detail = 'The resource has changed. Please refresh and try again.'
    default_code = 'conflict'


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        original = response.data
        code = getattr(exc, 'default_code', 'error')
        if isinstance(original, dict) and 'detail' in original:
            detail = original['detail']
            code = getattr(detail, 'code', code)
            response.data = {'code': code, 'message': str(detail)}
        else:
            response.data = {'code': 'validation_error', 'message': 'Check the submitted fields.', 'field_errors': original}
    return response


def csrf_failure(request, reason=''):
    return JsonResponse({'code': 'csrf_failed', 'message': 'Refresh the page and try again.'}, status=403)
