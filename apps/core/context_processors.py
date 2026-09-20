from django.db.utils import OperationalError, ProgrammingError
from .models import StoreSettings


def store_context(request):
    try:
        store = StoreSettings.load()
        language = getattr(request, 'LANGUAGE_CODE', 'uz')
        return {'store': store, 'landing_text': getattr(store, 'landing_' + language, '') or store.landing_uz}
    except (OperationalError, ProgrammingError):
        return {'store': None, 'landing_text': ''}

