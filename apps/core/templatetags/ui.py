from django import template
from django.utils.translation import get_language
from apps.core.i18n import dictionary
register = template.Library()

@register.simple_tag
def tr(key):
    return dictionary(get_language()).get(key, key)
