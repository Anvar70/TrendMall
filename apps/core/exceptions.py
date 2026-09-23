from django.http import JsonResponse
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler
from django.utils.translation import get_language
from .i18n import dictionary


def localized(detail, field=''):
    if isinstance(detail, dict):
        return {key: localized(value, key) for key, value in detail.items()}
    if isinstance(detail, list):
        return [localized(value, field) for value in detail]
    words = dictionary(get_language())
    message = str(detail).lower()
    code = getattr(detail, 'code', 'invalid')
    if 'cannot be submitted' in message or 'cannot be changed' in message or 'cannot be moved' in message:
        code = 'field_protected'
    elif 'translation' in message:
        code = 'translation_required'
    elif 'already' in message or 'unique' in message:
        code = 'unique'
    elif 'passwords do not match' in message:
        code = 'password_mismatch'
    elif field in ('password', 'new_password'):
        code = 'password_invalid'
    elif field == 'old_password':
        code = 'invalid_credentials'
    elif field == 'phone':
        code = 'phone_invalid'
    elif field in ('image', 'avatar', 'logo'):
        code = 'image_invalid'
    elif code in ('blank', 'null', 'required'):
        code = 'required'
    elif code in ('max_length', 'min_length'):
        code = 'length_invalid'
    elif code in ('min_value', 'max_value', 'max_digits', 'max_decimal_places'):
        code = 'number_invalid'
    return words.get(code, words['invalid'])


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
            words = dictionary(get_language())
            message_key = code
            message = str(detail).lower()
            if 'cart is empty' in message:
                message_key = 'empty_cart'
            elif 'unavailable' in message or 'quantity is not available' in message or 'insufficient stock' in message:
                message_key = 'unavailable_stock'
            elif 'preview' in message or 'quote' in message:
                message_key = 'quote_changed'
            elif 'history' in message and 'archive' in message:
                message_key = 'archive_required'
            response.data = {'code': code, 'message': words.get(message_key, words['error'])}
        else:
            response.data = {'code': 'validation_error', 'message': dictionary(get_language())['validation_error'], 'field_errors': localized(original)}
    return response


def csrf_failure(request, reason=''):
    return JsonResponse({'code': 'csrf_failed', 'message': dictionary(get_language())['csrf_failed']}, status=403)
