from datetime import datetime, time, timedelta, date
from django.utils import timezone
from rest_framework.exceptions import ValidationError


def date_filter(queryset, params, field='created_at'):
    bounds = {}
    for key, suffix in [('date_from', '__gte'), ('date_to', '__lt')]:
        if params.get(key):
            try:
                day = date.fromisoformat(params[key])
                if key == 'date_to':
                    day += timedelta(days=1)
                bounds[field + suffix] = timezone.make_aware(datetime.combine(day, time.min))
            except (ValueError, OverflowError):
                raise ValidationError({key: 'Use YYYY-MM-DD.'})
    return queryset.filter(**bounds)
