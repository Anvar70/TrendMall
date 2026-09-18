from urllib.parse import urlencode
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.utils.translation import get_language
from apps.core.i18n import dictionary

CUSTOMER_PAGES = ['home', 'catalog', 'favorites', 'cart', 'orders', 'messages', 'notifications', 'addresses', 'profile', 'settings']
ADMIN_PAGES = ['dashboard', 'products', 'categories', 'variants', 'inventory', 'orders', 'customers', 'messages', 'notifications', 'settings']


def page(request, section='guest', name='landing', **kwargs):
    user = request.user
    if section == 'guest' and user.is_authenticated:
        return redirect('/admin/dashboard/' if user.role == 'ADMIN' else '/shop/')
    if section != 'guest':
        if not user.is_authenticated:
            target = '/admin/login/' if section == 'admin_panel' else '/login/'
            return redirect(target + '?' + urlencode({'next': request.get_full_path()}))
        if section == 'admin_panel' and user.role != 'ADMIN':
            return render(request, 'errors/403.html', status=403)
        if section == 'customer' and user.role == 'ADMIN':
            return redirect('/admin/dashboard/')
    nav = []
    for item in CUSTOMER_PAGES if section == 'customer' else ADMIN_PAGES if section == 'admin_panel' else []:
        nav.append({'key': item, 'url': '/shop/' + ('' if item == 'home' else item + '/') if section == 'customer' else '/admin/' + item + '/'})
    return render(request, section + '/' + name + '.html', {'section': section, 'page': name, 'navigation': nav, 'route_params': kwargs})


def translations(request):
    return JsonResponse(dictionary(get_language()))


@require_POST
def language(request):
    selected = request.POST.get('language', 'uz')
    if selected not in ('uz', 'ru', 'en'):
        selected = 'uz'
    target = request.POST.get('next', '/')
    from django.utils.http import url_has_allowed_host_and_scheme
    if not url_has_allowed_host_and_scheme(target, {request.get_host()}, require_https=request.is_secure()):
        target = '/'
    response = redirect(target)
    response.set_cookie('django_language', selected, max_age=31536000, samesite='Lax')
    if request.user.is_authenticated:
        request.user.preferred_language = selected
        request.user.save(update_fields=['preferred_language'])
    return response


def error403(request, exception=None):
    return render(request, 'errors/403.html', status=403)


def error404(request, exception=None):
    return render(request, 'errors/404.html', status=404)


def error500(request):
    return render(request, 'errors/500.html', status=500)
